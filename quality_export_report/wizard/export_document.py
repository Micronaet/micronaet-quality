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
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)


class QualityExportExcelReport(orm.TransientModel):
    ''' Wizard for export data in Excel
    '''
    _name = 'quality.export.excel.report'

    # --------------------
    # Wizard button event:
    # --------------------
    def action_print(self, cr, uid, ids, context=None):
        ''' Event for print report
        '''
        if context is None: 
            context = {}        
        
        # Pool used:
        excel_pool = self.pool.get('excel.writer')
        wiz_proxy = self.browse(cr, uid, ids, context=context)[0]
        
        # Parameters:
        state_db = {
            'draft': 'Bozza',            
            'comunication': 'Comunicazione',
            'opened': 'Aperto',
            'nc': 'Nota di credito',
            'done': 'Nota di credito fatta',
            'closed': 'Chiuso',
            'cancel': 'Annullato',
            'saw': 'Visto',
            }
        report_db = {
            'claim': 'Reclami',
            }
            
        # ---------------------------------------------------------------------
        # Domain creation:
        # ---------------------------------------------------------------------
        domain = []
        filter_description = 'Report: %s' % report_db.get(wiz_proxy.report, '')
        
        # Date:
        if wiz_proxy.from_date:
            domain.append(('date', '>=', '%s 00:00:00' % \
                wiz_proxy.from_date[:10]))
            filter_description += _(', Dalla data: %s 00:00:00') % \
                wiz_proxy.from_date[:10]
        if wiz_proxy.to_date:
            domain.append(('date', '<=', '%s 23:59:59' % \
                wiz_proxy.to_date[:10]))
            filter_description += _(', Alla data: %s 23:59:59') % \
                wiz_proxy.to_date[:10]

        # Text:
        if wiz_proxy.subject:
            domain.append(('subject', 'ilike', wiz_proxy.subject))
            filter_description += _(', Oggetto: "%s"') % wiz_proxy.subject
        
        # One2many:    
        if wiz_proxy.partner_id:
            domain.append(('partner_id', '=', wiz_proxy.partner_id.id))
            filter_description += _(', Partner: %s') % \
                wiz_proxy.partner_id.name
        if wiz_proxy.reference_user_id:
            domain.append(
                ('reference_user_id', '=', wiz_proxy.reference_user_id))
            filter_description += _(', Riferimento: %s') % \
                wiz_proxy.reference_user_id.name
            
        if wiz_proxy.origin_id:
            domain.append(('origin_id', '=', wiz_proxy.origin_id.id))
            filter_description += _(', Origine: %s') % wiz_proxy.origin_id.name
        if wiz_proxy.cause_id:
            domain.append(('cause_id', '=', wiz_proxy.cause_id.id))
            filter_description += _(', Cause: %s') % wiz_proxy.cause_id.name
        if wiz_proxy.gravity_id:
            domain.append(('gravity_id', '=', wiz_proxy.gravity_id.id))
            filter_description += _(', Gravita\': %s') % \
                wiz_proxy.gravity_id.name

        if wiz_proxy.state:
            domain.append(('state', '=', wiz_proxy.state))
            filter_description += _(', Stato: %s') % state_db.get(
                wiz_proxy.state, '')

        # ---------------------------------------------------------------------
        #                       REPORT CASES:
        # ---------------------------------------------------------------------
        if wiz_proxy.report == 'claim':
            # -----------------------------------------------------------------
            # Claims:
            # -----------------------------------------------------------------
            # Parameters:
            ws_name = _('Reclami')
            name_of_file = _('reclami.xls')            
            
            header = [
                _('Rif.'), _('Data'),
                _('Partner'), _('Destinazione'), _('Rif. cliente'),
                _('Descrizione'), _('Dettaglio'), _('Analisi'),

                _('Origini'), _('Cause'), _('Gravita\''), _('Stato'),
                # TODO lot?
                ]

            # -----------------------------------------------------------------            
            # Create Excel file:    
            # -----------------------------------------------------------------            
            # Worksheet:
            ws = excel_pool.create_worksheet(ws_name)
            
            # Format:
            excel_pool.set_format()
            format_title = excel_pool.get_format('title')
            format_header = excel_pool.get_format('header')
            format_text = excel_pool.get_format('text')
            
            # Column satup:
            excel_pool.column_width(ws_name, [
                15, 20,
                40, 40, 20,
                50, 50, 50,
                30, 30, 30, 20,
                ])
            
            # Title:
            row = 0
            excel_pool.write_xls_line(ws_name, row, [
                _('Filtro:'),
                filter_description,
                ], format_title)

            # Header:            
            row = 1
            excel_pool.write_xls_line(ws_name, row, header, format_header)

            # -----------------------------------------------------------------            
            # Load data:            
            # -----------------------------------------------------------------            
            claim_pool = self.pool.get('quality.claim')
            claim_ids = claim_pool.search(cr, uid, domain, context=context)
            for claim in sorted(
                    claim_pool.browse(
                        cr, uid, claim_ids, context=context), 
                    key=lambda x: (x.date, x.ref)):
                row += 1    
                data = [
                    claim.ref or '',
                    claim.date,
                    claim.partner_id.name,
                    claim.partner_address_id.name or '',
                    claim.customer_ref or '',
                    claim.name or '',
                    claim.subject or '',
                    claim.analysis or '',
                    claim.origin_id.name or '',
                    claim.cause_id.name or '',
                    claim.gravity_id.name or '',
                    state_db.get(claim.state, ''),
                    ]

                excel_pool.write_xls_line(ws_name, row, data, format_text)
        else:
            pass # Error      
            
        return excel_pool.return_attachment(cr, uid, ws_name, 
            name_of_file=name_of_file, version='7.0', php=True, 
            context=context)

    _columns = {
        'report': fields.selection([
            ('claim', 'Claim'),
            ], 'Report', required=True),
            
        'from_date': fields.date('From date >= '),
        'to_date': fields.date('To date <='),
        
        'subject': fields.char('Subject', size=100),
        
        'partner_id': fields.many2one('res.partner', 'Customer'),
        'origin_id': fields.many2one('quality.origin', 'Origin'),
        'cause_id': fields.many2one('quality.claim.cause', 'Cause'),
        'gravity_id': fields.many2one('quality.gravity', 'Gravity'),
        'reference_user_id': fields.many2one('res.users', 'Reference user', 
            help="Reference for claim to your customer"),

        'state': fields.selection([
            ('draft', 'Draft'),
            ('comunication', 'Comunication'),
            ('opened', 'Opened'),
            ('nc', 'Credit Note'),
            ('done', 'Credit Note Done'),
            ('closed', 'Closed'), # TODO Vista RAQ
            ('cancel', 'Cancel'),
            ('saw', 'Saw'),
        ],'State'),
        }
        
    _defaults = {
        'report': lambda *x: 'claim',
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


