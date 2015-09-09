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
import openerp.netsvc
import logging
from openerp.osv import osv, fields
from datetime import datetime, timedelta
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare)
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _


_logger = logging.getLogger(__name__)

class ResPartnerSwap(osv.osv):
    ''' Swap partner parent code
    '''    
    _name = 'res.partner.swap'
    _description = 'Swap parent'
    
    _columns = {
        'name': fields.char('Original', size=10, required=True), 
        'swap': fields.char('Swap code', size=10, required=True), 
        }

class ResPartner(osv.osv):
    ''' Insert override elements
    '''    
    _inherit = 'res.partner'

    # -------------------------------------------------------------------------
    #                         Override function:
    # -------------------------------------------------------------------------
    # Virtual function that calculate swap dict:
    def get_swap_parent(self, cr, uid, context=None):
        ''' Override with function that load override fields
        '''
        res = {}
        swap_pool = self.pool.get('res.partner.swap')
        swap_ids = swap_pool.search(cr, uid, [], context=None)
        for swap in swap_pool.browse(
                cr, uid, swap_ids, context=context):
            res[swap.name] = swap.swap
        return res
    
    # Scheduled function that import partner (and after update forms)
    # TODO better create new module only for quality only with this function:
    def schedule_sql_partner_import(self, cr, uid, verbose_log_count=100, 
        capital=True, write_date_from=False, write_date_to=False, 
        create_date_from=False, create_date_to=False, sync_vat=False,
        address_link=False, only_block=False, context=None):
        
        # -----------------------
        # Call original function:
        # -----------------------
        res = super(ResPartner, self).schedule_sql_partner_import(
            cr, uid, verbose_log_count=verbose_log_count, 
            capital=capital, write_date_from=write_date_from, 
            write_date_to=write_date_to, create_date_from=create_date_from, 
            create_date_to=create_date_to, sync_vat=sync_vat,
            address_link=address_link, only_block=only_block, context=context)
        
        # ---------------------------------
        # Update form if there's swap list:
        # ---------------------------------
        swap_list = self.get_swap_parent(cr, uid, context=context)  
        if swap_list: # Update forms:
            for origin, swap in swap_list.iteritems():
                from_id = self.get_partner_from_sql_code(
                    cr, uid, origin, context=context)
                to_id = self.get_partner_from_sql_code(
                    cr, uid, swap, context=context)
                
                if not from_id or not to_id: # check both present
                    _logger.error(
                        'Partner not found for origin: %s destination: %s' % (
                            origin, swap))
                    continue
                    
                # Replace function:    
                self.replace_partner_id(
                    cr, uid, from_id, to_id, context=context)
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
