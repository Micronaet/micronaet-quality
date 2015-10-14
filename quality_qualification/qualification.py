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


class QualityQualificationParameter(orm.Model):
    ''' Manage qualification parameters for assign automatically the
        value su supplier depend on claims and other forms
    '''
    
    _name = 'quality.qualification.parameter'
    _description = 'Qualification parameter'
    _order = 'name'
    
    _columns = {
        'name': fields.selection([
            ('claim', 'From Claim'),
            ('acceptation', 'From acceptation'),
            ('sampling', 'From sampling'),
            ('packaging', 'From packaging'),
            ], 'Origin', select=True, required=True),        
        'note': fields.text('Note'),
        }

    _sql_constraints = [(
        'name_uniq', 'unique(name)', 
        'There\'s another model that is created fom this origin!'), 
        ]

class QualityQualificationParameterLine(orm.Model):
    ''' Line for every form type
    '''
    
    _name = 'quality.qualification.parameter.line'
    _description = 'Qualification parameter line'
    
    _columns = {
        # Furniture:
        'from': fields.integer('Range From (>=)')),
        'to': fields.integer('Range To (<)')),
        
        # Total forms:
        'perc_from': fields.float('% from (>=)', digits=(16, 3))),
        'perc_to': fields.float('% to (<)', digits=(16, 3))),

        'qualification': fields.selection([
            ('reserve', 'With reserve'),
            ('full', 'Full qualification'),
            ('discarded', 'Discarded'),
            ], 'Qualification type', select=True, required=True),        
        'parameter_id': fields.many2one('quality.qualification.parameter', 
            'Parameter'),        
        # UOM?    
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
