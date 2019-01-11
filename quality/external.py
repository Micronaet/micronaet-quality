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

conformed_external_state = [
    ('draft', 'Draft'),
    ('opened', 'Opened'),
    ('closed', 'Closed'),
    ('cancel', 'Cancel'),
    ('saw', 'Saw'),
    ]
    
# -----------------------------------------------------------------------------
#                             NOT CONFORMED EXTERNAL
# -----------------------------------------------------------------------------
class quality_conformed_external(osv.osv):
    ''' Forms of not conformed
    '''
    _name = 'quality.conformed.external'
    _inherit = ['mail.thread']

    _description = 'Not conformed external'
    _order = 'ref desc'
    _rec_name = 'ref'

    # ---------------------------
    # Workflow Activity Function:
    # ---------------------------
    def conformed_external_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'draft',
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def conformed_external_opened(self, cr, uid, ids, context=None):
        conformed_proxy = self.browse(cr, uid, ids, context=context)[0]
        if conformed_proxy.ref:
            ref = conformed_proxy.ref
        else:
            ref = self.pool.get('ir.sequence').get(cr, uid, 
                'quality.conformed')
        self.write(cr, uid, ids, {
            'state': 'opened',
            'ref': ref,
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def conformed_external_closed(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'closed',
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def conformed_external_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
                    'state': 'cancel',
                    }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def conformed_external_saw(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'saw',
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True
        
    _columns = {
        'ref': fields.char('Ref', size=100, readonly=True),
        'insert_date': fields.date('Insert date', required=True),
        
        #'aesthetic_packaging': fields.boolean('Confezione'),        
        #'quantity': fields.boolean('Quantity'),
        #'sanitation': fields.boolean('Sanitation'),
        #'temperature': fields.boolean('Temperature'),
        #'label': fields.boolean('Label'),
        #'quality': fields.boolean('Quality'),
        #'deadline': fields.boolean('Deadline'),
        #'delay': fields.boolean('Ritardo'),
        #'no_delivery': fields.boolean('Mancata consegna'),
        #'external_material': fields.boolean('Corpi estranei'),
        
        'gravity_id': fields.many2one('quality.gravity', 'Gravity',
            required=True),
        #'genesis':fields.selection([
            #('acceptance', 'Acceptance'),
            #('sample', 'Sample'),
            #('claim', 'Claim'),
            #('packaging', 'Packaging'),
            #('other', 'Other'),
            #   ],'Genesis', select=True),
        #'other':fields.char('Other', size=100),
        'origin': fields.selection([
            #('acceptation', 'Acceptation'),
            #('sampling', 'Sampling'),
            #('claim', 'Claim'),
            #('packaging', 'Packaging'),
            ('other', 'Other'),
        ], 'Origin', select=True),
        'mode': fields.selection([
            ('internal', 'Internal'),
            ('supplier', 'Supplier'),
        ], 'Mode', required=True, select=True),
        'origin_other': fields.char('Other', size=60),
        'reference_user_id': fields.many2one(
            'res.users', 'Ref. user', 
            help='Ref. user when no origin from claim'),
        #'claim_id': fields.many2one('quality.claim', 'Claim'),
        #'sampling_id': fields.many2one('quality.sampling', 'Sampling'),
        #'acceptation_id': fields.many2one('quality.acceptation', 
        #    'Acceptation'),
        #'ddt_ref': fields.char('DDT reference', size=50),
        # TODO mandatory??
        #'lot_id':fields.many2one('stock.production.lot', 'Real Lot'), 
        #'label_lot': fields.char('Label Lot', size=25),
        #'label_supplier': fields.char('Label Supplier', size=50),
        #'lot_deadline': fields.related('lot_id', 'real_deadline', type='char', 
        #    string='Lot Deadline', store=False),
        #'cancel': fields.boolean('Cancel'),
        #'supplier_lot': fields.related('lot_id', 'default_supplier_id', 
        #    type='many2one', relation='res.partner', string='Supplier'),
        #'descr_product': fields.related('lot_id', 'product_id',
        #    type='many2one', relation='product.product', 
        #    string='Product description'),

        'name': fields.text('Type'),
        'note_RAQ': fields.text('Note RAQ'),
        'stock_note': fields.text('Stock note'),
        'comunication_note': fields.text('Comunication note'),
        #'note_warehouse': fields.text('Note Warehouse'),

        # TODO Change reference field:
        #'comunication_ids': fields.one2many('quality.comunication', 
        #    'conformed_id', 'Comunications'),
        #'treatment_ids': fields.one2many('quality.treatment', 'conformed_id', 
        #    'Treatments'),
            
        'action_id': fields.many2one('quality.action', 'Action', 
            ondelete='set null'),
        'action_state': fields.related('action_id', 'state', type='selection', 
            string='Action state', store=False),
        # TODO fields.relater action_id state

        #'parent_sampling_id': fields.many2one('quality.sampling', 
        #    'Parent Sampling', ondelete='set null'),
        #'sampling_id': fields.many2one('quality.sampling', 'Sampling', 
        #    ondelete='set null'),
        #'sampling_state': fields.related('sampling_id', 'state', 
        #    type='selection', selection=sampling_state, 
        #    string='Sampling state', store=False),
        # TODO fields.relater sampling_id state (come per action)

        'state':fields.selection(conformed_external_state, 'State', 
            select=True, readonly=True),
        } 

    _defaults = {
        'mode': lambda *x: 'supplier',
        'reference_user_id': lambda s, cr, uid, ctx: uid,
        'gravity_id': lambda s, cr, uid, ctx: s.pool.get(
            'ir.model.data').get_object_reference(
                cr,  uid, 'quality', 'quality_gravity_serious')[1],
        'insert_date': lambda *x: datetime.now().strftime(
            DEFAULT_SERVER_DATE_FORMAT),
        'origin': lambda *a: 'other',
        'state': lambda *a: 'draft',
        }


