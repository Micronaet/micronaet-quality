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

class ResPartnerDelivery(orm.Model):
    """ Model name: ResPartnerDelivery
    """

    _name = 'res.partner.delivery'
    _description = 'Carrier delivery'
    _rec_name = 'name'
    _order = 'name'

    def clean_string(self, value):
        """ Clean string
        """
        return (value or '').strip()

    def clean_date(self, value):
        """ Clean string
        """
        value = self.clean_string(value)
        return '20%s-%s-%s' % (
            value[6:8],
            value[3:5],
            value[:2],
            )

    # -------------------------------------------------------------------------
    # Scheduled procedure:
    # -------------------------------------------------------------------------
    def csv_import_carrier_files(self, cr, uid, path, only_current=True,
            context=None):
        """ Schedule import procedure:
            only_current: force reimport of current year
        """
        _logger.info('Start carrier delivery import procedure')

        # Parameters:
        final = 'vet.csv'
        separator = ';'

        carrier_pool = self.pool.get('res.partner')

        # ---------------------------------------------------------------------
        # Two launch mode:
        # ---------------------------------------------------------------------
        # 1. Only this year:
        if only_current:
            year = datetime.now().year
            csv_files = ['%s%s' % (year, final)]
            delivery_ids = self.search(cr, uid, [
                ('date', '>=', '%s-01-01' % year),
                ], context=context)
        # 2. All year present in folder:
        else:
            csv_files = []
            for root, dirs, files in os.walk(os.path.expanduser(path)):
                for filename in files:
                    if filename.endswith(final):
                        csv_files.append(filename)
            delivery_ids = self.search(cr, uid, [], context=context)

        # Delete previous record:
        _logger.info('Delete all record for this importation')
        self.unlink(cr, uid, delivery_ids, context=context)

        # ---------------------------------------------------------------------
        # Import procedure:
        # ---------------------------------------------------------------------
        partner_cache = {}
        for filename in csv_files:
            fullname = os.path.expanduser(os.path.join(path, filename))
            _logger.info('Read file: %s' % fullname)
            f_csv = open(fullname, 'r')
            for line in f_csv:
                line = line.strip()
                row = line.split(separator)

                # -------------------------------------------------------------
                # Read fields
                # -------------------------------------------------------------
                name = self.clean_string(row[0])
                date = self.clean_date(row[1])
                carrier_code = self.clean_string(row[2])
                carrier_name = self.clean_string(row[2])
                trip = self.clean_string(row[4])[:3]

                # -------------------------------------------------------------
                # Search carrier:
                # -------------------------------------------------------------
                if carrier_code in partner_cache:
                    carrier_id = partner_cache[carrier_code]
                else:
                    carrier_ids = carrier_pool.search(cr, uid, [
                        '|',
                        ('sql_customer_code', '=', carrier_code),
                        ('sql_supplier_code', '=', carrier_code),
                        ], context=context)

                    if carrier_ids:
                        carrier_id = carrier_ids[0]
                    else:
                        _logger.warning('New partner created: %s' % carrier_code)
                        carrier_id = carrier_pool.create(cr, uid, {
                            'is_company': True,
                            'supplier': True,
                            'name': carrier_name,
                            'sql_supplier_code': carrier_code,
                            }, context=context)
                    partner_cache[carrier_code] = carrier_id

                # -------------------------------------------------------------
                # Create delivery:
                # -------------------------------------------------------------
                self.create(cr, uid, {
                    'name': name,
                    'date': date,
                    'carrier_id': carrier_id,
                    'trip': trip,
                    }, context=context)

            f_csv.close()
        _logger.info('Stop carrier delivery import procedure')
        return True

    _columns = {
        'name': fields.char('DDT num.', size=20, required=True),
        'date': fields.date('Data', required=True),
        'carrier_id': fields.many2one('res.partner', 'Carrier'),
        'trip': fields.char('Trip', size=5),
        }
