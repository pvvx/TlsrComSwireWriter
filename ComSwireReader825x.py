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
__version__ = "20.11.20"

COMPORT_MIN_BAUD_RATE=460800
COMPORT_DEF_BAUD_RATE=921600
USBCOMPORT_BAD_BAUD_RATE=700000

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
		data = 0;
		for el in range(8):
			data <<= 1
			if (blk[el] & 0x20) == 0:
				data |= 1
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
	serialPort.timeout = 0.01
	# send addr and flag read
	rd_wr_usbcom_blk(serialPort, sws_rd_addr(addr))
	out=[]
	# read size bytes
	for i in range(size):
		# send bit start read byte
		serialPort.write([0xfe])
		# read 9 bits swire, decode read byte
		x = sws_decode_blk(serialPort.read(9))
		if x != None:
			out += [x]
		else:
			# send stop read
			rd_wr_usbcom_blk(serialPort, sws_code_end())
			out = None
			break
	# send stop read
	rd_wr_usbcom_blk(serialPort, sws_code_end())
	return out
# set sws speed according to clk frequency and serialPort baud
def set_sws_speed(serialPort, clk):
	#--------------------------------
	# Set register[0x00b2]
	swsdiv = int(round(clk*2/serialPort.baudrate))
	byteSent = sws_wr_addr_usbcom(serialPort, 0x00b2, [swsdiv])
	print('SWire speed for CLK %.1f MHz... ' % (clk/1000000), end='')
	# print('Test SWM/SWS %d/%d baud...' % (int(serialPort.baudrate/5),int(clk/5/swsbaud)))
	read = serialPort.read(byteSent)
	if len(read) != byteSent:
		if serialPort.baudrate > USBCOMPORT_BAD_BAUD_RATE and byteSent > 64 and len(read) >= 64 and len(read) < byteSent:
			print('!!!!!!!!!!!!!!!!!!!BAD USB-UART Chip!!!!!!!!!!!!!!!!!!!')
			print('UART Output:')
			hex_dump(0,sws_wr_addr(0x00b2, [swsdiv]))
			print('UART Input:')
			hex_dump(0,read)
			print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
			return False
		print('\rError: Wrong RX-TX connection!')
		return False
	#--------------------------------
	# Test read register[0x00b2]
	x = sws_read_data(serialPort, 0x00b2, 1)
	#print(x)
	if x != None and x[0] == swsdiv:
		print('ok.')
		#print('Chip CLK %d MHz, regs[0x0b2]=0x%02x' % (clk/1000000, swsbaud))
		#print('regs[0x0b2]:0x%02x' % x[0])
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
	swsdiv = int(round(24000000*2/serialPort.baudrate))
	#print('default swdiv = %d (0x%02x)' % (swsdiv,swsdiv)) # debug
	serialPort.timeout = 0.01 # A serialPort.timeout must be set !
	swsdiv = int(round(16000000*2/serialPort.baudrate))
	swsdiv_max = int(round(48000000*2/serialPort.baudrate))
	while swsdiv <= swsdiv_max:
		# register[0x00b2] = swsdiv
		rd_sws_wr_addr_usbcom(serialPort, 0x00b2, [swsdiv])
		# send addr and flag read
		rd_wr_usbcom_blk(serialPort, sws_rd_addr(0x00b2))
		# start read data
		serialPort.write([0xfe])
		# read 9 bits data
		blk = serialPort.read(50)
		# send stop read
		rd_wr_usbcom_blk(serialPort, sws_code_end())
		#hex_dump(swsdiv, blk) # debug
		if len(blk) == 9 and blk[8] == 0xfe and (blk[0]&0xe0) == 0xe0:
			cmp = sws_encode_blk([swsdiv])
			#print('info') # debug
			#hex_dump(swsdiv+0xccc00, sws_encode_blk([swsdiv])) # debug
			if blk[1] == cmp[2] and blk[2] == cmp[3] and blk[4] == cmp[5] and blk[6] == cmp[7] and blk[7] == cmp[8]:
				print('UART-SWS %d baud. SW-CLK ~%.1f MHz(?)' % (int(serialPort.baudrate/10), serialPort.baudrate*swsdiv/2000000))
				return True
		swsdiv += 1
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

def main():
	comport_def_name='COM1'
	if platform == "linux" or platform == "linux2":
		comport_def_name = '/dev/ttyS0'
	#elif platform == "darwin":
	#elif platform == "win32":	
	#else:
	parser = argparse.ArgumentParser(description='%s version %s' % (__progname__, __version__), prog=__filename__)
	parser.add_argument(
		'--port', '-p',
		help='Serial port device (default: '+comport_def_name+')',
		default=comport_def_name)
	parser.add_argument(
		'--tact','-t', 
		help='Time Activation ms (0-off, default: 0 ms)', 
		type=arg_auto_int, 
		default=0)
	parser.add_argument(
		'--clk','-c', 
		help='SWire CLK (default: 24 MHz, 0 - auto)', 
		type=arg_auto_int,
		default=24)
	parser.add_argument(
		'--baud','-b', 
		help='UART Baud Rate (default: '+str(COMPORT_DEF_BAUD_RATE)+', min: '+str(COMPORT_MIN_BAUD_RATE)+')', 
		type=arg_auto_int, 
		default=COMPORT_DEF_BAUD_RATE)
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
#		print('serialPort.timeout =', serialPort.timeout)
	except:
		print ('Error: Open %s, %d baud!' % (args.port, args.baud))
		sys.exit(1)
	if args.tact != 0:
		# activate
		activate(serialPort, args.tact);
	if args.clk == 0:
		# auto speed
		if not set_sws_auto_speed(serialPort):
			print('Chip sleep? -> Use reset chip (RTS-RST): see option --tact')
			sys.exit(1)
	else:
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
	# print('Connection...')
	#--------------------------------
	# Read swire addres[size]
	blk = sws_read_data(serialPort, args.address, args.size)
	#--------------------------------
	# Set default register[0x00b2]
	# serialPort.read(serialPort.write(sws_wr_addr(0x00b2, 0x05)))
	# print('------------------------------------------------')
	if blk != None:
		hex_dump(args.address, blk)
		print('-------------------------------------------------------')
		print('Done!')
		sys.exit(0)
	print('Error!')
	sys.exit(1)
 
if __name__ == '__main__':
	main()
