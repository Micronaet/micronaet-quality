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
    """ Swap partner parent code
    """
    _name = 'res.partner.swap'
    _description = 'Swap parent'

    _columns = {
        'name': fields.char('Original', size=10, required=True),
        'swap': fields.char('Swap code', size=10, required=True),
        }


class ResPartner(osv.osv):
    """ Insert override elements
    """
    _inherit = 'res.partner'

    # -------------------------------------------------------------------------
    #                         Override function:
    # -------------------------------------------------------------------------
    # Virtual function that calculate swap dict:
    def get_swap_parent(self, cr, uid, context=None):
        """ Override with function that load override fields
        """
        res = {}
        swap_pool = self.pool.get('res.partner.swap')
        swap_ids = swap_pool.search(cr, uid, [], context=None)
        for swap in swap_pool.browse(
                cr, uid, swap_ids, context=context):
            res[swap.name] = swap.swap
        return res

    # Scheduled function that import partner (and after update forms)
    # todo better create new module only for quality only with this function:
    # -------------------------------------------------------------------------
    #                             Scheduled action
    # -------------------------------------------------------------------------
    # Change original function schedule_sql_partner_import:
    def schedule_sql_partner_import_version_2(
            self, cr, uid, verbose_log_count=100,
            capital=True, write_date_from=False, write_date_to=False,
            create_date_from=False, create_date_to=False,
            context=None):
        """ Import partner from external DB
            verbose_log_count: number of record for verbose log (0 = nothing)
            capital: if table has capital letters (usually with mysql in win)
            write_date_from: for smart update (search from date update record)
            write_date_to: for smart update (search to date update record)
            create_date_from: for smart update (search from date create record)
            create_date_to: for smart update (search to date create record)
            sync_vat: Supplier update partner customer with same VAT
            address_link: Link to parent partner as an address the destination
            only_block: update only passed block name:
                (supplier, customer destination... TODO agent, employee)
            context: context of procedure

        """
        # Load country for get ID from code
        country_pool = self.pool.get('res.country')
        fiscal_pool = self.pool.get('account.fiscal.position')
        accounting_pool = self.pool.get('micronaet.accounting')
        company_pool = self.pool.get('res.company')

        # ---------------------------------------------------------------------
        # Load company for parameters:
        # ---------------------------------------------------------------------
        company_proxy = company_pool.get_from_to_dict(
            cr, uid, context=context)
        if not company_proxy:
            _logger.error('Company parameters not set up!')

        # ---------------------------------------------------------------------
        #                          MASTER LOOP:
        # ---------------------------------------------------------------------
        # Order, key field, from code, to code, type
        import_loop = [
            (1,
             'sql_customer_code',
             company_proxy.sql_customer_from_code,
             company_proxy.sql_customer_to_code,
             'customer'),

            (2,
             'sql_supplier_code',
             company_proxy.sql_supplier_from_code,
             company_proxy.sql_supplier_to_code,
             'supplier'),

            (3,
             'sql_destination_code',
             company_proxy.sql_destination_from_code,
             company_proxy.sql_destination_to_code,
             'destination'),

            # todo (vedere come comportarsi durante la creazione
            # (simili a fornitori, agganciarli a fiscalcode)
            # (4,
            # 'sql_agent_code',
            # company_proxy.sql_agent_from_code,
            # company_proxy.sql_agent_to_code,
            # 'agent'),

            # (5,
            # 'sql_employee_code',
            # company_proxy.sql_employee_from_code,
            # company_proxy.sql_employee_to_code,
            # 'employee'),
        ]

        # =====================================================================
        #                          Foreign keys:
        # =====================================================================
        # Load fiscal position type CEI:
        # ---------------------------------------------------------------------
        fiscal_position_db = {}
        fiscal_ids = fiscal_pool.search(cr, uid, [], context=context)
        for fiscal in fiscal_pool.browse(
                cr, uid, fiscal_ids, context=context):
            try:
                cei_ref = fiscal.cei_ref
            except:
                _logger.error(
                    'No CEI Management in fiscal position. '
                    'No fiscal position loaded!')
                break
            fiscal_position_db[cei_ref] = fiscal.id

        # ---------------------------------------------------------------------
        # Load Country:
        # ---------------------------------------------------------------------
        countries = {}
        country_ids = country_pool.search(cr, uid, [], context=context)
        country_proxy = country_pool.browse(
            cr, uid, country_ids, context=context)
        for item in country_proxy:
            countries[item.code] = item.id

        # ---------------------------------------------------------------------
        # Parent for destination:
        # ---------------------------------------------------------------------
        destination_parents = {}  # Partner code for Destination

        # Swap parent couple:
        swap_parent = self.get_swap_parent(cr, uid, context=context)

        _logger.info('Read parent for destinations')
        cursor = accounting_pool.get_parent_partner(cr, uid, context=context)
        if not cursor:
            _logger.error('Unable to connect to parent for destination!')
        else:
            for record in cursor:
                # Swapped:
                destination_parents[
                    record['CKY_CNT']] = swap_parent.get(
                        record['CKY_CNT_CLI_FATT'], record['CKY_CNT_CLI_FATT'])

        # ---------------------------------------------------------------------
        #                          Master import:
        # ---------------------------------------------------------------------
        try:
            _logger.info('Start import SQL: customer, supplier, destination')
            parents = {}  # Client / Supplier converter

            # Master Loop:
            for order, key_field, from_code, to_code, block in import_loop:
                if only_block and only_block != block:
                    _logger.warning('Jump block: %s!' % block)
                    continue
                cursor = accounting_pool.get_partner(
                    cr, uid, from_code=from_code, to_code=to_code,
                    write_date_from=write_date_from,
                    write_date_to=write_date_to,
                    create_date_from=create_date_from,
                    create_date_to=create_date_to, context=context)
                if not cursor:
                    _logger.error('Unable to connect, no partner!')
                    continue  # next block

                _logger.info('Start import %s from: %s to: %s' % (
                    block, from_code, to_code))
                i = 0
                for record in cursor:
                    i += 1
                    if verbose_log_count and not i % verbose_log_count:
                        _logger.info(
                            'Import %s: %s record imported / updated!' % (
                                block, i, ))
                    try:
                        # if record['CKY_CNT'] in ('06.03132', '06.03173'):
                        #    pdb.set_trace()
                        data = {
                            'name': record['CDS_CNT'],
                            # 'sql_customer_code': record['CKY_CNT'],
                            'sql_import': True,
                            'is_company': True,
                            'street': record['CDS_INDIR'] or False,
                            'city': record['CDS_LOC'] or False,
                            'zip': record['CDS_CAP'] or False,
                            'phone': record['CDS_TEL_TELEX'] or False,
                            'email': record['CDS_INET'] or False,
                            'fax': record['CDS_FAX'] or False,
                            # 'mobile': record['CDS_INDIR'] or False,
                            'website': record['CDS_URL_INET'] or False,
                            'vat': record['CSG_PIVA'] or False,
                            key_field: record['CKY_CNT'],  # key code
                            'country_id': countries.get(
                                record['CKY_PAESE'], False),
                            }

                        # -----------------------------------------------------
                        # Extra data depend on block:
                        # -----------------------------------------------------
                        if block == 'customer':
                            data['type'] = 'default'
                            data['customer'] = True
                            data['ref'] = record['CKY_CNT']
                            if fiscal_position_db:
                                data['property_account_position'] = \
                                    fiscal_position_db.get(record['IST_NAZ'])

                        if block == 'supplier':
                            data['type'] = 'default'
                            data['supplier'] = True
                            if fiscal_position_db:
                                data['property_account_position'] = \
                                    fiscal_position_db.get(record['IST_NAZ'])

                        if block == 'destination':
                            data['type'] = 'delivery'
                            data['is_address'] = True
                            # No fiscal position

                            parent_code = destination_parents.get(
                                record['CKY_CNT'], False)
                            if parent_code:  # Convert value with dict
                                # Cache search:
                                data['parent_id'] = parents.get(
                                    parent_code, False)

                                # if not in convert dict try to search
                                if not data['parent_id']:
                                    # Normal search:
                                    parent_ids = self.search(cr, uid, [
                                        '|',
                                        ('sql_customer_code', '=',
                                         parent_code),
                                        ('sql_supplier_code', '=',
                                         parent_code),
                                        ], context=context)
                                    if parent_ids:
                                        data['parent_id'] = parent_ids[0]

                        # Search parent:
                        partner_ids = self.search(cr, uid, [
                            (key_field, '=', record['CKY_CNT'])])

                        # Connect if theres a partner VAT equal:
                        if not partner_ids and record['CSG_PIVA'] and \
                                block != 'destination':
                            partner_ids = self.search(cr, uid, [
                                ('vat', '=', record['CSG_PIVA'])])

                        # Update / Create
                        if partner_ids:
                            partner_id = partner_ids[0]
                            try:
                                self.write(
                                    cr, uid, [partner_id], data,
                                    context=context)
                            except:
                                del data['vat']
                                try:  # Remove vat for vat check problems:
                                    self.write(
                                        cr, uid, [partner_id], data,
                                        context=context)
                                except:
                                    _logger.error(
                                        '%s. Error updating partner [%s]: '
                                        '%s' % (i, record, sys.exc_info()))
                                    continue
                        else:
                            try:
                                partner_id = self.create(
                                    cr, uid, data, context=context)
                            except:
                                del data['vat']
                                try:  # Remove vat for vat check problems:
                                    partner_id = self.create(
                                        cr, uid, data, context=context)
                                except:
                                    _logger.error(
                                        '%s. Error creating partner [%s]: '
                                        '%s' % (i, record, sys.exc_info()))
                                    continue

                        if block != 'destination':  # Cache partner ref.
                            parents[record['CKY_CNT']] = partner_id
                    except:
                        _logger.error(
                            'Error importing partner [%s], jumped: %s' % (
                                record['CDS_CNT'], sys.exc_info()))
                        continue
                _logger.info('>>>> All record in block %s is updated!' % block)
        except:
            _logger.error(
                'Error generic import partner: %s' % (sys.exc_info(), ))
            return False
        return True


    '''
    def schedule_sql_partner_import(
        self, cr, uid, verbose_log_count=100,
        capital=True, write_date_from=False, write_date_to=False,
        create_date_from=False, create_date_to=False, sync_vat=False,
        address_link=False, only_block=False, context=None):

        # -----------------------
        # Call original function:
        # -----------------------
        _logger.info('QUALITY: Call original module for import partner')
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
        _logger.info('QUALITY: Swap partner list: %s' % (swap_list, ))
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
    '''
