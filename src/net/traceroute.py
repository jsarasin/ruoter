from random import randint
import scapy.all
import time

class TraceRouteNode:
    def __init__(self, ttl, ip):
        self.ttl = ttl
        if ip == "*":
            self.ip = ip + str(ttl)
        else:
            self.ip = ip

    def resolve_hostname(self):
        pass

    def resolve_asn(self):
        pass

    def find_device_type(self):
        pass


class TraceRoute:
    def __init__(self, target):
        self.target = target
        self.nodes = []
        self.hops = []

    def start_traceroute(self, target):
        self.target = target
        answers = []

        for n in range(9):
            scapy.
            ans, unans = sr(IP(dst=target, ttl=n,id=RandShort())/TCP(flags=0x2))
            answers = answers + [ans]

        # time.sleep(1)


    def run_test(self):
        def randomIP():
            random_ip = ""
            random_ip = random_ip + str(randint(1, 253)) + "."
            random_ip = random_ip + str(randint(1, 253)) + "."
            random_ip = random_ip + str(randint(1, 253)) + "."
            random_ip = random_ip + str(randint(1, 253))
            return random_ip

        self.register_hop_response(0, "192.168.0.1")
        for i in range(3):
            self.register_hop_response(i+1, "192.168.0.1")
        self.register_hop_response(i+2, self.target)



        self.nodes = self.nodes + [TraceRouteNode(0, "192.168.0.1")]
        for i in range(3):
            self.nodes = self.nodes + [TraceRouteNode(i+1, randomIP())]

        self.nodes = self.nodes + [TraceRouteNode(i+2, self.target)]

    def register_hop_response(self, ttl, ip):
        pass
#        if ip not in [n for n in self.nodes[]]
