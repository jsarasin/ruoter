from scapy.all import *
import scapy.layers.inet


class ExistingInstance(Exception):
    """Only one instance of MultiTraceroute is allowed to avoid other instances stealing eachothers replies."""


class TargetExists(Exception):
    """Can only run one traceroute on a single target at a time"""


class TracerouteException(Exception):
    """An unhandled error occured"""


class UnhandledNetworkResponse(Exception):
    """The traceroute engine received a response it was not expecting"""

    def __init__(self, message):
        self.message = message


class MultiTraceroute:
    INITIALIZED = False
    UDP_SYN_PORT_START = 33434
    MAX_WORKERS = 15
    START_IP_ID = 35454
    TIMEOUT = 15
    DefaultConfiguration = {
        'target': '1.1.1.1',
        'tr_freq': 500,
        'traceroute_type': MultiTraceroute._TracerouteFlags.ADAPTIVE,
        'start_immediately': False,
        'hop_check_count': 20,
    }

    # Private record keeping class
    class _TargetRequest:
        def __init__(self, address, callback, options):
            self.address = address
            self.callback = callback
            self.options = options
            self.running = False
            self.hops = []

    # Options to configure traceroute specifics
    class _TracerouteFlags:
        ADAPTIVE = 0xFF

    # Message passing of handled response types
    class _ResponseType:
        TIMEOUT = 0
        ICMP_TTL_EXCEEDED = 1
        ICMP_PORT_UNREACH = 2

    # Only allow and maintain one instance of this class
    def _initialize_singleton(self):
        if MultiTraceroute.INITIALIZED:
            raise ExistingInstance
        MultiTraceroute.INITIALIZED = self

        # TODO: Should create a temporary .lock file in a global location
        # instance they have multiple instances of the client running

    ######################################
    ## Beginning of the main class code ##
    ######################################
    def __init__(self, targets):
        self._initialize_singleton()

        self.target_requests = {}
        self.outstanding_packets = {}
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=MultiTraceroute.MAX_WORKERS)

    def new_target(self, target, callback, configuration=MultiTraceroute.DefaultConfiguration, start_now=False):
        # TODO: Verify configuration

        if target in self.target_requests:
            raise TargetExists

        self.target_requests[target] = MultiTraceroute._TargetRequest(target, callback, configuration)
        self.target_requests[target].hops = [HopStatus.]

        if start_now:
            self.start_traceroute(self.target_requests[target])

    # Dispatch the traceroute request to the correct initializer
    def start_traceroute(self, traceroute_request):
        if traceroute_request.configuration['traceroute_type'] == MultiTraceroute._TracerouteFlags.ADAPTIVE:
            self.start_adaptive_traceroute(traceroute_request)
        else:
            raise TracerouteException

    # Dispatch a single traceroute response to the correct handler
    def processed_finished_request(self, future):
        response = future.result()

        traceroute_target = self.target_requests[response['ip_id']]
        if traceroute_target.configuration['traceroute_type'] == MultiTraceroute._TracerouteFlags.ADAPTIVE:
            self.process_adaptive_response(traceroute_target, response)

    ############################################
    # Different implemantations of traceroute ##
    ############################################

    # The adaptive traceroute handler initializer
    def start_adaptive_traceroute(self, traceroute_request):
        hop_count = traceroute_request.configuration['hop_check_count']
        target = traceroute_request.configuration['target']
        for ttl in range(1, hop_count):
            MultiTraceroute.CURRENT_IP_ID = MultiTraceroute.CURRENT_IP_ID + 1

            # Register this new packet to this traceroute request
            self.outstanding_packets[MultiTraceroute.CURRENT_IP_ID] = traceroute_request

            # Create the job
            future = self.executor.submit(MultiTraceroute.worker_udpsyn, target, ttl,
                                          MultiTraceroute.CURRENT_IP_ID)
            future.add_done_callback(self.processed_finished_request)

    def process_adaptive_response(self, traceroute_target, response):
        hop_status = traceroute_target
        self.adaptive_scan_complete()

    # Look over all hops sent out in this traceroute. If there is a ICMP Destination
    # unreachable, or timeouts then try to establish a connection or PING response
    def adaptive_scan_complete(self):
        pass

    ##########################################################
    ## Blocking sending/receiving packets and response type ##
    ##########################################################
    # Response dict format
    # target := IpV4 | IpV6 address as a str
    # type := _ResponseType
    # raw_sent
    # raw_recv
    # ttl
    # ip_id = the id field in the returned ip header contained in the icmp message
    # rtt

    @staticmethod
    def worker_udpsyn(target, cttl, custom_id, include_raw=False):
        response = dict()
        sent_time = time.time()
        cork = MultiTraceroute.UDP_SYN_PORT_START + cttl + custom_id

        myfilter = ""
        DATA = b"\x40\x41\x42\x43\x44\x45\x46\x47\x48\x49\x4a\x4b\x4c\x4d\x4e\x4f\x50\x51\x52\x53\x54\x55\x56\x57\x58\x59\x5a\x5b\x5c\x5d\x5e\x5f"
        answered, unanswered_sent = sr(IP(dst=target, ttl=(cttl), id=custom_id) / UDP(dport=cork) / Raw(DATA),
                                       verbose=False, timeout=MultiTraceroute.TIMEOUT, filter=myfilter)

        recv_time = time.time()
        rtt = recv_time - sent_time  # TODO: This is wrong

        # Timeout Exceeded
        if len(unanswered_sent):
            response['target'] = target
            response['ttl'] = unanswered_sent[0].ttl
            response['ip_id'] = unanswered_sent[0].id
            response['type'] = MultiTraceroute._ResponseType.TIMEOUT
            if include_raw:
                response['raw_sent'] = unanswered_sent
                response['raw_recv'] = None
            return response

        answered_sent = answered[0][0]
        answered_received = answered[0][1]

        if include_raw:
            response['raw_sent'] = answered_sent
            response['raw_recv'] = answered_received

        if type(answered_received[1]) == scapy.layers.inet.ICMP:
            if answered_received[1].type == 11:
                # ICMP TTL Exceeded
                response['target'] = target
                response['ttl'] = answered_received[2].ttl  # answered_sent.ttl
                response['host'] = answered_received[0].src
                response['rtt'] = rtt
                response['request_id'] = answered_received[2].id
                response['type'] = MultiTraceroute._ResponseType.ICMP_TTL_EXCEEDED
                return response
            elif answered_received[1].type == 3:
                # ICMP Destination Unreachable/Port Unreachable
                assert (answered_received[1].code == 3)
                response['target'] = target
                response['ttl'] = answered_received[2].ttl  # answered_sent.ttl
                response['host'] = answered_received[0].src
                response['rtt'] = rtt
                response['request_id'] = answered_received[2].id
                response['type'] = MultiTraceroute._ResponseType.ICMP_PORT_UNREACH
                return response

        return UnhandledNetworkResponse(answered_received.show())





