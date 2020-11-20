# TlsrComSwireWriter
TLSR826x/825x COM port Swire Writer Utility


### Telink SWIRE simulation on a COM port.

Using only the COM port, downloads and runs the program in SRAM for TLSR826x or TLSR825x chips.

![SCH](https://github.com/pvvx/TlsrComSwireWriter/blob/master/schematicc.gif)

COM-RTS connect to Chip RST or Vcc.


    usage: ComSwireWriter [-h] [--port PORT] [--tact TACT] [--file FILE] [--baud BAUD]
    
    TLSR826x ComSwireWriter Utility version 21.02.20
    
    optional arguments:
        -h, --help            show this help message and exit
        --port PORT, -p PORT  Serial port device (default: COM1)
        --tact TACT, -t TACT  Time Activation ms (0-off, default: 600 ms)
        --file FILE, -f FILE  Filename to load (default: floader.bin)
        --baud BAUD, -b BAUD  UART Baud Rate (default: 230400)

Added ComSwireReader for TLSR825x chips:

    usage: ComSwireReader [-h] [--port PORT] [--tact TACT] [--clk CLK]
                          [--baud BAUD] [--address ADDRESS] [--size SIZE]
    
    TLSR825x ComSwireReader Utility version 20.11.20
    
    optional arguments:
      -h, --help            show this help message and exit
      --port PORT, -p PORT  Serial port device (default: COM1)
      --tact TACT, -t TACT  Time Activation ms (0-off, default: 0 ms)
      --clk CLK, -c CLK     SWire CLK (default: 24 MHz, 0 - auto)
      --baud BAUD, -b BAUD  UART Baud Rate (default: 921600, min: 460800)
      --address ADDRESS, -a ADDRESS
                            SWire addres (default: 0x06bc (PC))
      --size SIZE, -s SIZE  Size data (default: 4)
        usage: ComSwireReader [-h] [--port PORT] [--tact TACT] [--clk CLK]
                          [--baud BAUD] [--address ADDRESS] [--size SIZE]
    

#### Samples:
> **Read SRAM:** python.exe ComSwireReader825x.py -p COM11 -t 70 -c 0 -a 0x40000 -s 256
```
=======================================================
TLSR825x ComSwireReader Utility version 20.11.20
-------------------------------------------------------
Open COM11, 921600 baud...
Reset module (RTS low)...
Activate (70 ms)...
UART-SWS 92160 baud. SW-CLK ~24.0 MHz(?)
-------------------------------------------------------
040000: 00 00 00 00 70 76 76 78 4b 4e 4c 54 93 03 88 00 
040010: 86 80 00 00 00 00 00 00 24 ad 00 00 00 00 00 00 
040020: 0c 64 81 a2 09 0b 1a 40 c0 06 c0 06 c0 06 c0 06 
040030: c0 06 c0 06 c0 06 c0 06 c0 06 c0 06 c0 06 c0 06 
040040: c0 06 c0 06 c0 06 c0 06 0c 6c 70 07 6f 00 80 00 
040050: 04 a2 11 48 a5 a0 88 02 03 c1 05 a2 11 48 2e 08 
040060: 01 40 2c 08 00 a1 41 40 ab a1 01 40 00 a2 06 a3 
040070: 01 b2 9a 02 fc cd 01 a1 41 40 23 08 23 09 24 0a 
040080: 91 02 02 ca 08 50 04 b1 fa 87 12 a0 c0 6b 13 08 
040090: 85 06 13 a0 c0 6b 12 08 85 06 00 a0 11 09 12 0a 
0400a0: 91 02 02 ca 08 50 04 b1 fa 87 11 09 11 0a 91 02 
0400b0: 02 ca 08 50 04 b1 fa 87 0c 09 0f 08 08 40 01 b0 
0400c0: 48 40 0e 09 0e 0a 0f 0b 9a 02 04 ca 08 58 10 50 
0400d0: 04 b1 04 b2 f8 87 00 90 23 9c c0 46 90 44 84 00 
0400e0: 00 80 84 00 10 43 84 00 0d 45 84 00 0c 06 80 00 
0400f0: 00 3a 84 00 00 3b 84 00 3a 00 00 00 1c ad 00 00 
-------------------------------------------------------
Done!
```
