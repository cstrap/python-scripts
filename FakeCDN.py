#!/usr/bin/env python
# -*- coding: utf-8 *-*

"""
Call by CMS: http://localhost:8888/activate?url=/path...
File get from CMS_SERVER and copied to CDN_DIR
"""

import logging
import os
import sys
import threading
import urllib
import urlparse

from BaseHTTPServer import BaseHTTPRequestHandler
from BaseHTTPServer import HTTPServer
from SocketServer import ThreadingMixIn

try:
    from local_settings import PORT, CMS_SERVER
except Exception, e:
    print "No local settings found."
    sys.exit(1)


ALLOWED_CHARS = \
    'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890-./'

"""
Serving file with simple http server
$ mkdir -p /tmp/CDN && cd /tmp/CDN && python -m SimpleHTTPServer 8008
"""
CDN_DIR = '/tmp/CDN'


def clean_string(chunk):
    result = chunk
    for c in chunk:
        if c not in ALLOWED_CHARS:
            result = result.replace(c, '-')
    return result


def logger():
    """
    Stream log to console
    """

    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    logger.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def reporthook(blocks_read, block_size, total_size):
    """
    Code from Doug Helman - PyMOTW
    total_size is reported in bytes
    block_size is the amount read each time
    blocks_read is the number of blocks successfully read
    """

    if not blocks_read:
        log.info('Connection opened')
        return

    if total_size < 0:
        log.info('Read %d blocks (%d bytes)' % \
            (blocks_read, blocks_read * block_size))
    else:
        amount_read = blocks_read * block_size
        log.info('Read %d blocks, or %d/%d' % \
            (blocks_read, amount_read, total_size))


class Dispatcher(object):
    """
    Dispatcher - command pattern
    """

    routing = {}

    def __init__(self, route, query_string):
        self._initCmd()
        self._route = route

        # The cms need this tricks...
        self._url = urlparse.parse_qs(query_string).get('url', '')[0]
        self._file_to_get = "%s%s" % (CMS_SERVER, urllib.quote(self._url))
        self._file_name = self._file_to_get.split('/')[-1:][0]
        self._file_folder = "%s%s" % (CDN_DIR,
                '/'.join(clean_string(s) for s in self._url.split('/')[:-1]))
        self._file_stored = "%s/%s" % (self._file_folder,
                clean_string(self._file_name.replace('%20', '-')))
        self._error = False

    def _initCmd(self):
        self.routing['/activate'] = self._activate
        self.routing['/deactivate'] = self._dectivate

    def dispatch(self):
        log.debug("Thread name: ", threading.currentThread().getName())
        if self._route in self.routing.keys():
            return self.routing[self._route]()
        return "KO"

    def _activate(self):
        """
        Copy file on storage
        """

        log.info('File name: ', self._file_name)
        log.info('File folder: ', self._file_folder)
        try:
            os.makedirs(self._file_folder)
        except OSError, e:
            log.warning("Directory already exists, nothing to do.")

        log.info('File from: ', self._file_to_get)
        try:
            file_to_store, msg = urllib.urlretrieve(
                self._file_to_get,
                self._file_stored,
                reporthook)
            log.info('File: %s' % file_to_store)
            log.info('Headers')
            log.info('%s' % msg)
        except urllib.URLError, e:
            log.error('Error getting file: %s\n' % e)
            self._error = True
        except IOError, e:
            log.error('Error: file not found: %s\n' % e)
            self._error = True
        except Exception, e:
            log.error('Exception %s' % e)
            self._error = True
        finally:
            urllib.urlcleanup()
            log.info("File %s uploaded.\n" % self._file_to_get)

        return ("OK", "KO")[self._error]

    def _dectivate(self):
        """
        Delete file from storage
        """

        log.info("Delete file: ", self._file_stored)
        self._error = True
        if os.path.isfile(self._file_stored):
            try:
                os.remove(self._file_stored)
                self._error = False
            except IOError, e:
                log.error("Error! ", e)

        return ("OK", "KO")[self._error]


class GetHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        parsed_url = urlparse.urlparse(self.path)
        dispatcher = Dispatcher(parsed_url.path, parsed_url.query)
        response = dispatcher.dispatch()

        self.send_response(200, "OK")
        self.end_headers()
        self.wfile.write(response)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """
    Handle request in a separate thread.
    """

if __name__ == "__main__":

    log = logger()

    server = ThreadedHTTPServer(('localhost', PORT), GetHandler)
    log.info('Starting server on port %s, use <Ctrl-C> to stop' % PORT)
    server.serve_forever()
