# barrowed from pyre

import random
import zmq
import threading
import binascii
import os
import sys
from . import zsocket


if sys.version.startswith('3'):
    u = str
else:
    u = unicode

# --------------------------------------------------------------------------
# Create a pipe, which consists of two PAIR sockets connected over inproc.
# The pipe is configured to use a default 1000 hwm setting. Returns the
# frontend and backend sockets.
def zcreate_pipe(ctx, hwm=1000):
    backend = zsocket.ZSocket(ctx, zmq.PAIR)
    frontend = zsocket.ZSocket(ctx, zmq.PAIR)
    backend.set_hwm(hwm)
    frontend.set_hwm(hwm)
    # close immediately on shutdown
    backend.setsockopt(zmq.LINGER, 0)
    frontend.setsockopt(zmq.LINGER, 0)

    endpoint = "inproc://zactor-%04x-%04x\n"\
                 %(random.randint(0, 0x10000), random.randint(0, 0x10000))
    while True:
        try:
            frontend.bind(endpoint)
        except:
            endpoint = "inproc://zactor-%04x-%04x\n"\
                 %(random.randint(0, 0x10000), random.randint(0, 0x10000))
        else:
            break
    backend.connect(endpoint)
    return (frontend, backend)


def zthread_fork(ctx, func, *args, **kwargs):
    """
    Create an attached thread. An attached thread gets a ctx and a PAIR
    pipe back to its parent. It must monitor its pipe, and exit if the
    pipe becomes unreadable. Returns pipe, or NULL if there was an error.
    """
    a = ctx.socket(zmq.PAIR)
    a.setsockopt(zmq.LINGER, 0)
    a.setsockopt(zmq.RCVHWM, 100)
    a.setsockopt(zmq.SNDHWM, 100)
    a.setsockopt(zmq.SNDTIMEO, 5000)
    a.setsockopt(zmq.RCVTIMEO, 5000)
    b = ctx.socket(zmq.PAIR)
    b.setsockopt(zmq.LINGER, 0)
    b.setsockopt(zmq.RCVHWM, 100)
    b.setsockopt(zmq.SNDHWM, 100)
    b.setsockopt(zmq.SNDTIMEO, 5000)
    a.setsockopt(zmq.RCVTIMEO, 5000)
    iface = "inproc://%s" % binascii.hexlify(os.urandom(8))
    a.bind(iface)
    b.connect(iface)

    thread = threading.Thread(target=func, args=((ctx, b) + args), kwargs=kwargs)
    thread.daemon = False
    thread.start()

    return a