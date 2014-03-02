from migen.fhdl.std import *
from migen.flow.actor import *
import socket
import select
import os
import errno
import struct


class SimUSBActor(Module):
    def __init__(self, width=16, loop=False):
        assert width in [8, 16], (
            'ez usb fx2 fifo must be 8 or 16 bits wide')

        self.loop = loop
        self.width = width
        self.byte_width = width // 8
        self.sink = Sink([('d', width)])
        self.source = Source([('d', width)])
        self.busy = Signal()
        self.connection = None
        self._recv_buffer = b''
        self._send_buffer = b''
        self._idle_count = 0

        self.comb += self.sink.ack.eq(True)

    def gen_simulation(self, selfp):

        target = os.environ.get('EZUSBFIFO', 'unix')

        protocol, arguments = (target.split(':', 1) + [None])[:2]
        if protocol == 'unix':
            addr = '/tmp/ezusbfifo'
            if arguments is not None:
                addr = arguments

            self.socket = socket.socket(socket.AF_UNIX)
            try:
                self.socket.bind(addr)
            except OSError as e:
                if e.errno != errno.EADDRINUSE:
                    raise
                os.remove(addr)
                self.socket.bind(addr)
            self.socket.listen(0)
        else:
            raise RuntimeError("unsupported protocol %s" % protocol)

        reconnect = True

        while True:
            if self.connection is None:
                if reconnect:
                    self.connection = self.socket.accept()[0]
                    reconnect = self.loop
                else:
                    if len(self._recv_buffer) < self.byte_width:
                        print("exiting")
                        break

            if len(self._recv_buffer) < self.byte_width:
                rt_read, rt_write, err = select.select(
                    [self.connection],[],[],0)
                if rt_read:
                    data = self.connection.recv(1024)
                    if not data:
                        self.connection = None
                    else:
                        self._recv_buffer += data

            if selfp.source.stb and selfp.source.ack:
                self._recv_buffer = self._recv_buffer[self.byte_width:]

            have_data = len(self._recv_buffer) >= self.byte_width

            if have_data:
                if self.byte_width == 2:
                    data = struct.unpack('<H', self._recv_buffer[:2])[0]
                else:
                    data = struct.unpack('B', self._recv_buffer[:1])[0]

                selfp.source.payload.d = data

            selfp.source.stb = have_data

            if selfp.sink.stb:
                if self.byte_width == 2:
                    self._send_buffer += struct.pack(
                        '<H', selfp.sink.payload.d)
                else:
                    self._send_buffer += struct.pack(
                        'B', selfp.sink.payload.d)
                self._idle_count = 0
            else:
                self._idle_count += 1

            if len(self._send_buffer) and self.connection is not None:
                if len(self._send_buffer) > 1024 or self._idle_count > 64:
                    try:
                        self.connection.sendall(self._send_buffer)
                        self._send_buffer = b''
                    except BrokenPipeError:
                        # wait for the socket read buffer to exhaust
                        pass

            selfp.busy = bool(have_data or self._send_buffer)
            yield
