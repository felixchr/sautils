#!/usr/bin/python

'''
NTPMonitor - Monitor server NTP status
Dependency: ntplib (https://pypi.python.org/pypi/ntplib/)
'''

__version__ = '0.1'

import ntplib
import os
from threading import Thread


datadir = '/export/home/felixc/ntpmonitor'
serverlist = datadir + '/serverlist'
_from = 'ntpmonitor@felix.com'
_to = 'felix.cao@felix.com'

def checkMyNetwork():
    '''
        Check if current host can reach whole network.
        Need baseline hosts are pingable from this host
        Use os.system() instead of ping module because ping module requires root permission
    '''
    ntpstatus = 0
    a = os.popen('/usr/sbin/ntpq -p')
    for line in a:
        if line.find('*') == 0:
            ntpstatus = 1
            break
    if ntpstatus == 0:
        print "NTP on current server is not good. Please check"
        return False
    baseline = ['10.10.8.123', '10.10.4.20', '10.10.40.165']
    ping = '/usr/sbin/ping'
    s = 0
    ll = len(baseline)
    if ll < 3:
        print "Baseline servers must be at least 3"
        return False
    for host in baseline:
        a = os.system(ping + ' ' + host + ' > /dev/null 2>&1')
        if a == 0:
            s += 1
    if s * 100 / ll > 50:
        return True
    else:
        print "More than half of baseline servers are unreachable, please check your settings"
        return False
        
class NTPCheckThread(Thread):
    __result = -1
    __host = ''
    def __init__(self, host):
        Thread.__init__(self)
        self.__host = host
    def run(self):
        '''
            Use ntplib to check NTP status of a server
        '''
        offset = 0
        host = self.__host
        c = ntplib.NTPClient()
        try:
            resp = c.request(host, version=3)
            offset = int(abs(resp.offset * 1000))
        except ntplib.NTPException, e:
            #print "Error: ", host, e
            self.__result = -1
            return
        if(offset > 10):
            #print "Warn: ", host, "Offset is ", offset, "ms"
            self.__result = 0
        else:
            #print "Good: ", host, offset
            self.__result = 1
    def getResult(self):
        return self.__host, self.__result

def checkNTPStatus(host, ver=3):
    '''
        Use ntplib to check NTP status of a server
    '''
    offset = 0
    c = ntplib.NTPClient()
    try:
        resp = c.request(host, version=ver)
        offset = int(abs(resp.offset * 1000))
    except ntplib.NTPException, e:
        print "Error: ", host, e
        return -1
    if(offset > 10):
        print "Warn: ", host, "Offset is ", offset, "ms"
        return 0
    else:
        print "Good: ", host, offset
        return 1

def stat(host, status):
    os.chdir(datadir)
    err1 = "NTP_" + host + "_ERR1"
    #err2 = "NTP_" + host + "_ERR2"
    warn1 = "NTP_" + host + "_WARN1"
    #warn2 = "NTP_" + host + "_WARN2"
    filelist = [warn1, err1]
    err = False
    if status == 1:
        for filename in filelist:
            if os.path.isfile(filename):
                os.remove(filename)
                err = True
        if err:
            alert(host, "OK")
    if status == 0:
        f = open(warn1, 'w')
        f.write(host)
        f.close()
        alert(host, "Bad")
    if status == -1:
        f = open(err1, 'w')
        f.write(host)
        f.close()
        alert(host, "Unreachable")

def alert(host, status):
    _subject = "NTP Monitor: " + host + " is " + status
    comm = '/usr/bin/mailx -s \"' + _subject + '\"'
    if _from != '':
        comm = comm + ' -r ' + _from
        comm = comm + ' ' + _to + ' < /dev/null'
        print comm
        os.system(comm)
        
if __name__ == '__main__':
    if not checkMyNetwork():
        exit(1)
    hostlist = ['10.10.55.98', '10.10.40.167', '10.10.8.88', '192.168.65.214']
    threads = []
    f = open(serverlist)
    for line in f:
        host = line.strip('\n')
        #t = Thread(target=checkNTPStatus, args=(host,))
        t = NTPCheckThread(host)
        threads.append(t)
    f.close()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    for t in threads:
        host, status = t.getResult()
        stat(host, status)
        print host,status
        