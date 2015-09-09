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


class ResPartner(osv.osv):
    ''' Inherit partner elements
    '''    
    _inherit = 'res.partner'

    # -------------------------------------------------------------------------
    #                         Utility function:
    # -------------------------------------------------------------------------
    def replace_partner_id(self, cr, uid, from_id, to_id, context=None):
        ''' Replace in all form the from_id and put to_id
            (used for swap function but also for a possibly wizard
        '''
        subtitution = [
            ('quality.claim', 'partner_id'),
            #('quality.claim', 'partner_address_id'), # TODO address to check!
            #('quality.claim.product', 'partner_id'), # TODO check (is related)
            ('quality.conformed', 'partner_id'),
            #('quality.acceptation', 'partner_id'), # TODO check (is related)
            ('stock.production.lot', 'default_supplier_id'),
            ('quality.supplier.rating', 'partner_id'),
            ('quality.supplier.check', 'partner_id'),
            ('quality.supplier.certificate', 'partner_id'),
            ]

        for (pool, field) in substitution:
            form_pool = self.pool.get(pool)
            form_ids = form_pool.search(cr, uid, [
                (field, '=', from_id)], context=context)
            if form_ids:
                form_pool.write(cr, uid, form_ids, {
                    field: to_id}, context=context)
                _logger.info('Swapped partner in %s: from %s to %s [%s]' % (
                    pool, from_id, to_id, len(form_ids)))
        return 
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
