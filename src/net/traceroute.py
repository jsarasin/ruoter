from random import randint

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

        self.run_test()

    def run_traceroute(self):
        self.nodes.append(TraceRouteNode(2, "65.94.12.6"))
        self.nodes.append(TraceRouteNode(3, "65.94.12.6"))
        pass

    def run_test(self):
        def randomIP():
            random_ip = ""
            random_ip = random_ip + str(randint(1, 253)) + "."
            random_ip = random_ip + str(randint(1, 253)) + "."
            random_ip = random_ip + str(randint(1, 253)) + "."
            random_ip = random_ip + str(randint(1, 253))
            return random_ip

        for i in range(4):
            self.nodes.append(TraceRouteNode(i, randomIP()))

        self.target = self.nodes[-1].ip
