# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP) 
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<http://www.micronaet.it>)
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
from openerp.report import report_sxw
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


class Parser(report_sxw.rml_parse):    
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_objects': self.get_objects,
            'get_filter': self.get_filter,
            })

    # --------
    # Utility:
    # --------
    def _get_domain(self, data=None, description=False, field='date'):
        ''' Get domain from data passed with wizard
            create domain for search filter depend on data
            if description is True, return description of filter instead 
        '''
        # TODO need also other information?!?!
        if data is None:
            data = {}

        if description:
            res = ''
            if data.get('from_date', False):
                res += _('da data >= %s') % data['from_date']
            if data.get('to_date', False):
                res += _(' a data < %s') % data['to_date']
                
        else:
            res = []
            if data.get('from_date', False):
                res.append(
                    (field, '>=', '%s' % data['from_date']))
            if data.get('to_date', False):
                res.append(
                    (field, '<', '%s' % data['to_date']))
        return res
        
    # ------------------
    # Exported function:
    # ------------------
    def get_filter(self, data=None):
        ''' Return string for filter conditions
        '''
        return self._get_domain(data, description=True)
       
    def get_total_lot(self, data=None):
        ''' All lot created in the domain period
        '''
        domain = self._get_domain(data)
        domain.append(('state', '!=', 'cancel'))
        acceptation_pool = self.pool.get('quality.acceptation')
        acceptation_ids = acceptation_pool.search(self.cr, self.uid, domain)
        res = 0
        for item in acceptation_pool.browse(
                self.cr, self.uid, acceptation_ids):
            res += len(item.line_ids)            
        return res
    
    def get_objects(self, data=None):
        ''' Load all supplier for statistic
        '''
        res = []
        # Create a domain:
        domain = [('supplier', '=', True)]
        if data.get('quality_class_id', False):
            domain.append(
                ('quality_class_id', '=', data.get('quality_class_id', False))
                )
        if data.get('partner_id', False):
            domain.append(
                ('id', '=', data.get('partner_id', False))
                )

        partner_pool = self.pool.get('res.partner')
        partner_ids = partner_pool.search(self.cr, self.uid, domain)
        
        for partner in partner_pool.browse(self.cr, self.uid, partner_ids):
            # TODO complete with evaluation            
            acc_esit = _('full')
            claim_esit = _('full')
            sample_esit = _('full')
            pack_esit = _('full')            
            esit = _('full')
            
            # partner obj, total lot, total q, accept, claim, sample, pack
            res.append((
                partner, # partner obj
                0.0, # total lot
                0.0, # total q. 
                
                0.0, # acceptation NC
                0.0, # claim NC
                0.0, # sampling NC
                0.0, # pack NC
                
                acc_esit, # acceptation result
                claim_esit, # claim result
                sample_esit, # sampling result
                pack_esit, # pack result

                esit, # general result
                ))
        return res
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
