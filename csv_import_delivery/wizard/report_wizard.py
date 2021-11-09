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
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    DATETIME_FORMATS_MAP,
    float_compare)
import xlsxwriter


_logger = logging.getLogger(__name__)


class ResPartnerDeliveryReportWizard(orm.TransientModel):
    """ Wizard for report totals
    """
    _name = 'res.partner.delivery.report.wizard'

    # --------------------
    # Wizard button event:
    # --------------------
    def action_print(self, cr, uid, ids, context=None):
        """ Event for print done
        """
        delivery_pool = self.pool.get('res.partner.delivery')
        excel_pool = self.pool.get('excel.writer')


        if context is None:
            context = {}

        wizard = self.browse(cr, uid, ids, context=context)[0]
        from_date = wizard.from_date
        to_date = wizard.to_date

        # Filter per date
        domain = [
            ('date', '>=', from_date),
            ('date', '<=', to_date),
        ]
        delivery_ids = delivery_pool.search(cr, uid, domain, context=context)

        # Pre-read
        carrier_total = {}
        for delivery in delivery_pool.browse(
                cr, uid, delivery_ids, context=context):
            carrier = delivery.carrier_id
            if carrier not in carrier_total:
                carrier_total[carrier] = 1
            else:
                carrier_total[carrier] += 1

        # Excel Report:
        ws_name = 'Qualifiche trasportatori'
        header = [
            u'Nome trasportatore',
            u'Città',
            u'Nazione',
            u'Tot. consegne',
        ]

        width = [
            40,
            30,
            25,
            15,
        ]

        # ---------------------------------------------------------------------
        # Create WS:
        # ---------------------------------------------------------------------
        ws = excel_pool.create_worksheet(name=ws_name)
        excel_pool.column_width(ws_name, width)

        # ---------------------------------------------------------------------
        # Generate format used:
        # ---------------------------------------------------------------------
        excel_pool.set_format()
        f_title = excel_pool.get_format(key='title')
        f_header = excel_pool.get_format(key='header')
        f_text = excel_pool.get_format(key='text')
        f_number = excel_pool.get_format(key='number')

        # ---------------------------------------------------------------------
        # Write title / header
        # ---------------------------------------------------------------------
        row = 0
        excel_pool.write_xls_line(
            ws_name, row, [
                'Totale consegne nel periodo: [%s - %s]' % (
                    from_date, to_date)], default_format=f_title)

        row += 1
        excel_pool.write_xls_line(
            ws_name, row, header, default_format=f_header)

        # Data part:
        for carrier in sorted(carrier_total, key=lambda c: c.name):
            total = carrier_total[carrier]
            row += 1
            excel_pool.write_xls_line(
                ws_name, row, [
                    carrier.name,
                    carrier.city or '',
                    carrier.country_id.name or '',
                    (total, f_number),
                ], default_format=f_text)

        return excel_pool.return_attachment(
            cr, uid, 'Spedizionieri', version='7.0', php=True)


    _columns = {
        'from_date': fields.date('Dalla data >=', required=True),
        'to_date': fields.date('Alla data <=', required=True),
        }
