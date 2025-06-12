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

class product_product(osv.osv):
    """ Extend product.product (override schedule function)
    """
    _inherit = 'product.product'

    # -------------------------------------------------------------------------
    #                     Scheduled action (overriden)
    # -------------------------------------------------------------------------
    def schedule_sql_product_import(self, cr, uid, verbose_log_count=100,
            write_date_from=False, write_date_to=False, create_date_from=False,
            create_date_to=False, context=None):
        """ Import product from external DB
            product has a code like [product_code][product_lot] (separator is
            the char lenght of product_code)
            1. Create product for product code length = separator
            2. Create lot for product code lenght > separator, link to product
            3. Nothing for code < separator (in context)
        """
        if context is None:
            context = {}

        lot_pool = self.pool.get('stock.production.lot')
        accounting_pool = self.pool.get('micronaet.accounting')
        separator = context.get('separator', 11)  # default (parametrize)

        # ---------------------------------------------------------------------
        #                            Function
        # ---------------------------------------------------------------------
        def create_update_supplier(self, cr, uid, record, context=None):
            """ Utility function for create / update a product from record
            """
            try:
                partner_pool = self.pool.get('res.partner')
                sql_supplier_code = record['CKY_CNT_FOR_AB']
                if not sql_supplier_code:
                    return False

                partner_ids = partner_pool.search(cr, uid, [
                    ('sql_supplier_code', '=', sql_supplier_code),
                    ], context=context)

                if partner_ids:
                    return partner_ids[0]
                else:
                   return partner_pool.create(cr, uid, {
                       'name': _('Supplier: %s') % sql_supplier_code,
                       'sql_supplier_code': sql_supplier_code,
                       'sql_import': True,
                       'is_company': True,
                       'supplier': True,
                       }, context=context)
            except:
                return False

        def create_update_product(self, cr, uid, record, context=None):
            """ Utility function for create / update a product from record
            """
            default_code = record['CKY_ART'][:separator]

            data = {
                # todo IFL_ART_DBP o DBV for supply_method='produce'
                'name': "%s%s" % (
                    record['CDS_ART'] or "",
                    record['CDS_AGGIUN_ART'] or ""),
                'default_code': default_code,
                'sql_import': True,
                'active': True,
                'statistic_category': "%s%s" % (
                    record['CKY_CAT_STAT_ART'] or '',
                    "%02d" % int(
                        record['NKY_CAT_STAT_ART'] or '0') if record[
                            'CKY_CAT_STAT_ART'] else '',
                ),
            }
            if accounting_pool.is_active(record):
                data['state'] = 'sellable'
            else:
                data['state'] = 'obsolete'

            product_ids = self.search(cr, uid, [
                ('default_code', '=', default_code)])

            if product_ids: # update
                product_id = product_ids[0]
                self.write(cr, uid, product_id, data, context=context)
            else:          # create
                product_id = self.create(cr, uid, data, context=context)
            return product_id

        def create_update_lot(self, cr, uid, record, context=None):
            """ Create product lot with record passed
            """
            lot_pool = self.pool.get('stock.production.lot')

            # --------
            # Product:
            # --------
            product_code = record['CKY_ART'][:separator]
            lot_code = record['CKY_ART'][separator:]
            product_ids = self.search(cr, uid, [
                ('default_code', '=', product_code)], context=context)
            if product_ids:
                product_id = product_ids[0]
            else:
                product_id = create_update_product(
                    self, cr, uid, record, context=context)

            # ------------
            # Product lot:
            # ------------
            try: # test if lot is integer
                int(lot_code)
            except:
                _logger.warning('Not a lot: %s' % record['CKY_ART'])
                return False

            default_supplier_id = create_update_supplier(
                self, cr, uid, record, context=context)
            real_deadline = lot_pool.get_lot_from_alternative_code(
                cr, uid, record['CSG_ART_ALT'], record['DTT_CRE'],
                context=context)

            lot_ids = lot_pool.search(cr, uid, [
                ('name', '=', lot_code),
                ('product_id', '=', product_id),
                # ('supplier_id', '=', supplier_id),
                ], context=context)

            if lot_ids:
                lot_id = lot_ids[0]
                # Update only deadline for now!!!
                lot_pool.write(cr, uid, lot_id, {
                    # 'name': lot_code,
                    # 'product_id': product_id,
                    # 'date': date,
                    # 'deadline': deadline,
                    'real_deadline': real_deadline,
                    # 'default_supplier_id': default_supplier_id,
                    }, context=context)
            else: # production lot or not imported
                lot_id = lot_pool.create(cr, uid, {
                    'name': lot_code,
                    'product_id': product_id,
                    # 'date': date,
                    # 'deadline': deadline,
                    'real_deadline': real_deadline,
                    'default_supplier_id': default_supplier_id,
                    }, context=context)

            # Duplicate flag:
            lot_ids = lot_pool.search(cr, uid, [
                ('name', '=', lot_code),
            ], context=context)
            if len(lot_ids) > 1:
                lot_pool.write(cr, uid, lot_ids, {
                    'duplicated': True,
                    }, context=context)
            return lot_id

        try:
            _logger.error("Load product only active!")
            cursor = accounting_pool.get_product(
                cr, uid,
                active=True, write_date_from=write_date_from,
                write_date_to=write_date_to, create_date_from=create_date_from,
                create_date_to=create_date_to, context=context)
            if not cursor:
                _logger.error("Unable to connect no importation for product!")
                return False

            i = 0
            # Create product (code length = separator:
            for record in cursor:
                i += 1
                try:
                    if verbose_log_count and i % verbose_log_count == 0:
                        _logger.info('Import %s: record imported / updated!' % i)
                    default_code = record['CKY_ART']

                    # Less code:
                    if len(default_code) < separator: # Code < separator
                        continue

                    # Product code:
                    elif len(default_code) == separator: # Code = separator
                        create_update_product(self, cr, uid, record, context=context)

                    # Lot code:
                    elif len(default_code) > separator: # Lot
                        create_update_lot(self, cr, uid, record, context=context)
                except:
                    _logger.error(
                        'Record: %s On import product/lot [%s], jumped: %s' % (
                            i, record['CDS_ART'], sys.exc_info(), ))

            _logger.info('All product is updated!')
        except:
            _logger.error('Error generic import product: %s' % (sys.exc_info(), ))
            return False
        return True


class stock_production_lot(osv.osv):
    """ Add extra fields
    """
    _inherit = 'stock.production.lot'

    def get_lot_from_alternative_code(
            self, cr, uid, code, creation_date, context=None):
        """ Custom function for get deadline for particular customer
            The deadline is insert in first 5 char of alternative code, like:
            01-10, 01/10, 01.10 and so on
            year is from creation_date
        """
        separator = ('.', ',', '-', ' ', ':', '_', ';', '/', '\\')
        code = code[:5]
        if len(code) == 5 and code[2] in separator:
            try:
                # deadline = "%s-%s-%s" % (
                #    creation_date.year,
                #    code[:2], code[3:])
                # deadline = "20%s-%s-01" % (code[3:], code[:2])
                deadline = '20%s-%s' % (code[3:], code[:2])
                # Date test (removed 07-11-2017)
                # test = datetime.strptime(
                # deadline, DEFAULT_SERVER_DATE_FORMAT)
                return deadline
            except:
                pass # test raise error (no date)
        return False

    _columns = {
        'duplicated': fields.boolean('Duplicated'),
        }

    _defaults = {
        'duplicated': lambda *a: False,
        }
