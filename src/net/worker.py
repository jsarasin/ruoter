from multiprocessing import Process, Pipe
from scapy.all import *
import time
import sys

from net.data import *

def worker(pipe_connection):
    running = True

    while(running):
        sys.stdout.flush()
        message = pipe_connection.recv()
        if message[0] == "DIE":
            running = False

        if message[0] == "TCPSYN":
            tcpsyn(message[1:], pipe_connection)
        time.sleep(0.1)




def tcpsyn(message, pipe_connection):

    target = message[0]
    ttl = message[1]
    sent_time = time.time()
    ans, unans = sr(IP(dst=target, ttl=ttl, id=RandShort()) / TCP(flags=0x2), timeout=3,verbose=0)
    recv_time = time.time()

    if len(ans) == 1:
        result = TracerouteHop(ans[0][1].src, ttl, sent_time, recv_time, ans[0][1][1])

        pipe_connection.send(result)

    if len(unans) == 1:
        pipe_connection.send("No trc")