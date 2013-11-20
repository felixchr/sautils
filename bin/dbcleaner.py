#!/usr/bin/python

_doc_ = '''
dbcleaner.py - remove expired data from database

Author: Felix Cao(felix.chr@gmail.com)
Usage:
dbcleaner.py -c <configuration file>
'''



import time
import re
import ConfigParser
import string, os, sys
import getopt
import socket
import MySQLdb as mdb

from easylog import EasyLog

moduleName = 'dbcleaner'
ts = {'min' : 60, 'hour' : 3600, 'day' : 86400}

def usage():
	print '''Usage: dbcleaner.py -c <configuration file>
	-h: Print help information
	'''

	
def confchk(host, dbuser, password, dbname, pattern, timeformat, unit, retention):
	'''check configuration items'''
	if unit != 'hour' and unit != 'min' and unit != 'day':
		return False
	if isinstance(retention, int) == False:
		return False
	
	strinfo = re.compile('%Y|%y|%m|%d|%H|%M|%S|%%')
	t = strinfo.sub('', timeformat)
	m = re.match('%', t)
	if m:
		return False
	m = re.match('.*\(.*\).*', pattern)
	if m == None:
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
		host = cf.get(item, "host")
		dbuser = cf.get(item, "user")
		password = cf.get(item, "password")
		dbname = cf.get(item, "dbname")
		pattern = cf.get(item, "pattern")
		timeformat = cf.get(item, "timeformat")
		unit = cf.get(item, "unit")
		retention = cf.getint(item, "retention")
	except:
		log.err("Configuration items for section " + item + " is not correct. Ignore")
		continue
	log.log('Host: \t' + host)
	log.log('Database: \t' + dbname)
	log.log('Table pattern: \t' + pattern)
	log.log('Time format: \t' + timeformat)
	log.log('Retention: \t' + str(retention) + ' ' + unit + '(s)')
	log.log('Time Unit: \t' + str(ts[unit]))

	# if confchk(host, dbuser, password, dbname, pattern, timeformat, unit, retention) == False:
		# log.err("Configuration itesm for section " + item + " is not correct. Ignore")
		# continue	
	try:
		con = mdb.connect(host, dbuser, password, dbname)
	except mdb.Error, e:
		print "Error %d: %s" % (e.args[0], e.args[1])
		log.err("Connect to " + dbname + "@" + host + " failed")
		continue
		
	cur = con.cursor()
	strinfo = re.compile("\(.*\)")
	tableNamePattern = strinfo.sub("%", pattern)
	sql = "SHOW TABLES LIKE \'" + tableNamePattern + "\'"
	
	try:
		cur.execute(sql)
		rows = cur.fetchall()
	except:
		log.err("Execute SQL \'" + sql + "\' failed. Please check")
		continue
	
	
	
	lastKeep = time.strftime('%Y%m%d%H%M%S', time.localtime(int(now) - ts[unit] * retention))
	log.log("Time point is " + str(lastKeep))
	
	for row in rows:
		tname = row[0]
		rmflag = 0
		m = re.match(pattern, tname)
		if m:
			match = m.group(1)
			try:
				#print tname
				timeStr = time.strftime('%Y%m%d%H%M%S', time.strptime(match, timeformat))
			except:
				continue
			if timeStr <= lastKeep:
				rmflag = 1
			if rmflag == 1:
				log.log("Removing table " + tname)
				sql = "drop table " + tname
				try:
					cur.execute(sql)
				except:
					log.err("Execute SQL \'" + sql + "\' failed")
				else:
					log.log("Remove table " + tname + " done")
				#print
	if con:
		con.close()
if log.alert > 0:
	try:
		alertsubject = cf.get('global', 'alertsubject')
	except:
		alertsubject = "dbcleaner error log from " + hostname + " by " + user
	try:
		alertfrom = cf.get('global', 'alertfrom')
	except:
		alertfrom = user + '@' + hostname + '.com'
	log.log(str(log.alert) + " errors found. Send alert to " + admin)
	log.sendalert(admin, alertsubject.replace('%host%', hostname).replace('%user%', user), alertfrom)