# -*- coding: utf-8 -*-
##############################################################################
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
##############################################################################
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

qualification_list = [
    ('reserve', 'With reserve'),
    ('full', 'Full qualification'),
    ('discarded', 'Discarded'),
    ('error', 'Error, not found'), # TODO needed?
    ]

class QualityQualificationParameter(orm.Model):
    ''' Manage qualification parameters for assign automatically the
        value su supplier depend on claims and other forms
    '''
    _name = 'quality.qualification.parameter'
    _description = 'Qualification parameter'
    _order = 'name,sequence'

    # --------
    # Utility:
    # --------
    def _load_parameters(self, cr, uid, context=None):
        ''' Load all parameters in dict database for code purpose
            format:
            key = name of parameter (claim etc.)
            value = uom, (from, to range), lines browseable obj
        '''
        res = {}
        parameter_ids = self.search(cr, uid, [], context=context)
        for item in self.browse(cr, uid, parameter_ids, context=context):
            if item.name not in res:
                res[item.name] = []
            res[item.name].append((
                item.uom,
                (item.from_value, item.to_value), # from to lot / q. range
                item.line_ids, # list of line for evaluation
                ))
        return res

    def _check_parameters(self, parameters, block, weight, lot, failed,
           failed_n):
        ''' Check in parameters and return qualification value
            parametes: database for all evaluation
            block: key value for parameters
            weight: weight delivered
            lot: number of lot delivered
            failed: number of lot/weigth failed (perc value)
            failed_n: number of NC failed
        '''
        parameter = parameters.get(block, {})
        for item in parameter: #check range in parameter for block
            if item[0] == 'lot': # uom
                total = lot
            else:
                total = weight

            if (total >= item[1][0]) and (
                    not item[1][1] or total < item[1][1]):
                for line in item[2]:
                    # Choose % value or number:
                    if line.value == 'perc':
                        fail = failed
                    else: # 'number'
                        fail = failed_n

                    if (fail >= line.perc_from) and (
                            not line.perc_to or fail < line.perc_to):
                        return line.qualification
        return 'error'

    _columns = {
        'sequence': fields.integer('Sequence', required=True),
        'name': fields.selection([
            ('claim', 'From Claim'),
            ('acceptation', 'From acceptation'),
            ('sampling', 'From sampling'),
            ('packaging', 'From packaging'),
            ('external', 'NC External'),
            ], 'Origin', select=True, required=True),

        # Furniture range:
        'from_value': fields.integer('Range From (>=)'),
        'to_value': fields.integer('Range To (<)'),
        'uom': fields.selection([
            ('unused', 'Non necessario'),
            ('lot', 'Lotti'),
            ('weight', 'Peso'),
            ('delivery', 'Consegne'),
            ], 'uom', required=True),

        'note': fields.text('Note'),
        }

    _defauls = {
        'uom': lambda *x: 'lot',
        }

    _sql_constraints = [(
        'name_from_to_uniq', 'unique(name, from, to)',
        _('There\'s another model that is created fom this origin!')),
        ]

class QualityQualificationParameterLine(orm.Model):
    ''' Line for every form type
    '''
    _name = 'quality.qualification.parameter.line'
    _description = 'Qualification parameter line'
    _rec_name = 'qualification'
    _order = 'parameter_id,perc_from,perc_to'

    _columns = {
        # Total forms:
        'perc_from': fields.float('from (>=)', digits=(16, 3)),
        'perc_to': fields.float('to (<)', digits=(16, 3)),
        'value': fields.selection([
            ('perc', '% on total'),
            ('number', 'Number'),
            ], 'value', required=True),

        'qualification': fields.selection(qualification_list,
            'Qualification type', select=True, required=True),
        'parameter_id': fields.many2one('quality.qualification.parameter',
            'Parameter'),
        }

    _defaults = {
        'value': lambda *x: 'number',
        }

class QualityQualificationParameter(orm.Model):
    ''' Extra *many relation fields
    '''

    _inherit = 'quality.qualification.parameter'

    _columns = {
        'line_ids': fields.one2many('quality.qualification.parameter.line',
            'parameter_id', 'Details'),
        }

class ResPartner(orm.Model):
    ''' Add some extra fields for manage automatic qualification
    '''

    _inherit = 'res.partner'

    _columns = {
        'qualification_date': fields.date('Qualification date'),
        'qualification_claim': fields.selection(qualification_list,
            'Qualification from claim'),
        'qualification_acceptation': fields.selection(qualification_list,
            'Qualification from acc.'),
        'qualification_sampling': fields.selection(qualification_list,
            'Qualification from sampl.'),
        'qualification_packaging': fields.selection(qualification_list,
            'Qualification from pack.'),
        # TODO from to period?
        # TODO qualification assigned?
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
