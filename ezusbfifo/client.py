import os
import socket
import select
import time
import usb1


class UsbComm:
    POLLRATE = 64
    BLOCKSIZE = 16384

    def __init__(self, vid=0x221A, pid=0x0100, in_ep=0x82, out_ep=0x06):
        self.vid, self.pid = vid, pid
        self.in_ep, self.out_ep = in_ep, out_ep

        self.context = usb1.LibUSBContext()
        self.dev = self.context.openByVendorIDAndProductID(
            self.vid, self.pid)

        if self.dev is None:
            raise RuntimeError("device not found")

        self.write_buffer = b""
        self.read_buffer = b""

        for i in range(self.POLLRATE):
            transfer = self.dev.getTransfer()
            transfer.setBulk(self.in_ep, self.BLOCKSIZE,
                self._read_callback, None, 0)
            transfer.submit()

        # clear leftover data
        time.sleep(0.1)
        self.read_buffer = b""

    def _read_callback(self, transfer):
        status = transfer.getStatus()
        if status == 3: # cancelled
            return
        elif status:
            raise RuntimeError("usb communication error")
        size = transfer.getActualLength()
        self.read_buffer += transfer.getBuffer()[:size]
        transfer.submit()

    def read(self, size, timeout=None):
        self.flush()
        if timeout is None:
            while len(self.read_buffer) < size:
                self.context.handleEvents()

        else:
            self.context.handleEvents(tv=timeout)
        data = self.read_buffer[:size]
        self.read_buffer = self.read_buffer[len(data):]
        return data

    def _write_callback(self, transfer):
        pass

    def _write_unbuffered(self, data):
        transfer = self.dev.getTransfer()
        transfer.setBulk(self.out_ep, data, self._write_callback, None, 0)
        transfer.submit()

    def write(self, data):
        self.write_buffer += data
        while len(self.write_buffer) > self.BLOCKSIZE:
            self._write_unbuffered(self.write_buffer[:self.BLOCKSIZE])
            self.write_buffer = self.write_buffer[self.BLOCKSIZE:]

    def flush(self):
        if self.write_buffer:
            self._write_unbuffered(self.write_buffer)
            self.write_buffer = b""


class SimComm:
    def __init__(self, addr='/tmp/ezusbfifo'):
        self.socket = socket.socket(socket.AF_UNIX)
        self.socket.connect(addr)

    def write(self, s):
        self.socket.sendall(s)

    def read(self, size, timeout=None):
        result = b''
        if timeout is None:
            self.socket.setblocking(1)
            while len(result) < size:
                result += self.socket.recv(size - len(result))
        else:
            end_time = time.time() + timeout
            self.socket.setblocking(0)
            while len(result) < size:
                delta = end_time - time.time()
                if delta <= 0:
                    break
                ready = select.select([self.socket], [], [], delta)
                if ready[0]:
                    result += self.socket.recv(size - len(result))
        return result

    def flush(self):
        pass


def connect():
    target = os.environ.get('EZUSBFIFO', 'usb')

    protocol, arguments = (target.split(':', 1) + [None])[:2]

    if protocol == 'usb':
        return UsbComm()
    elif protocol == 'unix':
        addr = '/tmp/ezusbfifo'
        if arguments is not None:
            addr = arguments
        return SimComm(addr=addr)
    else:
        raise RuntimeError("unsupported protocol %s" % protocol)
