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

class quality_intervent_planned(osv.osv):
    _name = 'quality.intervent.planned'
    _description = 'Intervent planned'
    #_rec_name = ''
    #_order = 'date desc'
    
    _columns = {
    'action_id': fields.many2one('quality.action', 'Action', required=True),
    'conformed_id': fields.many2one('quality.conformed', 'Conformed', required=True),
    'conformed_external_id': fields.many2one('quality.conformed.external', 'Conformed External', required=True),
        }

class quality_intervent_verify(osv.osv):
    _name = 'quality.intervent.verify'
    _description = 'Intervent verify'
    #_rec_name = ''
    #_order = 'date desc'
    
    _columns = {
        }
            
class quality_intervent_valutation(osv.osv):
    _name = 'quality.intervent.valutation'
    _description = 'Intervent valutation'
    #_rec_name = ''
    #_order = 'date desc'
    
    _columns = {
        }    
        
class quality_action(osv.osv):
    ''' Update extra field for action
    '''
    _inherit = 'quality.action'

    _columns = {
        }
class quality_conformed(osv.osv):
    ''' Assign *2many fields to conformed
    '''
    _inherit = 'quality.conformed'

    _columns = {
        }



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
