#!/usr/bin/env python
 
### ComSwireFlasher.py ###
###    Autor: pvvx     ###
 
import sys
import struct
import serial
import platform
import time
import argparse
import os
import io

__progname__ = 'TLSR825x ComSwireFlasher Utility'
__filename__ = 'ComSwireFlasher'
__version__ = "20.11.20(test)"

#typedef struct {		// Start values:
#	volatile u32 faddr; //[+0] = flash jedec id
#	volatile u32 pbuf;	//[+4] = buffer addr
#	volatile u16 count; //[+8] = buffer size 
#	volatile u16 cmd;   //[+10]
#	volatile u16 iack;	//[+12] = Version, in BCD 0x1234 = 1.2.3.4
#	volatile u16 oack;  //[+14] != 0 -> Start ok
#} sext;
class floader_ext:
	faddr = 0
	pbuf = 0
	count = 0
	cmd = 0
	iack = -1
	oack = -1
	jedecid = 0
	fsize = 0
	ver = 0
	cid = 0
	chip = '?'

COMPORT_MIN_BAUD_RATE=340000
COMPORT_DEF_BAUD_RATE=921600
USBCOMPORT_BAD_BAUD_RATE=700000

ext = floader_ext()

debug = False
bit8mask = 0x20

class FatalError(RuntimeError):
	def __init__(self, message):
		RuntimeError.__init__(self, message)
	@staticmethod
	def WithResult(message, result):
		message += " (result was %s)" % hexify(result)
		return FatalError(message)
def arg_auto_int(x):
	return int(x, 0)
def hex_dump(addr, blk):
	print('%06x: ' % addr, end='')
	for i in range(len(blk)):
		if (i+1) % 16 == 0:
			print('%02x ' % blk[i])
			if i < len(blk) - 1:
				print('%06x: ' % (addr + i + 1), end='')
		else:
			print('%02x ' % blk[i], end='')
	if len(blk) % 16 != 0:
		print('')
# encode data (blk) into 10-bit swire words 
def sws_encode_blk(blk):
	pkt=[]
	d = bytearray(10) # word swire 10 bits
	d[0] = 0x80 # start bit byte cmd swire = 1
	for el in blk:
		m = 0x80 # mask bit
		idx = 1
		while m != 0:
			if (el & m) != 0:
				d[idx] = 0x80
			else:
				d[idx] = 0xfe
			idx += 1
			m >>= 1
		d[9] = 0xfe # stop bit swire = 0
		pkt += d 
		d[0] = 0xfe # start bit next byte swire = 0 
	return pkt
# decode 9 bit swire response to byte (blk)
def sws_decode_blk(blk):
	if (len(blk) == 9) and ((blk[8] & 0xfe) == 0xfe):
		bitmask = bit8mask
		data = 0;
		for el in range(8):
			data <<= 1
			if (blk[el] & bitmask) == 0:
				data |= 1
			bitmask = 0x10
		#print('0x%02x' % data)
		return data
	#print('Error blk:', blk)
	return None
# encode a part of the read-by-address command (before the data read start bit) into 10-bit swire words
def sws_rd_addr(addr):
	return sws_encode_blk(bytearray([0x5a, (addr>>16)&0xff, (addr>>8)&0xff, addr & 0xff, 0x80]))
# encode command stop into 10-bit swire words
def sws_code_end():
	return sws_encode_blk([0xff])
# encode the command for writing data into 10-bit swire words
def sws_wr_addr(addr, data):
	return sws_encode_blk(bytearray([0x5a, (addr>>16)&0xff, (addr>>8)&0xff, addr & 0xff, 0x00]) + bytearray(data)) + sws_encode_blk([0xff])
# send block to USB-COM
def wr_usbcom_blk(serialPort, blk):
	# USB-COM chips throttle the stream into blocks at high speed!
	if serialPort.baudrate > USBCOMPORT_BAD_BAUD_RATE:
		i = 0
		s = 60
		l = len(blk)
		while i < l:
			if l - i < s:
				s = l - i
			i += serialPort.write(blk[i:i+s])
		return i
	return serialPort.write(blk)
# send and receive block to USB-COM
def	rd_wr_usbcom_blk(serialPort, blk):
	i = wr_usbcom_blk(serialPort, blk)
	return i == len(serialPort.read(i))
# send swire command write to USB-COM
def sws_wr_addr_usbcom(serialPort, addr, data):
	return wr_usbcom_blk(serialPort, sws_wr_addr(addr, data))
# send and receive swire command write to USB-COM  
def rd_sws_wr_addr_usbcom(serialPort, addr, data):
	i = wr_usbcom_blk(serialPort, sws_wr_addr(addr, data))
	return i == len(serialPort.read(i))
# send and receive swire command read to USB-COM
def sws_read_data(serialPort, addr, size):
	# A serialPort.timeout must be set !
	serialPort.timeout = 0.05
	# send addr and flag read
	rd_wr_usbcom_blk(serialPort, sws_rd_addr(addr))
	out=[]
	# read size bytes
	for i in range(size):
		# send bit start read byte
		serialPort.write([0xfe])
		# read 9 bits swire, decode read byte
		blk = serialPort.read(9)
		# Added retry reading for Prolific PL-2303HX and ...
		if len(blk) < 9:
			blk += serialPort.read(9-len(blk))
		x = sws_decode_blk(blk)
		if x != None:
			out += [x]
		else:
			if debug:
				print('\r\nDebug: read swire byte:')
				hex_dump(addr+i, blk)
			# send stop read
			rd_wr_usbcom_blk(serialPort, sws_code_end())
			out = None
			break
	# send stop read
	rd_wr_usbcom_blk(serialPort, sws_code_end())
	return out
def sws_read_dword(serialPort, addr):
	blk = sws_read_data(serialPort, addr, 4)
	if blk != None:
		#return struct.unpack('<I', bytearray(blk))
		return blk[0]+(blk[1]<<8)+(blk[2]<<16)+(blk[3]<<24)
	return None
# set sws speed according to clk frequency and serialPort baud
def set_sws_speed(serialPort, clk):
	#--------------------------------
	# Set register[0x00b2]
	print('SWire speed for CLK %.1f MHz... ' % (clk/1000000), end='')
	swsdiv = int(round(clk*2/serialPort.baudrate))
	if swsdiv > 0x7f:
		print('Low UART baud rate!')
		return False
	byteSent = sws_wr_addr_usbcom(serialPort, 0x00b2, [swsdiv])
	# print('Test SWM/SWS %d/%d baud...' % (int(serialPort.baudrate/5),int(clk/5/swsbaud)))
	read = serialPort.read(byteSent)
	if len(read) != byteSent:
		if serialPort.baudrate > USBCOMPORT_BAD_BAUD_RATE and byteSent > 64 and len(read) >= 64 and len(read) < byteSent:
			print('\n\r!!!!!!!!!!!!!!!!!!!BAD USB-UART Chip!!!!!!!!!!!!!!!!!!!')
			print('UART Output:')
			hex_dump(0,sws_wr_addr(0x00b2, [swsdiv]))
			print('UART Input:')
			hex_dump(0,read)
			print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
			return False
		print('\n\rError: Wrong RX-TX connection!')
		return False
	#--------------------------------
	# Test read register[0x00b2]
	x = sws_read_data(serialPort, 0x00b2, 1)
	#print(x)
	if x != None and x[0] == swsdiv:
		print('ok.')
		if debug:
			print('Debug: UART-SWS %d baud. SW-CLK ~%.1f MHz' % (int(serialPort.baudrate/10), serialPort.baudrate*swsdiv/2000000))
			print('Debug: swdiv = 0x%02x' % (swsdiv))
		return True
	#--------------------------------
	# Set default register[0x00b2]
	rd_sws_wr_addr_usbcom(serialPort, 0x00b2, 0x05)
	print('no')
	return False
# auto set sws speed according to serialport baud
def set_sws_auto_speed(serialPort):
	#---------------------------------------------------
	# swsbaud = Fclk/5/register[0x00b2]
	# register[0x00b2] = Fclk/5/swsbaud
	# swsbaud = serialPort.baudrate/10 
	# register[0x00b2] = Fclk*2/serialPort.baudrate
	# Fclk = 16000000..48000000 Hz
	# serialPort.baudrate = 460800..3000000 bits/s
	# register[0x00b2] = swsdiv = 10..208
	#---------------------------------------------------
	serialPort.timeout = 0.05 # A serialPort.timeout must be set !
	if debug:
		swsdiv_def = int(round(24000000*2/serialPort.baudrate))
		print('Debug: default swdiv for 24 MHz = %d (0x%02x)' % (swsdiv_def, swsdiv_def))
	swsdiv = int(round(16000000*2/serialPort.baudrate))
	if swsdiv > 0x7f:
		print('Low UART baud rate!')
		return False
	swsdiv_max = int(round(48000000*2/serialPort.baudrate))
	#bit8m = (bit8mask + (bit8mask<<1) + (bit8mask<<2))&0xff
	bit8m = ((~(bit8mask-1))<<1)&0xff
	while swsdiv <= swsdiv_max:
		# register[0x00b2] = swsdiv
		rd_sws_wr_addr_usbcom(serialPort, 0x00b2, [swsdiv])
		# send addr and flag read
		rd_wr_usbcom_blk(serialPort, sws_rd_addr(0x00b2))
		# start read data
		serialPort.write([0xfe])
		# read 9 bits data
		blk = serialPort.read(9)
		# Added retry reading for Prolific PL-2303HX and ...
		if len(blk) < 9:
			blk += serialPort.read(9-len(blk))
		# send stop read
		rd_wr_usbcom_blk(serialPort, sws_code_end())
		if debug:
			print('Debug (read data):')
			hex_dump(swsdiv, blk)
		if len(blk) == 9 and blk[8] == 0xfe:
			cmp = sws_encode_blk([swsdiv])
			if debug:
				print('Debug (check data):')
				hex_dump(swsdiv+0xccc00, sws_encode_blk([swsdiv]))
			if (blk[0]&bit8m) == bit8m and blk[1] == cmp[2] and blk[2] == cmp[3] and blk[4] == cmp[5] and blk[6] == cmp[7] and blk[7] == cmp[8]:
				print('UART-SWS %d baud. SW-CLK ~%.1f MHz(?)' % (int(serialPort.baudrate/10), serialPort.baudrate*swsdiv/2000000))
				return True
		swsdiv += 1
		if swsdiv > 0x7f:
			print('Low UART baud rate!')
			break
	#--------------------------------
	# Set default register[0x00b2]
	rd_sws_wr_addr_usbcom(serialPort, 0x00b2, 0x05)
	return False
def activate(serialPort, tact_ms):
		#--------------------------------
		# issue reset-to-bootloader:
		# RTS = either RESET (active low = chip in reset)
		# DTR = active low
		print('Reset module (RTS low)...')
		serialPort.setDTR(True)
		serialPort.setRTS(True)
		time.sleep(0.05)
		serialPort.setDTR(False)
		serialPort.setRTS(False)
		#--------------------------------
    	# Stop CPU|: [0x0602]=5
		print('Activate (%d ms)...' % tact_ms)
		sws_wr_addr_usbcom(serialPort, 0x06f, 0x20) # soft reset mcu
		blk = sws_wr_addr(0x0602, 0x05)
		if tact_ms > 0:
			tact = tact_ms/1000.0
			t1 = time.time()
			while time.time()-t1 < tact:
				for i in range(5):
					wr_usbcom_blk(serialPort, blk)
				serialPort.reset_input_buffer()
		#--------------------------------
		# Duplication with syncronization
		time.sleep(0.01)
		serialPort.reset_input_buffer()
		rd_wr_usbcom_blk(serialPort, sws_code_end())
		rd_wr_usbcom_blk(serialPort, blk)
		time.sleep(0.01)
		serialPort.reset_input_buffer()

def ReadBlockFlash(serialPort, stream, faddr, size):
	global ext
	ext.cmd = 0x03
	ext.count = 1024
	ext.faddr = faddr
	while size > 0:
		if ext.count > size:
			ext.count = size
		print('\rRead from 0x%06x...' % ext.faddr, end = '')
		ext.iack += 1
		blk = struct.pack('<IIHHH', ext.faddr, ext.pbuf, ext.count, ext.cmd, ext.iack)
		rd_sws_wr_addr_usbcom(serialPort, ext.addr, blk)
		while ext.iack == ext.oack:
			#(ext.faddr, ext.pbuf, ext.count, ext.cmd, ext.iack, ext.oack) = struct.unpack('<IIHHHH', bytearray(blk))
			blk = sws_read_data(serialPort,ext.addr+14, 2)
			if blk == None:
				print(' Error')
				return False
			ext.oack = blk[0] | (blk[1]>>8)
		blk = sws_read_data(serialPort, ext.pbuf, ext.count)
		if blk == None:
			print(' Error')
			return False
		stream.write(bytearray(blk));
		#hex_dump(address, blk)
		#print('ok', end='')
		size -= ext.count
		ext.faddr += ext.count
	print('\r                               \r',  end = '')
	return True
#--------------------------------
# Main()
def main():
	global ext
	comport_def_name='COM1'
	if platform == "linux" or platform == "linux2":
		comport_def_name = '/dev/ttyS0'
	#elif platform == "darwin":
	#elif platform == "win32":	
	#else:
	parser = argparse.ArgumentParser(description='%s version %s' % (__progname__, __version__), prog=__filename__)
	parser.add_argument(
		'--port', '-p',
		help='Serial port device (default: COM1)',
		default='COM1')
	parser.add_argument(
		'--tact','-t', 
		help='Time Activation ms (0-off, default: 0 ms)', 
		type=arg_auto_int, 
		default=0)
	parser.add_argument(
		'--clk','-c', 
		help='SWire CLK (default: 24 MHz)', 
		type=arg_auto_int, 
		default=24)
	parser.add_argument(
		'--baud','-b', 
		help='UART Baud Rate (default: 921600, min: 460800)', 
		type=arg_auto_int, 
		default=921600)
	parser.add_argument(
		'--file','-f', 
		help='Filename to load (default: floader825x.bin)', 
		default='floader825x.bin')
	parser.add_argument(
		'--address','-a', 
		help='Flash addres (default: 0))', 
		type=arg_auto_int, 
		default=0)
	parser.add_argument(
		'--size','-s', 
		help='Size data (default: 524288)', 
		type=arg_auto_int, 
		default=524288)
	parser.add_argument(
		'--debug','-d', 
		help='Debug info', 
		action="store_true")
	
	args = parser.parse_args()
	global debug
	debug = args.debug
	global bit8mask
	if args.baud > 1000000:
		bit8mask = 0x40
		if args.baud > 3000000:
			bit8mask = 0x80
	print('=======================================================')
	print('%s version %s' % (__progname__, __version__))
	print('-------------------------------------------------------')
	if(args.baud < COMPORT_MIN_BAUD_RATE):
		print ('The minimum speed of the COM port is %d baud!' % COMPORT_MIN_BAUD_RATE)
		sys.exit(1)
	print ('Open %s, %d baud...' % (args.port, args.baud))
	try:
		serialPort = serial.Serial(args.port, args.baud, \
								   serial.EIGHTBITS,\
								   serial.PARITY_NONE, \
								   serial.STOPBITS_ONE)
		serialPort.reset_input_buffer()
#		serialPort.flushInput()
#		serialPort.flushOutput()
		serialPort.timeout = 0.05
	except:
		print ('Error: Open %s, %d baud!' % (args.port, args.baud))
		sys.exit(1)
	if args.tact != 0:
		#--------------------------------
		# Open floder file
		try:
			stream = open(args.file, 'rb')
			size = os.path.getsize(args.file)
		except:
			serialPort.close
			print('Error: Not open input file <%s>!' % args.file)
			sys.exit(2)
		if size < 1:
			stream.close
			serialPort.close
			print('Error: File size = 0!')
			sys.exit(3)
		#--------------------------------
		# activate
		activate(serialPort, args.tact);

		#--------------------------------
		# Load floader.bin
		binWrite = 0
		rdsize = 0x80
		addr = 0x840000
		print('Load <%s> to 0x%06x...' % (args.file, addr))		
		while size > 0:
			print('\r0x%06x' % addr, end = '')		
			data = stream.read(rdsize)
			if not data: # end of stream
				print('send: at EOF')
				break
			sws_wr_addr_usbcom(serialPort, addr, data)	
			binWrite += len(data)
			addr += len(data)
			size -= len(data)
			serialPort.reset_input_buffer()
		stream.close
		print('\rBin bytes writen:', binWrite)
		print('CPU go Start...')
		sws_wr_addr_usbcom(serialPort, 0x0602, b'\x88') # cpu go Start
		time.sleep(0.05)
		serialPort.flushInput()
		serialPort.flushOutput()
		serialPort.reset_input_buffer()
		serialPort.reset_output_buffer()

	if args.clk == 0:
		# auto speed
		if not set_sws_auto_speed(serialPort):
			print('Chip sleep? -> Use reset chip (RTS-RST): see option --tact')
			sys.exit(1)
	else:
		# Set SWS Speed = CLK/5/[0xb2] bits/s 
		if not set_sws_speed(serialPort, args.clk * 1000000):
			if not set_sws_speed(serialPort, 16000000):
				if not set_sws_speed(serialPort, 24000000):
					if not set_sws_speed(serialPort, 32000000):
						if not set_sws_speed(serialPort, 48000000):
							print('Chip sleep? -> Use reset chip (RTS-RST): see option --tact')
							sys.exit(1)

	print('-------------------------------------------------------')
	# print('Connection...')
	serialPort.timeout = 0.05 # A serialPort.timeout must be set !
	# test id floader
	lid = sws_read_dword(serialPort, 0x40014)
	if lid == None:
		print('Swire Error!')
		sys.exit(1)
	if lid != 0x78353238:
		print('Warning: Unknown floader!')
		sys.exit(1)
	# Test CPU Program Counter (Running?)
	pc = sws_read_dword(serialPort, 0x06bc)
	if pc == None:
		print('Swire Error!')
		sys.exit(1)
	if debug:
		print('CPU PC: %08x' % pc)	
	if pc == 0:
		print('Warning: CPU is in reset and stop state! Restart CPU...' )
		rd_sws_wr_addr_usbcom(serialPort,0x0602, [0x88]) # cpu go
		time.sleep(0.03)
		if debug:
			print('CPU pc: %08x' % sws_read_dword(serialPort, 0x06bc))	
	# Read floader config
	#ext = floader_ext()
	ext.addr = sws_read_dword(serialPort, 0x40004)
	#print('ext.addr: %08x' % ext.addr)	
	if ext.addr == None or ext.addr < 0x840000 or  ext.addr > 0x84fff0:
		print('Floder format or download error!')
		sys.exit(1)
	blk = sws_read_data(serialPort, ext.addr, 16)
	if blk == None:
		print('Swire Error!')
		sys.exit(1)
	#hex_dump(ext.addr, blk)
	(ext.faddr, ext.pbuf, ext.count, ext.cmd, ext.iack, ext.oack) = struct.unpack('<IIHHHH', bytearray(blk))
	if debug:
		print('ext.faddr: %08x' % ext.faddr)	
		print('ext.pbuf: %08x' % ext.pbuf)	
		print('ext.count: %04x' % ext.count)	
		print('ext.cmd: %04x' % ext.cmd)	
		print('ext.iack: %04x' % ext.iack)
		print('ext.oack: %04x' % ext.oack)
	if ext.oack == 0 or ext.oack != ext.iack or ext.cmd != 0x9f:
		print("Warning: Floader format error or it doesn't work!")
	ext.ver = ext.iack;
	print('Floader id: %X, ver: %x.%x.%x.%x, bufsize: %d' % (lid, (ext.ver>>12)&0x0f,(ext.ver>>8)&0x0f,(ext.ver>>4)&0x0f, ext.ver&0x0f, ext.count))
	ext.cid = sws_read_dword(serialPort, 0x07c)
	if ext.cid == None:
		print('Swire Error!')
		sys.exit(1)
	print('ChipID: 0x%04x, ver: 0x%02x' % (ext.cid>>16, (ext.cid>>8)&0xff) )
	#if cid == 0x5562:
	#		chip = 'TLSR8253?'
	#	else:	
	#		chip = '?'
	ext.jedecid = (ext.faddr>>8)&0xffff00 | (ext.faddr&0xff)
	ext.fsize = (1<<(ext.jedecid&0xff))>>10
	print('Flash JEDEC ID: %06X, Size: %d kbytes' % (ext.jedecid, ext.fsize))
	#??????????
	pc = sws_read_dword(serialPort, 0x06bc)
	if pc == None:
		print('Swire Error!')
		sys.exit(1)
	if debug:
		print('CPU PC: %08x' % pc)	
	if pc == 0:
		print('CPU PC: %08x - CPU Not Runing!' % pc)	
		sys.exit(1)
	#--------------------------------
	# Info read swire addres[size]
	print('-------------------------------------------------------')
	#blk = sws_read_blk(serialPort, args.address, args.size)
	print('Read Flash from 0x%06x to 0x%06x...' % (args.address, args.address+args.size))
	print('Outfile: %s' % 'out.bin')
	try:
		stream = open('out.bin', 'wb')
	except:
		print('Error: Not open Outfile file <%s>!' % 'out.bin')
		sys.exit(2)
	if not ReadBlockFlash(serialPort, stream, args.address, args.size):
		stream.close
		serialPort.close
		sys.exit(5)
	stream.close
	print('-------------------------------------------------------')
	print('Done!')
	sys.exit(0)
 
if __name__ == '__main__':
	main()
