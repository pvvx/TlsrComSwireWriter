#!/usr/bin/env python
 
### ComSwireWriter.py ###
###    Autor: pvvx    ###
 
import sys
import struct
import serial
import platform
import time
import argparse
import os
import io

__progname__ = 'TLSR825x ComSwireReader Utility'
__filename__ = 'ComSwireReader'
__version__ = "19.11.20"

class FatalError(RuntimeError):
	def __init__(self, message):
		RuntimeError.__init__(self, message)

	@staticmethod
	def WithResult(message, result):
		message += " (result was %s)" % hexify(result)
		return FatalError(message)
		
def arg_auto_int(x):
	return int(x, 0)
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
		for el in range(8):
			data <<= 1
			if (blk[el] & 0x10) == 0:
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
def sws_read_data(serialPort, addr, size):
	# A serialPort.timeout must be set !
	serialPort.timeout = 0.01
	# send addr and flag read
	serialPort.read(serialPort.write(sws_rd_addr(addr)))
	out=[]
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
	x = sws_read_data(serialPort, 0x00b2, 1)
	#print(x)
	if x != None and x[0] == swsbaud:
		print('ok.')
		#print('Chip CLK %d MHz, regs[0x0b2]=0x%02x' % (clk/1000000, swsbaud))
		#print('regs[0x0b2]:0x%02x' % x[0])
		return True
	#--------------------------------
	# Set default register[0x00b2]
	serialPort.read(serialPort.write(sws_wr_addr(0x00b2, 5)))
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
		'--address','-a', 
		help='SWire addres (default: 0x06bc (PC))', 
		type=arg_auto_int, 
		default=0x06bc)
	parser.add_argument(
		'--size','-s', 
		help='Size data (default: 4)', 
		type=arg_auto_int, 
		default=4)
	
	args = parser.parse_args()
	print('=======================================================')
	print('%s version %s' % (__progname__, __version__))
	print('-------------------------------------------------------')
	if(args.baud < 460800):
		print ('The minimum speed of the COM port is 460800 baud!')
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
#		print('serialPort.timeout =', serialPort.timeout)
	except:
		print ('Error: Open %s, %d baud!' % (args.port, args.baud))
		sys.exit(1)
	if args.tact != 0:
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
		print('Activate (%d ms)...' % args.tact)
		tact = args.tact/1000.0
		blk = sws_wr_addr(0x0602, bytearray([5]))
		byteSent = serialPort.write(blk)
		if args.tact != 0:
			t1 = time.time()
			while time.time()-t1 < tact:
				for i in range(5):
					byteSent +=	serialPort.write(blk)
				serialPort.reset_input_buffer()
		time.sleep(byteSent*12/args.baud + 0.05 - tact)
		while len(serialPort.read(1000)):
			continue
	#--------------------------------
	time.sleep(0.05)
	#--------------------------------
	# Stop CPU
	# serialPort.read(serialPort.write(sws_wr_addr(0x0602, 0x05)))
	#--------------------------------
	# Set SWS speed low
	# SWS Speed = CLK/5/[0xb2] bits/s
	if not set_sws_speed(serialPort, args.clk * 1000000):
		if not set_sws_speed(serialPort, 16000000):
			if not set_sws_speed(serialPort, 24000000):
				if not set_sws_speed(serialPort, 32000000):
					if not set_sws_speed(serialPort, 48000000):
						sys.exit(1)
	print('-------------------------------------------------------')
	# print('Connection...')
	#--------------------------------
	# Read swire addres[size]
	x = sws_read_data(serialPort, args.address, args.size)
	#--------------------------------
	# Set default register[0x00b2]
	# serialPort.read(serialPort.write(sws_wr_addr(0x00b2, 5)))
	# print('------------------------------------------------')
	if x != None:
		addr = args.address
		print('%06x: ' % addr, end='')
		for i in range(len(x)):
			if (i+1) % 16 == 0:
				print('%02x ' % x[i])
				if i < len(x) - 1:
					print('%06x: ' % (addr + i), end='')
			else:
				print('%02x ' % x[i], end='')
		if len(x) % 16 != 0:
			print('')
		print('-------------------------------------------------------')
		print('Done!')
		sys.exit(0)
	print('Error!')
	sys.exit(1)
 
if __name__ == '__main__':
	main()
