#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# Modules used for ETL - Create User

# Modules required:
import os
import xmlrpclib, sys, csv, ConfigParser
from datetime import datetime

# Set up parameters (for connection to Open ERP Database) *********************
config = ConfigParser.ConfigParser()
file_config = os.path.expanduser('~/ETL/generalfood/openerp.cfg')
config.read([file_config])
dbname = config.get('dbaccess','dbname')
user = config.get('dbaccess','user')
pwd = config.get('dbaccess','pwd')
server = config.get('dbaccess','server')
port = config.get('dbaccess','port')   # verify if it's necessary: getint
separator = eval(config.get('dbaccess','separator')) # test

# XMLRPC connection for autentication (UID) and proxy
sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/common' % (server, port), allow_none=True)
uid = sock.login(dbname ,user ,pwd)
sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (server, port), allow_none=True)

if len(sys.argv) != 2: 
    print "Use: errata_corrige parameters\n parameters: partner"
    sys.exit()
if sys.argv[1] == 'partner':
    result = sock.execute(dbname, uid, pwd, "quality.claim" , "correct_parent_partner")
    print "Partner updated"


