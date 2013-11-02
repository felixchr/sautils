#!/usr/bin/python

import sys,string, os
import time
'''
	Write log to logfile
	Author: felix.chr@gmail.com
	usage:
		log = easyLog(mName, 'yourfile.log')
		log.log('Error 443')
	Last update: 12/20/2012 4:04PM
'''

class EasyLog:
	logfile = ''
	errfile = ''
	mName = ''
	alert = 0
	sent = 0
	status = 0
	seq = 0
	def __init__(self, _mName = '', _logfile = ''):
		logfile = ''
		mName = ''
		errfile = ''
		if _mName != '':
			mName = _mName
		else:
			mName = 'NoName'
		now = time.time()
		if _logfile != '':
			logfile = time.strftime(_logfile, time.localtime(now))
		else:
			logfile = '/tmp/' + mName + '_run.log'

		self.logfile = logfile
		self.mName = mName
		
		try:
			logHandle = file(logfile, 'a')
		except:
			print 'Create/open log file ' + logfile + ' for ' + mName + ' failed'
			sys.exit(1)
		else:
			logHandle.close()
			self.status = 1
			timeStr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
			self.log('------' + timeStr + ' Module ' + mName + ' log begin ------')
	def __del__(self):
		if self.status == 1:
			logfile = self.logfile
			mName = self.mName
			errfile = self.errfile
			if self.sent == 1 or self.alert == 0:
				try:
					os.remove(errfile)
				except:
					self.log('Remove error log ' + errfile + ' failed.')
			now = time.time()
			timeStr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
			self.log('------' + timeStr + ' Module ' + mName + ' log end ------')
	def alertinit(self, _script = '', _host = '', _user = '', _runtime = ''):
		mName = self.mName
		now = time.time()
		stamp = time.strftime("%Y%m%d%H%M%S", time.localtime(now))
		errfile = '/tmp/' + mName + '.err.' + stamp
		try:
			errHandle = file(errfile, 'a')
		except:
			print 'Create error log ' + errfile + ' for ' + mName + ' failed'
			sys.exit(2)
		errHandle.write('Script: \t' + _script + '\n')
		errHandle.write('Host: \t' + _host + '\n')
		errHandle.write('User: \t' + _user + '\n')
		errHandle.write('Date: \t' + _runtime + '\n')
		errHandle.write('Log file: \t' + self.logfile + '\n')
		timeStr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
		errHandle.write('----------Error Log of ' + mName + ' ' + timeStr + '----------\n')
		self.log('Alert log file ' + errfile + ' created.')
		errHandle.close()
		self.errfile = errfile
	def log(self, _msg, _level = 'Info', _inc = 1):
		logfile = self.logfile
		mName = self.mName
		try:
			logHandle = file(logfile, 'a')
		except:
			print 'Open log file ' + logfile + ' for ' + mName + ' failed'
			sys.exit(1)
		now = time.time()
		timeStr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
		seq = self.seq + _inc
		self.seq = seq
		msg = timeStr + ' [' + _level + '] ' + str(seq) + ' ' + _msg + '\n'
		try:
			logHandle.write(msg)
		except:
			print 'Write log failed ' + logfile
			sys.exit(1)
		logHandle.close()
	def err(self, _msg, _level = "ERROR"):
		errfile = self.errfile
		try:
			errHandle = file(errfile, 'a')
		except:
			print 'Open error log ' + errfile + ' for ' + mName + ' failed'
			sys.exit(2)
		now = time.time()
		timeStr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
		seq = self.seq + 1
		try:
			errHandle.write(timeStr + ' [' + _level + '] ' + str(seq) + ' ' + _msg + '\n')
		except:
			self.log('Write error log failed ' + errfile)
		self.seq = seq
		self.log(_msg, _level, 0)
		self.alert = self.alert + 1
		errHandle.close()
	def sendalert(self, _to, _subject, _from = ''):
		mName = self.mName
		sent = 0
		if self.alert == 0:
			return
		errfile = self.errfile
		try:
			errHandle = file(errfile, 'a')
		except:
			print 'Open error log ' + errfile + ' for ' + mName + ' failed'
			sys.exit(2)
		now = time.time()
		timeStr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
		errHandle.write('--------- End of Error Log of ' + mName + ' ' + timeStr + '------')
		errHandle.close()
		comm = '/usr/bin/mailx -s \"' + _subject + '\"'
		if _from != '':
			comm = comm + ' -r ' + _from
		comm = comm + ' ' + _to + ' < ' + self.errfile
		print comm
		if os.system(comm) == 0:
			self.log('Send out alert email by ' + comm)
			sent = 1
		else:
			self.log('Send out alert email by ' + comm + ' failed!')
		self.sent = sent
		