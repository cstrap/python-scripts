#!/usr/bin/env python
# -*- coding: utf-8 *-*

"""
Call by CMS: http://localhost:8888/activate?url=/path...
File get from FILESERVER and copied to CDN_DIR
"""

import os
import urllib
import urllib2
import urlparse
import threading
import sys

from BaseHTTPServer import BaseHTTPRequestHandler
from BaseHTTPServer import HTTPServer
from SocketServer import ThreadingMixIn

PORT = 8888
if len(sys.argv) > 1:
    PORT = int(sys.argv[1])

FILESERVER = 'http://localhost:8081/webapp'
ALLOWED_CHARS = \
    'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890-./'

# run python -m SimpleHTTPServer 8008 to serve files
CDN_DIR = '/tmp/CDN/'


def clean_string(chunk):
    result = chunk
    for c in chunk:
        if c not in ALLOWED_CHARS:
            result = result.replace(c, '-')
    return result


class Dispatcher(object):
    """
    Dispatcher command pattern
    """

    routing = {}

    def __init__(self, route, query_string):
        self._initCmd()
        self._route = route

        # The cms need this triks...
        self._url = urlparse.parse_qs(query_string).get('url', '')[0]
        self._file_to_get = "%s%s" % (FILESERVER, urllib.quote(self._url))
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
        print "-------------------------------------------------------------\n"
        print "Thread name: ", threading.currentThread().getName()
        if self._route in self.routing.keys():
            return self.routing[self._route]()
        return "KO"

    def _activate(self):
        """
        Copy file on storage
        """

        print 'File from: ', self._file_to_get
        try:
            file_to_store = urllib2.urlopen(self._file_to_get)
        except urllib2.URLError, e:
            print 'Error getting file: %s\n' % e
            self._error = True
        except IOError, e:
            print 'Error: file not found: %s\n' % e
            self._error = True
        except Exception, e:
            print 'Exception %s\n' % e
            self._error = True

        if not self._error:
            print 'file file: ', self._file_name
            print 'file folder: ', self._file_folder
            try:
                os.makedirs(self._file_folder)
            except OSError, e:
                print "Directory already exists, nothing to do"

            f = file(self._file_stored, 'w')
            f.write(file_to_store.read())
            f.close()
            print "File %s downloaded\n" % self._file_to_get

        return ("OK", "KO")[self._error]

    def _dectivate(self):
        """
        Delete file from storage
        """
        if os.path.isfile(self._file_stored):
            try:
                os.remove(self._file_stored)
            except IOError, e:
                print "Errore! ", e
                self._error = True

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

    server = ThreadedHTTPServer(('localhost', PORT), GetHandler)
    print 'Starting server on port %s, use <Ctrl-C> to stop' % PORT
    server.serve_forever()
