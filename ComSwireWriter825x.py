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

__progname__ = 'TLSR825x ComSwireWriter Utility'
__filename__ = 'ComSwireWriter'
__version__ = "10.11.20"

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
	
def sws_rd_addr(addr):
	return sws_code_blk(bytearray([0x5a, (addr>>16)&0xff, (addr>>8)&0xff, addr & 0xff, 0x80]))
def sws_code_end():
	return sws_code_blk([0xff])
def sws_wr_addr(addr, data):
	return sws_code_blk(bytearray([0x5a, (addr>>16)&0xff, (addr>>8)&0xff, addr & 0xff, 0x00]) + bytearray(data)) + sws_code_blk([0xff])
	
def main():
	parser = argparse.ArgumentParser(description='%s version %s' % (__progname__, __version__), prog=__filename__)
	parser.add_argument(
		'--port', '-p',
		help='Serial port device (default: COM1)',
		default='COM1')
	parser.add_argument(
		'--tact','-t', 
		help='Time Activation ms (0-off, default: 600 ms)', 
		type=arg_auto_int, 
		default=600)
	parser.add_argument(
		'--file','-f', 
		help='Filename to load (default: floader.bin)', 
		default='floader.bin')
	parser.add_argument(
		'--baud','-b', 
		help='UART Baud Rate (default: 230400)', 
		type=arg_auto_int, 
		default=230400)
	
	args = parser.parse_args()
	print('================================================')
	print('%s version %s' % (__progname__, __version__))
	print('------------------------------------------------')
	print ('Open %s, %d baud...' % (args.port, args.baud))
	try:
		serialPort = serial.Serial(args.port, args.baud, \
								   serial.EIGHTBITS,\
								   serial.PARITY_NONE, \
								   serial.STOPBITS_ONE)
#		serialPort.flushInput()
#		serialPort.flushOutput()
		serialPort.timeout = 100*12/args.baud
	except:
		print ('Error: Open %s, %d baud!' % (args.port, args.baud))
		sys.exit(1)
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
	warn = 0
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
	time.sleep(byteSent*12/args.baud)
	while len(serialPort.read(1000)):
		continue
	#--------------------------------
	# Set SWS speed low: [0x00b2]=50
	byteSent = serialPort.write(sws_wr_addr(0x00b2, [45]))
	read = serialPort.read(byteSent+33)
	byteRead = len(read)
	if byteRead != byteSent:
		byteSent = 0
		warn += 1
		print('Warning: Wrong RX-TX connection?')
	#--------------------------------
	# Test read bytes [0x00b2]
	byteSent += serialPort.write(sws_rd_addr(0x00b2))
	# start read
	byteSent += serialPort.write([0xff])
	read = serialPort.read(byteSent-byteRead+33)
	byteRead += len(read)
	if byteRead <= byteSent:
		print('Warning: Pin RX no connection to the module?')		
		warn += 1
	else:
		print('Connection...')		
	# stop read
	byteSent += serialPort.write(sws_code_end())
	read = serialPort.read(byteSent-byteRead+33)
	byteRead += len(read)
	#--------------------------------
	# Load floader.bin
	binWrite = 0
	rdsize = 0x100
	addr = 0x40000
	print('Load <%s> to 0x%04x...' % (args.file, addr))		
	while size > 0:
		print('\r0x%04x' % addr, end = '')		
		data = stream.read(rdsize)
		if not data: # end of stream
			print('send: at EOF')
			break
		byteSent += serialPort.write(sws_wr_addr(addr, data))
		serialPort.reset_input_buffer()
		binWrite += len(data)
		addr += len(data)
		size -= len(data)
	stream.close
	print('\rBin bytes writen:', binWrite)		
	print('CPU go Start...')
	byteSent += serialPort.write(sws_wr_addr(0x0602, [0x88])) # cpu go Start
	serialPort.close
	print('COM bytes sent:', byteSent)
	print('------------------------------------------------')
	if warn == 0:
		print('Done!')
	else:
		print('(%d) Warning' % warn)
	sys.exit(0)
 
if __name__ == '__main__':
	main()
