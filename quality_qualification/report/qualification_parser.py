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
    
        # Reset totals:
        self.totals = {
            'not_conformed': 0,
            'claims': 0,
            }     
        
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_objects': self.get_objects,
            'get_total_lot': self.get_total_lot,
            'get_filter': self.get_filter,
            'get_total': self.get_total,
            })





    # --------
    # Utility:
    # --------
    def _get_domain(self, data=None, description=False, field='date'):
        ''' Get domain from data passed with wizard
            create domain for search filter depend on data
            if description is True, return description of filter instead 
        '''
        if data is None:
            data = {}

        if description:
            res = ''
            if data.get('from_date', False):
                res += _('da data >= %s 00:00:00') % data['from_date']
            if data.get('to_date', False):
                res += _(' a data <= %s 23:59:59') % data['to_date']
        else:
            res = []
            if data.get('from_date', False):
                res.append(
                    (field, '>=', '%s 00:00:00' % data['from_date']))
            if data.get('to_date', False):
                res.append(
                    (field, '<=', '%s 23:59:59' % data['to_date']))
        return res
        
    # ------------------
    # Exported function:
    # ------------------
    def get_total(self, name):
        ''' Return total loaded in report procedure
        '''
        return self.totals.get(name, 0.0)

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
                ('quality_class_id', '', data.get('quality_class_id', False))
                )
        if data.get('partner_id', False):
            domain.append(
                ('id', '', data.get('partner_id', False))
                )

        partner_pool = self.pool.get('res.partner')
        partner_ids = partner_pool.search(self.cr, self.uid, domain)
        
        for partner in partner_pool.browse(self.cr, self.uid, partner_ids):
            res.append((partner, 0.0, 0.0, 0.0, 0.0))
        return res
            
        """# Reset totals:
        self.totals['not_conformed'] = 0
        self.totals['claims'] = 0

        domain = self._get_domain(data)
        domain.append(('state', 'not in', ('draft', 'cancel')))
        claim_pool = self.pool.get('quality.claim')
        claim_ids = claim_pool.search(self.cr, self.uid, domain)

        res = {
            'Origine': {},
            'Cause': {},
            "Gravita'": {},
            }

        # Language:
        context = {}
        context['lang'] = 'it_IT'
        
        for item in claim_pool.browse(self.cr, self.uid, claim_ids, 
                context):
            self.totals['claims'] += 1
            
            # --------------
            # Caracteristic:
            # --------------
            # Origin:
            block = res['Origine'] # for fast replace
            name = _(item.origin_id.name) if item.origin_id else 'Nessuna'
            
            if name not in block: # Create totalizer
                block[name] = 0                
            block[name] += 1
            
            #  Cause
            block = res['Cause'] # for fast replace
            name = _(item.cause_id.name) if item.cause_id else 'Nessuna'
            if name not in block: # Create totalizer
                block[name] = 0                
            block[name] += 1
            
            # Gravity
            block = res["Gravita'"] # for fast replace
            name = _(item.gravity_id.name) if item.gravity_id else 'Nessuna'
            if name not in block: # Create totalizer
                block[name] = 0                
            block[name] += 1
            
            # -------
            # Totals:
            # -------
            if item.conformed_id:
                self.totals['not_conformed'] += 1"""
            
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
