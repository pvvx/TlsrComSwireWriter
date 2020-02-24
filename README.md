# TlsrComSwireWriter
TLSR826x COM port Swire Writer Utility


### Telink SWIRE simulation on a COM port.

Using only the COM port, downloads and runs the program in SRAM for TLSR826x chips.

![SCH](https://github.com/pvvx/TlsrComSwireWriter/blob/master/schematicc.gif)


    usage: ComSwireWriter [-h] [--port PORT] [--tact TACT] [--file FILE] [--baud BAUD]
    
    TLSR826x ComSwireWriter Utility version 21.02.20
    
    optional arguments:
        -h, --help            show this help message and exit
        --port PORT, -p PORT  Serial port device (default: COM1)
        --tact TACT, -t TACT  Time Activation ms (0-off, default: 600 ms)
        --file FILE, -f FILE  Filename to load (default: floader.bin)
        --baud BAUD, -b BAUD  UART Baud Rate (default: 230400)
