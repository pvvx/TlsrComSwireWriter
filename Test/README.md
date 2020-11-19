# TlsrComSwireRW
TLSR825x COM port Swire Utility

### Telink SWIRE simulation on a COM port.

Using only the COM port and TLSR825x chips.

![SCH](https://github.com/pvvx/TlsrComSwireWriter/blob/master/schematicc.gif)


The project was closed without starting.
Low polling speed when reading the USB COM port - 3 ms per byte.
An incomplete example is attached.


#### Samples:
> **Read Flash:** python.exe ComSwireFlasher825x.py -p COM11 -a 0 -s 256 -t 70
```
=======================================================
TLSR825x ComSwireFlasher Utility version 19.11.20(test)
-------------------------------------------------------
Open COM11, 230400 baud...
Reset module (RTS low)...
Activate (70 ms)...
Load <floader825x.bin> to 0x840000...
Bin bytes writen: 1188
CPU go Start...
-------------------------------------------------------
ReOpen COM11, 921600 baud...
SWire speed for CLK 24.0 MHz... ok.
SWM/SWS 184320/92307 bits/s
-------------------------------------------------------
CPU PC: 00000168
Floader id: 78353238, ver: 0.0.0.5, bufsize: 8654352
ChipID: 0x5562, ver: 0x02
Flash JEDEC ID: C86013, Size: 512 kbytes
CPU PC: 00000168
-------------------------------------------------------
Read faddr 0x000000, size 256 ...
000000: 26 80 01 00 70 76 76 78 4b 4e 4c 54 93 03 88 00 
00000f: 86 80 00 00 00 00 00 00 24 ad 00 00 00 00 00 00 
00001f: 0c 64 81 a2 09 0b 1a 40 c0 06 c0 06 c0 06 c0 06 
00002f: c0 06 c0 06 c0 06 c0 06 c0 06 c0 06 c0 06 c0 06 
00003f: c0 06 c0 06 c0 06 c0 06 0c 6c 70 07 6f 00 80 00 
00004f: 04 a2 11 48 a5 a0 88 02 03 c1 05 a2 11 48 2e 08 
00005f: 01 40 2c 08 00 a1 41 40 ab a1 01 40 00 a2 06 a3 
00006f: 01 b2 9a 02 fc cd 01 a1 41 40 23 08 23 09 24 0a 
00007f: 91 02 02 ca 08 50 04 b1 fa 87 12 a0 c0 6b 13 08 
00008f: 85 06 13 a0 c0 6b 12 08 85 06 00 a0 11 09 12 0a 
00009f: 91 02 02 ca 08 50 04 b1 fa 87 11 09 11 0a 91 02 
0000af: 02 ca 08 50 04 b1 fa 87 0c 09 0f 08 08 40 01 b0 
0000bf: 48 40 0e 09 0e 0a 0f 0b 9a 02 04 ca 08 58 10 50 
0000cf: 04 b1 04 b2 f8 87 00 90 23 9c c0 46 90 44 84 00 
0000df: 00 80 84 00 10 43 84 00 0d 45 84 00 0c 06 80 00 
0000ef: 00 3a 84 00 00 3b 84 00 3a 00 00 00 1c ad 00 00 
-------------------------------------------------------
Done!
```
