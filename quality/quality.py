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
import base64
import pdb
import logging
import shutil
from openerp import netsvc
from openerp.osv import osv, fields
from datetime import datetime, timedelta
from openerp.tools import (
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare)
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _


# -----------------------------------------------------------------------------
#           State for selection (used for real field and related
# -----------------------------------------------------------------------------
acceptation_state = [
    ('opened', 'Opened'),
    ('closed', 'Closed'),
    ('cancel', 'Cancel'),
    ]

action_state = [
    ('draft', 'Draft'),
    ('opened', 'Opened'),
    ('closed', 'Closed'),
    ('cancel', 'Cancel'),
    ('saw', 'Saw'),
    ]

sampling_state = [
    ('draft', 'Draft'),
    ('opened', 'Opened'),
    ('passed', 'Passed'),
    ('notpassed', 'Not passed'),
    ('cancel', 'Cancel'),
    ]

conformed_state = [
    ('draft', 'Draft'),
    ('opened', 'Opened'),
    ('closed', 'Closed'),
    ('cancel', 'Cancel'),
    ('saw', 'Saw'),
    ]

conformed_external_state = [
    ('draft', 'Draft'),
    ('opened', 'Opened'),
    ('closed', 'Closed'),
    ('cancel', 'Cancel'),
    ('saw', 'Saw'),
    ]

_logger = logging.getLogger(__name__)


class quality_document(osv.osv):
    """ Simple document management
    """
    _name = 'quality.document'
    _description = 'Documenti'

    # -------------------------------------------------------------------------
    # Utility:
    # -------------------------------------------------------------------------
    def dummy_save(self, cr, uid, ids, context=None):
        """ Save
        """
        return True

    def open_generator_document(
            self, cr, uid, ids, context=None):
        """ Open form with default
        """
        document = self.browse(cr, uid, ids, context=context)[0]
        model_ref_part = document.model_ref.split(',')

        return  {
            'type': 'ir.actions.act_window',
            'name': _('Collega documento'),
            'view_type': 'form',
            'view_mode': 'form',
            # 'res_id': res_id,
            'res_model': model_ref_part[0],
            'view_id': int(model_ref_part[1]),
            'views': [(False, 'form')],
            'domain': [],
            'context': context,
            'target': 'new',
            'nodestroy': False,
            }

    def open_quality_document_add(
            self, cr, uid, model, item_id, area='', context=None):
        """ Open form with default
        """
        if context is None:
            context = {}
        ctx = context.copy()
        ctx['default_model_ref'] = '%s,%s' % (model, item_id)
        ctx['default_area'] = area

        return  {
            'type': 'ir.actions.act_window',
            'name': _('Collega documento'),
            'view_type': 'form',
            'view_mode': 'form',
            # 'res_id': res_id,
            'res_model': 'quality.document',
            'view_id': False,
            'views': [(False, 'form')],
            'domain': [],
            'context': ctx,
            'target': 'new',
            'nodestroy': False,
            }


    def get_many2many(self, cr, uid, model, item_id, context=None):
        """ Search model ref
        """
        result = {}

        search_ids = self.search(cr, uid, [
            ('model_ref', '=', '%s,%s' % (model, item_id)),
        ], context=context)

        result[item_id] = search_ids
        return result

    def get_php_return_page(self, cr, uid, fullname, name, context=None):
        """ Generate return object for pased files
        """
        config_pool = self.pool.get('ir.config_parameter')
        key = 'quality.document.base.url'
        config_ids = config_pool.search(cr, uid, [
            ('key', '=', key)], context=context)
        if not config_ids:
            raise osv.except_osv(
                _('Errore'),
                _('Avvisare amministratore: configurare parametro: %s' % key),
                )
        config_proxy = config_pool.browse(
            cr, uid, config_ids, context=context)[0]
        base_address = config_proxy.value
        _logger.info('URL parameter: %s' % base_address)

        return {
            'type': 'ir.actions.act_url',
            'url': '%s/save_as.php?filename=%s&name=%s' % (
                base_address, fullname, name),
            # 'target': 'new',
            }

    # Button
    def return_file_apache_php(
            self, cr, uid, ids, context=None):
        """ Return file with PHP page
        """
        origin = self.get_fullname(cr, uid, ids[0], context=context)
        filename = os.path.basename(origin)
        destination = os.path.join('/tmp', filename)

        # Copy current file in temp destination
        try:
            shutil.copyfile(origin, destination)
        except:
            raise osv.except_osv(
                _('File non trovato'),
                _(u'File non trovato nella gest. documentale!\n%s' % origin),
                )

        # Return link for open temp file:
        name = 'Quality_Doc_%s' % filename
        return self.get_php_return_page(
            cr, uid, destination, name, context=context)

    def delete_document(self, cr, uid, ids, context=None):
        """ Load document from binary file
        """
        return True

    def get_store_path(self, cr, uid, context=None):
        """ Extract store path from parameter
        """
        config_pool = self.pool.get('ir.config_parameter')
        param = 'quality.document.store.folder'
        try:
            config_ids = config_pool.search(cr, uid, [
                ('key', '=', param),
            ], context=context)
            config = config_pool.browse(
                cr, uid, config_ids, context=context)[0]
            return os.path.expanduser(config.value)
        except:
            raise osv.except_osv(
                _('Errore'),
                _('Necessario indicare nel parametro %s '
                  'il valore della cartella di store documentale!' % param),
                )

    # -------------------------------------------------------------------------
    # Override function:
    # -------------------------------------------------------------------------
    def get_fullname(self, cr, uid, ids, context=None):
        """ Return fullname of the file
        """
        if type(ids) == int:
            res_id = ids
        else:
            res_id = ids[0]

        document = self.browse(cr, uid, res_id, context=context)
        path = self.get_store_path(cr, uid, context=context)
        extension = document.extension

        # Save file as ID.extension in Store folder
        fullname = os.path.join(
            path,
            '%s.%s' % (res_id, extension),
        )
        return fullname

    def create(self, cr, uid, vals, context=None):
        """ Generate not conformed if one problem is fount
        """
        # Technically during creation there's not check operation (automated)
        try:
            document_string = vals['file']
        except:
            document_string = False

        if not document_string:
            raise osv.except_osv(
                _('Errore'),
                _('Necessario indicare il file per creare un documento!'),
                )

        del(vals['file'])
        vals['loaded'] = True  # Hide Binary widget
        res_id = osv.osv.create(self, cr, uid, vals, context=context)

        fullname = self.get_fullname(cr, uid, [res_id], context=context)
        with open(fullname, 'wb') as f:
            f.write(base64.b64decode(document_string))
        _logger.info('Storing file: %s' % fullname)
        return res_id

    _columns = {
        'name': fields.char(
            'Descrizione', size=120, required=True),
        'date': fields.date('Data creazione'),
        'user_id': fields.many2one('res.users', 'Utente'),

        'area': fields.char('Area', size=80),
        'model_ref': fields.char(
            'Collegato a', size=60,
            help='Contiene il riferimento come: model.name,ID'),
        'note': fields.text('Note'),
        'loaded': fields.boolean(
            'Caricato', help='Nasconde il caricamento di file successivi'),

        'extension': fields.selection([
            ('pdf', 'Acrobat PDF'),
            ('docx', 'Word DOCX'),
            ('doc', 'Word DOC (obsoleto)'),
            ('xlsx', 'Excel XLSX'),
            ('xls', 'Excel XLS (obsoleto)'),
            ('zip', 'Cartella comprezza ZIP'),
            ], 'Tipo file', required=True),
        'file': fields.binary('File'),
    }

    _defaults = {
        'extension': lambda *x: 'pdf',
        'user_id': lambda s, cr, uid, ctx: uid,
        'date':
            lambda *x: datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
    }

class mail_thread(osv.osv):
    """ Add extra function for changing state in mail.thread
    """
    _inherit = 'mail.thread'
    _name = 'mail.thread'

    # --------
    # Utility:
    # --------
    def write_object_change_state(self, cr, uid, ids, context=None):
        """ Write info in thread list (used in WF actions)
        """
        current_proxy = self.browse(cr, uid, ids, context=context)[0]

        # Default part of message:
        message = {
            'subject': _("Changing state:"),
            'body': _("State variation in <b>%s</b>") % current_proxy.state,
            'type': 'comment', #'notification', 'email',
            'subtype': False,  #parent_id, #attachments,
            'content_subtype': 'html',
            'partner_ids': [],
            'email_from': 'openerp@micronaet.it', #wizard.email_from,
            'context': context,
            }
        #message['partner_ids'].append(
        #    task_proxy.assigned_user_id.partner_id.id)
        self.message_subscribe_users(
            cr, uid, ids, user_ids=[uid], context=context)

        msg_id = self.message_post(cr, uid, ids, **message)
        #if notification:
        #    _logger.info(">> Send mail notification! [%s]" % message[
        #    'partner_ids'])
        #    self.pool.get(
        #        'mail.notification')._notify(cr, uid, msg_id,
        #        message['partner_ids'],
        #        context=context
        #        )
        return


class quality_conformed_external(osv.osv):
    """ Forms of not conformed
    """
    _name = 'quality.conformed.external'
    _inherit = ['mail.thread']

    _description = 'Not conformed external'
    _order = 'ref desc'
    _rec_name = 'ref'

    # -------------------------------------------------------------------------
    # Workflow Activity Function:
    # -------------------------------------------------------------------------
    def conformed_external_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'draft',
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def conformed_external_opened(self, cr, uid, ids, context=None):
        external_proxy = self.browse(cr, uid, ids, context=context)[0]
        if external_proxy.ref:
            ref = external_proxy.ref
        else:
            if external_proxy.mode == 'internal':
                ref = self.pool.get('ir.sequence').get(cr, uid,
                    'quality.conformed.internal')
            else: #supplier
                ref = self.pool.get('ir.sequence').get(cr, uid,
                    'quality.conformed.external')

        self.write(cr, uid, ids, {
            'state': 'opened',
            'ref': ref,
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def conformed_external_closed(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'closed',
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def conformed_external_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'cancel',
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def conformed_external_saw(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'saw',
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    _columns = {
        'name': fields.text('Type'),
        'ref': fields.char('Ref', size=100, readonly=True),
        'insert_date': fields.date('Insert date', required=True),
        'supplier_id':fields.many2one('res.partner', 'Supplier'),
        'origin': fields.selection([
            # ('acceptation', 'Acceptation'),
            # ('sampling', 'Sampling'),
            ('claim', 'Claim'),
            # ('packaging', 'Packaging'),
            ('doc', 'Documentation not send'),
            ('other', 'Other'),
        ], 'Origin', select=True),
        'mode': fields.selection([
            ('internal', 'Internal'),
            ('supplier', 'Supplier'),
        ], 'Mode', required=True, select=True),
        'origin_other': fields.char('Other', size=60),
        'reference_user_id': fields.many2one(
            'res.users', 'Ref. user',
            help='Ref. user when no origin from claim'),
        'note_RAQ': fields.text('Note RAQ'),
        'stock_note': fields.text('Stock note'),
        'comunication_note': fields.text('Comunication note'),
        'treatment': fields.text('Treatment'),
        'judgement': fields.text('Judgement'),
        'judgement_date': fields.date('Data del giudizio'),
        'state': fields.selection(
            conformed_external_state, 'State',
            select=True, readonly=True),
        #'aesthetic_packaging': fields.boolean('Confezione'),
        #'quantity': fields.boolean('Quantity'),
        #'sanitation': fields.boolean('Sanitation'),
        #'temperature': fields.boolean('Temperature'),
        #'label': fields.boolean('Label'),
        #'quality': fields.boolean('Quality'),
        #'deadline': fields.boolean('Deadline'),
        #'delay': fields.boolean('Ritardo'),
        #'no_delivery': fields.boolean('Mancata consegna'),
        #'external_material': fields.boolean('Corpi estranei'),
        #'genesis':fields.selection([
            #('acceptance', 'Acceptance'),
            #('sample', 'Sample'),
            #('claim', 'Claim'),
            #('packaging', 'Packaging'),
            #('other', 'Other'),
            #   ],'Genesis', select=True),
        #'other':fields.char('Other', size=100),
        #'claim_id': fields.many2one('quality.claim', 'Claim'),
        #'sampling_id': fields.many2one('quality.sampling', 'Sampling'),
        #'acceptation_id': fields.many2one('quality.acceptation',
        #    'Acceptation'),
        #'ddt_ref': fields.char('DDT reference', size=50),
        # TODO mandatory??
        #'lot_id':fields.many2one('stock.production.lot', 'Real Lot'),
        #'label_lot': fields.char('Label Lot', size=25),
        #'label_supplier': fields.char('Label Supplier', size=50),
        #'lot_deadline': fields.related('lot_id', 'real_deadline', type='char',
        #    string='Lot Deadline', store=False),
        #'cancel': fields.boolean('Cancel'),
        #'supplier_lot': fields.related('lot_id', 'default_supplier_id',
        #    type='many2one', relation='res.partner', string='Supplier'),
        #'descr_product': fields.related('lot_id', 'product_id',
        #    type='many2one', relation='product.product',
        #    string='Product description'),
        #'note_warehouse': fields.text('Note Warehouse'),
        # TODO Change reference field:
        #'comunication_ids': fields.one2many('quality.comunication',
        #    'conformed_id', 'Comunications'),
        #'treatment_ids': fields.one2many('quality.treatment', 'conformed_id',
        #    'Treatments'),
        #'parent_sampling_id': fields.many2one('quality.sampling',
        #    'Parent Sampling', ondelete='set null'),
        #'sampling_id': fields.many2one('quality.sampling', 'Sampling',
        #    ondelete='set null'),
        #'sampling_state': fields.related('sampling_id', 'state',
        #    type='selection', selection=sampling_state,
        #    string='Sampling state', store=False),
        # TODO fields.relater sampling_id state (come per action)

        }

    _defaults = {
        'mode': lambda *x: 'supplier',
        'reference_user_id': lambda s, cr, uid, ctx: uid,
        'insert_date': lambda *x: datetime.now().strftime(
            DEFAULT_SERVER_DATE_FORMAT),
        'origin': lambda *a: 'other',
        'state': lambda *a: 'draft',
        }


# -----------------------------------------------------------------------------
#                                    CLAIMS:
# -----------------------------------------------------------------------------
class res_users(osv.osv):
    """ Add signature
    """
    _inherit = 'res.users'

    _columns = {
        'signature_image': fields.binary('Signature', filters=None),
        }

class quality_origin(osv.osv):
    """ Simple anagrafic for origin
    """
    _name = 'quality.origin'
    _description = 'Origin'

    _columns = {
        'name':fields.char('Description', size=64, required=True,
            translate=True),
        'note': fields.text('Note'),
        'type':fields.selection([
            ('claim','Claim'),
            #('action','Action'),
            ], 'Type', select=True),

        'access_id': fields.integer('Access ID'),
    }

class quality_claim_cause(osv.osv):
    """ Simple anagrafic for cause
    """
    _name = 'quality.claim.cause'
    _description = 'Claim cause'

    _columns = {
        'name':fields.char('Description', size=64, required=True,
            translate=True),
        'note': fields.text('Note'),

        'access_id': fields.integer('Access ID'),
    }

class quality_gravity(osv.osv):
    """ Simple anagrafic for gravity
    """
    _name = 'quality.gravity'
    _description = 'Claim gravity'

    _columns = {
        'name':fields.char('Description', size=64, required=True,
            translate=True),
        'note': fields.text('Note'),

        'access_id': fields.integer('Access ID'),
    }

class stock_production_lot(osv.osv):
    """ Manage the lot
    """
    _inherit = 'stock.production.lot'

    # -------------------------------------------------------------------------
    # Button event:
    # -------------------------------------------------------------------------
    def set_obsolete(self, cr, uid, ids, context=None):
        """ Button event for set boolean to obsolete
        """
        return self.write(cr, uid, ids, {'obsolete': True}, context=context)

    def set_not_obsolete(self, cr, uid, ids, context=None):
        """ Button event for set boolean to not obsolete
        """
        return self.write(cr, uid, ids, {'obsolete': False}, context=context)

    def go_to_acceptation(self, cr, uid, ids, context=None):
        """ Go to acceptation
        """
        #model_pool = self.pool.get('ir.model.data')
        #view_id = model_pool.get_object_reference('module_name', 'view_name')[1]

        current = self.browse(cr, uid, ids, context=context)[0]
        acceptation_ids = [item.id for item in current.acceptation_ids]
        if len(acceptation_ids) == 1:
            view_mode = 'form,tree'
            res_id = acceptation_ids[0]
            views = [(False, 'form'), (False, 'tree')]
        else:
            view_mode = 'tree,mode'
            res_id = False
            views = [(False, 'tree'), (False, 'form')]

        return {
            'type': 'ir.actions.act_window',
            'name': _('Result for view_name'),
            'view_type': 'form',
            'view_mode': view_mode,
            'res_id': res_id,
            'res_model': 'quality.acceptation',
            'view_id': False,
            'views': views,
            'domain': [('id', 'in', acceptation_ids)],
            'context': context,
            'target': 'current', # 'new'
            'nodestroy': False,
            }

    # -------------------------------------------------------------------------
    # Fields function:
    # -------------------------------------------------------------------------
    def _get_acceptation_ids(self, cr, uid, ids, fields, args, context=None):
        """ Fields function for calculate
        """
        res = {}
        for lot in self.browse(cr, uid, ids, context=context):
            res[lot.id] = []
            for line in lot.line_ids:
                acceptation_id = line.acceptation_id.id
                if acceptation_id not in res[lot.id]:
                    res[lot.id].append(acceptation_id)
        return res

    _columns = {
        'default_supplier_id': fields.many2one('res.partner', 'Supplier'),
        'obsolete': fields.boolean('Obsolete',
            help='Indicates that the lot is old'),
        'deadline': fields.date('Deadline'),
        'real_deadline': fields.char('Real deadline', size=12),
        'line_ids': fields.one2many(
            'quality.acceptation.line', 'lot_id', 'Riga accettazione'),
        'acceptation_ids': fields.function(
            _get_acceptation_ids, method=True,
            type='many2many', relation='quality.acceptation',
            string='Accettazioni', store=False),


        'access_id': fields.integer('Access ID'),
        }

    _defaults = {
        'obsolete': lambda *a: False,
        }

class quality_claim(osv.osv):
    """ Quality Claim
    """
    _name = 'quality.claim'
    _inherit = ['mail.thread']

    _description = 'Claim'
    _order = 'ref desc'
    _rec_name = 'ref'

    # ----------------------
    # Errata corrige events:
    # ----------------------
    # TODO delete after importation:
    def correct_parent_partner(self, cr, uid, context=None):
        """ Set claim to parent partner not destination
        """
        claim_ids = self.search(cr, uid, [], context=context)
        for claim in self.browse(cr, uid, claim_ids, context=context):
            if claim.partner_id and claim.partner_id.parent_id:
                try:
                    self.write(cr, uid, claim.id, {
                        'partner_id': claim.partner_id.parent_id.id,
                        }, context=context)
                    _logger.info("Partner changed: %s" % claim.ref)
                except:
                    _logger.error("Error changing partner: %s" % claim.ref)
        return True

    # -------------
    # Button event:
    # -------------
    def open_fast_report(self, cr, uid, ids, context=None):
        """ Open fast report
        """
        return {
           'type': 'ir.actions.report.xml',
           'report_name': 'quality_fast_claim_report',
           'model': 'quality.claim',
           }


    def open_real_lot_elements(self, cr, uid, ids, context=None):
        """ Open sampling present
        """
        assert len(ids), 'Works only for one claim a time!'

        res = []
        for line in self.browse(cr, uid, ids, context=context)[0].product_ids:
            if line.real_lot_id:
                res.append(line.real_lot_id.id)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Real lot claimed'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.production.lot',
            #'view_id': view_id, # False
            'views': [(False, 'tree'), (False, 'form')],
            'domain': [('id', 'in', res)],
            'context': context,
            'target': 'current', # 'new'
            'nodestroy': False,
            }

    def print_form(self, cr, uid, ids, context=None):
        """ Print report directly in form (for calendar form)
        """
        return {
           'type': 'ir.actions.report.xml',
           'report_name': 'quality_claim_report',
           'model': 'quality.claim',
           #'datas': data,
           }

    def create_action(self, cr, uid, ids, context=None):
        """ Create a Action and link to this Claim
        """
        claim_proxy = self.browse(cr, uid, ids, context=context)[0]
        action_pool = self.pool.get('quality.action')
        action_id = action_pool.create(cr, uid, {
            'name': claim_proxy.name,
            'date': datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
            'claim_id': ids[0],
            'origin': 'claim',
            'type': 'corrective',
        }, context=context)
        self.write(cr, uid, ids, {'action_id': action_id, }, context=context)

        # Raise trigger for open AC:
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'quality.action', action_id,
            'trigger_action_draft_opened', cr)

        return self.pool.get('micronaet.tools').get_view_dict(cr, uid, {
            'model': 'quality.action',
            'module': 'quality',
            'record': action_id,
            #'name': _("name"),
            #'tree': tree name
            #'form': form name
            #'calendar': calendar name
            #'gantt': gantt name
            #'graph': graph name,

            #'default': 'form'
            #'type': 'form'
            #'domain': [],
            #'context': context,
            })

    def create_sampling(self, cr, uid, ids, context=None):
        """ Create a Sampling form and link to this Claim
        """
        claim_proxy = self.browse(cr, uid, ids, context=context)[0]
        sampling_pool = self.pool.get('quality.sampling')
        sampling_id = sampling_pool.create(cr, uid, {
            #'name': claim_proxy.name,
            'date': datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
            'claim_id': ids[0],
            'origin': 'claim',
            'lot_id': claim_proxy.product_ids and claim_proxy.product_ids[
                0].real_lot_id.id,

        }, context=context)
        self.write(cr, uid, ids, {'sampling_id': sampling_id, },
            context=context)

        # Raise trigger for open AC:
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'quality.sampling', sampling_id,
            'trigger_sampling_draft_opened', cr)
        return self.pool.get('micronaet.tools').get_view_dict(cr, uid, {
            'model': 'quality.sampling',
            'module': 'quality',
            'record': sampling_id,
            })

    def create_conformed(self, cr, uid, ids, context=None):
        """ Create a Sampling form and link to this Claim
        """
        claim_proxy = self.browse(cr, uid, ids, context=context)[0]
        conformed_pool = self.pool.get('quality.conformed')
        conformed_id = conformed_pool.create(cr, uid, {
            'name': claim_proxy.name,
            'date': datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
            'claim_id': ids[0],
            'origin': 'claim',
            'genesis': 'claim',
            'lot_id': claim_proxy.product_ids and claim_proxy.product_ids[
                0].real_lot_id.id,
            'label_lot': claim_proxy.product_ids and claim_proxy.product_ids[
                0].label_lot,
            'label_supplier':
                claim_proxy.product_ids and claim_proxy.product_ids[
                    0].label_supplier,
            }, context=context)
        self.write(cr, uid, ids, {'conformed_id': conformed_id, },
            context=context)

        # Raise trigger for open AC:
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'quality.conformed', conformed_id,
            'trigger_conformed_draft_opened', cr)
        return self.pool.get('micronaet.tools').get_view_dict(cr, uid, {
            'model': 'quality.conformed',
            'module': 'quality',
            'record': conformed_id,
            })

        #onchange
    def onchange_search_code(self, cr, uid, ids, search_code, context=None):
        """ Insert and trasform the code
        """
        res = {}
        if not search_code:
            return res
        code = search_code.split(".")
        if len(code) != 2:
            res['warning'] = {
                'title': _("Warning"),
                'message': _('Wrong code, format: 06.00001'),
                }
            return res

        search_code= "%s.%05d" % (code[0], int(code[1]))
        res['value'] = {}
        res['value']['search_code'] = search_code

        partner_pool = self.pool.get('res.partner')
        partner_ids = partner_pool.search(cr, uid, ['|', '|',
            ('sql_customer_code', '=', search_code),
            ('sql_supplier_code', '=', search_code),
            ('sql_destination_code', '=', search_code)], context=context)

        if not partner_ids:
            res['warning'] = {
                'title': _("Warning"),
                'message': _('No record found!'),
                }
            return res

        partner_proxy = partner_pool.browse(
            cr, uid, partner_ids, context=context)[0]

        if partner_proxy.is_address: #partner_proxy.parent_id.id:
            res['value']['partner_id'] = partner_proxy.parent_id.id
            res['value']['partner_address_id'] = partner_proxy.id
        else:
            res['value']['partner_id'] = partner_proxy.id
        return res

    def _get_lot_from_claim(self, cr, uid, ids, fields, args, context=None):
        """ Fields function for calculate
        """
        res = {}
        for claim in self.browse(cr, uid, ids, context=context):
            res[claim.id] = ''
            for line in claim.product_ids:
                if line.real_lot_id:
                    res[claim.id] += '%s %s\n' % (
                        line.real_lot_id.name or '??',
                        line.real_supplier_id.name or '??',
                        )
        return res

    # -------------------------------------------------------------------------
    # Fields:
    # -------------------------------------------------------------------------
    def _get_partner_name(self, cr, uid, ids, fields, args, context=None):
        """ Fields function for calculate
        """
        res = {}
        for item in self.browse(cr, uid, ids, context=context):
            res[item.id] = item.partner_id.name or ''
        return res

    # -------------------------------------------------------------------------
    # Store function:
    # -------------------------------------------------------------------------
    def _store_res_partner_name(self, cr, uid, ids, context=None):
        """ Change in res.partner the name
        """
        return self.pool.get('quality.claim').search(cr, uid, [
            ('partner_id', 'in', ids),
            ], context=context)

    def _store_form_partner_id(self, cr, uid, ids, context=None):
        """ Change in form partner_id
        """
        return ids

    # Search fields function:
    def _search_lot_from_claim(self, cr, uid, obj, name, args, context=None):
        """ Search lot or supplier in claims
        """
        try:
            # Search supplier or lot name:
            search_name = args[0][2]
            product_pool = self.pool.get('quality.claim.product')
            product_ids = product_pool.search(cr, uid, [
                '|',
                ('real_lot_id.name', 'ilike', search_name),
                ('real_supplier_id.name', 'ilike', search_name),
                ], context=context)
            item_ids = [
                item.claim_id.id for item in product_pool.browse(
                    cr, uid, product_ids, context=context)]
            return [('id', 'in', item_ids)]
        except:
            return []

    _columns = {
        'name': fields.char('Description', size=80, required=True),
        'partner_name': fields.function(
            _get_partner_name, method=True,
            type='char', string='Nome partner',
            store={
                'res.partner': (_store_res_partner_name, ['name'], 10),
                'quality.claim': (_store_form_partner_id, ['partner_id'], 10),
                }),

        'ref': fields.char('Ref', size=12, readonly=True),
        'customer_ref': fields.char('Customer ref', size=30),
        'date': fields.datetime('Date'),
        'receive_user_id':fields.many2one('res.users', 'Receive user',
            required=True),

        # Fast insert:
        'fast_insert': fields.boolean('Fast insert'),
        'request_quantity': fields.char('Request quantity', size=40),
        'fast_note': fields.text('Fast note',
            help='Note from fast insert user (not write in reports)'),

        'subject': fields.text('Description of not conformed'),
        'comunication': fields.text('Comunication message',
            help='Comunication message, if sent by mail could be the body text, instead could be phone contact dialog'),
        'analysis': fields.text('Cause analysis'),
        'responsability': fields.text('Responsability'),
        'solution': fields.text('Action correptive / preventive'),
        'consideration': fields.text('Consideration'),
        'treatment_conformed': fields.text('Treatment of not conformed'),

        'partner_id': fields.many2one('res.partner', 'Customer',
            required=True),
        'partner_address_id': fields.many2one('res.partner', 'Destination'),
        'partner_ref': fields.char('Contact', size=64),

        'request_return': fields.boolean('Product return request'),
        #'RAQ_saw': fields.boolean('RAQ saw'),
        'RTR_request': fields.boolean('RTR request for the return of product',
            help="Send an alert to logistic for activate return of products"),
        'ddt_date': fields.date('Date DDT'),
        'ddt_ref': fields.char('DDT ref.', size=20),

        #'NC':fields.boolean('Credit note required'),
        'NC_ref': fields.char('Credit note ref', size=40),
        'SFA_saw': fields.boolean('SFA saw'), # TODO WF button
        'RAQ_confirm': fields.boolean('RAQ confirm'), # TODO WF button

        'NC_comment': fields.boolean('NC comment'),
        'NC_comment_text': fields.char('NC comment text', size=60),

        'origin_id': fields.many2one('quality.origin', 'Origin'),
        'cause_id': fields.many2one('quality.claim.cause', 'Cause'),
        'gravity_id': fields.many2one('quality.gravity', 'Gravity'),

        'reference_user_id': fields.many2one('res.users', 'Reference user',
            help="Reference for claim to your customer"),
        'insert_user_id': fields.many2one('res.users', 'Insert user',
            readonly=True),
        'date_insert_user': fields.datetime('Date creation', readonly=True),
        'comunication_user_id': fields.many2one('res.users',
            'Comunication user', readonly=True),
        'date_comunication': fields.datetime('Date comunication',
            readonly=True),
        'open_user_id': fields.many2one('res.users', 'Opened user',
            readonly=True),
        'date_open': fields.datetime('Date opened', readonly=True),
        'nc_user_id': fields.many2one('res.users', 'Credit Note User',
            readonly=True),
        'date_nc': fields.datetime('Date Credit Note', readonly=True),
        'close_user_id': fields.many2one('res.users', 'Closed user',
            readonly=True),
        'closed_date': fields.datetime('Date Closed', readonly=True),
        'RAQ_id': fields.many2one('res.users', 'RAQ', readonly=True),
        'date_RAQ': fields.datetime('Date confirm RAQ', readonly=True),
        'cancel_user_id': fields.many2one('res.users', 'Cancel user',
            readonly=True),
        'date_cancel': fields.datetime('Date cancel', readonly=True),

        'search_code': fields.char('Search code', size=8),

        #'one': fields.integer('Total'),

        'real_lot_list': fields.function(
            _get_lot_from_claim, method=True, type='char', size=50,
            string='Real lot', fnct_search=_search_lot_from_claim,
            store=False, multi=False),

        'state': fields.selection([
            ('draft', 'Draft'),
            ('comunication', 'Comunication'),
            ('opened', 'Opened'),
            ('nc', 'Credit Note'),
            ('done', 'Credit Note Done'),
            ('closed', 'Closed'), # TODO Vista RAQ
            ('cancel', 'Cancel'),
            ('saw', 'Saw'),
        ],'State', select=True, readonly=True),

        # used only for WF trigger (removable)
        'need_accredit': fields.boolean('Need accredit'),
        'access_id': fields.integer('Access ID'),
        }

    _defaults = {
        'gravity_id': lambda s, cr, uid, ctx: s.pool.get(
            'ir.model.data').get_object_reference(
                cr, uid, 'quality', 'quality_gravity_serious')[1],
        'date': lambda *x: datetime.now().strftime(
            DEFAULT_SERVER_DATETIME_FORMAT),
        'date_insert_user': lambda *x: datetime.now().strftime(
            DEFAULT_SERVER_DATETIME_FORMAT),
        'insert_user_id': lambda s, cr, uid, ctx: uid,
        'reference_user_id': lambda s, cr, uid, ctx: uid,
        'receive_user_id': lambda s, cr, uid, ctx: uid,
        'request_return': lambda *x: False,
        'RTR_request': lambda *x: False,
        'state': lambda *a: 'draft',
        #'one': lambda *x: 1,
        }

    # ---------------------------
    # Workflow Activity Function:
    # ---------------------------
    def claim_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'draft',
            'open_user_id': False,
            'date_open': False,
            'comunication_user_id': False,
            'date_comunication': False,
            'nc_user_id': False,
            'date_nc': False,
            'close_user_id': False,
            'closed_date': False,
            'cancel_user_id': False,
            'date_cancel': False,
            'RAQ_id': False,
            'date_RAQ': False,
        }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def claim_comunication(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'comunication',
            'comunication_user_id': uid,
            'date_comunication': datetime.now().strftime(
                DEFAULT_SERVER_DATETIME_FORMAT),
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def claim_opened(self, cr, uid, ids, context=None):
        claim_proxy = self.browse(cr, uid, ids, context=context)[0]
        if claim_proxy.ref:
            ref = claim_proxy.ref
        else:
            ref = self.pool.get('ir.sequence').get(cr, uid, 'quality.claim')
        self.write(cr, uid, ids, {
            'fast_insert': False, # reset
            'state': 'opened',
            'ref': ref,
            'open_user_id':uid,
            'reference_user_id': uid,
            'date_open': datetime.now().strftime(
                DEFAULT_SERVER_DATETIME_FORMAT),
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def claim_nc(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'nc',
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def claim_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'done',
            'nc_user_id':uid,
            'date_nc':datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def claim_closed(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'closed',
            'close_user_id': uid,
            'closed_date':datetime.now().strftime(
                DEFAULT_SERVER_DATETIME_FORMAT),
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def claim_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'cancel',
            'cancel_user_id': uid,
            'date_cancel':datetime.now().strftime(
                DEFAULT_SERVER_DATETIME_FORMAT),
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def claim_saw(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'saw',
            'RAQ_id': uid,
            'date_RAQ':datetime.now().strftime(
                DEFAULT_SERVER_DATETIME_FORMAT),
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

class quality_claim_product(osv.osv):
    """ List of product / lot claimed
    """
    _name = 'quality.claim.product'
    _description = 'Claim product'
    _rec_name = 'lot_id'

    # ---------
    # On change
    # ---------
    def onchange_lot_id(self, cr, uid, ids, lot_id, context=None):
        """ Find the product
        """
        res = {}
        if lot_id:
            lot_pool = self.pool.get('stock.production.lot')
            lot_proxy = lot_pool.browse(cr, uid, lot_id, context=context)
            res['value'] = {}
            try:
                res['value']['real_lot_id'] = lot_id
                #res['value']['product_id'] = lot_proxy.product_id.id
                #res['value']['real_product_id'] = lot_proxy.product_id.id
                #res['value'][
                #    'real_supplier_id'] = lot_proxy.default_supplier_id.id
            except:
                pass
        return res

    def onchange_real_lot_id(self, cr, uid, ids, real_lot_id, context=None):
        """ Find the product
        """
        res = {}
        if real_lot_id:
            real_lot_pool = self.pool.get('stock.production.lot')
            real_lot_proxy = real_lot_pool.browse(cr, uid, real_lot_id,
                context=context)
            res['value'] = {}
            try:
                res['value'][
                    'real_supplier_id'] = real_lot_proxy.default_supplier_id.id
                #res['value']['real_product_id'] = real_lot_proxy.product_id.id
            except:
                pass
        return res

    # -------------------------------------------------------------------------
    # Button event:
    # -------------------------------------------------------------------------
    def open_external_conformed(self, cr, uid, ids, context=None):
        """ Open form, if not present create new
        """
        external_pool = self.pool.get('quality.conformed.external')
        origin_proxy = self.browse(cr, uid, ids, context=context)[0]

        external_id = origin_proxy.conformed_external_id.id
        now = ('%s' % datetime.now())[:19]
        if not external_id:
            external_id = external_pool.create(cr, uid, {
                'claim_id': origin_proxy.claim_id.id,
                'insert_date': now,
                'origin': 'claim',
                'reference_user_id': uid,
                #'name'
                #'ref'
                #'supplier_id': 1, # General Food?
                #'mode'
                #'origin_other'
                #'state'
                }, context=context)
            self.write(cr, uid, ids, {
                'conformed_external_id': external_id,
                }, context=context)

        # ---------------------------------------------------------------------
        # Open form:
        # ---------------------------------------------------------------------
        #model_pool = self.pool.get('ir.model.data')
        #view_id = model_pool.get_object_reference(
        #    cr, uid, 'module_name', 'view_name')[1]
        view_id = False

        return {
            'type': 'ir.actions.act_window',
            'name': _('Not conformed External'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_id': external_id,
            'res_model': 'quality.conformed.external',
            'view_id': view_id,
            'views': [(False, 'form'),(False, 'tree')],
            'domain': [],
            'context': context,
            'target': 'current', # 'new'
            'nodestroy': False,
            }

    _columns = {
        # Linked to external not conformed:
        'conformed_external_id': fields.many2one(
            'quality.conformed.external', 'External conformed',
            ondelete='set null'),

        'return_date': fields.date('Return date'),
        'return_qty': fields.float('Return q.', digits=(16, 3)),
        'lot_id':fields.many2one('stock.production.lot', 'Lot', required=True),
        'real_lot_id':fields.many2one('stock.production.lot', 'Real lot',
            required=True),

        'real_supplier_id': fields.related('real_lot_id','default_supplier_id',
            type='many2one', relation='res.partner', string='Real Supplier'),
        'product_id': fields.related('lot_id', 'product_id', type='many2one',
            relation='product.product', string='Product'),
        'real_product_id': fields.related('real_lot_id', 'product_id',
            type='many2one', relation='product.product',
            string='Real product'),

        #'real_product_id': fields.many2one('product.product', 'Real product'),
        'claim_id':fields.many2one('quality.claim', 'Claim',
            ondeleted='cascade'),
        'label_lot': fields.char('Label Lot', size=50),
        'label_supplier': fields.char('Label Supplier', size=50),
        'lot_deadline': fields.related('lot_id', 'real_deadline', type='char',
            string='Lot deadline', store=False),

        'access_id': fields.integer('Access ID'),
        }

# -----------------------------------------------------------------------------
#                                    ACCEPTATION
# -----------------------------------------------------------------------------
class quality_acceptation(osv.osv):
    """ Acceptation form
    """
    _name = 'quality.acceptation'
    _inherit = ['mail.thread']

    _description = 'Acceptation'
    _order = 'ref desc'
    _rec_name = 'ref'

    # Button event:
    def open_nc_elements(self, cr, uid, ids, context=None):
        """ Open NC present
        """
        assert len(ids), 'Works only for one accepation a time!'

        res = []
        for line in self.browse(cr, uid, ids, context=context)[0].line_ids:
            if line.conformed_id:
                res.append(line.conformed_id.id)

        return {
            'type': 'ir.actions.act_window',
            'name': _('NC from acceptation'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'quality.conformed',
            #'view_id': view_id, # False
            'views': [(False, 'tree'), (False, 'form')],
            'domain': [('id', 'in', res)],
            'context': context,
            'target': 'current', # 'new'
            'nodestroy': False,
            }

    def open_sampling_elements(self, cr, uid, ids, context=None):
        """ Open sampling present
        """
        assert len(ids), 'Works only for one accepation a time!'

        res = []
        for line in self.browse(cr, uid, ids, context=context)[0].line_ids:
            if line.sampling_id:
                res.append(line.sampling_id.id)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Sampling from acceptation'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'quality.sampling',
            #'view_id': view_id, # False
            'views': [(False, 'tree'), (False, 'form')],
            'domain': [('id', 'in', res)],
            'context': context,
            'target': 'current', # 'new'
            'nodestroy': False,
            }

    # Fields function:
    def _get_nc_from_lines(self, cr, uid, ids, fields, args, context=None):
        """ Fields function for calculate
        """
        res = {}
        for acceptation in self.browse(cr, uid, ids, context=context):
            res[acceptation.id] = ''
            for line in acceptation.line_ids:
                if line.conformed_id:
                    res[acceptation.id] += '%s ' % (
                        line.conformed_id.ref)
        return res

    def _get_sampling_from_lines(self, cr, uid, ids, fields, args, context=None):
        """ Fields function for calculate
        """
        res = {}
        for acceptation in self.browse(cr, uid, ids, context=context):
            res[acceptation.id] = ''
            for line in acceptation.line_ids:
                if line.sampling_id:
                    res[acceptation.id] += '%s ' % (
                        line.sampling_id.ref or '??')
        return res

    _columns = {
        'ref': fields.char('Ref', size=100, readonly=True),
        'date': fields.date('Date', required=True),
        'origin': fields.char('BF document', size=50),
        'partner_id': fields.many2one('res.partner', 'Supplier'),
        'note': fields.text('Note'),

        # Function fields:
        'nc_list': fields.function(
            _get_nc_from_lines, method=True, type='char', size=100,
            string='NC opened', store=False),
        'sampling_list': fields.function(
            _get_sampling_from_lines, method=True, type='char', size=100,
            string='Sampling opened', store=False),

        'state':fields.selection(acceptation_state, 'State', select=True,
            readonly=True),
        'cancel': fields.boolean('Cancel'),

        'access_id': fields.integer('Access ID'),
    }

    _defaults = {
        'date': lambda *x: datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
        'state': lambda *a: 'opened',
        }

    # ---------------------------
    # Workflow Activity Function:
    # ---------------------------
    def acceptation_opened(self, cr, uid, ids, context=None):
        acceptation_proxy = self.browse(cr, uid, ids, context=context)[0]
        if acceptation_proxy.ref:
            ref = acceptation_proxy.ref
        else:
            ref = self.pool.get('ir.sequence').get(cr, uid,
                'quality.acceptation')
        self.write(cr, uid, ids, {
            'state': 'opened',
            'ref': ref,
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def acceptation_closed(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'closed',
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def acceptation_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'cancel',
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

class quality_acceptation_line(osv.osv):
    """ Acceptation form line
    """
    _name = 'quality.acceptation.line'
    _description = 'Acceptation line'
    _rec_name = 'product_id'

    # --------------
    # Button action:
    # --------------
    def open_conformed(self, cr, uid, ids, context=None):
        """ Open NC element
        """
        line_proxy = self.browse(cr, uid, ids, context=context)[0]
        return self.pool.get('micronaet.tools').get_view_dict(cr, uid, {
            'model': 'quality.conformed',
            'module': 'quality',
            'record': line_proxy.conformed_id.id or False,
            })

    def open_sampling(self, cr, uid, ids, context=None):
        """ Return view for see all claims:
        """
        sampling_pool = self.pool.get('quality.sampling')

        line_proxy = self.browse(cr, uid, ids, context=context)[0]
        if line_proxy.sampling_id:
            sampling_id = line_proxy.sampling_id.id
        else:
            # create sampling
            sampling_id = sampling_pool.create(cr, uid, {
                'lot_id': line_proxy.lot_id.id,
                'date': datetime.now().strftime(
                    DEFAULT_SERVER_DATE_FORMAT),
                'origin': 'acceptation',
                'acceptation_id': line_proxy.acceptation_id.id,
                }, context=context)

            # Save reference:
            self.write(cr, uid, ids, {
                'sampling_id': sampling_id,
                }, context=context)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Acceptation sampling'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_id': sampling_id,
            'res_model': 'quality.sampling',
            #'view_id': view_id, # False
            'views': [(False, 'form'),(False, 'tree')],
            'domain': [('id', '=', sampling_id)],
            'context': context,
            'target': 'current', # 'new'
            'nodestroy': False,
        }

    # --------
    # Utility:
    # --------
    def create_conformed(self, cr, uid, ids, context=None):
        """ Ex button now utility for create a NC
        """
        line_proxy = self.browse(cr, uid, ids, context=context)[0]
        conformed_pool = self.pool.get('quality.conformed')
        conformed_id = conformed_pool.create(cr, uid, {
            'date': datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
            'acceptation_id': line_proxy.acceptation_id.id,
            'origin': 'acceptation',
            'genesis': 'acceptance',
            'lot_id': line_proxy and line_proxy.lot_id.id,

        }, context=context)
        self.write(cr, uid, ids, {
            'conformed_id': conformed_id},  context=context)

        # Raise trigger for open AC:
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'quality.conformed', conformed_id,
            'trigger_conformed_draft_opened', cr)
        return True

    # ------------------
    # Override function:
    # ------------------
    def create(self, cr, uid, vals, context=None):
        """ Generate not conformed if one problem is fount
        """
        # Technically during creation there's not check operation (automated)
        res_id = osv.osv.create(self, cr, uid, vals, context=context)

        # If theres a problems create a not conformed:
        if (vals.get('qty', False) or vals.get('temp', False) or
            vals.get('label', False) or vals.get('package', False) or
            vals.get('expired', False)):
                self.create_conformed(cr, uid, ids, context=context)
        return res_id

    def write(self, cr, uid, ids, vals, context=None):
        """ Generate not conformed if one problem is fount
        """
        osv.osv.write(self, cr, uid, ids, vals, context=context)
        line_proxy = self.browse(cr, uid, ids, context=context)[0]

        if not line_proxy.conformed_id:
            # If there's a problems create a not conformed:
            if (line_proxy.qty or line_proxy.temp or line_proxy.label or
                line_proxy.package or line_proxy.expired):
                    self.create_conformed(cr, uid, ids, context=context)
            return True

    _columns = {
        'acceptation_id': fields.many2one('quality.acceptation', 'Acceptation'),
        'lot_id':fields.many2one('stock.production.lot', 'Lot'),
        'product_id': fields.many2one('product.product', 'Product'), #TODO rel?
        'qty_arrived': fields.float('Quantity Arrived', digits=(16, 2)),
        'qty_expected': fields.float('Quantity Expected', digits=(16, 2)),
        'um': fields.char('UM', size=4),

        # Problems to check:
        'qty': fields.boolean('Quantity'),
        'temp': fields.boolean('Temperature'),
        'label': fields.boolean('Label'),
        'package': fields.boolean('Package'),
        'quality': fields.boolean('Quality'),
        'expired': fields.boolean('Expired'),

        'motivation': fields.text('Motivation'),
        'access_id': fields.integer('Access ID'),
    }

    _defaults = {
        'qty': False,
        'temp': False,
        'label': False,
        'package': False,
        'quality': False,
        'expired': False,
    }

# -----------------------------------------------------------------------------
#                                     SAMPLING
# -----------------------------------------------------------------------------
class quality_sampling_plan(osv.osv):
    """ Sampling Plan
    """
    _name = 'quality.sampling.plan'
    _description = 'Sampling Plan'

    _columns = {
        'name': fields.char('Category', size=100),
        'period': fields.integer('Period', help='in month'),
        'visual': fields.boolean('Need Visual'),
        'taste': fields.boolean('Need Taste'),
        'glazing': fields.boolean('Need Glazing'),
        'analysis': fields.boolean('Need Analysis'),
        'note': fields.text('Note'),

        'access_id': fields.integer('Access ID'),
    }

class quality_sampling(osv.osv):
    """ Sampling
    """
    _name = 'quality.sampling'
    _inherit = ['mail.thread']

    _description = 'Sampling'
    _order = 'ref desc'
    _rec_name = 'ref'

    # -------------
    # Button event:
    # -------------
    def print_form(self, cr, uid, ids, context=None):
        """ Print report directly in form (for calendar form)
        """
        return {
           'type': 'ir.actions.report.xml',
           'report_name': 'quality_sampling_report',
           'model': 'quality.sampling',
           }

    def create_conformed(self, cr, uid, ids, context=None):
        """ Create a Not Conformed form and link to this Sampling
        """
        sampling_proxy = self.browse(cr, uid, ids, context=context)[0]
        conformed_pool = self.pool.get('quality.conformed')
        conformed_id = conformed_pool.create(cr, uid, {
            'date': datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
            'parent_sampling_id': ids[0],
            'origin': 'sampling',
            'lot_id': sampling_proxy and sampling_proxy.lot_id.id,
        }, context=context)
        self.write(cr, uid, ids,
            {'conformed_id': conformed_id, }, context=context)

        # Raise trigger for open AC:
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'quality.conformed', conformed_id,
            'trigger_conformed_draft_opened', cr)
        return self.pool.get('micronaet.tools').get_view_dict(cr, uid, {
            'model': 'quality.conformed',
            'module': 'quality',
            'record': conformed_id,
            })

    _columns = {
        'ref': fields.char('Ref', size=100, readonly=True),
        'date': fields.date('Date', required=True),
        'lot_id':fields.many2one('stock.production.lot', 'Real Lot',
            required=True),
        'origin': fields.selection([
            #('direction', 'Direction exam'),
            #('audit', 'Internal audit'),
            ('claim', 'Claim'),
            ('acceptation', 'Acceptation'),
            ('packaging', 'Packaging'),
            ('nc', 'Not conformed'),
            ('other', 'Other'),
        ], 'Origin', select=True),
        'origin_other': fields.char('Other', size=60),
        'claim_id': fields.many2one('quality.claim', 'Claim'),
        'conformed_id': fields.many2one('quality.conformed', 'Not conformed',
            required=False),
        'acceptation_id': fields.many2one('quality.acceptation',
            'Acceptation'),
        'lot_deadline': fields.related('lot_id', 'real_deadline', type='char',
            string='Lot deadline', store=False),
        'lot_supplier_id': fields.related('lot_id', 'default_supplier_id',
            type='many2one', relation='res.partner', string='Lot supplier',
            store=False,
            ),
        'lot_product_id': fields.related('lot_id', 'product_id',
            type='many2one', relation='product.product', string='Lot prod.',
            store=False,
            ),

        'visual': fields.text('Visual examination'),
        'do_visual': fields.boolean('Request visual analysis'),
        'visual_state': fields.selection([
            ('to_examined', 'To be examined'),
            ('passed', 'Passed'),
            ('not_passed', 'Not passed'),
        ],'Visual State', select=True, readonly=True),
        'visual_ok': fields.boolean('Conformed'),

        'analysis': fields.text('Analysis'),
        'do_analysis': fields.boolean('Request analysis'),
        'analysis_state': fields.selection([
            ('to_examined', 'To be examined'),
            ('passed', 'Passed'),
            ('not_passed', 'Not passed'),
        ],'Analysis State', select=True, readonly=True),
        'analysis_ok': fields.boolean('Conformed'),

        'taste': fields.text(
            'Taste(After cooking the product in elemental form - simple cooking in salted water)'),
        'do_taste': fields.boolean('Request taste analysis'),
        'taste_state': fields.selection([
            ('to_examined', 'To be examined'),
            ('passed', 'Passed'),
            ('not_passed', 'Not passed'),
        ],'Taste State', select=True, readonly=True),
        'taste_ok': fields.boolean('Conformed'),

        'do_glazing': fields.boolean('Request glazing analysis'),
        'glazing_state': fields.selection([
            ('to_examined', 'To be examined'),
            ('passed', 'Passed'),
            ('not_passed', 'Not passed'),
        ],'Glazing State', select=True, readonly=True),
        'weight_glazing': fields.float('Sample weight glazing'),
        'perc_glazing_indicated': fields.float('Glazing indicated (%)'),
        'weight_drained': fields.float('Sample weight drained'),
        'perc_glazing_calculated': fields.float('Glazing calculated (%)'),
        'glazing_ok': fields.boolean('Conformed'),
        'sampling_plan_id': fields.many2one('quality.sampling.plan',
            'Sampling Plan'),
        'cancel': fields.boolean('Cancel'),

        'taster_ids': fields.one2many('quality.sampling.taster', 'sample_id'),
        'note': fields.text('Note'),

        'state': fields.selection(sampling_state, 'State', select=True,
            readonly=True),

        'access_id': fields.integer('Access ID'),
        }

    _defaults = {
        'date': lambda *x: datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
        'state': lambda *a: 'draft',
        'visual_state': lambda *a: 'to_examined',
        'analysis_state': lambda *a: 'to_examined',
        'taste_state': lambda *a: 'to_examined',
        'glazing_state': lambda *a: 'to_examined',
        }

    # -------
    # Button:
    # -------
    def set_passed(self, cr, uid, ids, context=None):
        """ Button event for set the state of the test in the sampling
        """
        parameter = context.get('button', False)
        if not parameter:
            return False

        button = parameter[0]
        result = parameter[1] == "t" # t = True, f = False

        if button == '1': # visual
            return self.write(cr, uid, ids, {
                'visual_state': 'passed' if result else 'not_passed',
                'visual_ok': result,
            }, context=context)

        if button == '2': # analysis
            return self.write(cr, uid, ids, {
                'analysis_state': 'passed' if result else 'not_passed',
                'analysis_ok': result,
            }, context=context)

        if button == '3': # taste
            return self.write(cr, uid, ids, {
                'taste_state': 'passed' if result else 'not_passed',
                'taste_ok': result,
            }, context=context)

        if button == '4': # glazing
            return self.write(cr, uid, ids, {
                'glazing_state': 'passed' if result else 'not_passed',
                'glazing_ok': result,
            }, context=context)

    # ---------------
    # Onchange event:
    # ---------------

    def onchange_do_visual(self, cr, uid, ids, do_visual, context=None):
        res = {}
        if not do_visual:
            res['value'] = {}
            res['value']['visual_state'] = 'to_examined'
        return res

    def onchange_visual_state(self, cr, uid, ids, visual_state, context=None):
        res = {}
        if visual_state:
            visual_pool = self.pool.get('quality.sampling')
            visual_proxy = visual_pool.browse(cr, uid, visual_state,
                context=context)
            res['value'] = {}
            try:
                if visual_state == 'passed':
                    res['value']['visual_ok'] = True
                else:
                    res['value']['visual_ok'] = False
            except:
                pass
        return res

    def onchange_do_analysis(self, cr, uid, ids, do_analysis, context=None):
        res = {}
        if not do_analysis:
            res['value'] = {}
            res['value']['analysis_state'] = 'to_examined'
        return res

    def onchange_analysis_state(self, cr, uid, ids, analysis_state,
            context=None):
        res = {}
        if analysis_state:
            analysis_pool = self.pool.get('quality.sampling')
            analysis_proxy = analysis_pool.browse(cr, uid, analysis_state,
                context=context)
            res['value'] = {}
            try:
                if analysis_state == 'passed':
                    res['value']['analysis_ok'] = True
                else:
                    res['value']['analysis_ok'] = False
            except:
                pass
        return res

    def onchange_do_taste(self, cr, uid, ids, do_taste, context=None):
        res = {}
        if not do_taste:
            res['value'] = {}
            res['value']['taste_state'] = 'to_examined'
        return res

    def onchange_taste_state(self, cr, uid, ids, taste_state, context=None):
        res = {}
        if taste_state:
            taste_pool = self.pool.get('quality.sampling')
            taste_proxy = taste_pool.browse(cr, uid, taste_state,
                context=context)
            res['value'] = {}
            try:
                if taste_state == 'passed':
                    res['value']['taste_ok'] = True
                else:
                    res['value']['taste_ok'] = False
            except:
                pass
        return res

    def onchange_do_glazing(self, cr, uid, ids, do_glazing, context=None):
        res = {}
        if not do_glazing:
            res['value'] = {}
            res['value']['glazing_state'] = 'to_examined'
        return res

    def onchange_glazing_state(self, cr, uid, ids, glazing_state,
            context=None):
        res = {}
        if glazing_state:
            glazing_pool = self.pool.get('quality.sampling')
            glazing_proxy = glazing_pool.browse(cr, uid, glazing_state,
                context=context)
            res['value'] = {}
            try:
                if glazing_state == 'passed':
                    res['value']['glazing_ok'] = True
                else:
                    res['value']['glazing_ok'] = False
            except:
                pass
        return res

    # ---------------------------
    # Workflow Activity Function:
    # ---------------------------
    def sampling_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'draft',
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def sampling_opened(self, cr, uid, ids, context=None):
        sampling_proxy = self.browse(cr, uid, ids, context=context)[0]
        if sampling_proxy.ref:
            ref = sampling_proxy.ref
        else:
            ref = self.pool.get('ir.sequence').get(cr, uid, 'quality.sampling')
        self.write(cr, uid, ids, {
            'state': 'opened',
            'ref': ref,
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def sampling_passed(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'passed',
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def sampling_notpassed(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'notpassed',
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def sampling_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'cancel',
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

class quality_sampling_taster(osv.osv):
    """ Sampling
    """
    _name = 'quality.sampling.taster'
    _description = 'Sampling Taster'

    _columns = {
        'name': fields.char('Name', size=100),
        'note': fields.text('Note'),
        'sample_id': fields.many2one('quality.sampling', 'Sample'),
        'access_id': fields.integer('Access ID'),
    }


# -----------------------------------------------------------------------------
#                                   NOT CONFORMED
# -----------------------------------------------------------------------------
class quality_conformed(osv.osv):
    """ Forms of not conformed
    """
    _name = 'quality.conformed'
    _inherit = ['mail.thread']

    _description = 'Not conformed'
    _order = 'ref desc'
    _rec_name = 'ref'

    # -------------
    # Button event:
    # -------------
    def print_form(self, cr, uid, ids, context=None):
        """ Print report directly in form (for calendar form)
        """
        return {
           'type': 'ir.actions.report.xml',
           'report_name': 'quality_conformed_report',
           'model': 'quality.conformed',
           'datas': context,
           }

    def print_form_supplier(self, cr, uid, ids, context=None):
        """ Print report supplier directly in form (for calendar form)
        """
        if context is None:
            context = {}
        context['supplier'] = True

        return {
           'type': 'ir.actions.report.xml',
           'report_name': 'quality_conformed_report',
           'model': 'quality.conformed',
           'datas': context,
           }

    def create_action(self, cr, uid, ids, context=None):
        """ Create a Action and link to this Claim
        """
        conformed_proxy = self.browse(cr, uid, ids, context=context)[0]
        action_pool = self.pool.get('quality.action')
        action_id = action_pool.create(cr, uid, {
            'name': conformed_proxy.name,
            'date': datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
            'conformed_id': ids[0],
            'origin': 'nc',
            'type': 'corrective',
        }, context=context)
        self.write(cr, uid, ids, {'action_id': action_id, }, context=context)

        # Raise trigger for open AC:
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'quality.action', action_id,
            'trigger_action_draft_opened', cr)
        return self.pool.get('micronaet.tools').get_view_dict(cr, uid, {
            'model': 'quality.action',
            'module': 'quality',
            'record': action_id,
            })

    def create_sampling(self, cr, uid, ids, context=None):
        """ Create a Sampling form and link to this Claim
        """
        conformed_proxy = self.browse(cr, uid, ids, context=context)[0]
        sampling_pool = self.pool.get('quality.sampling')
        sampling_id = sampling_pool.create(cr, uid, {
            'date': datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
            'parent_conformed_id': ids[0],
            'origin': 'nc',
            'lot_id': conformed_proxy and conformed_proxy.lot_id.id,

        }, context=context)
        self.write(cr, uid, ids, {'sampling_id': sampling_id}, context=context)

        # Raise trigger for open AC:
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'quality.sampling', sampling_id,
            'trigger_sampling_draft_opened', cr)
        return self.pool.get('micronaet.tools').get_view_dict(cr, uid, {
            'model': 'quality.sampling',
            'module': 'quality',
            'record': sampling_id,
            })

    # -------------------------------------------------------------------------
    # Document Management:
    # -------------------------------------------------------------------------
    def quality_document_add(self, cr, uid, ids, context=None):
        """ Open Document add form
        """
        return self.pool.get('quality.document').open_quality_document_add(
            cr, uid,
            model='quality.conformed',
            item_id=ids[0],
            area=u'Non conformità',
            context=context)

    def _get_quality_document(
            self, cr, uid, ids, field_name, arg, context=None):
        """ Return quality document
        """
        return self.pool.get('quality.document').get_many2many(
            cr, uid,
            model='quality.conformed',
            item_id=ids[0],
            context=context)

    _columns = {
        'ref': fields.char('Ref', size=100, readonly=True),
        'insert_date': fields.date('Insert date', required=True),
        'document_ids': fields.function(
            _get_quality_document, type='many2many', readonly=True,
            relation='quality.document', string='Documenti'),

        'aesthetic_packaging': fields.boolean('Confezione'),
        'quantity': fields.boolean('Quantity'),
        'sanitation': fields.boolean('Sanitation'),
        'temperature': fields.boolean('Temperature'),
        'label': fields.boolean('Label'),
        'quality': fields.boolean('Quality'),
        'deadline': fields.boolean('Deadline'),
        'delay': fields.boolean('Ritardo'),
        'no_delivery': fields.boolean('Mancata consegna'),
        'external_material': fields.boolean('Corpi estranei'),

        'gravity_id': fields.many2one(
            'quality.gravity', 'Gravity',
            required=True),
        # 'genesis':fields.selection([
            #('acceptance', 'Acceptance'),
            #('sample', 'Sample'),
            #('claim', 'Claim'),
            #('packaging', 'Packaging'),
            #('other', 'Other'),
            #   ],'Genesis', select=True),
        # 'other':fields.char('Other', size=100),
        'origin': fields.selection([
            ('acceptation', 'Acceptation'),
            ('sampling', 'Sampling'),
            ('claim', 'Claim'),
            ('packaging', 'Packaging'),
            ('other', 'Other'),
        ], 'Origin', select=True),
        'origin_other': fields.char('Other', size=60),
        'reference_user_id': fields.many2one(
            'res.users', 'Ref. user',
            help='Ref. user when no origin from claim'),
        'claim_id': fields.many2one('quality.claim', 'Claim'),
        'sampling_id': fields.many2one('quality.sampling', 'Sampling'),
        'acceptation_id': fields.many2one('quality.acceptation',
            'Acceptation'),
        'ddt_ref': fields.char('DDT reference', size=50),
        # TODO mandatory??
        'lot_id':fields.many2one('stock.production.lot', 'Real Lot'),
        'label_lot': fields.char('Label Lot', size=25),
        'label_supplier': fields.char('Label Supplier', size=50),
        'lot_deadline': fields.related('lot_id', 'real_deadline', type='char',
            string='Lot Deadline', store=False),
        'cancel': fields.boolean('Cancel'),
        'supplier_lot': fields.related('lot_id', 'default_supplier_id',
            type='many2one', relation='res.partner', string='Supplier'),
        'descr_product': fields.related('lot_id', 'product_id',
            type='many2one', relation='product.product',
            string='Product description'),

        'name': fields.text('Type'),
        'note_RAQ': fields.text('Note RAQ'),
        'stock_note': fields.text('Stock note'),
        'comunication_note': fields.text('Comunication note'),
        #'note_warehouse': fields.text('Note Warehouse'),

        'state':fields.selection(conformed_state, 'State', select=True,
            readonly=True),

        'access_id': fields.integer('Access ID'),
        }

    _defaults = {
        'gravity_id': lambda s, cr, uid, ctx: s.pool.get(
            'ir.model.data').get_object_reference(
                cr,  uid, 'quality', 'quality_gravity_serious')[1],
        'insert_date': lambda *x: datetime.now().strftime(
            DEFAULT_SERVER_DATE_FORMAT),
        'state': lambda *a: 'draft',
        }


class quality_comunication_type(osv.osv):
    """ Quality comunication type
    """
    _name = 'quality.comunication.type'
    _description = 'Quality comunication type'

    _columns = {
        'name': fields.char('Name', size=100, translate=True),
        'note': fields.text('Note'),

        'access_id': fields.integer('Access ID'),
    }


class quality_comunication(osv.osv):
    """ Quality comunication
    """
    _name = 'quality.comunication'
    _description = 'Quality comunication'

    _columns = {
        'name': fields.char('Description', size=200),
        'type_id': fields.many2one('quality.comunication.type', 'Type',
            required=True),
        'conformed_id': fields.many2one('quality.conformed', 'Not Conformed'),
        'prot_number': fields.char('Protocol n.', size=40, required=True),
        'prot_date': fields.date('Protocol date'),
        #TODO m2o protocol_id

        'access_id': fields.integer('Access ID'),
        }

    _defaults = {
        'prot_date': lambda *x: datetime.now().strftime(
            DEFAULT_SERVER_DATE_FORMAT),
        }


class quality_treatment(osv.osv):
    """ Quality treatment
    """
    _name = 'quality.treatment'
    _description = 'Quality treatment'

    _columns = {
        'name': fields.char('Note', size=200),
        'conformed_id': fields.many2one('quality.conformed', 'Not Conformed'),
        'type':fields.selection([
            ('accept_exception', 'Accept as an exception'),
            ('discard', 'Discard'),
            ('make_supplier', 'Supplier to make'),
        ],'Type', select=True),
        'qty': fields.float('Quantity'),

        'access_id': fields.integer('Access ID'),
        }


class quality_conformed(osv.osv):
    """ Forms of not conformed
    """
    _inherit = 'quality.conformed'

    _columns = {
        'comunication_ids': fields.one2many('quality.comunication',
            'conformed_id', 'Comunications'),
        'treatment_ids': fields.one2many('quality.treatment', 'conformed_id',
            'Treatments'),
        }

    # ---------------------------
    # Workflow Activity Function:
    # ---------------------------
    def conformed_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'draft',
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def conformed_opened(self, cr, uid, ids, context=None):
        conformed_proxy = self.browse(cr, uid, ids, context=context)[0]
        if conformed_proxy.ref:
            ref = conformed_proxy.ref
        else:
            ref = self.pool.get('ir.sequence').get(cr, uid,
                'quality.conformed')
        self.write(cr, uid, ids, {
            'state': 'opened',
            'ref': ref,
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def conformed_closed(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'closed',
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def conformed_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
                    'state': 'cancel',
                    }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def conformed_saw(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'saw',
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True


# -----------------------------------------------------------------------------
#                            ACTIONS (CORREPTIVE, PREVENTIVE)
# -----------------------------------------------------------------------------
class quality_action(osv.osv):
    """ Correptive / preventive action
    """
    _name = 'quality.action'
    _inherit = ['mail.thread']

    _description = 'Action'
    _order = 'ref desc'
    _rec_name = 'ref'

    # -------------
    # Button event:
    # -------------
    def print_form(self, cr, uid, ids, context=None):
        """ Print report directly in form (for calendar form)
        """
        return {
           'type': 'ir.actions.report.xml',
           'report_name': 'quality_action_report',
           'model': 'quality.action',
           }

    def new_action(self, cr, uid, ids, context=None):
        """ Create a new action
        """
        action_proxy = self.browse(cr, uid, ids, context=context)[0]
        action_id = self.create(cr, uid, {
            'origin': action_proxy.origin,
            'type': action_proxy.type,
            'parent_id': ids[0],
        }, context=context)
        self.write(cr, uid, ids, {'child_id': action_id, }, context=context)

        # Raise trigger for open AC:
        #wf_service = netsvc.LocalService("workflow")
        #wf_service.trg_validate(uid, 'quality.action', action_id,
        #    'trigger_action_draft_opened', cr)
        return self.pool.get('micronaet.tools').get_view_dict(cr, uid, {
            'model': 'quality.action',
            'module': 'quality',
            'record': action_id,
            })

    _columns = {
        'ref': fields.char('Ref', size=12, readonly=True),
        'date': fields.date('Date'),
        #'origin_id': fields.many2one('quality.origin', 'Origin'),
        'origin': fields.selection([
            ('claim', 'Claim'),
            ('nc', 'Not conformed'),
            ('other', 'Other'),
            ('audit', 'Audit'), # TODO coretta? c'è nella impostazione
        ], 'Origin', select=True),
        'origin_other': fields.char('Other', size=60),
        'note': fields.text('Cause analysis'),
        'proposed_subject': fields.text('Subject proposing'),
        'proposing_entity': fields.char('Proposing entity', size=100),
        'esit_date': fields.date('Esit date'),
        'closed_date': fields.date('Closed date'),
        'esit_note': fields.text('Judgment'),
        'claim_id': fields.many2one('quality.claim', 'Claim'),
        'conformed_id': fields.many2one('quality.conformed', 'Not conformed'),
        'conformed_external_id': fields.many2one(
            'quality.conformed.external', 'Not conformed external'),
        'type': fields.selection([
            ('corrective', 'Corrective'),
            ('preventive', 'Preventive'),
            ('enhance', 'Enhance intervent'),
        ], 'Type', select=True),
        'cancel': fields.boolean('Cancel'),
        'state':fields.selection(action_state, 'State', select=True,
            readonly=True),

        'access_id': fields.integer('Access ID'),
    }

    _defaults = {
        'date': lambda *x: datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
        'state': lambda *a: 'draft',
        'type': 'corrective'
        }

    # ---------------------------
    # Workflow Activity Function:
    # ---------------------------
    def action_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'draft',
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def action_opened(self, cr, uid, ids, context=None):
        conformed_proxy = self.browse(cr, uid, ids, context=context)[0]
        if conformed_proxy.ref:
            ref = conformed_proxy.ref
        else:
            ref = self.pool.get('ir.sequence').get(cr, uid, 'quality.action')
        self.write(cr, uid, ids, {
            'state': 'opened',
            'ref': ref,
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def action_closed(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'closed',
            'closed_date':datetime.now().strftime(
                DEFAULT_SERVER_DATETIME_FORMAT),
                }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def action_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'cancel',
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True

    def action_saw(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'saw',
            }, context=context)
        self.write_object_change_state(cr, uid, ids, context=context)
        return True


class quality_action_intervent(osv.osv):
    """ Correptive / preventive action intervent
    """
    _name = 'quality.action.intervent'
    _description = 'Action intervent'

    _columns = {
        'name': fields.text('Proposed activity'),
        'manager_id': fields.many2one('res.users', 'Manager'),
        'deadline': fields.date('Deadline'),
        'action_id': fields.many2one('quality.action', 'Action',
            ondelete='cascade'),
        #'action_state': fields.related('action_id','state', type='selction',
        #    string='State'),

        'access_id': fields.integer('Access ID'),
    }


class quality_action_intervent_working(osv.osv):
    """ Work in progress intervent activity
    """
    _name = 'quality.action.intervent.working'
    _description = 'Work in progress intervent'

    _columns = {
        'name': fields.char('Description', size=100),
        'date': fields.date('Date'),
        'intervent_id': fields.many2one('quality.action.intervent',
            'Intervent', ondelete='cascade',
            ),
        'user_id': fields.many2one('res.users', 'User'),
        'note': fields.text('Note'),
        'internal': fields.boolean('Internal'),
    }

    _defaults = {
        'date': lambda *x: datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
        'user_id': lambda s, cr, uid, ctx: uid,
        'internal': False,
    }


class quality_action_intervent(osv.osv):
    """ Add *2many fields
    """
    _inherit = 'quality.action.intervent'

    _columns = {
        'working_ids': fields.one2many('quality.action.intervent.working',
            'intervent_id', 'Work in progress'),
        }


class quality_action(osv.osv):
    """ Update extra field for action
    """
    _inherit = 'quality.action'

    _columns = {
        'child_id': fields.many2one('quality.action', 'Child',
            ondelete='set null'),
        'parent_id': fields.many2one('quality.action', 'Parent',
            ondelete='set null'),
        'intervent_ids': fields.one2many('quality.action.intervent',
            'action_id', 'Intervent'),
        'claim_id': fields.many2one('quality.claim', 'Claim',
            ondelete='set null'),
        }


class quality_supplier_rating(osv.osv):
    """ Form that manage the list of supplier
    """
    _name = 'quality.supplier.rating'
    _description = 'Quality supplier rating'
    _order = 'obsolete, deadline desc'

    _columns = {
        'name': fields.char('Qualification obtained', size=100),
        'date': fields.date('Date'),
        'type': fields.selection([
            ('first', 'First qualification'),
            ('renewal', 'Renewal'),
            ], 'Type', select=True),
        'deadline': fields.date('Deadline'),
        'obsolete': fields.boolean('Obsolete'),
        'qualification': fields.selection([
            ('reserve', 'With reserve'),
            ('test', 'In test'),
            ('uneventful', 'Uneventful'),
            ('occasional', 'Occasional'),
            ('full', 'Full qualification'),
            ('discarded', 'Discarded'),
            ], 'Type', select=True),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'manual': fields.boolean(
            'Manuale',
            help='Forzato manualmente cambiando il valore automatico'),

        'access_id': fields.integer('Access ID'),
    }

    _defaults = {
        'date': lambda *x: datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
    }


class quality_supplier_check(osv.osv):
    """ Form that manage the list of supplier
    """
    _name = 'quality.supplier.check'
    _description = 'Quality supplier check'
    _order = 'date desc'

    _columns = {
        'date': fields.date('Date'),
        'name': fields.char('Esit', size=100),
        'note': fields.text('Note'),
        'partner_id': fields.many2one('res.partner', 'Partner'),

        'access_id': fields.integer('Access ID'),
        }

    _defaults = {
        'date': lambda *x: datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
        }

class quality_supplier_certification(osv.osv):
    """ Form that manage the list of supplier
    """
    _name = 'quality.supplier.certification'
    _description = 'Quality supplier certification'
    _order = 'date desc'

    _columns = {
        'date': fields.date('Date'),
        'entity': fields.char('Entity', size=100),
        'name': fields.char('Name', size=100), # TODO esiste nel vecchio DB?
        'deadline': fields.date('Deadline', size=100),
        'note': fields.text('Purpose'),
        'rule': fields.char('Rule', size=100),
        'number': fields.char('Number', size=30),
        'partner_id': fields.many2one('res.partner', 'Partner'),

        'access_id': fields.integer('Access ID'),
        }

    _defaults = {
        'date': lambda *x: datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
        }

class quality_supplier_reference(osv.osv):
    """ Form that manage the list of supplier
    """
    _name = 'quality.supplier.reference'
    _description = 'Quality supplier reference'
    _order = 'date desc'

    _columns = {
        'date': fields.date('Date'),
        'name': fields.char('Name', size=100), # TODO se Andamento non c'è name
        'note': fields.text('Note'),
        'partner_id': fields.many2one('res.partner', 'Partner'),

        'access_id': fields.integer('Access ID'),
    }

    _defaults = {
        'date': lambda *x: datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
    }


class quality_partner_class(osv.osv):
    """ Class for categorize supplier
    """
    _name = 'quality.partner.class'
    _description = 'Quality partner class'

    _columns = {
        'name': fields.char('Name', size=100),
        'note': fields.text('Note'),

        'access_id': fields.integer('Access ID'),
        }


class res_company(osv.osv):
    """ Add fields for index manager
    """
    _inherit = 'res.company'

    _columns = {
        'index_from': fields.date('From date', required=True,
            help='From date (used in index valorization'),
        'index_to': fields.date('To date', required=True,
            help='To date (used in index valorization'),
        }


# -----------------------------------------------------------------------------
#                                        RELATIONS:
# -----------------------------------------------------------------------------
class res_partner(osv.osv):
    """ Add *2many fields
    """
    _inherit = 'res.partner'

    # -------------
    # Button event:
    # -------------
    def open_print_rating_wizard(self, cr, uid, ids, context=None):
        """ Open Wizard for print report
        """
        return {
            'target': 'new',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'quality.supplier.qualification.wizard',
            'domain': [],
            'type': 'ir.actions.act_window',
            'context': {'default_partner_id': ids[0]}
            }

    def open_claimed_line_real_lot(self, cr, uid, ids, context=None):
        """ Return view for see all claims:
        """
        product_pool = self.pool.get('quality.claim.product')
        product_ids = product_pool.search(cr, uid, [
            ('real_lot_id.default_supplier_id', '=', ids[0]),
            ], context=context)

        return {
            #'target': 'new',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'quality.claim.product',
            'domain': [('id', 'in', product_ids)],
            #'views': [(view_id, 'form')],
            #'view_id': False,
            'type': 'ir.actions.act_window',
            #'res_id': res_id,  # IDs selected
            }

    def open_claimed_real_lot_list(self, cr, uid, ids, context=None):
        """ Return view for see all claims:
        """
        product_pool = self.pool.get('quality.claim.product')
        product_ids = product_pool.search(cr, uid, [
            ('real_lot_id.default_supplier_id', '=', ids[0]),
            ], context=context)

        lot_ids = []
        for product in product_pool.browse(
                cr, uid, product_ids, context=context):
            real_lot_id = product.real_lot_id.id
            if real_lot_id and real_lot_id not in lot_ids:
                lot_ids.append(real_lot_id)

        return {
            #'target': 'new',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.production.lot',
            'domain': [('id', 'in', lot_ids)],
            #'views': [(view_id, 'form')],
            #'view_id': False,
            'type': 'ir.actions.act_window',
            #'res_id': res_id,  # IDs selected
            }

    def open_claim_list(self, cr, uid, ids, context=None):
        """ Return view for see all claims:
        """
        supplier_proxy = self.browse(cr, uid, ids, context=context)[0]
        claim_ids = eval(supplier_proxy.index_claim_list)
        return {
            #'target': 'new',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'quality.claim',
            'domain': [('id', 'in', claim_ids)],
            #'views': [(view_id, 'form')],
            #'view_id': False,
            'type': 'ir.actions.act_window',
            #'res_id': res_id,  # IDs selected
            }

    def open_conformed_list(self, cr, uid, ids, context=None):
        """ Return view for see all claims:
        """
        supplier_proxy = self.browse(cr, uid, ids, context=context)[0]
        conformed_ids = eval(supplier_proxy.index_conformed_list)
        return {
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'quality.conformed',
            'domain': [('id', 'in', conformed_ids)],
            'type': 'ir.actions.act_window',
            }

    def open_sampling_list(self, cr, uid, ids, context=None):
        """ Return view for see all claims:
        """
        supplier_proxy = self.browse(cr, uid, ids, context=context)[0]
        sampling_ids = eval(supplier_proxy.index_sampling_list)
        return {
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'quality.sampling',
            'domain': [('id', 'in', sampling_ids)],
            'type': 'ir.actions.act_window',
            }

    def open_acceptation_list(self, cr, uid, ids, context=None):
        """ Return view for see all claims:
        """
        acceptation_pool = self.pool.get('quality.acceptation')
        acceptation_ids = acceptation_pool.search(cr, uid, [
            ('partner_id', '=', ids[0]),
            ], context=context)
        if acceptation_ids:
            return {
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'quality.acceptation',
                'domain': [('id', 'in', acceptation_ids)],
                'type': 'ir.actions.act_window',
                }
        return True # nothing

    # ----------------
    # Utility function
    # ----------------
    def _get_index_delivery(self, cr, uid, index_from, index_to, supplier_id,
            context=None):
        """ Query database for total acceptation in period passed (not
        """
        if index_to and index_from:
            cr.execute("""
                SELECT count(*) 
                FROM quality_acceptation
                WHERE 
                    state not in ('cancel') AND
                    date >= %s AND
                    date <= %s AND
                    partner_id = %s;""",
                (index_from, index_to, supplier_id))
            total_acceptation = cr.fetchone()[0]
        else:
            total_acceptation = 0
        return total_acceptation

    def _get_index_lot(self, cr, uid, index_from, index_to, supplier_id,
            context=None):
        """ Total lot in period passed
        """
        if index_to and index_from:
            cr.execute("""
                SELECT count(*) 
                FROM quality_acceptation_line qal JOIN quality_acceptation qa 
                    ON (qal.acceptation_id = qa.id)
                WHERE 
                    qa.state not in ('cancel') AND
                    qa.date >= %s AND
                    qa.date <= %s AND
                    qa.partner_id = %s;""",
                (index_from, index_to, supplier_id))
            total_acceptation_lot = cr.fetchone()[0]
        else:
            total_acceptation_lot = 0
        return total_acceptation_lot

    def _get_index_weight(self, cr, uid, index_from, index_to, supplier_id,
            context=None):
        """ Total lot in period passed
        """
        if index_to and index_from:
            # total arrived not expected:
            cr.execute("""
                SELECT sum(qty_arrived) 
                FROM quality_acceptation_line qal JOIN quality_acceptation qa 
                    ON (qal.acceptation_id = qa.id)
                WHERE 
                    qa.state not in ('cancel') AND
                    qa.date >= %s AND
                    qa.date <= %s AND
                    qa.partner_id = %s;""",
                (index_from, index_to, supplier_id))
            total_acceptation_lot = cr.fetchone()[0]
        else:
            total_acceptation_lot = 0
        return total_acceptation_lot

    def _get_index_delivery(self, cr, uid, index_from, index_to, supplier_id,
                            context=None):
        """ Total delivery in period passed
        """
        if index_to and index_from:
            cr.execute("""
                SELECT count(*) 
                FROM res_partner_delivery
                WHERE 
                    date >= %s AND
                    date <= %s AND
                    carrier_id = %s;
                """, (index_from, index_to, supplier_id))
            total_acceptation_lot = cr.fetchone()[0]
        else:
            total_acceptation_lot = 0
        return total_acceptation_lot

    # ----------------
    # Fields function:
    # ----------------
    def _get_index_information(self, cr, uid, ids, field_name, arg,
            context=None):
        """
        Return a HTML tables for important claim indexes  (only for form view)
        @param cr: cursor to database
        @param user: id of current user
        @param ids: list of record ids to be process
        @param fieldname:
        @param arg:
        @param context: context arguments, like lang, time zone

        @return: HTML tables for index informations
        """
        res = dict.fromkeys(ids, {
            'index_info': '',

            'index_claim': '',
            'index_claim_list': '',

            'index_conformed': '',
            'index_conformed_list': '',

            'index_sampling': '',
            'index_sampling_list': '',
            })

        if len(ids) > 1: # work only in form view
            return res

        # ---------------------------------------------------------------------
        #                         COMMON SETUP
        # ---------------------------------------------------------------------
        supplier_proxy = self.browse(cr, uid, ids, context=context)[0]
        if supplier_proxy.is_address: # no count for destination
            return res # TODO also only supplier

        if supplier_proxy.custom_range:
            index_from = supplier_proxy.index_from
            index_to = supplier_proxy.index_to
        else:
            company_pool = self.pool.get('res.company')
            company_ids = company_pool.search(cr, uid, [], context=context)
            company_proxy = company_pool.browse(cr, uid, company_ids)[0]

            # Query parameters:
            index_from = company_proxy.index_from#[:10]
            index_to = company_proxy.index_to#[:10]
        supplier_id = ids[0]

        # Mask for parameters:
        table_mask = """
            <p><table witdh='500px' class='oe_list_content'>
            <tr><td width='400px' align='center'>%s</td>
            <td width='100px' align='center'>%s</td></tr>
            %s</table></p><br/><br/>
            """
        parameter_mask = "%s: <strong>%s</strong><br/>"
        row_mask = "<tr><td>%s</td><td align='right'>%s</td></tr>"

        claim_pool = self.pool.get('quality.claim')
        conformed_pool = self.pool.get('quality.conformed')
        sampling_pool = self.pool.get('quality.sampling')

        # ---------------------------------------------------------------------
        #                           INFORMATION:
        # ---------------------------------------------------------------------
        # Total acceptation:
        total_acceptation = self._get_index_delivery(
            cr, uid, index_from, index_to, supplier_id, context=context)

        # Total acceptation lots:
        total_acceptation_lot = self._get_index_lot(
            cr, uid, index_from, index_to, supplier_id, context=context)

        html = parameter_mask % (_("Range date"), "[%s - %s]" % (
            index_from, index_to))
        html += parameter_mask % (_("Total picking"), total_acceptation)
        html += parameter_mask % (_("Total lots"), total_acceptation_lot)
        res[ids[0]]['index_info'] = html

        # ---------------------------------------------------------------------
        #                            CLAIMS:
        # ---------------------------------------------------------------------
        # Total lot claimed:
        if index_to and index_from:
            cr.execute(""" 
                SELECT count(*) 
                FROM quality_claim_product qcp join quality_claim qc 
                    ON (qcp.claim_id = qc.id) 
                WHERE 
                    qc.state not in ('cancel') AND
                    qc.date >= %s AND
                    qc.date <= %s AND
                    real_lot_id in (
                        SELECT id 
                        FROM stock_production_lot 
                        WHERE default_supplier_id = %s);""",
                (index_from, index_to, supplier_id))
            total_lot_claimed = cr.fetchone()[0]
        else:
            total_lot_claimed = 0

        # Total claims:
        # Index totals:
        claim_gravity = {}
        claim_origin = {}
        claim_cause = {}
        if index_to and index_from:
            cr.execute(""" 
                SELECT DISTINCT qc.id 
                FROM quality_claim_product qcp join quality_claim qc 
                    ON (qcp.claim_id = qc.id) 
                WHERE 
                    qc.state not in ('cancel') AND
                    qc.date >= %s AND
                    qc.date <= %s AND
                    real_lot_id in (
                        SELECT id 
                        FROM stock_production_lot 
                        WHERE default_supplier_id = %s);""",
                (index_from, index_to, supplier_id))

            # ---------------------------------------------------
            # Loop for total computation (gravity, origin, cause)
            # ---------------------------------------------------
            claim_ids = [item[0] for item in cr.fetchall()]
            total_claim = len(claim_ids)
            res[ids[0]]['index_claim_list'] = "%s" % claim_ids

            for claim in claim_pool.browse(
                    cr, uid, claim_ids, context=context):
                if claim.origin_id:
                    claim_origin[claim.origin_id.name] = claim_origin.get(
                        claim.origin_id.name, 0) + 1
                if claim.cause_id:
                    claim_cause[claim.cause_id.name] = claim_cause.get(
                        claim.cause_id.name, 0) + 1
                if claim.gravity_id:
                    claim_gravity[claim.gravity_id.name] = claim_gravity.get(
                        claim.gravity_id.name, 0) + 1
        else:
            total_claim = 0


        # ---------------------------------
        # Lot totals claimed (calculation):
        # ---------------------------------
        distinct_lot_claimed = 0
        distinct_table = ""
        if index_to and index_from:
            cr.execute("""
                SELECT spl.name, count(*) FROM (        
                    SELECT 
                        QCP.real_lot_id id
                    FROM
                          quality_claim_product QCP 
                        JOIN
                          quality_claim QC
                        ON
                          (QCP.claim_id = QC.id) 
                    WHERE
                        QC.date >= %s AND
                        QC.date <= %s AND
                        QC.state not in ('cancel') AND
                        QCP.real_lot_id in (
                            SELECT id 
                            FROM stock_production_lot 
                            WHERE default_supplier_id = %s)
                ) AS l 
                JOIN stock_production_lot spl 
                ON (l.id = spl.id) 
                GROUP BY l.id, spl.name
                ORDER BY count(*) desc, spl.name;""",
                (index_from, index_to, supplier_id))

            for record in cr.fetchall():
                distinct_lot_claimed += 1
                distinct_table += row_mask % (record[0], record[1])

        # ---------------------------------------------------------------------
        #                Formatting data for HTML presentation
        # ---------------------------------------------------------------------
        # Header information:
        html = parameter_mask % (
            _('Lot claimed / Lot provided'),
            "%7.2f%s" % (
                100.0 * distinct_lot_claimed / total_acceptation_lot if total_acceptation_lot else 0.0,
                "%", ))
        html += parameter_mask % (
            _('Total distinct lot claimed'), distinct_lot_claimed)
        html += parameter_mask % (
            _('Total product claimed'), total_lot_claimed)
        html += parameter_mask % (
            _('Total claims'), total_claim)

        # Gravity:
        if claim_gravity:
            table = ""
            for key in sorted(claim_gravity.keys()):
                table += row_mask % (key, claim_gravity[key])
            html +=  table_mask % (_('Gravity'), _('Total'), table)

        # Origin:
        if claim_origin:
            table = ""
            for key in sorted(claim_origin.keys()):
                table += row_mask % (key, claim_origin[key])
            html +=  table_mask % (_('Origin'), _('Total'), table)

        # Cause:
        if claim_cause:
            table = ""
            for key in sorted(claim_cause.keys()):
                table += row_mask % (key, claim_cause[key])
            html +=  table_mask % (_('Cause'), _('Total'), table)

        # Lot distinct (loaded before)
        html += table_mask % (_('Lot claimed'), _('Total'), distinct_table)

        res[ids[0]]['index_claim'] = html

        # ---------------------------------------------------------------------
        #                          NOT CONFORMED:
        # ---------------------------------------------------------------------
        # Total conformed:
        # Index totals:
        conformed_gravity = {}
        conformed_origin = {}
        conformed_motivation = {
            'quantity': 0,
            'temperature': 0,
            'label': 0,
            'aesthetic_packaging': 0,
            'quality': 0,
            'deadline': 0,
            'sanitation': 0,
            'delay': 0,
            'no_delivery': 0,
            'external_material': 0,
            }
        conformed_motivation_label = {
            'quantity': u'Quantità',
            'temperature': u'Temperatura',
            'label': u'Etichetta',
            'aesthetic_packaging': u'Confezione',
            'quality': u'Qualità',
            'deadline': u'Scadenza',
            'sanitation': u'Igienico/Sanitario',
            'delay': u'Ritardo',
            'no_delivery': u'Mancata consegna',
            'external_material': 'Corpi estranei',
            }


        # TODO vedere come gestire il supplier_lot (prendere quello eventualm.)
        if index_to and index_from:
            cr.execute(""" 
                SELECT id 
                FROM quality_conformed 
                WHERE 
                    state not in ('cancel') AND
                    insert_date >= %s AND
                    insert_date <= %s AND
                    lot_id in (
                        SELECT id 
                        FROM stock_production_lot 
                        WHERE default_supplier_id = %s);""",
                (index_from, index_to, supplier_id))

            # --------------------------
            # Loop for total computation
            # --------------------------

            conformed_ids = [item[0] for item in cr.fetchall()]
            total_conformed = len(conformed_ids)
            res[ids[0]]['index_conformed_list'] = "%s" % conformed_ids

            for conformed in conformed_pool.browse(cr, uid, conformed_ids,
                    context=context):
                if conformed.origin:
                    conformed_origin[conformed.origin] = conformed_origin.get(
                        conformed.origin, 0) + 1
                if conformed.gravity_id:
                    conformed_gravity[
                        conformed.gravity_id.name] = conformed_gravity.get(
                            conformed.gravity_id.name, 0) + 1
                for motivation in conformed_motivation:
                    conformed_motivation[
                        motivation] += 1 if conformed.__getattr__(
                            motivation) else 0
        else:
            total_conformed = 0

        # ----------------------------
        # Load tables for format data:
        # ----------------------------
        # Header information:
        html = parameter_mask % (_('Total conformed'), total_conformed)

        # Gravity:
        if conformed_gravity:
            table = ""
            for key in sorted(conformed_gravity.keys()):
                table += row_mask % (key, conformed_gravity[key])
            html +=  table_mask % (_('Gravity'), _('Total'), table)

        # Origin:
        if conformed_origin:
            table = ""
            for key in sorted(conformed_origin.keys()):
                table += row_mask % (key, conformed_origin[key])
            html +=  table_mask % (_('Origin'), _('Total'), table)

        # Motivation:
        if any(conformed_motivation.values()):
            table = ""
            for key in sorted(conformed_motivation.keys()):
                table += row_mask % (
                    conformed_motivation_label.get(key, '?'),
                    conformed_motivation[key],
                    )
            html +=  table_mask % (_('Motivation'), _('Total'), table)

        res[ids[0]]['index_conformed'] = html

        # ---------------------------------------------------------------------
        #                            SAMPLING:
        # ---------------------------------------------------------------------
        # Total conformed:
        # TODO vedere comme gestire il supplier_lot (prendere quello eventual.)
        # Index totals:
        sampling_state = {}
        sampling_origin = {}

        if index_to and index_from:

            cr.execute(""" 
                SELECT id 
                FROM quality_sampling 
                WHERE 
                    state not in ('cancel') AND
                    date >= %s AND
                    date <= %s AND
                    lot_id in (
                        SELECT id 
                        FROM stock_production_lot 
                        WHERE default_supplier_id = %s);""",
                (index_from, index_to, supplier_id))

            # --------------------------
            # Loop for total computation
            # --------------------------
            sampling_ids = [item[0] for item in cr.fetchall()]
            total_sampling = len(sampling_ids)
            res[ids[0]]['index_sampling_list'] = "%s" % sampling_ids

            for sampling in sampling_pool.browse(cr, uid, sampling_ids,
                    context=context):
                if sampling.origin:
                    sampling_origin[sampling.origin] = sampling_origin.get(
                        sampling.origin, 0) + 1
                if sampling.state in ('passed', 'notpassed'):
                    sampling_state[sampling.state] = sampling_state.get(
                        sampling.state, 0) + 1
        else:
            total_sampling = 0

        # ----------------------------
        # Load tables for format data:
        # ----------------------------
        # Header information:
        html = parameter_mask % (_('Total sampling'), total_sampling)

        # Origin:
        if sampling_origin:
            table = ""
            for key in sorted(sampling_origin.keys()):
                table += row_mask % (key, sampling_origin[key])
            html +=  table_mask % (_('Origin'), _('Total'), table)

        # State:
        if sampling_state:
            table = ""
            for key in sorted(sampling_state.keys()):
                table += row_mask % (key, sampling_state[key])
            html +=  table_mask % (_('Esit'), _('Total'), table)

        res[ids[0]]['index_sampling'] = html

        return res

    _columns = {
        'no_quality_search': fields.boolean(
            'Non ricercabile',
            help='Non visibile nelle ricerche delle schede qualita\'',
            ),
        'rating_ids': fields.one2many('quality.supplier.rating', 'partner_id',
            'Rating'),
        'check_ids': fields.one2many('quality.supplier.check', 'partner_id',
            'Check'),
        'certification_ids': fields.one2many('quality.supplier.certification',
           'partner_id', 'Certification'),
        'reference_ids': fields.one2many('quality.supplier.reference',
            'partner_id', 'Reference'),
        'quality_email':  fields.char('Quality email', size=240,
            help="Email for quality comunications"),
        'quality_contact': fields.boolean('Quality contact',
            help="Contact to be used for quality purpose"),

        # Extra info for quality:
        'quality_activity': fields.text('Activity',
            help="Extra information about activity used in quality manage"),
        'quality_product': fields.text('Product',
            help="Extra information about product used in quality manage"),
        'quality_rating_info': fields.text('Rating info',
            help="Extra information about rating info used in quality manage"),
        'quality_commercial_reference': fields.text('Commercial reference',
            help="Extra information about commercial reference used in quality manage"),
        'quality_update_date': fields.date('Update Date',
            help="Extra information about information updared, used in quality manage"),
        'quality_start_supplier': fields.date('Start supplier',
            help="Extra information about start supplier service, used in quality manage"),
        'quality_end_supplier': fields.date('End supplier',
            help="Extra information about stop supplier service, used in quality manage"),
        'quality_class_id':fields.many2one('quality.partner.class', 'Class'),

        'access_c_id': fields.integer('Access Customer ID'),
        'access_s_id': fields.integer('Access Supplier ID'),

        'custom_range': fields.boolean('Custom range',
            help='If checked specify custom range else use company default'),
        'index_from': fields.date('From date',
            help='From date (used in index valorization'),
        'index_to': fields.date('To date',
            help='To date (used in index valorization'),

        # -------------
        # Index fields:
        # -------------
        'index_claim': fields.function(_get_index_information, method=True,
            type='text', string='Claim index', store=False,
            help='Claim information tables', multi="index"),
        'index_claim_list': fields.function(_get_index_information,
            method=True,
            type='text', string='Claim list', store=False,
            help='Used for button claims', multi="index"),
        #'index_lot_claimed': fields.function(_get_index_information,
        #    method=True,
        #    type='text', string='Lot claimed', store=False,
        #    help='Total lot claimed', multi="index"),

        'index_conformed': fields.function(_get_index_information, method=True,
            type='text', string='Claim index', store=False,
            help='Not conformed information tables', multi="index"),
        'index_conformed_list': fields.function(_get_index_information,
            method=True,
            type='text', string='Conformed list', store=False,
            help='Used for button Conformed', multi="index"),

        'index_sampling': fields.function(_get_index_information, method=True,
            type='text', string='Claim index', store=False,
            help='Sampling information tables', multi="index"),
        'index_sampling_list': fields.function(_get_index_information,
            method=True,
            type='text', string='Sampling list', store=False,
            help='Used for button Sampling', multi="index"),

        'index_info': fields.function(_get_index_information, method=True,
            type='text', string='Claim index', store=False,
            help='General info about product and lot supplied', multi="index"),
        }

class quality_conformed(osv.osv):
    """ Assign *2many fields to conformed
    """
    _inherit = 'quality.conformed'

    _columns = {
        'action_id': fields.many2one('quality.action', 'Action',
            ondelete='set null'),
        'action_state': fields.related('action_id', 'state', type='selection',
            selection=action_state, string='Action state', store=False),
        # TODO fields.relater action_id state

        'parent_sampling_id': fields.many2one('quality.sampling',
            'Parent Sampling', ondelete='set null'),
        'sampling_id': fields.many2one('quality.sampling', 'Sampling',
            ondelete='set null'),
        'sampling_state': fields.related('sampling_id', 'state',
            type='selection', selection=sampling_state,
            string='Sampling state', store=False),
        # TODO fields.relater sampling_id state (come per action)
    }

class quality_sampling(osv.osv):
    """ Assign *2many fields to conformed
    """
    _inherit = 'quality.sampling'

    _columns = {
        'parent_conformed_id': fields.many2one('quality.conformed',
            'Parent Not Conformed', ondelete='set null'),
        'conformed_id': fields.many2one('quality.conformed', 'Not Conformed',
            ondelete='set null'),
        'conformed_state': fields.related('conformed_id', 'state',
            type='selection', selection=conformed_state,
            string='Conformed state', store=False),
        }

class quality_acceptation(osv.osv):
    """ Acceptation form
    """
    _inherit = 'quality.acceptation'

    _columns = {
        'line_ids': fields.one2many('quality.acceptation.line',
            'acceptation_id', 'Lines'),
        }

class quality_acceptation_line(osv.osv):
    """ Acceptation form add relation extra fields
    """
    _inherit = 'quality.acceptation.line'

    _columns = {
        'conformed_id': fields.many2one('quality.conformed', 'Not conformed'),
        # TODO togliere lo stato e mettere una non conformità per spunta
        'conformed_state': fields.related('conformed_id', 'state',
            type='selection', selection=conformed_state,
            string='Conformed state', store=False),
        'sampling_id': fields.many2one('quality.sampling', 'Sampling'),
        }

# -----------------------------------------------------------------------------
#                             NOT CONFORMED EXTERNAL
# -----------------------------------------------------------------------------
class quality_conformed_external(osv.osv):
    """ Forms of not conformed
    """
    _inherit = 'quality.conformed.external'

    # -------------------------------------------------------------------------
    # Button events:
    # -------------------------------------------------------------------------
    def create_action(self, cr, uid, ids, context=None):
        """ Create a Action and link to this Claim
        """
        external_proxy = self.browse(cr, uid, ids, context=context)[0]
        if external_proxy.mode == 'internal':
            origin = 'audit'
        else: # supplier
            origin = 'other'

        action_pool = self.pool.get('quality.action')
        action_id = action_pool.create(cr, uid, {
            'name': external_proxy.name,
            'date': datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
            'conformed_external_id': ids[0],
            'origin': origin,
            'type': 'corrective',
            }, context=context)
        self.write(cr, uid, ids, {
            'action_id': action_id,
            }, context=context)

        # Raise trigger for open AC:
        wf_service = netsvc.LocalService('workflow')
        wf_service.trg_validate(uid, 'quality.action', action_id,
            'trigger_action_draft_opened', cr)
        return self.pool.get('micronaet.tools').get_view_dict(cr, uid, {
            'model': 'quality.action',
            'module': 'quality',
            'record': action_id,
            })

    _columns = {
        'claim_id': fields.many2one(
            'quality.claim', 'Claim'),
        'gravity_id': fields.many2one('quality.gravity', 'Gravity',
            required=True),
        'action_id': fields.many2one('quality.action', 'Action',
            ondelete='set null'),
        'action_state': fields.related('action_id', 'state', type='selection',
            selection=action_state, string='Action state', store=False),
        # TODO fields.relater action_id state
        }

    _defaults = {
        'gravity_id': lambda s, cr, uid, ctx: s.pool.get(
            'ir.model.data').get_object_reference(
                cr,  uid, 'quality', 'quality_gravity_serious')[1],
        }


class quality_claim(osv.osv):
    """ Assign *2many fields to claims
    """
    _inherit = 'quality.claim'

    _columns = {
        'product_ids':fields.one2many('quality.claim.product', 'claim_id',
            'Product'),
        'conformed_external_ids': fields.one2many(
            'quality.conformed.external', 'claim_id', 'NC esterne'),

        'action_id': fields.many2one('quality.action', 'Action',
            ondelete='set null'),
        'action_state': fields.related('action_id', 'state', type='selection',
            selection=action_state, string='Action state', store=False),

        'sampling_id': fields.many2one('quality.sampling', 'Sampling',
            ondelete='set null'),
        'sampling_state': fields.related('sampling_id', 'state',
            type='selection', selection=sampling_state,
            string='Sampling state', store=False),

        'conformed_id': fields.many2one('quality.conformed', 'Not Conformed',
            ondelete='set null'),
        'conformed_state': fields.related('conformed_id', 'state',
            type='selection', selection=conformed_state,
            string='Not Conformed state', store=False),
        }
