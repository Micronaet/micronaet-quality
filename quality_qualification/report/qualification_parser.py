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
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.report import report_sxw
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


class Parser(report_sxw.rml_parse):    
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_objects': self.get_objects,
            'get_filter': self.get_filter,
            })

    # --------
    # Utility:
    # --------
    def _get_domain(self, data=None, description=False, field='date'):
        ''' Get domain from data passed with wizard
            create domain for search filter depend on data
            if description is True, return description of filter instead 
        '''
        # TODO need also other information?!?!
        if data is None:
            data = {}

        if description:
            res = ''
            if data.get('from_date', False):
                res += _('da data >= %s') % data['from_date']
            if data.get('to_date', False):
                res += _(' a data < %s') % data['to_date']
                
        else:
            res = []
            if data.get('from_date', False):
                res.append(
                    (field, '>=', '%s' % data['from_date']))
            if data.get('to_date', False):
                res.append(
                    (field, '<', '%s' % data['to_date']))
        return res
        
    # ------------------
    # Exported function:
    # ------------------
    def get_filter(self, data=None):
        ''' Return string for filter conditions
        '''
        return self._get_domain(data, description=True)
       
    def get_total_lot(self, data=None):
        ''' All lot created in the domain period
        '''
        domain = self._get_domain(data)
        domain.append(('state', '!=', 'cancel'))
        acceptation_pool = self.pool.get('quality.acceptation')
        acceptation_ids = acceptation_pool.search(self.cr, self.uid, domain)
        res = 0
        for item in acceptation_pool.browse(
                self.cr, self.uid, acceptation_ids):
            res += len(item.line_ids)            
        return res
    
    def get_objects(self, data=None):
        ''' Load all supplier for statistic
        '''
        res = []

        # ---------------------------------------------------------------------
        #                           Load partner list:
        # ---------------------------------------------------------------------        
        partner_pool = self.pool.get('res.partner')

        # Open in force mode:
        force_mode = data.get('report_type', 'report') == 'force'
        ref_date = data.get('ref_date', False)
        ref_deadline = data.get('ref_deadline', False)
        
        # Create a domain:
        domain = [('supplier', '=', True)]
        if data.get('quality_class_id', False):
            domain.append(
                ('quality_class_id', '=', data.get('quality_class_id', False))
                )
        if data.get('partner_id', False):
            domain.append(
                ('id', '=', data.get('partner_id', False))
                )

        partner_ids = partner_pool.search(self.cr, self.uid, domain)
        only_active = data.get('only_active', False)

        # Range date must be present (if comes from wizard):
        index_from = data.get('from_date', False)
        index_to = data.get('to_date', False)        
        if not index_to or not index_from:
            raise osv.except_osv(
                _('Error'), 
                _('This report will be lauched from wizard!'),
                )

        # ---------------------------------------------------------------------
        #                        Load NC for that partner:
        # ---------------------------------------------------------------------        
        nc_stat = {
            'acceptation': {},
            'claim': {},
            'packaging': {},
            'sampling': {},
            'other': {}, # not used!
            }
        nc_pool = self.pool.get('quality.conformed')

        nc_ids = nc_pool.search(self.cr, self.uid, [
            ('state', '!=', 'cancel'),
            ('insert_date', '>=', index_from),
            ('insert_date', '<', index_to),
            #('supplier_lot', 'in', tuple(partner_ids)),
            ])
            
        for nc in nc_pool.browse(self.cr, self.uid, nc_ids):
            if not nc.origin or nc.origin not in nc_stat:
                _logger.error(
                    'Origin not found or not in list: %s!' % nc.origin)
                continue    

            if not nc.supplier_lot.id: # TODO send alert!!!
                _logger.error('Not found supplier lot!')
            if nc.supplier_lot.id not in nc_stat[nc.origin]:
                nc_stat[nc.origin][nc.supplier_lot.id] = 1
            else:    
                nc_stat[nc.origin][nc.supplier_lot.id] += 1

        # Load parameter dict for controls:
        parameter_pool = self.pool.get('quality.qualification.parameter')
        parameters = parameter_pool._load_parameters(self.cr, self.uid)
         
        # Description conversion: 
        description = { # TODO usare quella nel modulo!!
            'reserve': _('Reserve'),
            'full': _('Full'),
            'discarded': _('Discarded'),
            'error': _('Error'), # TODO needed?
            }
        for partner in partner_pool.browse(self.cr, self.uid, partner_ids):            
            # Total lots:
            total_acceptation_lot = partner_pool._get_index_lot(
                self.cr, self.uid, index_from, index_to, partner.id)

            # Total weight (t so converted)    
            try:
                total_acceptation_weight = float(
                    partner_pool._get_index_weight(
                        self.cr, self.uid, index_from, index_to, partner.id
                        )) / 1000.0
            except:
                total_acceptation_weight = 0.0

            if only_active and not total_acceptation_lot:
                continue # jump line without lot in period (if request)    
            
            acc_total = nc_stat[
                'acceptation'].get(partner.id, 0)
            claim_total = nc_stat[
                'claim'].get(partner.id, 0) 
            sample_total = nc_stat[
                'sampling'].get(partner.id, 0) 
            pack_total = nc_stat[
                'packaging'].get(partner.id, 0)
            # % total:
            if total_acceptation_lot:
                # Perc on total:
                acc_failed = 100.0 * acc_total / total_acceptation_lot
                claim_failed = 100.0 * claim_total / total_acceptation_lot
                sample_failed = 100.0 * sample_total / total_acceptation_lot           
                pack_failed = 100.0 * pack_total / total_acceptation_lot
            else:                    
                acc_failed = 0.0
                claim_failed = 0.0
                sample_failed = 0.0
                pack_failed = 0.0                
                
            outcome_list = []
            outcome = parameter_pool._check_parameters(
                parameters, 'acceptation', 
                total_acceptation_weight, # weight
                total_acceptation_lot, # Note:  % lot
                acc_failed,
                acc_total, 
                )
            acc_outcome = description.get(outcome, '# Error')
            outcome_list.append(outcome)

            outcome = parameter_pool._check_parameters(
                parameters, 'claim', 
                total_acceptation_weight, # weight
                total_acceptation_lot, # Note:  % lot
                claim_failed,
                claim_total, 
                )
            claim_outcome = description.get(outcome, '# Error')
            outcome_list.append(outcome)

            outcome = parameter_pool._check_parameters(
                parameters, 'sampling', 
                total_acceptation_weight, # weight
                total_acceptation_lot, # Note:  % lot
                sample_failed,
                sample_total, 
                )
            sample_outcome = description.get(outcome, '# Error')
            outcome_list.append(outcome)

            outcome = parameter_pool._check_parameters(
                parameters, 'packaging', 
                total_acceptation_weight, # weight
                total_acceptation_lot, # Note:  % lot
                pack_failed,
                pack_total, 
                )
            pack_outcome = description.get(outcome, '# Error')
            outcome_list.append(outcome)

            if 'discarded' in outcome_list:
                outcome = description.get('discarded')
            else:    
                if 'reserve' in outcome_list:
                    outcome = description.get('reserve')
                else:
                   if 'full' in outcome_list:
                       outcome = description.get('full')
                   else:
                       outcome = description.get('error')
                
            res.append((
                partner, # 0. browse obj

                total_acceptation_lot, # 1. total lot
                total_acceptation_weight, # 2. total q.                
                
                # Total NC present comes from:
                acc_failed, # 3. acc failed
                claim_failed, # 4. claim failed
                sample_failed, # 5. sample failed
                pack_failed, # 6. packaging failed
                
                # Outcome for origin:
                acc_outcome, # 7. acc. outcome
                claim_outcome, # 8. claim outcome
                sample_outcome, # 9. sample outcome
                pack_outcome, # 10. packaging outcome

                # Total NC in number:
                acc_total, # 11. acc failed
                claim_total, # 12. claim failed
                sample_total, # 13. sample failed
                pack_total, # 14. packaging failed

                # General result:
                outcome, # 15. total outcome
                ))

        # ---------------------------------------------------------------------
        #  Update mode (supplier data)
        # ---------------------------------------------------------------------
        if force_mode:            
            import pdb; pdb.set_trace()
            rating_pool = self.pool.get('quality.supplier.rating')
            
            partner_ids = [item[0].id for item in res]
            # -------------------------------------------------------------
            # 1. Clean all previous supplier evaluation with same data:
            # -------------------------------------------------------------
            # Delete all rating for this partner with current date
            rating_ids = rating_pool.search(cr, uid, [
                ('partner_id', 'in', partner_ids),
                ('date', '=', ref_date),
                ], context=context)
            _logger.info('Unlink yet present rating: %s' % len(rating_ids))
            rating_pool.unlink(rating_ids)    
            
            # -------------------------------------------------------------
            # 2. Set as old all previous:
            # -------------------------------------------------------------
            # Set remain rating for all partner as obsolete
            rating_ids = rating_pool.search(cr, uid, [
                ('partner_id', 'in', partner_ids),
                ('obsolete', '=', False),
                ], context=context)
            _logger.info('Obsolete rating setted: %s' % len(rating_ids))
            rating_pool.write(cr, uid, rating_ids, {
                'obsolete': True,
                }, context=context)    
            
            for record in res:                
                partner = record[0]
                # TODO check strange case (one rating in ref_date)
                if partner.rating_ids:
                    rating_move = 'renewal'
                else:    
                    rating_move = 'first' 

                # -------------------------------------------------------------
                # 3. Update supplier info:
                # -------------------------------------------------------------
                partner_pool.write(cr, uid, partner.id, {
                    'qualification_date': ref_date,
                    'qualification_claim': record[8],
                    'qualification_acceptation': record[7],
                    'qualification_sampling ': record[9],
                    'qualification_packaging': record[10],
                    }, context=context)
                
                # -------------------------------------------------------------
                # 4. Create new evaluation:
                # -------------------------------------------------------------
                rating_pool.create(cr, uid, {
                    'date': ref_date,
                    'deadline': ref_deadline,
                    'name': '', # XXX
                    'type': rating_mode,
                    'qualification': record[15],
                    'obsolete': False,
                    }, context=context)
        return res
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
