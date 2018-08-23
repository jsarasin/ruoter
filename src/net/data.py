class TracerouteHop:
    def __init__(self, address, ttl, send_time, recv_time, ack):
        self.address = address
        self.ttl = ttl
        self.send_time = send_time
        self.recv_time = recv_time
        self.ack = ack


class TracerouteResult:
    def __init__(self, target, hop_results):
        self.target = target
        self.send_time = None
        self.hops = []

        for hop in hop_results:
            self.hops.append(TracerouteHop())
