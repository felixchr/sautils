#!/usr/bin/python

_doc_ = '''
cleanpro.py - remove expired files or directories

Author: felix.chr@gmail.com
Usage:
cleanpro.py -c <configuration file>

Note: the configuration file and easylog.py is required
Configuration file example:
/************************
[global]
basedir=/export/home/felixc
logfile=/export/home/felixc/cleanpro.log
admin=felix.cao@aicent.com
# subject definition:
# %host%: hostname
# %user%: current user
alertsubject=[Alert]: Cleanpro Error on %host% by %user%
alertfrom=nocadm@aicent.com
[cap]
path=/export/home/felixc/cap
pattern=.*(\d{14}).cap
judgement=name
timeformat=%Y%m%d%H%M%S
retention=1500
unit=min
type=f
[capbk]
path=/export/home/felixc/data2/cap
pattern=(\d{8})
timeformat=%Y%m%d
retention=15
unit=day
type=d
judgement=name
[syslog]
path=/export/home/felixc/data2/syslog
pattern=syslog.*
judgement=mtime
retention=15
unit=day
type=f
*******************/
global section and the 3 attributes are required
each data define section should have:
path: the directory of the files/directories located
pattern: the regular expression of the file name
	if the judgement is 'name', the pattern should contain '()' to indicate which string is the date stamp
	if the judgement is 'mtime', don't put the '()' in the pattern
judgement: the script will determine whether the file should be deleted according to it, only two values supported:
	name: the script will check the date stamp in the file name
	mtime: the modify time of the file
retention:
	Integer
unit: day, hour, min supported
type: the file type
	f: file
	d: directory
timeformat: see 'man strftime'. Only %Y, %y, %m, %d, %H, %M, %S supported
'''



import time
import re
import ConfigParser
import string, os, sys
import shutil
import getopt
import socket

from easylog import EasyLog

moduleName = 'cleanpro'
ts = {'min' : 60, 'hour' : 3600, 'day' : 86400}

def usage():
	print '''Usage: cleanpro.py -c <configuration file>
	-h: Print help information
	'''

	
def confchk(path, judgement, pattern, unit, retention, type, timeformat):
	'''check configuration items'''
	if type != 'f' and type != 'd':
		return False
	if unit != 'hour' and unit != 'min' and unit != 'day':
		return False
	if judgement != 'name' and judgement != 'mtime':
		return False
	if isinstance(retention, int) == False:
		return False
	
	strinfo = re.compile('%Y|%y|%m|%d|%H|%M|%S|%%')
	t = strinfo.sub('', timeformat)
	m = re.match('%', t)
	if m:
		return False
	if judgement == 'name':
		m = re.match('.*\(.*\).*', pattern)
		if m == None:
			return False
	m = re.match('/.*', path)
	if m == False:
		return False
	return True
		
	
	
try:
	opts, args = getopt.getopt(sys.argv[1:], 'hc:')
except getopt.GetoptError:
	usage()
	sys.exit(2)

now = time.time()

confFile = ''
for o,v in opts:
	if o == '-h':
		print _doc_
		sys.exit()
	if o == '-c':
		if os.path.isfile(v):
			confFile = v
		else:
			print "The configuration file " + v + " doesn't exist or isn't a regular file"
			sys.exit(1)
if confFile == '':
	usage()
	sys.exit(1)

print 'Configuration file is ' + confFile
	
try:
	cf = ConfigParser.ConfigParser()
	cf.read(confFile)
except:
	print "Read configuration file " + confFile + " error!"
	sys.exit(1)
else:
	print "Configuration file ok " + confFile

# Read global settings from configuration file
try:
	basedir = cf.get('global', 'basedir')
	logfile = cf.get('global', 'logfile')
	admin = cf.get('global', 'admin')
except:
	print "Get global settings failed"
	sys.exit(1)
	
log = EasyLog(moduleName, logfile)
log.log('Configuration file is ' + confFile)

script = os.path.abspath(os.path.join(os.getcwd(), __file__))
hostname = socket.gethostname()
ipaddr = socket.gethostbyname(hostname)
user = os.environ['LOGNAME']
runtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))

log.alertinit(script, hostname + '/' + ipaddr, user, runtime)

s = cf.sections()
for item in s:
	if item == 'global':
		continue
	log.log(">>>>> " + item + " <<<<<<<<<<<<<<<<<")
	try:
		path = cf.get(item, "path")
		pattern = cf.get(item, "pattern")
		judgement = cf.get(item, "judgement")
		unit = cf.get(item, "unit")
		retention = cf.getint(item, "retention")
		type = cf.get(item, "type")
		if judgement == 'name':
			timeformat = cf.get(item, "timeformat")
		else:
			timeformat = ''
	except:
		log.err("Configuration items for section " + item + " is not correct. Ignore")
		continue
	log.log('Path: ' + path)
	log.log('Pattern: ' + pattern)
	log.log('Retention: ' + str(retention) + ' ' + unit + '(s)')
	log.log('Time Unit: ' + str(ts[unit]))
	log.log('Time format: ' + timeformat)
	if confchk(path, judgement, pattern, unit, retention, type, timeformat) == False:
		log.err("Configuration itesm for section " + item + " is not correct. Ignore")
		continue	
	
	if judgement == 'name':
		lastKeep = time.strftime('%Y%m%d%H%M%S', time.localtime(int(now) - ts[unit] * retention))
	if judgement == 'mtime':
		lastKeep = int(now) - ts[unit] * retention
	log.log("Last keep " + str(lastKeep))
	if os.access(path, os.R_OK) == False:
		log.err("Path " + path + " can't be accesed!")
		continue
	for file in os.listdir(path):
		fullName = path + os.sep + file
		rmflag = 0
		m = re.match(pattern, file)
		if m:
			if judgement == 'name':
				match = m.group(1)
				try:
					timeStr = time.strftime('%Y%m%d%H%M%S', time.strptime(match, timeformat))
				except:
					continue
				if timeStr <= lastKeep:
					rmflag = 1
			if judgement == 'mtime':
				try:
					mtime = os.stat(fullName)[8]
				except:
					log.err("Read attribute of " + fullName + " failed")
					continue
				if mtime <= lastKeep:
					rmflag = 1
			if rmflag == 1:
				log.log("Removing " + fullName)
				if type == 'f':
					if os.path.isfile(fullName):
						#print "Removing...",
						try:
							os.remove(fullName)
						except:
							log.err('Remove ' + fullName + ' failed')
						else:
							log.log('Remove ' + fullName + ' done')
					else:
						log.log(fullName + " is not a file. Ignore")
				elif type == 'd':
					if os.path.isdir(fullName):
						#if the directory access denied, the os.path.isdir return False
						try:
							shutil.rmtree(fullName)
						except:
							log.err('Remove ' + fullName + ' failed')
						else:
							log.log('Remove ' + fullName + ' done')
					else:
						log.log(fullName + " is not a directory. Ignore")
				#print

if log.alert > 0:
	try:
		alertsubject = cf.get('global', 'alertsubject')
	except:
		alertsubject = "Cleanpro error log from " + hostname + " by " + user
	try:
		alertfrom = cf.get('global', 'alertfrom')
	except:
		alertfrom = user + '@' + hostname + '.com'
	log.log(str(log.alert) + " errors found. Send alert to " + admin)
	log.sendalert(admin, alertsubject.replace('%host%', hostname).replace('%user%', user), alertfrom)