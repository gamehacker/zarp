from signal import SIGINT
from datetime import date, datetime
from commands import getoutput
from subprocess import Popen
import config
import os
import socket
import fcntl
import struct

from cmd import Cmd 
"""Utility class housing various functions in use
	throughout the zarp framework.
"""

isDebug = False
DEBUG_LOG = 'zarp_debug.log'
buffered = None

def version():
	"""Zarp version"""
	return "0.10"

def header():
	"""Zarp header"""
	print '\t\033[32m ____   __   ____  ____'
	print '\t(__  ) / _\ (  _ \(  _ \''
	print '\t / _/ /    \ )   / ) __/'
	print '\t(____)\_/\_/(__\_)(__)\033[0m'
	print "\t    [\033[33mVersion %s\033[0m]\t\t\t"%(version())
	if isDebug:
		print '\t      \033[34m[DEBUGGING]\033[0m'

def Error(msg):
	"""Prints the given message and, if debugging is on,
	   logs it.
	"""
	print '\033[31m[-] %s\033[0m'%(msg)
	if isDebug:
		debug(msg)	

def Msg(msg):
	"""Prints a warning message"""
	print '\033[33m[!] %s\033[0m'%(msg)

def debug(msg):
	"""If debugging is enabled, write the given string
	   to the debug file
	"""
	if isDebug and not os.path.islink(DEBUG_LOG):
		with open(DEBUG_LOG, 'a+') as f:
			f.write(format('[%s %s] %s\n'%(date.today().isoformat(), datetime.now().strftime("%I:%M%p"), msg)))

def next_ip(ip):
	"""Return the next IP address following the given IP address.
	   It needs to be converted to an integer, then add 1, 
	   then converted back to an IP address
	"""
	ip2int = lambda ipstr: struct.unpack('!I', socket.inet_aton(ipstr))[0]
	int2ip = lambda n: socket.inet_ntoa(struct.pack('!I', n))
	return int2ip(ip2int(ip) + 1)

def is_in_subnet(ip, mask):
	"""Check if a given IP address is lies within the given netmask
	   TRUE if 'ip' falls within 'mask'
       FALSE otherwise
	"""
	ipaddr = int(''.join([ '%02x' % int(x) for x in ip.split('.')]), 16)
	netstr,bits = net.split('/')
	netaddr = int(''.join([ '%02x' % int(x) for x in netstr.split('.')]), 16)
	mask = (0xffffffff << (32 - int(bits))) & 0xffffffff
	return (ipaddr & mask) == (netaddr & mask)	

def check_program(prog):
	"""Check if program is installed and pathed properly"""
	tmp = init_app('which {0}'.format(prog), True)
	if len(tmp) > 0 and '/' in tmp:
		return True
	else:
		return False

def init_app(prog, output):
	"""inititalize an application 
	   PROG is the full command with args
       OUTPUT true if output should be returned 
	   false if output should be dumped to null.  This will
	   return a process handle and is meant for initializing 
	   background processes.  Use wisely.
	"""
	# dump output to null
	if not output:
		try:
			null = open(os.devnull, 'w')
			proc = Popen(prog, stdout=null, stderr=null)
		except Exception,j:
			Error("Error initializing app: %s"%j)
			return False
		return proc
	# just grab output
	else:
		return getoutput(prog)

def kill_app(proc):
	"""Kill a process"""
	try:
		os.kill(proc.pid, SIGINT)
	except Exception, j:
		Error("Error killing app: %s"%(j))
		return False
	return True

def get_monitor_adapter():
	"""Try and automatically detect which adapter is in monitor mode.
       NONE if there are none.
	"""
	tmp = init_app('iwconfig', True)
	iface = None
	for line in tmp.split('\n'):	
		if line.startswith(' '):
			continue	
		elif len(line.split(' ')[0]) > 1:
			if 'Mode:Monitor' in line:
				return line.split(' ')[0]
	return None

def enable_monitor(channel=None):
	"""Enable monitor mode on the wireless adapter
	   CHANNEL is the channel to monitor on.
	"""
	tmp = init_app('iwconfig', True)
	iface = None
	for line in tmp.split('\n'):
		if line.startswith('wlan'):
			try:
				iface = line.split(' ')[0]
				if channel is None:
					tmp = getoutput('airmon-ng start {0}'.format(iface))
				else:
					tmp = getoutput('airmon-ng start {0} {1}'.format(iface,channel))
				debug("started \'%s\' in monitor mode"%iface)
			except Exception, j:
				Error("Error enabling monitor mode: %s"%j)
			break
	return get_monitor_adapter()

def disable_monitor():
	"""Kill the monitoring adapter"""
	try:
		adapt = get_monitor_adapter()
		if not adapt is None:
			tmp = getoutput('airmon-ng stop %s'%adapt)
			debug('killed monitor adapter %s'%adapt)
	except Exception, j:
		Error('error killing monitor adapter:%s'%j)

def verify_iface(iface):
	"""Verify that the given interface exists
	"""
	try:
		tmp = init_app('ifconfig', True)
		if not iface in tmp:
			return False
		return True
	except Exception, j:
		return False

def does_file_exist(fle):
	"""Check if a local file exists.
	"""
	try:
		with open(fle) as f: pass
	except IOError:
		return False
	return True

def get_local_ip(adapter):
	""" Return the IP address of an adapter.
		@param adapter is the adapter to fetch from.
		I do not know how portable this is yet.
	"""
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		addr = socket.inet_ntoa(fcntl.ioctl(
			s.fileno(),
			0x8915,
			struct.pack('256s', adapter[:15])
			)[20:24])
	except:
		addr = None
	return addr

def get_layer_bytes(layer):
	"""I havent found a neat way to pull RAW bytes out of Scapy packets,
	   so I just wrote a small utility function for it.
	"""
	arr = []
	layer = layer.encode('hex')
	for (f, s) in zip(layer[0::2], layer[1::2]):
		arr.append(f + s)
	return arr

def get_subclass(module, base_class):
	"""Return overloaded classes of loaded module.
	   @param module is the loaded user module
	   @param base_class is the class it should be overloading
	"""
	for name in dir(module):
		obj = getattr(module, name)
		try:
			if issubclass(obj,base_class) and obj != base_class:
				return obj
		except:
			pass
	return None

def background():
	""" Drops the user back into their shell environment.
		'exit' brings them back.
	"""
	Msg('\'exit\' when you\'re done..')
	if 'SUDO_USER' in os.environ:
		usr = os.environ['SUDO_USER']
	else:
		# hacky?
		usr = init_app('who -m | awk \'{print $1;}\'', True)
	
	shell = os.environ['SHELL'] if 'SHELL' in os.environ else '/bin/bash'
	if check_program(shell):
		os.system('su -c %s %s'%(shell, usr))
	else:
		os.system('su -c /bin/sh %s'%usr)
	
def print_menu(arr):
	global buffered
	"""Main menu printer
	   @param arr is the menu array to print.  Fetches input, 
		parses and built-in command keywords, and returns the selected idx.
	"""

	if not buffered is None:
		# buffered input, return
		if len(buffered) > 0: 
			return buffered.pop(0)
		else:	
			buffered = None

	tmp = Cmd()
	arr = ['\t[%d] %s'%(x+1,arr[x]) for x in xrange(len(arr))] 
	tmp.columnize(arr,35)
	print '\n0) Back'
	try:
		choice = raw_input('> ')
		if 'info' in choice:
			Error('\'info\' not implemented yet.')
			choice = -1
		elif 'set' in choice:
			opts = choice.split(' ')
			if opts[1] is None or opts[2] is None:
				return
			print '[!] Setting \033[33m%s\033[0m -> \033[32m%s\033[0m..'%(opts[1], opts[2])
			config.set(opts[1], opts[2])
			choice = -1
		elif 'opts' in choice:
			config.dump()
			choice = -1
		elif 'quit' in choice or 'exit' in choice:
			# hard quit
			os._exit(1)
		elif 'bg' in choice:
			background()
		else:
			# buffered input
			choice = choice.split(' ')
			if len(choice) > 1: 
				buffered = []
				for entry in choice[1:]:
					buffered.append(int(entry))
			choice = int(choice[0])
	except Exception:
		os.system('clear')
		choice = -1
	return choice
