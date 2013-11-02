#!/usr/bin/python

_doc_ = '''
packpro.py - remove expired files or directories

Author: felix.chr@gmail.com
Usage:
packpro.py -c <configuration file>

Note: the configuration file and easylog.py is required
Configuration file example:
/************************
[test]
path=/export/home/felixc/data2/cap
pattern=^(\d{8})$
judgement=name
timeformat=%Y%m%d
unit=day
type=d
range=5
removeorig=yes
[test2]
path=/export/home/felixc/data2/syslog
pattern=syslog.\d*$
judgement=mtime
unit=min
range=100+
removeorig=no
type=f
[test3]
path=/export/home/felixc/data2/out
pattern=(\d{10})\d{4}.cap$
timeformat=%Y%m%d%H
judgement=name
unit=hour
range=100
removeorig=no
type=f
# allinone indicate to add all files in one package, only valid when type is "f"
allinone=yes
# outdir, define the output path if the allinone is "yes"
outdir=/export/home/felixc/data2
# outformat, define the output format if the allinone is "yes"
# support strftime, %match% = pattern matched result
outformat=%match%_%Y%m%d%H%M
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
range:
	Integer or Interger with "+"
unit: day, hour, min supported
type: the file type
	f: file
	d: directory
timeformat: see 'man strftime'. Only %Y, %y, %m, %d, %H, %M, %S supported
removeorig: whether remove original file/directory
allinone: whether pack all files into one output file
outdir: valid only allineone is "yes"
'''


import time
import re
import ConfigParser
import string, os, sys
import shutil
import getopt
import socket

from easylog import EasyLog

moduleName = 'packpro'
gzip = '/usr/bin/gzip'
tar = '/usr/bin/tar'
ts = {'min' : 60, 'hour' : 3600, 'day' : 86400}

def usage():
	print '''Usage: packpro.py -c <configuration file>
	-h: Print help information
	'''

	
def confchk(path, judgement, pattern, unit, range, type, timeformat):
	'''check configuration items'''
	if type != 'f' and type != 'd':
		return "type"
	if unit != 'hour' and unit != 'min' and unit != 'day':
		return "day"
	if judgement != 'name' and judgement != 'mtime':
		return "judgement"
	m = re.match(r'^([0-9]*)\+*$', range)
	if m == False:
		return "range"	
	strinfo = re.compile('%Y|%y|%m|%d|%H|%M|%S|%%')
	t = strinfo.sub('', timeformat)
	m = re.match('%', t)
	if m:
		return "timeformat"
	if judgement == 'name':
		m = re.match('.*\(.*\).*', pattern)
		if m == None:
			return "pattern"
	m = re.match('/.*', path)
	if m == False:
		return "path"
	return "ok"
		
	
	
try:
	opts, args = getopt.getopt(sys.argv[1:], 'hc:')
except getopt.GetoptError:
	usage()
	sys.exit(2)

now = time.time()

confFile = ''
for o,v in opts:
	if o == '-h':
		usage()
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
		range = cf.get(item, "range")
		type = cf.get(item, "type")
		if judgement == 'name':
			timeformat = cf.get(item, "timeformat")
		else:
			timeformat = ''
	except:
		log.err("Configuration items for section " + item + " is not correct. Ignore")
		continue
	log.log('Path:\t' + path)
	log.log('Pattern:\t' + pattern)
	log.log('Range:\t' + str(range) + ' ' + unit + '(s)')
	log.log('Time unit:\t' + str(ts[unit]))
	log.log('Time format:\t' + timeformat)

	filelist = []
	searchFlag = 0
	m = re.match("^([0-9]*)\+$", range)
	if m:
		searchFlag = 1
		rangeN = int(m.group(1))
	else:
		rangeN = int(range)
	allinone = "no"
	if type == "f" and searchFlag == 0:
		try:
			allinone = cf.get(item, "allinone")
			if allinone == "yes":
				outdir = cf.get(item, "outdir")
				outformat = cf.get(item, "outformat")
				if os.access(outdir, os.W_OK) == False:
					log.err("Output directory " + outdir + " can't be accesed! Ignore")
					continue
				
			#outfile = os.path.join(outdir, outformat)
		except:
			allinone = "no"
	tconf = confchk(path, judgement, pattern, unit, range, type, timeformat)
	if tconf != "ok":
		log.err("Configuration item " + tconf + " for section " + item + " is not correct. Ignore")
		continue
	if judgement == 'name':
		lastKeep = time.strftime('%Y%m%d%H%M%S', time.localtime(int(now) - ts[unit] * rangeN))
	if judgement == 'mtime':
		lastKeep = int(now) - ts[unit] * rangeN
	log.log("Time point is " + str(lastKeep))
	
	if os.access(path, os.R_OK) == False:
		log.err("Path " + path + " can't be accesed!")
		continue
	try:
		os.chdir(path)
	except:
		log.err("Change working directory to " + path + " failed")
	else:
		log.log("Change working directory to " + path)
	if searchFlag == 0:
		if judgement == 'name':
			timePattern = time.strftime(timeformat, time.localtime(int(now) - ts[unit] * rangeN))
			if allinone == "yes":
				outfile = outformat.replace("%match%", timePattern)
				outfile = os.path.join(outdir, time.strftime(outfile, time.localtime()))
			rep = re.compile("\(.*\)")
			namePattern = rep.sub(timePattern, pattern)
			#print namePattern
			res = [f for f in os.listdir(path) if re.search(namePattern, f)]
			for file in res:
				filelist.append(file)
	if searchFlag == 1:
		for file in os.listdir(path):
			fullName = os.path.join(path, file)
			zipflag = 0
			m = re.match(pattern, file)
			if m:
				if judgement == 'name':
					match = m.group(1)
					#print match
					try:
						timeStr = time.strftime('%Y%m%d%H%M%S', time.strptime(match, timeformat))
					except:
						continue
					if timeStr <= lastKeep:
						zipflag = 1
				if judgement == 'mtime':
					try:
						mtime = os.stat(fullName)[8]
					except:
						log.err("Read attribute of " + fullName + " failed")
						continue
					if mtime <= lastKeep:
						zipflag = 1
				if zipflag == 1:
					filelist.append(file)
	for name in filelist:
		cmd = ""
		if type == "f":
			if allinone == "no":
				cmd = gzip + " " + name
			elif allinone == "yes":
				if os.path.isfile(outfile + ".tar"):
					cmd = tar + " rf " + outfile + ".tar " + name
				else:
					cmd = tar + " cf " + outfile + ".tar " + name
		elif type == "d":
			cmd = tar + " cf - " + name + " | " + gzip + " -c >" + name + ".tar.gz"
		log.log("Command is: " + cmd)
		exe = os.system(cmd)
		if exe == 0:
			log.log("Execute " + cmd + " successfully")	
			try:
				removeorig = cf.get(item, "removeorig")
			except:
				removeorig = "no"
			
			if removeorig == "yes":
				log.log("Removing " + name)
				if type == 'f' and allinone == "yes":
					if os.path.isfile(name):
						#print "Removing...",
						try:
							os.remove(name)
						except:
							log.err('Remove ' + name + ' failed')
						else:
							log.log('Remove ' + name + ' done')
					else:
						log.log(name + " is not a file. Ignore")
				elif type == 'd':
					if os.path.isdir(name):
						#if the directory access denied, the os.path.isdir return False
						try:
							shutil.rmtree(name)
						except:
							log.err('Remove ' + name + ' failed')
						else:
							log.log('Remove ' + name + ' done')
					else:
						log.log(name + " is not a directory. Ignore")
		else:
			log.err("Execute " + cmd + " failed. Keep original file/directory")
	if type == "f" and allinone == "yes" and os.path.isfile(outfile + ".tar"):
		log.log("Compressing output file...")
		cmd = gzip + " " + outfile + ".tar"
		log.log("Command is " + cmd)
		exe = os.system(cmd)
		if exe == 0:
			log.log("Execute " + cmd + " successfully.")	
		else:
			log.err("Execute " + cmd + " failed.")
if log.alert > 0:
	try:
		alertsubject = cf.get('global', 'alertsubject')
	except:
		alertsubject = "packpro error log from " + hostname + " by " + user
	try:
		alertfrom = cf.get('global', 'alertfrom')
	except:
		alertfrom = user + '@' + hostname + '.com'
	log.log(str(log.alert) + " errors found. Send alert to " + admin)
	log.sendalert(admin, alertsubject.replace('%host%', hostname).replace('%user%', user), alertfrom)