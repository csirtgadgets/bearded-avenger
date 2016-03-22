# =========================================================================
# zsocket - working with 0MQ sockets
#
# Copyright (c) the Contributors as noted in the AUTHORS file.
# This file is part of CZMQ, the high-level C binding for 0MQ:
# http://czmq.zeromq.org.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# =========================================================================
# The zsocket class provides helper functions for 0MQ sockets. It doesn't
# wrap the 0MQ socket type, to avoid breaking all libzmq socket-related
# calls.

import zmq
import struct

class ZSocket(zmq.Socket):

    def __init__(self, *args, **kwargs):
        super(zmq.Socket, self).__init__(*args, **kwargs)

    #  --------------------------------------------------------------------------
    #  Send a signal over a socket. A signal is a zero-byte message.
    #  Signals are used primarily between threads, over pipe sockets.
    #  Returns -1 if there was an error sending the signal.
    #def signal(self):
    #    self.send_unicode("")

    #  --------------------------------------------------------------------------
    #  Wait on a signal. Use this to coordinate between threads, over
    #  pipe pairs. Blocks until the signal is received. Returns -1 on error,
    #  0 on success.
    #def wait(self):
    #    while True:
    #        msg = self.recv()
    #        print("WAIT MSG", msg)

    # --------------------------------------------------------------------------
    #  Send a signal over a socket. A signal is a short message carrying a
    #  success/failure code (by convention, 0 means OK). Signals are encoded
    #  to be distinguishable from "normal" messages. Accepts a zock_t or a
    #  zactor_t argument, and returns 0 if successful, -1 if the signal could
    #  not be sent.
    # Send a signal over a socket. A signal is a zero-byte message.
    # Signals are used primarily between threads, over pipe sockets.
    # Returns -1 if there was an error sending the signal.
    def signal(self, status=0):
        signal_value = 0x7766554433221100 + status
        self.send(struct.pack("Q", signal_value))

    # --------------------------------------------------------------------------
    #  A signal is a message containing one frame with our 8-byte magic
    #  value. If we get anything else, we discard it and continue to look
    #  for the signal message
    def wait(self):
        while(True):
            msg = self.recv()
            if len(msg) == 8:
                signal_value = struct.unpack('Q', msg)[0]
                if (signal_value & 0xFFFFFFFFFFFFFF00) == 0x7766554433221100:
                    # return True or False based on the signal value send
                    return signal_value & 255
                else:
                    return -1
