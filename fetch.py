import sys

import time
from urllib.request import urlopen, Request


class Response:
    def __init__(self, data, url=None):
        self.data = data
        self.url = url


class TimedFetcher:

    DEFAULT_DELAY = 1
    USER_AGENT = 'webcomic-offliner'

    def __init__(self, delay=None, quiet=False):
        self.last_time = None
        self.delay = TimedFetcher.DEFAULT_DELAY if delay is None else delay
        self.quiet = quiet
        self.count = 0

    def get_current_time(self):
        return time.perf_counter()

    def log_before(self, url):
        if not self.quiet:
            print('Fetching:', url)

    def log_after(self, url, data):
        #print('Fetched {} bytes'.format(len(data)))
        pass

    def sleep(self):
        current_time = self.get_current_time()
        if self.last_time is not None:
            sleep_time = self.last_time + self.delay - current_time
            if sleep_time > 0:
                #print('sleeping for {:.6f} seconds'.format(sleep_time))
                time.sleep(sleep_time)

    def fetch(self, url):
        self.sleep()
        self.log_before(url)
        request = Request(url=url, headers={'User-Agent': self.USER_AGENT})
        with urlopen(request) as fobj:
            data = fobj.read()
            url2 = fobj.geturl()
            self.count += 1
            self.log_after(url, data)
        self.last_time = self.get_current_time()
        return Response(data, url=url2)
