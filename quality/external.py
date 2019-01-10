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

    _columns = {
        'ref': fields.char('Ref', size=12, readonly=True),
        'date': fields.date('Date'),
        #'origin_id': fields.many2one('quality.origin', 'Origin'),
        'origin': fields.selection([
            ('claim', 'Claim'),
            ('nc', 'Not conformed External'),
            ('other', 'Other'),
            ('audit', 'Audit'), # TODO coretta? c'è nella impostazione
        ], 'Origin', select=True),
        'origin_other': fields.char('Other', size=60),
        'note': fields.text('Cause analysis'),
        'proposed_subject': fields.text('Subject proposing'),
        'proposing_entity': fields.char('Proposing entity', size=100),
        'esit_date': fields.date('Esit date'),
        'closed_date': fields.date('Closed date'),
        'esit_note': fields.text('Judgment'),
        'claim_id': fields.many2one('quality.claim', 'Claim'),
        'conformed_id': fields.many2one('quality.conformed', 'Not conformed'),
        'type': fields.selection([
            ('corrective', 'Corrective'),
            ('preventive', 'Preventive'),
            ('enhance', 'Enhance intervent'),
        ], 'Type', select=True),
        'cancel': fields.boolean('Cancel'),        
        'state':fields.selection(action_state, 'State', select=True, 
            readonly=True),
            
        'access_id': fields.integer('Access ID'),
        'action_id': fields.many2one('quality.action', 'Action', 
            ondelete='set null'),
        'action_state': fields.related('action_id', 'state', type='selection', 
            selection=action_state, string='Action state', store=False),
        'parent_sampling_id': fields.many2one('quality.sampling', 
            'Parent Sampling', ondelete='set null'),
        'sampling_id': fields.many2one('quality.sampling', 'Sampling', 
            ondelete='set null'),
        'sampling_state': fields.related('sampling_id', 'state', 
            type='selection', selection=sampling_state, 
            string='Sampling state', store=False),
        }
