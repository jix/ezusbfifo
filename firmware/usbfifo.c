#include[ztex-conf.h]
#include[ztex-utils.h]

EP_CONFIG(2,0,BULK,IN,512,4);
EP_CONFIG(6,0,BULK,OUT,512,4);

IDENTITY_UFM_1_15(10.13.0.0,0);
ENABLE_UFM_1_15X_DETECTION;

#define[PRODUCT_STRING]["bidirectional usb fifo for ZTEX fpga 1.15"]

ENABLE_HS_FPGA_CONF(6);

__xdata BYTE run;

#define[PRE_FPGA_RESET][PRE_FPGA_RESET
    IFCONFIG = bmBIT7 | bmBIT5 | 0;
    SYNCDELAY;
    OEA = 0;
    OEB = 0;
    OEC = 0;
    OED = 0;
    OEE = 0;
    run = 0;
]

#define[POST_FPGA_CONFIG][POST_FPGA_CONFIG
    REVCTL = 0x3;
    SYNCDELAY;

    // 30 MHz internal, drive clock, non-inverted, sync, ports mode
    IFCONFIG = bmBIT7 | bmBIT5 | 3;
    SYNCDELAY;

    FIFOPINPOLAR = 0;
    SYNCDELAY;
    PINFLAGSAB = 0xCA;
    SYNCDELAY;
    PINFLAGSCD = 0;
    SYNCDELAY;

    FIFORESET = 0x80;
    SYNCDELAY;
    FIFORESET = 0x82;
    SYNCDELAY;
    FIFORESET = 0x86;
    SYNCDELAY;
    FIFORESET = 0x00;
    SYNCDELAY;

    OUTPKTEND = 0x86;
    SYNCDELAY;
    OUTPKTEND = 0x86;
    SYNCDELAY;
    OUTPKTEND = 0x86;
    SYNCDELAY;
    OUTPKTEND = 0x86;
    SYNCDELAY;

    EP6FIFOCFG = bmBIT4 | bmBIT0;
    SYNCDELAY;

    EP2FIFOCFG = bmBIT3 | bmBIT0;
    SYNCDELAY;

    EP2AUTOINLENH = 2;
    SYNCDELAY;
    EP2AUTOINLENL = 0;
    SYNCDELAY;

    EP2CS &= ~bmBIT0;
    EP6CS &= ~bmBIT0;
]

#include[ztex.h]

void main(void)
{
    init_USB();

    while (1) {
    }
}
