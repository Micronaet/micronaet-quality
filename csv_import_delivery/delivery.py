#!/usr/bin/python
# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP) 
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<https://micronaet.com>)
# Developer: Nicola Riolini @thebrush (<https://it.linkedin.com/in/thebrush>)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import os
import sys
import logging
import openerp
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class ResPartnerDelivery(orm.Model):
    """ Model name: ResPartnerDelivery
    """
    
    _name = 'res.partner.delivery'
    _description = 'Carrier delivery'
    _rec_name = 'name'
    _order = 'name'
    
    # -------------------------------------------------------------------------
    # Scheduled procedure:
    # -------------------------------------------------------------------------
    def csv_import_carrier_files(self, cr, uid, path, only_current=True, 
            context=None):
        ''' Schedule import procedure:
            only_current: force reimport of current year
        '''
        # Parameters:
        final = 'vet.csv'
        separator = ';'
        
        partner_pool = self.pool.get('res.partner')

        if only_current:
            year = datetime.now()[:4],
            csv_files = ['%s%s' % (year, final)]
            delivery_ids = self.search(cr, uid, [
                ('date', '>=', '%s-01-01' % year),
                ], context=context)
        else:        
            csv_files = []
            for root, dirs, files in os.walk(path):
                for filename in files:
                    if filename.endswith(final):
                        csv_files.append(filename)
            delivery_ids = self.search(cr, uid, [], context=context)
                        
        self.unlink(cr, uid, delivery_ids, context=context)
        for filename in csv_files:
            fullname = os.path.expanduser(os.path.join(path, filename))
            f_csv = open(fullname, 'r')
            for line in f_csv:
                line = line.strip()
                row = line.split(separator)
        

            partner_ids = partner_pool.search(cr, uid, [
                (sql_supplier_code, '=', carrier_id)], context=context)
            if partner_ids:
                partner_pool.write(cr, uid, partner_ids, {}, context=context)
        return 
            
                    
                # Read fields
                name = row[0]
                date = row[1]
                carrier_id = row[2]
                trip = row[3]
                # Import line:
                              
            f_csv.close()    
        return True
        
    _columns = {
        'name': fields.char('DDT num.', size=20, required=True),
        'date': fields.date('Data', required=True),
        'carrier_id': fields.many2one('res.partner', 'Carrier'),
        'trip': fields.char('Trip', size=5),          
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
