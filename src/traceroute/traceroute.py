from snapins.snapin import Snapin

from scapy.all import *
import scapy.layers.inet

class ResponseType:
    TIMEOUT = 0
    ICMP_TTL_EXCEEDED = 1
    ICMP_PORT_UNREACH = 2

class RequestType:
    UDP_SYN = 0 # First traceroute discovery. There will be multiple of these sent out at the same time.
    TCP_SYN_SEQUENTIAL = 1     # Fallback, initialize connection to tcp/80
    ICMP_ECHO = 2   # Vanilla Echo


class MultiTraceroute:
    def __init__(self, targets):
        self.requests = {}
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=15)


    def register_request(self, request_type, ip_id, target, ttl):
        if ip_id in self.requests:
            print("Registered a second request for the same ip.id")
            return

        self.requests[ip_id] = (request_type, target, ttl)

    def register_response(self, response):
        request = self.requests[response['request_id']]

        if response['type'] == ResponseType.TIMEOUT:
            assert(request[1] == response['target'])
            assert(request[2] == response['ttl'])

        if response['type'] == ResponseType.ICMP_PORT_UNREACH:
            assert(request[1] == response['target'])
            assert(request[2] == response['ttl'])

        if response['type'] == ResponseType.ICMP_TTL_EXCEEDED:
            assert(request[1] == response['target'])
            assert(request[2] == response['ttl'])

    # cat = getaddrinfo("microsoft.com", None, AddressFamily.AF_INET, SocketKind.SOCK_STREAM)


    def start_traceroute(self, addresses):
        custom_id = random.randint(1000, 20000)

        for ttl in range(1,20):
            custom_id = custom_id + 1
            for address in addresses:
                custom_id = custom_id + 1
                future = self.executor.submit(SnapInTraceroutePing.worker_tcpsyn, address, ttl, custom_id)
                future.add_done_callback(self.worker_tcpsyn_complete_callback)
                self.host_tracker.register_request(RequestType.UDP_SYN, custom_id, target, ttl)


    def register_hop(self, worker_data):
        if worker_data['unanswered']:
            host = "* -> " + worker_data['target']
        else:
            host = worker_data['host']

        if 'ttl' in worker_data:
            ttl = worker_data['ttl']
        else:
            ttl = 1

        if 'rtt' in worker_data:
            rtt = str(round(worker_data['rtt'] * 1000)) + "ms"
            worker_data['rtt'] = rtt
        else:
            rtt = None

        target = worker_data['target']

        self.hops[host] = dict()

        new_node = self.route_model.add_node(host)
        new_node.attributes.update(worker_data)
        new_node.posx = ((ttl) * 200) - 100
        new_node.posy = self.get_target_y(target)
        new_node.pixbuf = None
        new_node.presented = False
        self.visualizer.generate_node_animation(new_node)

        self.hops[host]['raw'] = worker_data
        self.hops[host]['ttl'] = ttl
        self.hops[host]['rtt'] = rtt
        self.hops[host]['node'] = new_node
        self.hops[host]['targets'] = [target]

        self.build_links(host, target, ttl, new_node)

    def build_links(self, host, target, ttl, new_node):
        last_hop = None
        for key in self.hops:
            if target in self.hops[key]['targets'] and (self.hops[key]['ttl'] == ttl - 1 or self.hops[key]['ttl'] == ttl + 1):
                self.hops[host]['previous'] = self.hops[key]
                self.hops[host]['previous_node'] = self.hops[key]['node']
                self.route_model.add_link(self.hops[key]['node'], new_node)



    @staticmethod
    def worker_tcpsyn(target, cttl, custom_id, include_raw=False):
        response = dict()
        sent_time = time.time()
        cork = 33434 + (cttl)

        myfilter = ""
        ddata = b"\x40\x41\x42\x43\x44\x45\x46\x47\x48\x49\x4a\x4b\x4c\x4d\x4e\x4f\x50\x51\x52\x53\x54\x55\x56\x57\x58\x59\x5a\x5b\x5c\x5d\x5e\x5f"
        answered, unanswered_sent = sr(IP(dst=target, ttl=(cttl), id=custom_id) / UDP(dport=cork) / Raw(ddata), verbose=False, timeout=10, filter=myfilter )

        recv_time = time.time()
        rtt = recv_time - sent_time


        if len(unanswered_sent):
            response['target'] = target
            response['ttl'] = unanswered_sent[0].ttl
            response['type'] = ResponseType.TIMEOUT
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
                response['ttl'] = answered_received[2].ttl # answered_sent.ttl
                response['host'] = answered_received[0].src
                response['rtt'] = rtt
                response['request_id'] = answered_received[2].id
                response['type'] = ResponseType.ICMP_TTL_EXCEEDED
                return response
            elif answered_received[1].type == 3:
                # ICMP Destination Unreachable/Port Unreachable
                assert(answered_received[1].code == 3)
                response['target'] = target
                response['ttl'] = answered_received[2].ttl # answered_sent.ttl
                response['host'] = answered_received[0].src
                response['rtt'] = rtt
                response['request_id'] = answered_received[2].id
                response['type'] = ResponseType.ICMP_PORT_UNREACH
                return response
            else:
                print("Unhandled ICMP response type:", answered_received[1].type)
                return answered_received[1].summary()

        print("Unhandled response:\n", answered_received.show())
        return None

