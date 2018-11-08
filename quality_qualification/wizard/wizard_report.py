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

class QualitySupplierQualificationWizard(orm.TransientModel):
    ''' Parameter for report
    '''
    _name = 'quality.supplier.qualification.wizard'
    _description = 'Supplier qualitication'

    # -------------
    # Button event: 
    # -------------
    def action_print_report(self, cr, uid, ids, context=None):
        ''' Wizard for paremeter of the report
        '''
        if context is None: 
            context = {}        
        
        wiz_browse = self.browse(cr, uid, ids, context=context)[0]
        
        datas = {
            'report_type': wiz_browse.report_type,
            'only_active': wiz_browse.only_active,
            'from_date': wiz_browse.from_date,
            'to_date': wiz_browse.to_date,
            'ref_date': wiz_browse.ref_date,
            'partner_id': (
                wiz_browse.partner_id.id if wiz_browse.partner_id else False),
            'quality_class_id': (
                wiz_browse.quality_class_id.id if \
                    wiz_browse.quality_class_id else False),
            }

        # Print report:
        return {
             # action report
            'type': 'ir.actions.report.xml',
            'report_name': 'quality_qualification_supplier_report',
            'datas': datas,
            }
        
    _columns = {
        'report_type': fields.selection([
            ('report', 'Report'),
            ('force', 'Force'),
            ], 'Wizard type'),
            
        # Partner filter information:
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'quality_class_id': fields.many2one('quality.partner.class', 'Class'),
        
        # Statistic filter information:
        'from_date': fields.date('From (>=)', required=True),
        'to_date': fields.date('To (<)', required=True),
        'ref_date': fields.date('Ref date'),        
        'only_active': fields.boolean('Only active', 
            help='Only the one who has lot in period'),
        }
        
    _defaults = {
        'report_type': lambda *x: 'report',
        'from_date': lambda *x: datetime.now().strftime(
            '%Y-01-01'), # first
        'to_date': lambda *x: '%s-01-01' % (int(datetime.now().year) + 1), 
        'ref_date': lambda *x: datetime.now().strftime(
            DEFAULT_SERVER_DATE_FORMAT),
        'only_active': lambda *x: True,
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
