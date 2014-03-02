from migen.fhdl.std import *
from migen.flow.actor import *
from migen.actorlib.fifo import AsyncFIFO
from mimisc.actors.plumbing import Relax
from ezusbfifo.actor import USBActor


class AsyncUSBActor(Module):
    def __init__(self, fx2_fifo, width=16, pktend_delay=15, fifo_depth=16):
        self.submodules.usb_actor = RenameClockDomains(
            USBActor(fx2_fifo, width=width, pktend_delay=pktend_delay),
            'ezusbfifo')

        self.submodules.input_buffer = RenameClockDomains(
            Relax([('d', width)]), 'ezusbfifo')
        self.submodules.input_fifo = RenameClockDomains(
            AsyncFIFO([('d', width)], fifo_depth),
            {'read': 'sys', 'write': 'ezusbfifo'})

        self.submodules.output_buffer = RenameClockDomains(
            Relax([('d', width)]), 'ezusbfifo')
        self.submodules.output_fifo = RenameClockDomains(
            AsyncFIFO([('d', width)], fifo_depth),
            {'read': 'ezusbfifo', 'write': 'sys'})

        self.comb += [
            self.output_buffer.d.connect(self.output_fifo.source),
            self.usb_actor.sink.connect(self.output_buffer.q),
            self.input_buffer.d.connect(self.usb_actor.source),
            self.input_fifo.sink.connect(self.input_buffer.q),
        ]

        self.sink = self.output_fifo.sink
        self.source = self.input_fifo.source
        self.busy = Signal()
        self.comb += self.busy.eq(0)
