# TlsrComSwireRW
TLSR825x COM port Swire Utility

### Telink SWIRE simulation on a COM port.

Using only the COM port and TLSR825x chips.

![SCH](https://github.com/pvvx/TlsrComSwireWriter/blob/master/schematicc.gif)


The project was closed without starting.

Low polling speed when reading the USB COM port on some chips - 3 ms per byte.

An incomplete example is attached.

Tested on Prolific PL-2303HX USB-COM chip:

![PL2303HXBAUD](https://github.com/pvvx/TlsrComSwireWriter/blob/master/Test/PL2303HX_baud.gif)


#### Samples:
> **Read Flash:** python.exe ComSwireFlasher825x.py -p COM11 -a 0 -s 256 -t 70
```
=======================================================
TLSR825x ComSwireFlasher Utility version 19.11.20(test)
-------------------------------------------------------
Open COM3, 921600 baud...
Reset module (RTS low)...
Activate (70 ms)...
Load <floader825x.bin> to 0x840000...
Bin bytes writen: 1188
CPU go Start...
SWire speed for CLK 24.0 MHz... ok.
-------------------------------------------------------
Floader id: 78353238, ver: 0.0.0.5, bufsize: 12288
ChipID: 0x5562, ver: 0x02
Flash JEDEC ID: C86013, Size: 512 kbytes
-------------------------------------------------------
Read Flash from 0x000000 to 0x000100...
Outfile: out.bin
-------------------------------------------------------
Done!
```
