from time import time, sleep

from scapy.all import *
from multiprocessing import Process, Pipe, Lock

THREADING_VERBOSE = False


class SnapinWorker:
    def __init__(self):
        self.parent_pipe, self.worker_pipe = Pipe(True)
        self.process = Process(target=SnapinWorker.worker_dispatcher, args=(self.worker_pipe,))

    def start(self):
        self.process.start()

    @staticmethod
    def worker_dispatcher(my_pipe):
        dispatcher_verbose = True
        # This function will run until the program shuts down. It will check for
        # new messages sent to it, if there are not it will sleep(WAIT_TIME)
        # Message format:
        #   - New tasks: [Snapin.worker_request_id, completion_callback, task_function, data]
        #   - Shutdown: str("DIE")

        if THREADING_VERBOSE: print("spawning worker")

        WAIT_TIME = 0.1
        running = True

        while running:
            if THREADING_VERBOSE: sys.stdout.flush()
            if not my_pipe.poll():
                sleep(WAIT_TIME)
                if THREADING_VERBOSE: print("sleeping")
                if THREADING_VERBOSE: sys.stdout.flush()
                continue
            message = my_pipe.recv()
            # if THREADING_VERBOSE:
            sys.stdout.flush()

            if message == "DIE":
                running = False
                continue

            if THREADING_VERBOSE: print("dispatching new task")
            # Any other messages are treated as worker processes
            worker_request_id, completion_callback, worker_function, data = message

            result = worker_function(*data)

            if THREADING_VERBOSE: print("SENDING")
            my_pipe.send((worker_request_id, completion_callback, result, ))
            if THREADING_VERBOSE: print("Sent")

        if THREADING_VERBOSE: print("killing worker dispatcher")


class Snapin:
    WORKER_COUNT = 1
    thread_handler = None
    worker_request_id = 999
    lock_mem = Lock()
    monitor_run = True
    worker_pool = [None] * WORKER_COUNT
    next_available_worker = -1  # This is used for worker selection, should make a more sophisticated method. This will
                                # just cycle through them. Could look for one that actually has no tasks or the least.


    def __init__(self):
        if Snapin.thread_handler == None:
            # Spawn all the worker threads
            for index in range(0, Snapin.WORKER_COUNT):
                Snapin.worker_pool[index] = SnapinWorker()
                Snapin.worker_pool[index].start()

            # Spawn the monitoring thread
            Snapin.thread_handler = Process(target=Snapin.worker_monitor, args=("",))
            Snapin.thread_handler.start()

    @staticmethod
    def get_free_worker_pipe():
        Snapin.next_available_worker = Snapin.next_available_worker + 1
        if Snapin.next_available_worker >= Snapin.WORKER_COUNT:
            Snapin.next_available_worker = 0
        return Snapin.worker_pool[Snapin.next_available_worker].parent_pipe



    @staticmethod
    def submit_task(completion_callback, worker_function, data):
        with Snapin.lock_mem:
            if THREADING_VERBOSE: print("sending new task")
            Snapin.worker_request_id = Snapin.worker_request_id  + 1
            worker_pipe = Snapin.get_free_worker_pipe()
            worker_pipe.send((Snapin.worker_request_id, completion_callback, worker_function, data,))
            return Snapin.worker_request_id

        return None

    @staticmethod
    def worker_monitor(cat):
        while Snapin.monitor_run:
            if THREADING_VERBOSE: print("                            checking for completed tasks")
            sys.stdout.flush()
            with Snapin.lock_mem:
                for worker in Snapin.worker_pool:
                    if worker.parent_pipe.poll():
                        if THREADING_VERBOSE: print("receiving new data from completed task")
                        data = worker.parent_pipe.recv()
                        worker_request_id, completion_callback, data = data
                        if THREADING_VERBOSE: print("    :", data, ":")
                        completion_callback(worker_request_id, data)
            sleep(0.1)


