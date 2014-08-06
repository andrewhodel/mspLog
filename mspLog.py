#!/usr/bin/python
# -*- coding: utf-8 -*-

# GPLv2 2014

import sys
import serial
import struct
import binascii
import random
import commands
import time
import datetime
import threading

CMD2CODE = {
    'MSP_IDENT' : 100,
    'MSP_STATUS' : 101,
    'MSP_RAW_IMU' : 102,
    'MSP_SERVO' : 103,
    'MSP_MOTOR' : 104,
    'MSP_RC' : 105,
    'MSP_RAW_GPS' : 106,
    'MSP_COMP_GPS' : 107,
    'MSP_ATTITUDE' : 108,
    'MSP_ALTITUDE' : 109,
    'MSP_ANALOG' : 110,
    'MSP_RC_TUNING' : 111,
    'MSP_PID' : 112,
    'MSP_BOX' : 113,
    'MSP_MISC' : 114,
    'MSP_MOTOR_PINS' : 115,
    'MSP_BOXNAMES' : 116,
    'MSP_PIDNAMES' : 117,
    'MSP_WP' : 118,
    'MSP_BOXIDS' : 119,
    'MSP_SET_RAW_RC' : 200,
    'MSP_SET_RAW_GPS' : 201,
    'MSP_SET_PID' : 202,
    'MSP_SET_BOX' : 203,
    'MSP_SET_RC_TUNING' : 204,
    'MSP_ACC_CALIBRATION' : 205,
    'MSP_MAG_CALIBRATION' : 206,
    'MSP_SET_MISC' : 207,
    'MSP_RESET_CONF' : 208,
    'MSP_SET_WP' : 209,
    'MSP_SWITCH_RC_SERIAL' : 210,
    'MSP_IS_SERIAL' : 211,
    'MSP_DEBUG' : 254,
}

# polling rate in seconds
pollRate =.2
# update rate of graph data in seconds
graphUpdateRate = .2

readyToGraph = False

# codes to graph
GRAPHTHIS = {
#    'MSP_RAW_IMU' : (),
#    'MSP_ATTITUDE' : (),
    #'MSP_ALTITUDE' : (),
#    'MSP_RC' : (),
#    'MSP_MOTOR' : (),
    #'MSP_RAW_GPS' : (),
    'MSP_DEBUG' : (),
}

baud_rate = 115200
ihead_flag = '$M>'
ser = None
data_length = 0
is_valid_serial = False;

# A format character may be preceded by an integral repeat count. For example, the format string '4h' means exactly the same as 'hhhh'.
# don't use integral repeat count, the program expects to count the number of letters to generate the csv header
# https://docs.python.org/2/library/struct.html
#    'int8'   :'b'
#    'uint8'  :'B'
#    'int16'  :'h'
#    'uint16' :'H'
#    'int32'  :'i'
#    'uint32' :'I'
#    'int64'  :'q'
#    'uint64' :'Q'
#    'float'  :'f'
#    'double' :'d'
#    'char'   :'s'
CODEDATATYPES = {
    100: {'type': ''},
    102: {'type': 'hhhhhhhhh'},
    104: {'type': 'hhhhhhhh'},
    105: {'type': 'hhhhhhhh'},
    106: {'type': 'BBIIHHH'},
    107: {'type': 'HHB'},
    108: {'type': 'hhh'},
    109: {'type': 'ih'},
    110: {'type': 'BHHH'},
    210: {'type': ''},
    211: {'type': 'B'},
    254: {'type': 'hhhh'},
}

def sendData(data_size, code, data):
    HEADER='$M<'
    #print "Data", data

    if code==CMD2CODE['MSP_SET_RAW_RC']:
        data_raw=[]
        for i in xrange(len(data)):
            #print data[i] & 0xff
            # uint16
            data_raw+=[data[i] & 0xff]
            data_raw+=[(data[i] >> 8) & 0xff]
            data_raw_chr=reduce(lambda x,y:x+y,map(chr,data_raw))

    elif code==CMD2CODE['MSP_SET_PID']:
        data_raw=[]
        for i in xrange(len(data)):
            #print data[i] & 0xff
            # uint8
            data_raw+=[data[i] & 0xff]
            data_raw_chr=reduce(lambda x,y:x+y,map(chr,data_raw))

    elif data_size==0:
        data_raw=[]
        data_raw_chr=''
    else:
        print "Error: Unknown send"
    checksum=(reduce(lambda x,y:x^y,data_raw+[code]+[data_size]) & 0xff)
    #print HEADER
    #print chr(data_size)+chr(code)+data_raw_chr+chr(checksum)
    ser_data=HEADER+chr(data_size)+chr(code)+data_raw_chr+chr(checksum)
    #print "Data: ", data
    #print "data_raw: ", data_raw
    #print "Checksum: ", hex(checksum)
    #print "data hex", map(hex,data_raw)
    #print "ser_data", map(str,ser_data)
    #print "ser_data_hex", map(ord,ser_data)
    ser.write(ser_data)
    ser.flush()

class pollThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        self.poll()

    def poll(self):
        while 1:

            #~ rc_data = [1401, 1300, 1598, 1389, 1289, 1487, 1278, 1698]  #roll,pitch,yaw,thr,aux1,aux2,aux3,aux4
            #~ i = 7
            #~ while i >= 0:
                #~ rc_data[i] = random.randint(1100, 1900)
                #~ i = i -1
            #~ sendData(16, CMD2CODE['MSP_SET_RAW_RC'], rc_data)
            #sendData(0, CMD2CODE['MSP_RAW_IMU'], [])
            #sendData(0, CMD2CODE['MSP_ATTITUDE'], [])
            #sendData(0, CMD2CODE['MSP_ALTITUDE'], [])
            #sendData(0, CMD2CODE['MSP_RC'], [])
            #sendData(0, CMD2CODE['MSP_MOTOR'], [])
            #sendData(0, CMD2CODE['MSP_RAW_GPS'], [])
            #sendData(0, CMD2CODE['MSP_COMP_GPS'], [])
            sendData(0, CMD2CODE['MSP_DEBUG'], [])
            time.sleep(pollRate)

class graphThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        self.capture()

    def capture(self):
        global readyToGraph
        # write csv header
        f = open('output.csv', 'w')
        for key, value in GRAPHTHIS.iteritems():
            l = len(CODEDATATYPES[CMD2CODE[key]]['type'])
            for x in range(0, l):
                f.write(str(key) + str(x) + ',')
        f.write('DATETIME')
        f.write('\n')
        f.close()
        print 'Waiting for data to flow'
        startTime = int(round(time.time()))
        while 1:
            if readyToGraph == True:
                f = open('output.csv', 'a')
                # we have data
                sys.stdout.write("Collecting Data for " + str(int(round(time.time()))-startTime) + " seconds\r")
                sys.stdout.flush()
                print GRAPHTHIS
                # write csv lines
                for key, value in GRAPHTHIS.iteritems():
                    for v in value:
                        if v == '':
                          f.write('0');
                        else:
                          f.write(str(v))
                        f.write(',')
                #millis epoch
                #millis = int(round(time.time() * 1000))
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f");
                f.write(str(now))
                f.write('\n');
                f.close();
            time.sleep(graphUpdateRate);

class receiveData(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        self.receive_proc()

    def unpack_data(self, data):
        global readyToGraph
        code = ord(data[1:2])
        dl = ord(data[0:1])

        if code in CODEDATATYPES:
            codeword = 'NOT_FOUND'
            for key, value in CMD2CODE.iteritems():
                if (value == code):
                    codeword = key
            try:
                dataTuple = struct.unpack('<' + CODEDATATYPES[code]['type'], data[2:2+dl])
                #print 'code ' + str(code) + ' ' + codeword + ': ' + str(dataTuple)
                if codeword in GRAPHTHIS:
                    readyToGraph = True
                    GRAPHTHIS[codeword] = dataTuple
            except Exception:
                print 'error unpacking'
        else:
            print 'code ' + str(code) + ' not in CODEDATATYPES'
        return

    def receive_proc(self):
        global ser
        rbuffer = ''
        need_read = True
        #search head flag
        pos = 0
        i = 0
        while 1:
            data_length = 0
            try:
                ser.flush()
                data_length = ser.inWaiting()
            except Exception, ex:
                print 'inWaiting is_valid_serial fail'
                connect()

            if data_length > 0:
                rbuffer += ser.read(data_length)
                need_read = 0
            else:
                time.sleep(0.1)
                continue

            while not need_read:
                try:
                    pos = rbuffer.find(ihead_flag)
                except Exception, ex:
                    need_read = True
                    break

                #print 'pos:' + str(pos)
                if pos >=0:
                    #print len(rbuffer)
                    try:
                        dl = ord(rbuffer[pos+len(ihead_flag):pos+len(ihead_flag)+1])
                    except Exception, ex:
                        need_read = True
                        break
                    data = rbuffer[pos+len(ihead_flag):pos+len(ihead_flag) + dl + 3]
                    #print 'data_len:' + str(len(data))
                    if (dl + 3) == len(data) and len(data) > 3:
                        checksum = 0
                        orig_checksum = data[-1:]
                        #sign checksum
                        for i in data[:-1]:
                            checksum = checksum ^ ord(i)
                        #print "checksum:" + str(checksum)
                        #print "orig_checksum:" + str(ord(orig_checksum))
                        if ord(orig_checksum) == checksum:
                            self.unpack_data(data)
                    #not complete data
                    elif (dl + 3) > len(data):
                        need_read = True
                        break
                    rbuffer = rbuffer[pos + len(ihead_flag) + len(data):]
                else:
                    rbuffer = ''
                    need_read = True
                    break

def connect():
    try:
        global ser
        while True:
            serial_port = sys.argv[1]
            print serial_port + ' Opened with baud rate ' + str(baud_rate)
            if serial_port:
                ser = serial.Serial(serial_port, baud_rate)
                if ser:
                    break
            time.sleep(1)
    except Exception, ex:
        print 'open serial port fail\n'
        sys.exit()
    is_valid_serial = True;


if __name__ == "__main__":

    if len(sys.argv) == 3:
        baud_rate = sys.argv[2]

    connect()
    #open csv
    #wait 5 sec
    print 'Waiting 5 seconds to begin, otherwise FC resets'
    time.sleep(5)
    #start threads
    rd = receiveData()
    rd.daemon = True
    rd.start()
    pd = pollThread()
    pd.daemon = True
    pd.start()
    gd = graphThread()
    gd.daemon = True
    gd.start()
    print 'Polling at ' + str(pollRate) + 's intervals'
    print 'Writing to output.csv at ' + str(graphUpdateRate) + 's intervals'
    print 'Use Ctrl-C to exit'
    while True:
        try:
            time.sleep(.5)
        except KeyboardInterrupt:
            print 'Exiting'
            sys.exit();
