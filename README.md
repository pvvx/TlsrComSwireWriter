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

Added TLSR825xComFlasher:

	usage: TLSR825xComFlasher.py [-h] [-p PORT] [-t TACT] [-c CLK] [-b BAUD] [-r]
	                             [-d]
    	                         {rf,wf,es,ea} ...

	TLSR825x Flasher version 00.00.02

	positional arguments:
	  {rf,wf,es,ea}         TLSR825xComFlasher {command} -h for additional help
	    rf                  Read Flash to binary file
	    wf                  Write file to Flash with sectors erases
	    es                  Erase Region (sectors) of Flash
	    ea                  Erase All Flash

	optional arguments:
	  -h, --help            show this help message and exit
	  -p PORT, --port PORT  Serial port device (default: COM1)
	  -t TACT, --tact TACT  Time Activation ms (0-off, default: 0 ms)
	  -c CLK, --clk CLK     SWire CLK (default: auto, 0 - auto)
	  -b BAUD, --baud BAUD  UART Baud Rate (default: 921600, min: 340000)
	  -r, --run             CPU Run (post main processing)
	  -d, --debug           Debug info


Warning: FTDI USB-COM chips don't work!

Prolific PL-2303HX, ...

#### Samples:
> **Write full flash:** python.exe TLSR825xComFlasher.py -p COM3 -t 70 wf 0 Original_full_flash_Xiaomi_LYWSD03MMC.bin
```
=======================================================
TLSR825x Flasher version 00.00.02
-------------------------------------------------------
Open COM3, 921600 baud...
Reset module (RTS low)...
Activate (70 ms)...
UART-SWS 92160 baud. SW-CLK ~23.0 MHz(?)
Inputfile: Original_full_flash_Xiaomi_LYWSD03MMC.bin
Write Flash data 0x00000000 to 0x00080000...
-------------------------------------------------------
Worked Time: 48.761 sec
Done!
```
