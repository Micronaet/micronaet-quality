# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2001-2014 Micronaet SRL (<http://www.micronaet.it>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
import os
import sys
import logging
import shutil
from openerp.osv import osv, fields, orm
from datetime import datetime, timedelta
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare)
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _


_logger = logging.getLogger(__name__)

class QualityStatisticWizard(orm.TransientModel):
    ''' Parameter for report
    '''
    _name = 'quality.statistic.wizard'
    _description = 'Statistic report'

    # -------------
    # Button event: 
    # -------------
    def action_print_report(self, cr, uid, ids, context=None):
        ''' Wizard for paremeter of the report
        '''
        if context is None: 
            context = {}        
        
        wiz_browse = self.browse(cr, uid, ids, context=context)[0]
        
        datas = {}
        datas['from_date'] = wiz_browse.from_date
        datas['to_date'] = wiz_browse.to_date

        return {
             # action report
            'type': 'ir.actions.report.xml',
            'report_name': 'quality_claim_status_report',
            'datas': datas,
            }            
        
    _columns = {
        'from_date': fields.date('From'),
        'to_date': fields.date('To'),
        }
        
    _defaults = {
        'from_date': lambda *x: datetime.now().strftime('%Y-01-01'), # first
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
