#!/bin/bash

def sendalert(_from, _to, _subject, _content = ''):
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
    timeStr = self.timestamp()
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
    
def timestamp(format = "%Y-%m-%d %H:%M:%S"):
    now = time.time()
    return time.strftime(format, time.localtime(now))