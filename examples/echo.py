from migen.fhdl.std import *
from migen.flow.plumbing import Buffer
from migen.actorlib.fifo import SyncFIFO, AsyncFIFO
from migen.flow.network import DataFlowGraph, CompositeActor
from ezusbfifo import SimUSBActor, AsyncUSBActor
from mimisc.actors.plumbing import Relax


class Echo(Module):
    def __init__(self, usb_actor):

        g = DataFlowGraph()

        fifo = SyncFIFO([('d', 16)], 64)
        in_buffer = Relax([('d', 16)])
        out_buffer = Relax([('d', 16)])

        g.add_connection(in_buffer, fifo)
        g.add_connection(fifo, out_buffer)

        g.add_connection(out_buffer, usb_actor)
        g.add_connection(usb_actor, in_buffer)

        self.submodules.composite = CompositeActor(g)
        self.busy = self.composite.busy


if __name__ == '__main__':
    import sys

    try:
        command = sys.argv.pop(1)
    except IndexError:
        command = 'help'

    if command == 'build':
        from mimisc.platforms import ztex_115d as board

        plat = board.Platform(manual_timing=True)

        fx2_fifo = plat.request('fx2_fifo')
        clk_if = plat.request('clk_if')

        echo = Echo(AsyncUSBActor(fx2_fifo))

        clk_ezusbfifo = Signal()
        clk_ezusbfifo_ub = Signal()

        clk_sys = Signal()
        clk_sys_ub = Signal()

        fraction = (3, 1)

        echo.specials += [
            Instance('DCM_SP',
                Instance.Input('CLKIN', clk_if),
                Instance.Input('CLKFB', clk_ezusbfifo),
                Instance.Input('RST', 0),
                Instance.Input('DSSEN', 0),
                Instance.Input('PSCLK', 0),
                Instance.Input('PSEN', 0),
                Instance.Input('PSINCDEC', 0),
                Instance.Output('CLK0', clk_ezusbfifo_ub),
                Instance.Parameter('STARTUP_WAIT', True),
            ),
            Instance('BUFG',
                Instance.Input('I', clk_ezusbfifo_ub),
                Instance.Output('O', clk_ezusbfifo),
            ),
            Instance('DCM_CLKGEN',
                Instance.Input('CLKIN', clk_if),
                Instance.Input('RST', 0),
                Instance.Input('FREEZEDCM', 0),
                Instance.Input('PROGDATA', 0),
                Instance.Input('PROGEN', 0),
                Instance.Input('PROGCLK', 0),
                Instance.Output('CLKFX', clk_sys_ub),
                Instance.Parameter('CLKFX_MULTIPLY', fraction[0]),
                Instance.Parameter('CLKFX_DIVIDE', fraction[1]),
                Instance.Parameter('STARTUP_WAIT', True),
            ),
            Instance('BUFG',
                Instance.Input('I', clk_sys_ub),
                Instance.Output('O', clk_sys),
            ),
        ]

        echo.clock_domains.cd_sys = ClockDomain(
            'sys', reset_less=True)
        echo.clock_domains.cd_ezusbfifo = ClockDomain(
            'ezusbfifo', reset_less=True)

        echo.comb += [
            echo.cd_sys.clk.eq(clk_sys),
            echo.cd_ezusbfifo.clk.eq(clk_ezusbfifo)
        ]

        plat.add_platform_command("""
            NET "{clk_if}" TNM_NET = "GRP_clk_if";
            TIMESPEC "TS_clk_if" = PERIOD "GRP_clk_if" 33.33 ns HIGH 50%;

            NET "{clk_sys}" TNM_NET = "GRP_clk_sys";
            NET "{clk_ezusbfifo}" TNM_NET = "GRP_clk_ezusbfifo";

            TIMESPEC "TS_cdc_fwd" =
                FROM "GRP_clk_sys" TO "GRP_clk_ezusbfifo"
                [delay] ns DATAPATHONLY;
            TIMESPEC "TS_cdc_bwd" =
                FROM "GRP_clk_ezusbfifo" TO "GRP_clk_sys"
                [delay] ns DATAPATHONLY;

            OFFSET = IN 15 ns VALID 30 ns BEFORE "{clk_if}";
            OFFSET = OUT 15 ns AFTER "{clk_if}";
            """.replace('[delay]',
                str(0.5 * 33.33 * fraction[1] / fraction[0])),
            clk_if=clk_if,
            clk_sys=clk_sys,
            clk_ezusbfifo=clk_ezusbfifo,
        )

        plat.build_cmdline(echo)
    elif command == 'sim':
        from migen.sim.generic import Simulator, TopLevel

        echo = Echo(SimUSBActor(loop=True))

        sim = Simulator(echo, TopLevel("echo.vcd"))

        with sim:
            sim.run()
    else:
        print('usage: python %s build|sim [options]' % sys.argv[0])
