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
from openerp import netsvc
import logging
from openerp.osv import osv, fields
from datetime import datetime, timedelta
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare)
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _


class quality_intervent_planned(osv.osv):
    """ Intervent list planned
    """
    _name = 'quality.intervent.planned'
    _description = 'Intervent planned'
    _rec_name = 'deadline'
    _order = 'deadline desc'
    
    _columns = {
        # Table fields:
        'planned_activity': fields.text('Planned Activity', required=True),
        'responsible_treatment': fields.text('Responsible Treatment'),
        'deadline': fields.date('Deadline'),
        
        # Linked objects:
        'action_id': fields.many2one(
            'quality.action', 'Action'),
        'conformed_id': fields.many2one(
            'quality.conformed', 'Conformed'),
        'conformed_external_id': fields.many2one(
            'quality.conformed.external', 'Conformed External'),
        }

class quality_intervent_verify(osv.osv):
    _name = 'quality.intervent.verify'
    _description = 'Intervent verify'
    _rec_name = 'scheduled_date'
    _order = 'scheduled_date desc'
    
    _columns = {
        # Table fields:
        'scheduled_date': fields.date('Scheduled Date'),
        'activities_check': fields.text('Activities to check'),
        'date': fields.date('Verification Date'),
        'note': fields.text('Note'),
        
        # Linked objects:
        'action_id': fields.many2one(
            'quality.action', 'Action'),
        'conformed_id': fields.many2one(
            'quality.conformed', 'Conformed'),
        'conformed_external_id': fields.many2one(
            'quality.conformed.external', 'Conformed External'),
        }
                    
class quality_intervent_valutation(osv.osv):
    _name = 'quality.intervent.valutation'
    _description = 'Intervent valutation'
    _rec_name = 'scheduled_date'
    _order = 'scheduled_date desc'
    
    _columns = {
        # Table fields:
        'scheduled_date': fields.date('Scheduled Date'),
        'date': fields.date('Verification Date'),
        'note': fields.text('Note'),
        
        # Linked objects:    
        'action_id': fields.many2one(
            'quality.action', 'Action'),
        'conformed_id': fields.many2one(
            'quality.conformed', 'Conformed'),
        'conformed_external_id': fields.many2one(
            'quality.conformed.external', 'Conformed External'),
        }        

class quality_action(osv.osv):
    ''' Update extra field for action
    '''
    _inherit = 'quality.action'

    _columns = {
        'intervent_planned_ids': fields.one2many(
            'quality.intervent.planned', 'action_id', 
            'Intervent planned'),
        'intervent_verify_ids': fields.one2many(
            'quality.intervent.verify', 'action_id', 
            'Intervent verify'),
        'intervent_valutation_ids': fields.one2many(
            'quality.intervent.valutation', 'action_id', 
            'Intervent valutation'),
        }
class quality_conformed(osv.osv):
    ''' Assign *2many fields to conformed
    '''
    _inherit = 'quality.conformed'

    _columns = {
        'intervent_planned_ids': fields.one2many(
            'quality.intervent.planned', 'conformed_id', 
            'Intervent planned'),
        'intervent_verify_ids': fields.one2many(
            'quality.intervent.verify', 'conformed_id', 
            'Intervent verify'),
        'intervent_valutation_ids': fields.one2many(
            'quality.intervent.valutation', 'conformed_id', 
            'Intervent valutation'),
        }        

class quality_conformed_external(osv.osv):
    ''' Forms of not conformed
    '''
    _inherit = 'quality.conformed.external'

    _columns = {
        'intervent_planned_ids': fields.one2many(
            'quality.intervent.planned', 'conformed_external_id', 
            'Intervent planned'),
        'intervent_verify_ids': fields.one2many(
            'quality.intervent.verify', 'conformed_external_id', 
            'Intervent verify'),
        'intervent_valutation_ids': fields.one2many(
            'quality.intervent.valutation', 'conformed_external_id', 
            'Intervent valutation'),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
