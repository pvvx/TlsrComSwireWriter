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
__version__ = "19.11.20(test)"

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
				print('%06x: ' % (addr + i), end='')
		else:
			print('%02x ' % blk[i], end='')
	if len(blk) % 16 != 0:
		print('')

def sws_code_blk(blk):
	pkt=[]
	d = bytearray([0xe8,0xef,0xef,0xef,0xef])
	for el in blk:
		if (el & 0x80) != 0:
			d[0] &= 0x0f
		if (el & 0x40) != 0:
			d[1] &= 0xe8
		if (el & 0x20) != 0:
			d[1] &= 0x0f
		if (el & 0x10) != 0:
			d[2] &= 0xe8
		if (el & 0x08) != 0:
			d[2] &= 0x0f
		if (el & 0x04) != 0:
			d[3] &= 0xe8
		if (el & 0x02) != 0:
			d[3] &= 0x0f
		if (el & 0x01) != 0:
			d[4] &= 0xe8
		pkt += d 
		d = bytearray([0xef,0xef,0xef,0xef,0xef])
	return pkt
def sws_code_blk_variant2(blk):
	pkt=[]
	d = bytearray([0xd8,0xdf,0xdf,0xdf,0xdf])
	for el in blk:
		if (el & 0x80) != 0:
			d[0] &= 0x1f
		if (el & 0x40) != 0:
			d[1] &= 0xf8
		if (el & 0x20) != 0:
			d[1] &= 0x1f
		if (el & 0x10) != 0:
			d[2] &= 0xf8
		if (el & 0x08) != 0:
			d[2] &= 0x1f
		if (el & 0x04) != 0:
			d[3] &= 0xf8
		if (el & 0x02) != 0:
			d[3] &= 0x1f
		if (el & 0x01) != 0:
			d[4] &= 0xf8
		pkt += d 
		d = bytearray([0xdf,0xdf,0xdf,0xdf,0xdf])
	return pkt
def sws_decode_blk(blk):
	if (len(blk) == 9) and ((blk[8] & 0xfe) == 0xfe):
		data = 0;
		for i in range(8):
			data <<= 1
			if (blk[i] & 0x10) == 0:
				data |= 1
		#print('0x%02x' % data)
		return data
	#print('Error blk:', blk)
	return None
def sws_rd_addr(addr):
	return sws_code_blk(bytearray([0x5a, (addr>>16)&0xff, (addr>>8)&0xff, addr & 0xff, 0x80]))
def sws_code_end():
	return sws_code_blk([0xff])
def sws_wr_addr(addr, data):
	return sws_code_blk(bytearray([0x5a, (addr>>16)&0xff, (addr>>8)&0xff, addr & 0xff, 0x00]) + bytearray(data)) + sws_code_blk([0xff])
def sws_read_dword(serialPort, addr):
	blk = sws_read_blk(serialPort, addr, 4)
	if blk != None:
		return blk[0]+(blk[1]<<8)+(blk[2]<<16)+(blk[3]<<24)
		#return struct.unpack('<I', bytearray(blk))
	return None
def sws_read_blk(serialPort, addr, size):
	# A serialPort.timeout must be set !
	serialPort.timeout = 0.01
	# send addr and flag read
	serialPort.read(serialPort.write(sws_rd_addr(addr)))
	out = []
	for i in range(size):
		# start read data
		serialPort.write([0xff])
		# read 9 bits data
		x = sws_decode_blk(serialPort.read(9))
		if x != None:
			out += [x]
		else:
			serialPort.read(serialPort.write(sws_code_end()))
			out = None
			break
	# stop read
	serialPort.read(serialPort.write(sws_code_end()))
	return out
def set_sws_speed(serialPort, clk):
	#--------------------------------
	# Set register[0x00b2]
	swsbaud = int(round(clk*2/serialPort.baudrate))
	byteSent = serialPort.write(sws_wr_addr(0x00b2, [swsbaud]))
	print('SWire speed for CLK %.1f MHz... ' % (clk/1000000), end='')
	# print('Test SWM/SWS %d/%d baud...' % (int(serialPort.baudrate/5),int(clk/5/swsbaud)))
	read = serialPort.read(byteSent)
	if len(read) != byteSent:
		print('Error: Wrong RX-TX connection!')
		return False
	#--------------------------------
	# Test read register[0x00b2]
	x = sws_read_blk(serialPort, 0x00b2, 1)
	#print(x)
	if x != None and x[0] == swsbaud:
		print('ok.')
		print('SWM/SWS %d/%d bits/s' % (int(serialPort.baudrate/5),int(clk/5/swsbaud)))
		#print('Chip CLK %d MHz, regs[0x0b2]=0x%02x' % (clk/1000000, swsbaud))
		#print('regs[0x0b2]:0x%02x' % x[0])
		return True
	#--------------------------------
	# Set default register[0x00b2]
	serialPort.read(serialPort.write(sws_wr_addr(0x00b2, 0x05)))
	print('no')
	return False

def main():
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
		default=0x40000)
	parser.add_argument(
		'--size','-s', 
		help='Size data (default: 524288)', 
		type=arg_auto_int, 
		default=256)
	
	args = parser.parse_args()
	print('=======================================================')
	print('%s version %s' % (__progname__, __version__))
	print('-------------------------------------------------------')
	if(args.baud < 460800):
		print ('The minimum speed of the COM port is 460800 baud!')
		sys.exit(1)
	print ('Open %s, %d baud...' % (args.port, 230400))
	start_com_baud = args.baud
	if args.tact != 0:
		start_com_baud = 230400
	#-------------------------------------------------------------
	# USB-COM chips throttle the stream into blocks at high speed!
	try:
		serialPort = serial.Serial(args.port, start_com_baud, \
								   serial.EIGHTBITS,\
								   serial.PARITY_NONE, \
								   serial.STOPBITS_ONE)
		serialPort.reset_input_buffer()
		serialPort.setDTR(False)
		serialPort.setRTS(False)
#		serialPort.flushInput()
#		serialPort.flushOutput()
		serialPort.timeout = 0.05
#		print('serialPort.timeout =', serialPort.timeout)
	except:
		print ('Error: Open %s, %d baud!' % (args.port, start_com_baud))
		sys.exit(1)
	if args.tact != 0:
		#--------------------------------
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
		# issue reset-to-bootloader:
		# RTS = either RESET (active low = chip in reset)
		# DTR = active low
		print('Reset module (RTS low)...')
		serialPort.setDTR(True)
		serialPort.setRTS(True)
		time.sleep(0.05)
		serialPort.setDTR(False)
		serialPort.setRTS(False)

		print('Activate (%d ms)...' % args.tact)
		serialPort.write(sws_wr_addr(0x06f, 0x20)) # soft reset mcu
		tact = args.tact/1000.0
		#--------------------------------
    	# Stop CPU|: [0x0602]=5
		blk = sws_wr_addr(0x0602, 0x05)
		serialPort.write(blk)
		if args.tact != 0:
			t1 = time.time()
			while time.time()-t1 < tact:
				for i in range(5):
					serialPort.write(blk)
				serialPort.reset_input_buffer()
		#--------------------------------
        # USB-COM chips throttle the stream into blocks at high speed!
        # Duplication with syncronization
		serialPort.reset_input_buffer()
		serialPort.read(serialPort.write(sws_code_end()))
		serialPort.read(serialPort.write(blk))
		time.sleep(0.01)
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
			serialPort.read(serialPort.write(sws_wr_addr(addr, data)))	
			binWrite += len(data)
			addr += len(data)
			size -= len(data)
		stream.close
		print('\rBin bytes writen:', binWrite)
		print('CPU go Start...')
		serialPort.write(sws_wr_addr(0x0602, b'\x88')) # cpu go Start
		time.sleep(0.05)
		serialPort.flushInput()
		serialPort.flushOutput()
		serialPort.reset_input_buffer()
		serialPort.reset_output_buffer()
	#--------------------------------------
	#  Set the COM speed above 460800 baud
	print('-------------------------------------------------------')
	if start_com_baud != args.tact:
		start_com_baud = args.baud
		print ('ReOpen %s, %d baud...' % (args.port, start_com_baud))
		serialPort.close()

		try:
			serialPort = serial.Serial(args.port, start_com_baud, \
									   serial.EIGHTBITS,\
									   serial.PARITY_NONE, \
									   serial.STOPBITS_ONE)
			serialPort.reset_input_buffer()
			serialPort.setDTR(False)
			serialPort.setRTS(False)
			serialPort.timeout = 0.05
		except:
			print ('Error: Open %s, %d baud!' % (args.port, start_com_baud))
			sys.exit(1)
	#--------------------------------
	# Set SWS speed low
	# SWS Speed = CLK/5/[0xb2] bits/s
	if not set_sws_speed(serialPort, args.clk * 1000000):
		if not set_sws_speed(serialPort, 16000000):
			if not set_sws_speed(serialPort, 24000000):
				if not set_sws_speed(serialPort, 32000000):
					if not set_sws_speed(serialPort, 48000000):
						print('Chip sleep? -> Use reset chip (RTS-RST): see option --tact')
						sys.exit(1)
	print('-------------------------------------------------------')
	#print('Loader Connection...')
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
	print('CPU PC: %08x' % pc)	
	if pc == 0:
		print('Warning: CPU is in reset and stop state! Restart CPU...' )

		print('CPU pc: %08x' % sws_read_dword(serialPort, 0x06bc))	
		print('CPU pc: %08x' % sws_read_dword(serialPort, 0x06bc))	
		print('CPU pc: %08x' % sws_read_dword(serialPort, 0x06bc))	
		print('CPU pc: %08x' % sws_read_dword(serialPort, 0x06bc))	

		serialPort.read(serialPort.write(sws_wr_addr(0x0602, [0x88]))) # cpu go

		print('CPU pc: %08x' % sws_read_dword(serialPort, 0x06bc))	
		print('CPU pc: %08x' % sws_read_dword(serialPort, 0x06bc))	
		print('CPU pc: %08x' % sws_read_dword(serialPort, 0x06bc))	
		time.sleep(0.03)
		print('CPU pc: %08x' % sws_read_dword(serialPort, 0x06bc))	
	# Read floader config
	ext = floader_ext()
	ext.addr = sws_read_dword(serialPort, 0x40004)
	#print('ext.addr: %08x' % ext.addr)	
	if ext.addr == None or ext.addr < 0x840000 or  ext.addr > 0x84fff0:
		print('Floder format or download error!')
		sys.exit(1)
	blk = sws_read_blk(serialPort, ext.addr, 16)
	if blk == None:
		print('Swire Error!')
		sys.exit(1)
	#hex_dump(ext.addr, blk)
	(ext.faddr, ext.pbuf, ext.count, ext.cmd, ext.iack, ext.oack) = struct.unpack('<IIHHHH', bytearray(blk))
	#print('ext.faddr: %08x' % ext.faddr)	
	#print('ext.pbuf: %08x' % ext.pbuf)	
	#print('ext.cmd: %04x' % ext.cmd)	
	#print('ext.iack: %04x' % ext.iack)
	#print('ext.oack: %04x' % ext.oack)
	if ext.oack == 0 or ext.oack != ext.iack or ext.cmd != 0x9f:
		print("Warning: Floader format error or it doesn't work!")
	ext.ver = ext.iack;
	print('Floader id: %X, ver: %x.%x.%x.%x, bufsize: %d' % (lid, (ext.ver>>12)&0x0f,(ext.ver>>8)&0x0f,(ext.ver>>4)&0x0f, ext.ver&0x0f, ext.pbuf))
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
	print('CPU PC: %08x' % pc)	
	if pc == 0:
		print('CPU PC: %08x - CPU Not Runing!' % pc)	
		sys.exit(1)
	#--------------------------------
	# Info read swire addres[size]
	print('-------------------------------------------------------')
	#blk = sws_read_blk(serialPort, args.address, args.size)
	print('Read faddr 0x%06x, size %d ...' % (args.address, args.size))   
	ext.faddr = args.address
	ext.count = args.size
	ext.cmd = 0x03
	ext.iack += 1
	blk = struct.pack('<IIHHH', ext.faddr, ext.pbuf, ext.count, ext.cmd, ext.iack)
	serialPort.read(serialPort.write(sws_wr_addr(ext.addr, blk)))
	while ext.iack == ext.oack:
		#(ext.faddr, ext.pbuf, ext.count, ext.cmd, ext.iack, ext.oack) = struct.unpack('<IIHHHH', bytearray(blk))
		blk = sws_read_blk(serialPort,ext.addr+14, 2)
		if blk == None:
			print('Swire Error!')
			sys.exit(1)
		ext.oack = blk[0] | (blk[1]>>8)
	blk =  sws_read_blk(serialPort, ext.pbuf, args.size)
	if blk == None:
		print('Swire Error!')
		sys.exit(1)
	addr = args.address
	hex_dump(args.address, blk)
	print('-------------------------------------------------------')
	print('Done!')
	sys.exit(0)
 
if __name__ == '__main__':
	main()
