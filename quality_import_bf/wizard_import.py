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
import logging
from openerp.osv import osv, fields
import shutil
from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _


_logger = logging.getLogger(__name__)

class quality_acceptation_import_wizard(osv.osv_memory):
    ''' Acceptation wizard for importation document
    '''
    _name = 'quality.acceptation.wizard.import'
    _description = 'Import acceptation'

    # -----------------
    # Utility function: 
    # -----------------
    def parse_line(self, line):
        ''' Get file line
            clean all chr(0) char
            parse in a tuple list of values
        '''
        line = line.replace(chr(0), '')        
        return line[:8].strip(), line[8:14].strip(), line[14:19].strip(), line[19:59].strip(), line[59:70].strip(), float(line[70:82].strip() or '0.0')
        
    def get_import_file(self, cr, uid, context=None):
        ''' Utility funciton for get file obj
        '''
        try:
            import_filename = self.pool.get('res.company').get_quality_import_bf_filename(cr, uid, context=context)        
            if import_filename:
                return open(import_filename, 'r'), import_filename
        except:
            return False, False
        
    # -------------
    # Button event: 
    # -------------
    def action_confirm_acceptation_import(self, cr, uid, ids, context=None):
        ''' Import button
        '''
        # -----
        # Init:
        # -----
        lot_pool = self.pool.get('stock.production.lot')
        product_pool = self.pool.get('product.product')
        partner_pool = self.pool.get('res.partner')
        acceptation_pool = self.pool.get('quality.acceptation')
        
        # -----------------
        # Utility function:
        # -----------------
        def get_create_supplier(self, cr, uid, code, context=None):
            ''' Get supplier id with code (or create a temporary supplier)
            '''
            try:
                partner_ids = partner_pool.search(cr, uid, [
                    ('sql_supplier_code', '=', code),
                    ], context=context)
                
                if partner_ids:
                    return partner_ids[0]
                else:
                   return partner_pool.create(cr, uid, {
                       'name': _("Supplier: %s") % code,
                       'sql_supplier_code': code,
                       'sql_import': True,
                       'supplier': True,
                       'is_company': True,
                       }, context=context)
            except:
                return False       

        def get_create_product(self, cr, uid, default_code, name, context=None):
            ''' Utility function for create / update a product from record
            '''
            try:
                product_ids = product_pool.search(cr, uid, [
                    ('default_code', '=', default_code)], context=context)

                if product_ids: # update
                    product_id = product_ids[0]
                else:          # create
                    product_id = product_pool.create(cr, uid, {
                        'name': name,
                        'default_code': default_code,
                        'sql_import': True,
                        }, context = context)
                return product_id
            except:
                return False

        def create_update_lot(self, cr, uid, lot_code, product_id, supplier_id, context=None):
            ''' Create product lot with record passed
            '''
            lot_ids = lot_pool.search(cr, uid, [
                ('name', '=', lot_code),
                ('product_id', '=', product_id),
                ], context=context)
            
            if lot_ids:
                return lot_ids[0]
            else:            
                if product_id and supplier_id:                    
                    return lot_pool.create(cr, uid, {
                        'name': lot_code,
                        'product_id': product_id,
                        'default_supplier_id': supplier_id,
                        }, context=context)
                else:
                    return False

        # -----------
        # Main event:
        # -----------
        f, filename = self.get_import_file(cr, uid, context=context)
        
        if not f:
            return _("Error reading filename for import, missing parameter in Company form!")    

        record = False
        for line in f:
            line = self.parse_line(line)
            
            supplier_code = line[0]
            origin = line[1]
            lot_code = line[2]
            product_description = line[3]
            product_code = line[4]
            quantity = line[5]

            product_id = get_create_product(
                self, cr, uid, product_code, product_description, 
                context=context)
            supplier_id = get_create_supplier(
                self, cr, uid, supplier_code, context=context)
            lot_id = create_update_lot(
                self, cr, uid, lot_code, product_id, supplier_id, 
                context=context)

            #if product_id and supplier_id and lot_id:
            if not record: 
                # Create header document:                
                record = {
                    'origin': origin,
                    'partner_id': supplier_id,
                    'note': False,
                    #'ref': ref,
                    #'date': , # today??
                    #'state' ,
                    'line_ids': []
                    }
                
            # Create line:     
            record['line_ids'].append( # new record to be created with
                [0, 0, {
                     'lot_id': lot_id,
                     'product_id': product_id,
                     'qty_arrived': quantity,
                     'qty_expected': quantity,
                     #'acceptation_id': 
                     #'um': quantity,
                     }])
        f.close()
        if record: 
            acceptation_id = acceptation_pool.create(
                cr, uid, record, context=context)
            #import pdb; pdb.set_trace() # TODO finire il debug??
            # Mode file in backup zone 
            history_folder = os.path.join(
                os.path.dirname(os.path.realpath(filename)), "history")
            try:            
                os.mkdir(history_folder)
            except:
                pass
                
            try:            
                shutil.move(filename, os.path.join(
                    history_folder, "%s.txt" % acceptation_id))
            except:
                _logger.error("Cannot move file in history folder!")
                #os.remove(filename)

        return self.pool.get('micronaet.tools').get_view_dict(cr, uid, {
            'model': 'quality.acceptation',
            'module': 'quality',
            'record': acceptation_id,
            })
        
    # -----------------------
    # Default field function:    
    # -----------------------
    def get_default_file(self, cr, uid, context=None):
        ''' Return file info for field in wizard
        '''
        f, filename = self.get_import_file(cr, uid, context=context)
        if f:
            text_file = """
                <style>
                    .table_bf {
                         border:1px 
                         padding: 3px;
                         solid black;
                     }
                    .table_bf td {
                         border:1px 
                         solid black;
                         padding: 3px;
                         text-align: center;
                     }
                    .table_bf th {
                         border:1px 
                         solid black;
                         padding: 3px;
                         text-align: center;
                         background-color: grey;
                         color: white;
                     }
                </style>
                <table class='table_bf'>"""
            text_file += _("<tr class='table_bf'><th>Supplier</th><th>Document</th><th>Lot</th><th>Description</th><th>Code</th><th>Quantity</th></tr>")
            for line in f:
                #import pdb; pdb.set_trace()
                line = self.parse_line(line)
                text_file += u"<tr><td>%-20s</td><td>%-10s</td><td>%-10s</td><td>%-40s</td><td>%-15s</td><td class='{text-align: right;}'>%14s</td></tr>" % line
            f.close()

            text_file += "</table>"
            return text_file
        else:
            return _("Error reading filename for import, missing parameter in Company form!")    

            
    _columns = {
        'file': fields.text('File to import'),
        'note': fields.text('Import information'),
        }
    _defaults = {
        'file': lambda s, cr, uid, ctx: s.get_default_file(cr, uid, context=ctx),
        'note': lambda *x: _("See the preview info about file above and decide to import if is correct!"),
        }

class res_company(osv.osv):
    ''' Add extra parameters for importation
    '''
    _name = 'res.company'
    _inherit = 'res.company'
    
    def get_quality_import_bf_filename(self, cr, uid, context=None):
        ''' Read parameter saved and return file name
        '''
        try:
            company_ids = self.search(cr, uid, [], context=context) # TODO only company selected
            company_proxy = self.browse(cr, uid, company_ids, context=context)[0]
            quality_import_filename = eval(company_proxy.quality_import_file)
            return os.path.expanduser(os.path.join(*quality_import_filename))
        except:
            _logger.error(_("Error trying to read filename parameters"))    
        return False
        
    _columns = {
        'quality_import_file': fields.char(
            'Quality import file', size=100, required=False, readonly=False, 
            help="Tuple value, like: ('~', 'etl', 'demo', 'BF.txt')"),
        }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
