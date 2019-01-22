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

{
    'name': 'Quality process',
    'version': '0.1',
    'category': 'Quality',
    'description': """Manage quality process""",
    'author': 'Micronaet s.r.l.',
    'website': 'http://www.micronaet.it',
    'license': 'AGPL-3',
    'depends': [
        'base', 
        'micronaet_tools',
        'stock',
        'mail',
        'report_aeroo',
        'report_aeroo_ooo',
        'partner_addresses',
        'csv_import_delivery', # Import supplier delivery from account
        #'base_mssql',
        #'base_mssql_accounting',
        #'partner_addresses',
    ],
    'init_xml': [],
    'demo_xml': [],
    'update_xml': [
        'security/quality_group.xml',
        'security/ir.model.access.csv',
        'quality_sequence.xml',
        'quality_view.xml',
        #'scheduler.xml',

        # Workflow:
        'workflow/claim_workflow.xml',
        'workflow/conformed_workflow.xml',
        'workflow/sampling_workflow.xml',
        'workflow/action_workflow.xml',
        'workflow/acceptation_workflow.xml',
        'workflow/conformed_external_workflow.xml',

        # Report:
        'report/quality_report.xml',
        
        'data/quality.xml',

        #'counter.xml',
    ],
    'active': False,
    'installable': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
