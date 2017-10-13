#!/usr/bin/env python

from multiprocessing import Process, Queue
import sys
import Queue as QMod
import httplib
import ssl
import time
import zlib
from math import log
import argparse


class Span:
    def __init__(self, start=None, last=None, now=None):
        self.start = start
        self.last = last
        self.now = now

    def set_time_start(self):
        self.now = time.time()
        self.start = self.now
        self.last = self.start - 1
        return self

    def set_count_start(self):
        self.now, self.start, self.last = 0, 0, 0
        return self

    def add_count(self, size=1):
        self.now += size
        return self

    def set_now(self):
        self.last, self.now = self.now, time.time()
        return self

    def set_last_bytes(self):
        self.last = self.now

    def short(self):
        if self.now == self.last:
            return 1
        return self.now - self.last

    def long(self):
        if self.now == self.start:
            return 1
        return self.now - self.start


#####################
# config constants
#####################
BUF_SIZE = 8192
PCOUNT = 4
# how often to report progress
MODDER = 40
# how often to update the sleeps for rate control
RATE_MODDER = 10
# default delay. determined by trial and error
DELAY = .3
# using python2.7
SEVEN = False
# amount to scale timing changes
# determined by trial and error
MODSCALE = .05
# maximum delay
# determined by trial and error
MAXDELAY = 7

#####################
# defaults
#####################
HOST = 'localhost'
PORT = 443
# default connection rate
TARGET = 20
# zip the data
ZIP = True
# use ssl
SSL = False

METHOD = 'GET'
PATH = '/'


def web_load(qu):
    if SEVEN:
        ctx = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)

    while True:
        try:
            pakt = qu.get(timeout=5)

            headers = {}
            if ZIP:
                packet = zlib.compress(pakt[1])
                headers['Zip'] = 'True'
            else:
                packet = pakt[1]

            # send pkt
            time.sleep(pakt[0])
            if SSL:
                if SEVEN:
                    h = httplib.HTTPSConnection(HOST, port=PORT, context=ctx)
                else:
                    h = httplib.HTTPSConnection(HOST, port=PORT)
            else:
                h = httplib.HTTPConnection(HOST, port=PORT)

            h.request(METHOD, PATH, packet, headers)
            _ = h.getresponse()
        except KeyboardInterrupt:
            return
        except QMod.Empty:
            return


def read_pkt(f_name):
    """
        generator that read phone home packets from a file
        and yields them
    """
    with open(f_name) as f:
        while True:
            try:
                pkt_len = int(f.readline())
            except:
                raise StopIteration

            left = pkt_len + 1
            pkt_data = []

            while True:
                to_read = min(BUF_SIZE, left)
                dat = f.read(to_read)
                left -= len(dat)
                pkt_data.append(dat)
                if left == 0:
                    break
                if left < 0 or len(dat) == 0:
                    raise StopIteration

            pakt = ''.join(pkt_data)
            pakt = pakt[:-1]
            yield pakt


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-o', '--host', default=HOST)
    parser.add_argument('-p', '--port', default=PORT)
    parser.add_argument('-z', '--zip', action='store_true')
    parser.add_argument('-s', '--ssl', action='store_true')
    parser.add_argument('-t', '--target', default='99999')
    parser.add_argument('-f', '--file')
    args = vars(parser.parse_args())

    TARGET = int(args['target'])
    HOST = args['host']
    PORT = int(args['port'])
    if args['file']:
        fname = args['file']
    else:
        print 'Must specify a file'
        sys.exit(-1)

    q = Queue(PCOUNT * 4)

    plist = []
    for i in range(PCOUNT):
        plist.append(Process(target=web_load, args=(q,)))

    for i in plist:
        i.start()

    display = Span().set_time_start()
    b_cnt = Span().set_count_start()
    rate_time = Span().set_time_start()
    conns = Span().set_count_start()

    delay = DELAY
    try:
        while True:
            for pkt in read_pkt(fname):
                b_cnt.add_count(len(pkt))
                conns.add_count()

                if conns.now % MODDER == 0:
                    display.set_now()

                    c = conns.now
                    long_r = int((c*1.0) / display.long())
                    short_r = int((MODDER*1.0) / display.short())
                    long_b = int((b_cnt.long() * 1.0) / display.long())
                    short_b = int((b_cnt.short() * 1.0) / display.short())
                    format_str = "{:10} [{:^10}]: {:5} ({:^5}) {:8} <{:^8}>  {:<10}"
                    print format_str.format(c, b_cnt.long(), long_r, short_r, long_b, short_b, round(delay,3))
                    conns.set_last_bytes()
                    b_cnt.set_last_bytes()

                if conns.now % RATE_MODDER == 0 and \
                   conns.now > 4 * RATE_MODDER:
                    rate_time.set_now()
                    rate = RATE_MODDER / (rate_time.short())
                    delay += MODSCALE * log(rate/TARGET)
                    delay = min(max(delay, 0), MAXDELAY)

                q.put((delay, pkt))
    except KeyboardInterrupt:
        pass

    for i in plist:
        i.join()
    sys.exit()
