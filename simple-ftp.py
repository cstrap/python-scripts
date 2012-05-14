#!/usr/bin/env python

"""
Require http://code.google.com/p/pyftpdlib/
pyftpdlib works out of the box!
"""

import ftpserver

FTP_DIR="/tmp"
USER_AUTH="cstrap"
USER_PSWD="12345"

authorizer = ftpserver.DummyAuthorizer()
authorizer.add_user(USER_AUTH, USER_PSWD, FTP_DIR, perm="elradfmw")
authorizer.add_anonymous(FTP_DIR)
handler = ftpserver.FTPHandler
handler.authorizer = authorizer
address = ("127.0.0.1", 7000)
ftpd = ftpserver.FTPServer(address, handler)
ftpd.serve_forever()

