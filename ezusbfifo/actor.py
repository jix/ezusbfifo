from migen.fhdl.std import *
from migen.flow.actor import *
from migen.fhdl.specials import Tristate


class USBActor(Module):
    def __init__(self, fx2_fifo, width=16, pktend_delay=15):
        assert width in [8, 16], (
            'ez usb fx2 fifo must be 8 or 16 bits wide')

        self.fx2_fifo = fx2_fifo
        self.width = width

        self.sink = Sink([('d', width)])
        self.source = Source([('d', width)])
        self.busy = Signal()

        ###

        usb_input_ready = Signal()
        usb_output_ready = Signal()
        input_ready = Signal()
        output_ready = Signal()
        input_enable = Signal()
        output_enable = Signal()
        input_data = Signal(width)
        output_data = Signal(width)
        transfer_active = Signal()
        pktend_ready = Signal()
        pktend_enable = Signal()
        pktend_counter = Signal(max=pktend_delay + 1)

        bus_dir_fpga_drive = Signal()
        bus_dir_fx2_drive = Signal()

        # source.stb depending on source.ack violates the endpoint protocol
        # but works just fine with a buffered connection to a fifo
        # and simplifies the logic here

        self.comb += [
            usb_input_ready.eq(fx2_fifo.flag[0]),
            usb_output_ready.eq(fx2_fifo.flag[1]),
            input_ready.eq(usb_input_ready & self.source.ack),
            output_ready.eq(usb_output_ready & self.sink.stb),
            input_enable.eq(input_ready & bus_dir_fx2_drive),
            output_enable.eq(output_ready & bus_dir_fpga_drive),
            fx2_fifo.sloe.eq(~bus_dir_fx2_drive),
            fx2_fifo.slrd.eq(~input_enable),
            fx2_fifo.slwr.eq(~output_enable),
            self.source.stb.eq(input_enable),
            self.sink.ack.eq(output_enable),
            self.source.payload.d.eq(input_data),
            output_data.eq(self.sink.payload.d),
            fx2_fifo.fifoadr.eq(Mux(bus_dir_fx2_drive, 2, 0)),
            pktend_ready.eq(transfer_active &
                (pktend_counter == 0) & usb_output_ready),
            pktend_enable.eq(pktend_ready &
                ~output_ready & ~bus_dir_fx2_drive),
            fx2_fifo.pktend.eq(~pktend_enable),
            self.busy.eq(usb_input_ready)
        ]

        self.specials += Tristate(
            target=fx2_fifo.fd,
            o=output_data,
            oe=bus_dir_fpga_drive,
            i=input_data)

        self.sync += [
            If(~bus_dir_fpga_drive & ~bus_dir_fx2_drive,
                If(output_ready,
                    bus_dir_fx2_drive.eq(0),
                    bus_dir_fpga_drive.eq(1)
                ).Elif(input_ready,
                    bus_dir_fx2_drive.eq(1),
                    bus_dir_fpga_drive.eq(0)
                )
            ).Elif(bus_dir_fpga_drive,
                If(~output_ready & input_ready,
                    bus_dir_fpga_drive.eq(0)
                )
            ).Elif(bus_dir_fx2_drive,
                If(~input_ready & (output_ready | pktend_ready),
                    bus_dir_fx2_drive.eq(0)
                )
            ),
            If(output_enable,
                transfer_active.eq(1),
            ).Elif(pktend_enable,
                transfer_active.eq(0)
            ),
            If(output_enable,
                pktend_counter.eq(pktend_delay)
            ).Elif(~input_enable,
                If(pktend_counter != 0,
                    pktend_counter.eq(pktend_counter - 1)
                )
            )
        ]
