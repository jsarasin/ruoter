# multiprocessing
from scapy.all import *
from multiprocessing import Process, Pipe
import time
from net.worker import worker
from net.data import *
import sys
class Traceroute:
    def __init__(self):
        pipes = Pipe(True)
        print(type(pipes))
        self.parent_conn = pipes[0]
        self.child_conn = pipes[1]

        self.p = Process(target=worker, args=(self.child_conn,))
        self.p.start()

    def start(self, target):
        message = [0,0,0]
        message[0] = "TCPSYN"
        message[1] = target
        for ttl in range(0, 30):
            message[2] = ttl
            self.parent_conn.send(message)
            print("send message")

    def check(self):
        sys.stdout.flush()
        messages = []

        while(self.parent_conn.poll()):
            print("a")
            recv = self.parent_conn.recv()
            if type(recv) == TracerouteHop:
                messages.append(recv)

        return messages




    def __del__(self):
        self.parent_conn.send("DIE")
        self.p.join()
        print("deleting")
