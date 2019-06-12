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
        report = wiz_proxy.report
        if report == 'conformed':
            state_name = wiz_proxy.state_conformed or ''
        elif report == 'claim':
            state_name = wiz_proxy.state or ''
        else:
            return True # not present
        
        # Parameters:
        parameter_db = {
            'claim': {            
                # Excel:
                'header': [
                    _('Rif.'), _('Data'),
                    _('Partner'), _('Destinazione'), _('Rif. cliente'),
                    _('Descrizione'), _('Dettaglio'), _('Analisi'),

                    _('Origini'), _('Cause'), _('Gravita\''), _('Stato'),
                    # TODO lot?
                    ],
                'header_width': [
                    15, 20,
                    40, 40, 20,
                    50, 50, 50,
                    30, 30, 30, 20,
                    ],
               
                # Translate:
                'report': 'Reclami',
                'state': {
                    'draft': 'Bozza',            
                    'comunication': 'Comunicazione',
                    'opened': 'Aperto',
                    'nc': 'Nota di credito',
                    'done': 'Nota di credito fatta',
                    'closed': 'Chiuso',
                    'cancel': 'Annullato',
                    'saw': 'Visto',
                    },
                
                # Fields:     
                'date': 'date',
                'subject': 'subject',
                #'origin': 'origin_id',
                # TODO 
                },
            'conformed': {
                # Excel:
                # TODO Change:
                'header': [
                    _('Rif.'), _('Data'), _('Fornitore'),
                    _('Descrizione'),
                    _('Gravita\''), 
                    _('Stato'),
                    _('Quantita'),
                    _('Temperatura'),
                    _('Etichetta'),
                    _('Confezione'),
                    _('Qualita'),
                    _('Scadenza'),
                    _('Igenico/Sanitario'),
                    _('Ritardo'),
                    _('Mancata consegna'),
                    _('Corpi estranei'),

                    ],
               'header_width': [
                    15, 20, 20,
                    20,
                    40,
                    40,
                    5, 5, 5, 5, 5,
                    5, 5, 5, 5, 5,
                    ],

                # Translate:
                'report': u'Non Conformità',
                'state' : {
                    'draft': 'Bozza',
                    'opened': 'Aperto',
                    'Closed': 'Chiuso',
                    'Cancel': 'Cancellato',
                    'Saw': 'Visto',
                    },
                                    
                # Field:
                'date': 'insert_date',
                'subject': 'name',
                #'origin': 'origin',
                # TODO 
                },
               
            }    
            
        # ---------------------------------------------------------------------
        #                           Domain creation:
        # ---------------------------------------------------------------------
        domain = []
        filter_description = 'Report: %s' % parameter_db[report]['report']
        
        # Date:
        field_name = parameter_db[report]['date']
        if wiz_proxy.from_date:            
            domain.append((field_name, '>=', '%s 00:00:00' % \
                wiz_proxy.from_date[:10]))
            filter_description += _(', Dalla data: %s 00:00:00') % \
                wiz_proxy.from_date[:10]
        if wiz_proxy.to_date:
            domain.append((field_name, '<=', '%s 23:59:59' % \
                wiz_proxy.to_date[:10]))
            filter_description += _(', Alla data: %s 23:59:59') % \
                wiz_proxy.to_date[:10]

        # Text:
        field_name = parameter_db[report]['subject']
        if wiz_proxy.subject:
            domain.append((field_name, 'ilike', wiz_proxy.subject))
            filter_description += _(', Oggetto: "%s"') % wiz_proxy.subject
        
        # One2many:    
        if wiz_proxy.partner_id:
            domain.append(('partner_id', '=', wiz_proxy.partner_id.id))
            filter_description += _(', Partner: %s') % \
                wiz_proxy.partner_id.name
        if wiz_proxy.supplier_lot:
            domain.append(('supplier_lot', '=', wiz_proxy.supplier_lot))
            filter_description += _(', Fornitore Lotto: %s') % \
                wiz_proxy.supplier_lot.name

        if wiz_proxy.reference_user_id:
            domain.append(
                ('reference_user_id', '=', wiz_proxy.reference_user_id.id))
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
        if wiz_proxy.conformed_type:
            domain.append((wiz_proxy.conformed_type, '=', True))
            filter_description += _('Tipo: %s') % \
                wiz_proxy.conformed_type
        if state_name:
            domain.append(('state', '=', state_name))
            filter_description += _(', Stato: %s'
                ) % parameter_db[report]['state'].get(state_name, '')

        # ---------------------------------------------------------------------
        #                       REPORT CASES:
        # ---------------------------------------------------------------------
        # Parameters:
        ws_name = _(parameter_db[report]['report'])
        name_of_file = _('%s.xls' % report)       

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
        
        excel_pool.column_width(ws_name, parameter_db[report]['header_width'])
        
        # Title:
        row = 0
        excel_pool.write_xls_line(ws_name, row, [
            _('Filtro:'),
            filter_description,
            ], format_title)

        # Header:            
        row = 1
        excel_pool.write_xls_line(ws_name, row, parameter_db[report]['header'], 
            format_header)

        # ---------------------------------------------------------------------
        # Load data:            
        # ---------------------------------------------------------------------        
        if report == 'claim':
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
                    parameter_db[report]['state'].get(state_name, ''),
                    ]

                excel_pool.write_xls_line(ws_name, row, data, format_text)
        elif report == 'conformed':
            conformed_pool = self.pool.get('quality.conformed')
            conformed_ids = conformed_pool.search(cr, uid, domain, context=context)
            for conformed in sorted(
                    conformed_pool.browse(
                        cr, uid, conformed_ids, context=context), 
                    key=lambda x: (x.insert_date, x.ref)):
                row += 1    
                data = [
                    conformed.ref or '',
                    conformed.insert_date,
                    conformed.supplier_lot.name,
                    conformed.name or '',
                    conformed.gravity_id.name or '',
                    parameter_db[report]['state'].get(state_name, ''),
                    
                    'X' if conformed.quantity else '',                    
                    'X' if conformed.temperature else '',                    
                    'X' if conformed.label else '',                    
                    'X' if conformed.aesthetic_packaging else '',                    
                    'X' if conformed.quality else '',                    
                    'X' if conformed.deadline else '',                    
                    'X' if conformed.sanitation else '',                    
                    'X' if conformed.delay else '',                    
                    'X' if conformed.no_delivery else '',                    
                    'X' if conformed.external_material else '',                    

                    ]
                excel_pool.write_xls_line(ws_name, row, data, format_text)
            
        return excel_pool.return_attachment(cr, uid, ws_name, 
            name_of_file=name_of_file, version='7.0', php=True, 
            context=context)

    _columns = {
        'report': fields.selection([
            ('claim', 'Claim'),
            ('conformed', 'Not conformed'),
            ], 'Report', required=True),
            
        'from_date': fields.date('From date >= '),
        'to_date': fields.date('To date <='),
        'subject': fields.char('Subject', size=100),
        'supplier_lot': fields.many2one('res.partner', 'Supplier'),        
        'partner_id': fields.many2one('res.partner', 'Customer'),
        'origin_id': fields.many2one('quality.origin', 'Origin'),
        'cause_id': fields.many2one('quality.claim.cause', 'Cause'),
        'gravity_id': fields.many2one('quality.gravity', 'Gravity'),
        'reference_user_id': fields.many2one('res.users', 'Reference user', 
            help="Reference for claim to your customer"),

        'conformed_type': fields.selection([
            ('quantity', u'Quantità'),
            ('temperature', 'Temperatura'),
            ('label', 'Etichetta'),
            ('aesthetic_packaging', 'Confezione'),
            ('quality', u'Qualità'),
            ('deadline', 'Scadenza'),
            ('sanitation', 'Igenico/Sanitario'),
            ('delay', 'Ritardo'),
            ('no_delivery', 'Mancata Consegna'),
            ('external_material', 'Corpi estranei'),
            ], 'Tipo'),

        # Claim state:
        'state': fields.selection([
            ('draft', 'Draft'),
            ('comunication', 'Comunication'),
            ('opened', 'Opened'),
            ('nc', 'Credit Note'),
            ('done', 'Credit Note Done'),
            ('closed', 'Closed'), # TODO Vista RAQ
            ('cancel', 'Cancel'),
            ('saw', 'Saw'),
            ], 'State'),
        
        # Conformed state:
        'state_conformed': fields.selection([
            ('draft', 'Draft'),
            ('opened', 'Opened'),
            ('closed', 'Closed'),
            ('cancel', 'Cancel'),
            ('saw', 'Saw'),
        ], 'State'),        
        
        }
        
    _defaults = {
        'report': lambda *x: 'claim',
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


