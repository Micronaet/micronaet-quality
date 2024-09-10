#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Modules used for ETL - Create User

# Modules required:
import os
import xmlrpclib, sys, csv, ConfigParser
from openerp.tools.status_history import status
from datetime import datetime

# -----------------------------------------------------------------------------
#           Set up parameters (for connection to Open ERP Database)
# -----------------------------------------------------------------------------
# Startup from config file:
config = ConfigParser.ConfigParser()
file_config = os.path.expanduser('~/ETL/generalfood/openerp.cfg')
config.read([file_config])
dbname = config.get('dbaccess','dbname')
user = config.get('dbaccess','user')
pwd = config.get('dbaccess','pwd')
server = config.get('dbaccess','server')
port = config.get('dbaccess','port')   # verify if it's necessary: getint
separator = eval(config.get('dbaccess','separator')) # test
log_only_error = eval(config.get('log','error')) # log only error in function

# Startup from code:
default_error_data = "2014/07/30"
default_product_id = 1921 # for lot creation (acceptation)
default_lot_id = 92710    # ERR
log_file = os.path.expanduser("~/ETL/generalfood/log/%s.txt" % (datetime.now()))
log = open(log_file, 'w')

# -----------------------------------------------------------------------------
#                           XMLRPC connection
# -----------------------------------------------------------------------------
sock = xmlrpclib.ServerProxy(
    'http://%s:%s/xmlrpc/common' % (server, port), allow_none=True)
uid = sock.login(dbname ,user ,pwd)
sock = xmlrpclib.ServerProxy(
    'http://%s:%s/xmlrpc/object' % (server, port), allow_none=True)

# -----------------------------------------------------------------------------
#                             Utility function
# -----------------------------------------------------------------------------
def format_string(valore):
    try:
        valore = valore.decode('cp1252')
    except:
        tmp = ""
        for i in valore:
            try:
                tmp += i.decode('cp1252')
            except:
                pass # jump char
        valore = tmp
    valore = valore.encode('utf-8')
    return valore.strip()

def format_date(valore,date=True):
    """ Formatta nella data di PG
    """
    try:
        if date:
            mga = valore.strip().split(' ')[0].split('/') # only date (not time)
            year = int(mga[2])
            if year < 100:
                if year > 50:
                    year += 1900
                else:
                    year += 2000

            return '%4d-%02d-%02d' % (year, int(mga[0]), int(mga[1]))
    except:
        return False

def format_currency(valore):
    """ Formatta nel float per i valori currency
    """
    try:
        return float(valore.strip().split(' ')[-1].replace(',','.'))
    except:
        return 0.0

def format_boolean(value):
    """ Formatta le stringhe '0' e '1' in boolean True e False
    """
    return value == '1'

def log_event(*event):
    """ Log event and comunicate with print
    """
    if log_only_error and event[0][:5] == "[INFO":
        return

    log.write("%s. %s\r\n" % (datetime.now(), event))
    print(event)
    return

def create_partner(partner_code, type_of_partner, default_dict):
    """ Create simple element for partner not found
        (write after in default_dict new element)
    """
    try:
        field = "sql_%s_code" % type_of_partner
        partner_ids = sock.execute(dbname, uid, pwd, "res.partner", "search",
            [(field, '=', partner_code)])
        if partner_ids:
            partner_id = partner_ids[0]
        else:
            data = {
                'name': "Partner %s (from migration)" % (partner_code),
                field: partner_code,
                'sql_import': True,
                }
            if type_of_partner == 'customer':
                data['ref'] = partner_code
                data['customer'] = True
            elif type_of_partner == 'supplier':
                data['supplier'] = True
            elif type_of_partner == 'destination':
                data['is_address'] = True

            partner_id = sock.execute(
                dbname, uid, pwd, "res.partner",
                'create', data)
            log_event("[WARN] %s partner created: %s" % (
                type_of_partner, partner_code))

        default_dict[partner_code] = partner_id
        return partner_id
    except:
        log_event("[ERROR] Error creating %s partner: %s" % (
            type_of_partner, partner_code))
        return False


def get_or_create_partner(
        partner_code, type_of_partner, mandatory, res_partner_customer,
        res_partner_supplier):
    """ Try to get partner element or create a simple element if not present
    """
    if type_of_partner == 'customer':
        default_dict = res_partner_customer
    elif type_of_partner == 'supplier':
        default_dict = res_partner_supplier
    elif type_of_partner == 'destination':
        default_dict = res_partner_customer # search in customer dict
    else:
        default_dict = {} # nothing

    partner_id = default_dict.get(partner_code, False)

    if not partner_id: # create e simple element
        partner_id = create_partner(
            partner_code, type_of_partner, default_dict)

    if mandatory and not partner_id:
        log_event("[ERROR] %s partner not found: %s" % (
            type_of_partner, partner_code))
    return partner_id


# -----------------------------------------------------------------------------
#                           Importazioni qualifiche fornitore
# -----------------------------------------------------------------------------
qualifications = {
    '1': 'full',       # Piena qualitica
    '2': 'reserve',    # Con riserva
    '3': 'discarded',  # Scartato
    '4': 'uneventful', # Non movimentato
    '5': 'test',       # In prova
    '6': 'occasional', # Occasionale
}

# -----------------------------------------------------------------------------
#                           Importazioni comunicazioni
# -----------------------------------------------------------------------------
comunications = {
    '1': 1,    # Cliente
    '2': 2,    # Fornitore
    '3': 3,    # ASL
}

# -----------------------------------------------------------------------------
#                           Importazioni gravità
# -----------------------------------------------------------------------------
gravity = {
    '1': 2,    # Grave
    '2': 3,    # Importante
    '3': 1,    # Secondario
}

# -----------------------------------------------------------------------------
#                           Importazioni origin
# -----------------------------------------------------------------------------
origin = {
    '1': 1,    # Ordine
    '2': 2,    # Magazzino
    '3': 3,    # Fornitore
    '4': 4,    # Cliente
    '5': 5,    # Trasporto
    '6': 6,    # Fatturazione
    '7': 7,    # Non definibile
    '8': 8,    # Commerciale
    '9': 9,    # Logistica
    '10': 10,  # Confezionamento
    '11': 11,  # Acquisti
}

# -----------------------------------------------------------------------------
#                           Importazioni cause
# -----------------------------------------------------------------------------
cause = {
    '1': 1,    # Igiene
    '2': 2,    # Qualità
    '3': 3,    # Quantità
    '4': 4,    # Ritardo
    '5': 5,    # Prodotto sbagliato
    '6': 6,    # Confezione
    '7': 7,    # Errore cliente
    '8': 8,    # Prezzo
    '9': 9,    # Non definibile
    '10': 10,  # Glassatura
    '11': 11,  # Temperatura
    '12': 12,  # Pezzatura
    '13': 13,  # Corpi estranei/Contaminati
    '14': 14,  # Mancanza prodotto risp a bolla
    '15': 15,  # Rottura di stock
}

# -----------------------------------------------------------------------------
#                           Importazioni Sampling plan
# -----------------------------------------------------------------------------
plan = {
    '1': 1,    # Bieta erbetta
    '3': 2,    # Broccoli calabri IGF
    '4': 3,    # Carote Baby e rondelle
    '6': 4,    # Cavolfiore
    '7': 5,    # Carciofi
    '9': 6,    # Patate crocchette
    '11': 7,   # Fagiolini
    '12': 8,   # Finocchi
    '13': 9,   # Minestrone
    '16': 10,  # Patate
    '18': 11,  # Piselli
    '19': 12,  # Spinaci
    '20': 13,  # Zucchine
    '21': 14,  # Halibut
    '22': 15,  # Bastoncini
    '23': 16,  # Calamari
    '25': 17,  # Cozze
    '26': 18,  # Merluzzo
    '27': 19,  # Palombo
    '28': 20,  # Platessa
    '29': 21,  # Seppie
    '30': 22,  # Trota
    '31': 23,  # Coscette pollo
    '32': 24,  # Pollo
    '33': 25,  # Suino
    '35': 26,  # Peperoni
    '38': 27,  # Tacchino
    '39': 28,  # Asparagi
    '40': 29,  # Macinato
    '41': 30,  # Pesce spada
    '42': 31,  # Mais
    '43': 32,  # Pangasio
    '44': 33,  # Aromi e sedano
}

# -----------------------------------------------------------------------------
#           Importazioni Origin (action)  >> (Uso stessa anagrafica per camp.)
# -----------------------------------------------------------------------------
origin_action = {
    '1': 'direction', # Riesame della direzione
    '2': 'audit',     # Audit interno
    '3': 'claim',     # Reclamo
    '4': 'nc',        # Rapporto di non conformità
    '5': 'other',     # Altro
}

stock_production_lot = {}
lot_ids = sock.execute(dbname, uid, pwd, 'stock.production.lot', 'search', [])
for lot in sock.execute(
        dbname, uid, pwd, 'stock.production.lot', 'read', lot_ids, [
            'id', 'name']):
    stock_production_lot[lot['name']] = lot['id']

# -----------------------------------------------------------------------------
#                          Importazione Classi fornitore
# -----------------------------------------------------------------------------
only_create = True
jump_because_imported = True

file_input = os.path.expanduser('~/ETL/generalfood/Classi.txt')
openerp_object = 'quality.partner.class'
log_event("Start import %s" % openerp_object)
quality_partner_class = {}
lines = csv.reader(open(file_input, 'rb'), delimiter=separator)
counter = {'tot': -1, 'new': 0, 'upd': 0}
try:
    for line in lines:
        if jump_because_imported:
            break
        if counter['tot'] < 0:
            counter['tot'] += 1
            continue
        if len(line):
            access_id = line[0]
            name = format_string(line[1])

            # Start of importation:
            counter['tot'] += 1

            # test if record exists (basing on Ref. as code of Partner)
            item = sock.execute(dbname, uid, pwd, openerp_object, 'search', [
                ('access_id', '=', access_id)])

            data = {
                'name': name,
                'access_id': access_id,
            }
            if item:  # already exist
                counter['upd'] += 1
                try:
                    if only_create:
                        log_event("[INFO]", counter['tot'], "Write",
                            openerp_object, " (jumped only_create clause: ",
                            name)
                    else:
                        item_mod = sock.execute(dbname, uid, pwd,
                            openerp_object, 'write', item, data)
                        log_event(
                            "[INFO]", counter['tot'], "Write", openerp_object,
                            name)
                    quality_partner_class[access_id] = item[0]
                except:
                    log_event("[ERROR] Modifing data, current record:", data)

            else:   # new
                counter['new'] += 1
                try:
                    openerp_id=sock.execute(
                        dbname, uid, pwd, openerp_object, 'create', data)
                    log_event(
                        "[INFO]", counter['tot'], "Create", openerp_object,
                        name)
                    quality_partner_class[access_id] = openerp_id
                except:
                    log_event(
                        "[ERROR] Error creating data, current record: ", data)
except:
    log_event('[ERROR] Error importing data!')
    raise  # Exception("Errore di importazione!") # Scrivo l'errore per debug

store = status(openerp_object)
if jump_because_imported:
    quality_partner_class = store.load()
else:
    store.store(quality_partner_class)
log_event("Total %(tot)s (N: %(new)s, U: %(upd)s)" % counter)

# -----------------------------------------------------------------------------
#                                   Importazione Clienti
# -----------------------------------------------------------------------------
only_create = True
jump_because_imported = True

file_input = os.path.expanduser('~/ETL/generalfood/Clienti.txt')
openerp_object = 'res.partner'
log_event("Start import %s (customer)" % openerp_object)
res_partner_customer = {}
lines = csv.reader(open(file_input, 'rb'), delimiter=separator)
counter = {'tot': -1, 'new': 0, 'upd': 0}
try:
    for line in lines:
        if jump_because_imported:
            break
        if counter['tot'] < 0:
            counter['tot'] += 1
            continue
        if len(line):
            access_c_id = line[0]
            code = format_string(line[1])
            name = format_string(line[2])

            # Start of importation:
            counter['tot'] += 1

            # test if record exists (basing on Ref. as code of Partner)
            if code[:2] == '06':
                search_key = 'sql_customer_code'
                destination = False
            else:
                search_key = 'sql_destination_code'
                destination = True

            item = sock.execute(
                dbname, uid, pwd, openerp_object , 'search', [
                    #('access_c_id', '=', access_c_id),
                    (search_key, '=', code),
            ])

            if not item:
                log_event(
                    "[WARNING] Customer/Destination not found "
                    "(must be yet imported)", data, )
                # continue # TODO lo creo lo stesso per ora

            data = {
                'name': "%s%s" % (name, "" if item else " [*]"), # Creato da importazione)
                'is_company': True,
                'access_c_id': access_c_id,
                'customer': True,
                # for link sql importation
                search_key: code,  # 'sql_customer_code'
                'sql_import': True,
            }
            if destination:
                data['is_address'] = True
                # parent_id = ?? TODO

            if item:
               counter['upd'] += 1
               try:
                   if only_create:
                       log_event(
                           "[INFO]", counter['tot'], "No Write",
                           openerp_object,
                           " (jumped only_create clause: ", code)
                   else:
                       item_mod = sock.execute(
                           dbname, uid, pwd, openerp_object, 'write', item,
                           data)
                       log_event(
                           "[INFO]", counter['tot'], "Write", openerp_object,
                           code)
                   res_partner_customer[code] = item[0]
               except:
                   log_event("[ERROR] Modifing data, current record:", data)

            else:
               counter['new'] += 1
               try:
                   openerp_id = sock.execute(
                       dbname, uid, pwd, openerp_object, 'create', data)
                   log_event(
                       "[INFO]", counter['tot'], "Create", openerp_object,
                       code)
                   res_partner_customer[code] = openerp_id
               except:
                   log_event(
                       "[ERROR] Error creating data, current record: ", data)
except:
    log_event('[ERROR] Error importing data!')
    raise

store = status('%sc' % openerp_object)
if jump_because_imported:
    res_partner_customer = store.load()
else:
    store.store(res_partner_customer)
log_event("Total %(tot)s (N: %(new)s, U: %(upd)s)" % counter)

# -----------------------------------------------------------------------------
#                           Importazione Fornitori
# -----------------------------------------------------------------------------
only_create = True
jump_because_imported = True

file_input = os.path.expanduser('~/ETL/generalfood/Fornitori.txt')
openerp_object = 'res.partner'
log_event("Start import %s (supplier)" % openerp_object)
res_partner_supplier = {}
lines = csv.reader(open(file_input,'rb'), delimiter=separator)
counter = {'tot': -1, 'new': 0, 'upd': 0}
max_col = 0
try:
    for line in lines:
        if jump_because_imported:
            break
        if counter['tot'] < 0:
            counter['tot'] += 1
            max_col = len(line)
            continue
        if len(line):
            if len(line) != max_col:
               log_event(
                   "[ERROR] %s Different cols not %s but now %s! Jumped: %s" % (
                   counter['tot'], max_col, len(line), line))
               continue

            access_s_id = line[0]
            code = format_string(line[1])
            name = format_string(line[2])
            quality_class_code = format_string(line[3])

            quality_activity = format_string(line[11])
            quality_product = format_string(line[12])
            quality_rating_info = format_string(line[13])
            quality_commercial_reference = format_string(line[14])
            quality_update_date = format_date(line[15])
            quality_start_supplier = format_date(line[33])
            quality_end_supplier = format_date(line[34])

            quality_class_id = quality_partner_class.get(
                quality_class_code, False)

            # Start of importation:
            counter['tot'] += 1

            # test if record exists (basing on Ref. as code of Partner)
            item = sock.execute(
                dbname, uid, pwd, openerp_object , 'search', [
                    #('access_s_id', '=', access_s_id),
                    ('sql_supplier_code', '=', code),
                ])
            if not item:
                log_event(
                    "[WARNING] Supplier not found (must be yet imported)",
                    data, )
                #continue

            data = {
                'name': name,
                'is_company': True,
                'access_s_id': access_s_id,
                'supplier': True,
                'quality_class_id': quality_class_id,
                'quality_activity': quality_activity,
                'quality_product': quality_product,
                'quality_rating_info': quality_rating_info,
                'quality_commercial_reference': quality_commercial_reference,
                'quality_update_date': quality_update_date,
                'quality_start_supplier': quality_start_supplier,
                'quality_end_supplier': quality_end_supplier,
                # for link sql importation
                'sql_supplier_code': code,
                'sql_import': True,
            }

            if item:
               counter['upd'] += 1
               try:
                   if only_create:
                       log_event(
                           "[INFO]", counter['tot'], "Write", openerp_object,
                           " (jumped only_create clause: ", code)
                   else:
                       item_mod = sock.execute(
                           dbname, uid, pwd, openerp_object, 'write', item,
                           data)
                       log_event(
                           "[INFO]", counter['tot'], "Write", openerp_object,
                           code)
                   #res_partner_supplier[access_s_id] = item[0]
                   res_partner_supplier[code] = item[0]
               except:
                   log_event("[ERROR] Modifing data, current record:", data)

            else:
               counter['new'] += 1
               try:
                   openerp_id = sock.execute(
                       dbname, uid, pwd, openerp_object, 'create', data)
                   log_event(
                       "[INFO]", counter['tot'], "Create", openerp_object,
                       code)
                   #res_partner_supplier[access_s_id] = openerp_id
                   res_partner_supplier[code] = openerp_id
               except:
                   log_event(
                       "[ERROR] Error creating data, current record: ", data)
except:
    log_event('[ERROR] Error importing data!')
    raise
store = status('%ss' % openerp_object)
if jump_because_imported:
    res_partner_supplier = store.load()
else:
    store.store(res_partner_supplier)
log_event("Total %(tot)s (N: %(new)s, U: %(upd)s)" % counter)

# -----------------------------------------------------------------------------
#                         Importazione Qualifiche fornitore
# -----------------------------------------------------------------------------
only_create = True
jump_because_imported = True

file_input = os.path.expanduser('~/ETL/generalfood/Qualifiche.txt')
openerp_object = 'quality.supplier.rating'
log_event("Start import %s" % openerp_object)
# Non storicizzati in dict
lines = csv.reader(open(file_input, 'rb'), delimiter=separator)
counter = {'tot': -1, 'new': 0, 'upd': 0}
max_col = 0
try:
    for line in lines:
        if jump_because_imported:
            break
        if counter['tot'] < 0:
            counter['tot'] += 1
            max_col = len(line)
            continue
        if len(line):
            counter['tot'] += 1
            if len(line) != max_col:
               log_event("[ERROR] %s Different cols not %s but now %s! Jumped:" % (
                   counter['tot'], max_col, len(line)))
               continue

            access_id = line[0]
            supplier_code = format_string(line[1])
            qualification_code = format_string(line[2])
            name = format_string(line[3])
            date = format_date(line[4])
            type_code = format_string(line[5]).upper()
            deadline = format_date(line[6])
            obsolete = format_boolean(line[7])

            # Convert foreign key:
            if type_code == "P":
                type_id = 'first'
            elif type_code == 'R':
                type_id = 'renewal'
            else:
                type_id = False

            partner_id = res_partner_supplier.get(supplier_code, False)
            if not partner_id: # Creo se non esiste
                partner_id = get_or_create_partner(supplier_code,
                    'supplier', True, res_partner_customer,
                    res_partner_supplier)
                if not partner_id:
                    log_event("[ERROR] Partner not found, jumped! %s" % (line))
                    continue

            qualification = qualifications.get(qualification_code, False)

            item = sock.execute(dbname, uid, pwd, openerp_object , 'search', [
                ('access_id', '=', access_id)])
            data = {
                'name': name,
                'date': date,
                'type': type_id,
                'deadline': deadline,
                'obsolete': obsolete,
                'qualification': qualification,
                'partner_id': partner_id,
                'access_id': access_id,
            }
            if item:
               counter['upd'] += 1
               try:
                   if only_create:
                       log_event(
                           "[INFO]", counter['tot'], "Write",
                           openerp_object, " (jumped only_create clause: ",
                           supplier_code)
                   else:
                       item_mod = sock.execute(
                           dbname, uid, pwd, openerp_object, 'write',
                           item, data)
                       log_event(
                           "[INFO]", counter['tot'], "Write",
                           openerp_object, supplier_code)
                   #quality_claim[access_id] = item[0]
               except:
                   log_event("[ERROR] Modifing data, current record:", data)

            else:
               counter['new'] += 1
               try:
                   openerp_id=sock.execute(
                       dbname, uid, pwd, openerp_object, 'create',
                       data)
                   log_event(
                       "[INFO]", counter['tot'], "Create",
                       openerp_object, name)
                   #quality_claim[access_id] = openerp_id
               except:
                   log_event(
                       "[ERROR] Error creating data, current record: ", data)
except:
    log_event('[ERROR] Error importing data!')
    raise
log_event("Total %(tot)s (N: %(new)s, U: %(upd)s)" % counter)

# -----------------------------------------------------------------------------
#                         Certificazioni fornitore
# -----------------------------------------------------------------------------
only_create = True
jump_because_imported = True

file_input = os.path.expanduser('~/ETL/generalfood/Certificazioni.txt')
openerp_object = 'quality.supplier.certification'
log_event("Start import %s" % openerp_object)
lines = csv.reader(open(file_input, 'rb'), delimiter=separator)
counter = {'tot': -1, 'new': 0, 'upd': 0}
max_col = 0
try:
    for line in lines:
        if jump_because_imported:
            break
        if counter['tot'] < 0:
            counter['tot'] += 1
            max_col = len(line)
            continue

        if len(line):
            counter['tot'] += 1
            if len(line) != max_col:
               log_event("[ERROR] %s Different cols not %s but now %s! Jumped:" % (
                  counter['tot'], max_col, len(line)))
               continue

            access_id = line[0]
            supplier_code = format_string(line[1])
            entity = format_date(line[2])
            rule = format_string(line[3])
            note = format_string(line[4]) # purpose
            date = format_date(line[5])
            deadline = format_date(line[6])
            number = format_string(line[7])

            # Convert foreign key:
            partner_id = res_partner_supplier.get(supplier_code, False)
            if not partner_id:
                partner_id = get_or_create_partner(supplier_code,
                    'supplier', True, res_partner_customer,
                    res_partner_supplier)
                if not partner_id:
                    log_event("[ERROR] Partner not found, jumped! %s" % (line))
                    continue

            item = sock.execute(dbname, uid, pwd, openerp_object , 'search', [
                ('access_id', '=', access_id)])

            data = {
                'date': date,
                'entity': entity,
                # 'name': # TODO esiste???
                'deadline': deadline,
                'note': note,
                'rule': rule,
                'number': number,
                'partner_id': partner_id,
                'access_id': access_id,
            }
            if item:
               counter['upd'] += 1
               try:
                   if only_create:
                       log_event(
                           "[INFO]", counter['tot'], "Write",
                           openerp_object, " (jumped only_create clause: ",
                           supplier_code)
                   else:
                       item_mod = sock.execute(
                           dbname, uid, pwd, openerp_object, 'write',
                           item, data)
                       log_event(
                           "[INFO]", counter['tot'], "Write",
                           openerp_object, supplier_code)
                   #quality_claim[access_id] = item[0]
               except:
                   log_event("[ERROR] Modifing data, current record:", data)

            else:
               counter['new'] += 1
               try:
                   openerp_id = sock.execute(
                       dbname, uid, pwd, openerp_object, 'create', data)
                   log_event(
                       "[INFO]", counter['tot'], "Create",
                       openerp_object, supplier_code)
                   #quality_claim[access_id] = openerp_id
               except:
                   log_event(
                       "[ERROR] Error creating data, current record: ", data)
except:
    log_event('[ERROR] Error importing data!')
    raise
log_event("Total %(tot)s (N: %(new)s, U: %(upd)s)" % counter)

# -----------------------------------------------------------------------------
#                         Referenze - Andamenti Qualifiche fornitore
# -----------------------------------------------------------------------------
only_create = True
jump_because_imported = True

file_input = os.path.expanduser('~/ETL/generalfood/Andamenti.txt')
openerp_object = 'quality.supplier.reference'
log_event("Start import %s" % openerp_object)
lines = csv.reader(open(file_input, 'rb'), delimiter=separator)
counter = {'tot': -1, 'new': 0, 'upd': 0}
max_col = 0
try:
    for line in lines:
        if jump_because_imported:
            break
        if counter['tot'] < 0:
            counter['tot'] += 1
            max_col = len(line)
            continue
        if len(line):
            counter['tot'] += 1
            if len(line) != max_col:
               log_event("[ERROR] %s Different cols not %s now %s! Jumped:" % (
                   counter['tot'], max_col, len(line)))
               continue

            access_id = line[0]
            supplier_code = format_string(line[1])
            date = format_date(line[2])
            note = format_string(line[3])

            # Convert foreign key:
            partner_id = res_partner_supplier.get(supplier_code, False)
            if not partner_id:
                partner_id = get_or_create_partner(supplier_code,
                    'supplier', True, res_partner_customer,
                    res_partner_supplier)
                if not partner_id:
                    log_event("[ERROR] Partner not found, jumped! %s" % (line))
                    continue

            item = sock.execute(dbname, uid, pwd, openerp_object , 'search', [
                ('access_id', '=', access_id)])
            data = {
                #'name': name, # TODO non esiste!!!
                'date': date,
                'note': note,
                'partner_id': partner_id,
                'access_id': access_id,
            }
            if item:
               counter['upd'] += 1
               try:
                   if only_create:
                       log_event(
                           "[INFO]", counter['tot'], "Write",
                           openerp_object, " (jumped only_create clause: ",
                           supplier_code)
                   else:
                       item_mod = sock.execute(
                           dbname, uid, pwd, openerp_object, 'write',
                           item, data)
                       log_event(
                           "[INFO]", counter['tot'], "Write",
                           openerp_object, supplier_code)
                   #quality_claim[access_id] = item[0]
               except:
                   log_event("[ERROR] Modifing data, current record:", data)

            else:
               counter['new'] += 1
               try:
                   openerp_id = sock.execute(
                       dbname, uid, pwd, openerp_object, 'create', data)
                   log_event(
                       "[INFO]", counter['tot'], "Create",
                       openerp_object, supplier_code)
                   #quality_claim[access_id] = openerp_id
               except:
                   log_event(
                       "[ERROR] Error creating data, current record: ", data)
except:
    log_event('[ERROR] Error importing data!')
    raise
log_event("Total %(tot)s (N: %(new)s, U: %(upd)s)" % counter)

# -----------------------------------------------------------------------------
#                         Verifiche fornitore
# -----------------------------------------------------------------------------
only_create = True
jump_because_imported = True

file_input = os.path.expanduser('~/ETL/generalfood/Verifiche.txt')
openerp_object = 'quality.supplier.check'
log_event("Start import %s" % openerp_object)
lines = csv.reader(open(file_input, 'rb'), delimiter=separator)
counter = {'tot': -1, 'new': 0, 'upd': 0}
max_col = 0
try:
    for line in lines:
        if jump_because_imported:
            break
        if counter['tot'] < 0:
            counter['tot'] += 1
            max_col = len(line)
            continue

        if len(line):
            counter['tot'] += 1
            if len(line) != max_col:
               log_event("[ERROR] %s Different cols not %s but now %s! Jumped:" % (
                   counter['tot'], max_col, len(line)))
               continue

            access_id = line[0]
            supplier_code = format_string(line[1])
            date = format_date(line[2])
            name = format_string(line[3])
            note = format_string(line[4])

            # Convert foreign key:
            partner_id = res_partner_supplier.get(supplier_code, False)
            if not partner_id:
                partner_id = get_or_create_partner(supplier_code,
                    'supplier', True, res_partner_customer,
                    res_partner_supplier)
                if not partner_id:
                    log_event("[ERROR] Partner not found, jumped! %s" % (line))
                    continue

            item = sock.execute(dbname, uid, pwd, openerp_object , 'search', [
                ('access_id', '=', access_id)])

            data = {
                'date': date,
                'name': name,
                'note': note,
                'partner_id': partner_id,
                'access_id': access_id,
            }
            if item:
               counter['upd'] += 1
               try:
                   if only_create:
                       log_event(
                           "[INFO]", counter['tot'], "Write",
                           openerp_object, " (jumped only_create clause: ",
                           supplier_code)
                   else:
                       item_mod = sock.execute(
                           dbname, uid, pwd, openerp_object, 'write',
                           item, data)
                       log_event(
                           "[INFO]", counter['tot'], "Write",
                           openerp_object, supplier_code)
                   #quality_claim[access_id] = item[0]
               except:
                   log_event("[ERROR] Modifing data, current record:", data)

            else:
               counter['new'] += 1
               try:
                   openerp_id = sock.execute(
                       dbname, uid, pwd, openerp_object, 'create', data)
                   log_event(
                       "[INFO]", counter['tot'], "Create",
                       openerp_object, supplier_code)
                   #quality_claim[access_id] = openerp_id
               except:
                   log_event(
                       "[ERROR] Error creating data, current record: ", data)
except:
    log_event('[ERROR] Error importing data!')
    raise
log_event("Total %(tot)s (N: %(new)s, U: %(upd)s)" % counter)

# -----------------------------------------------------------------------------
#                              PRECARICAMENTI
# -----------------------------------------------------------------------------
# RECLAMI ---------------------------------------------------------------------
jump_because_imported = True

file_input = os.path.expanduser('~/ETL/generalfood/Rapporti.txt')
openerp_object = 'quality.claim'
log_event("Start preload import %s" % openerp_object)
quality_claim = {}
lines = csv.reader(open(file_input, 'rb'), delimiter=separator)
counter = {'tot': -1, 'new': 0, 'upd': 0}

if not jump_because_imported:
    try:
        for line in lines:
            counter['tot'] += 1
            if counter['tot'] <= 0:
                continue
            if len(line):
                access_id = line[0]
                ref = "REC%05d" % (int(format_string(line[1]) or '0'))

                item = sock.execute(dbname, uid, pwd, openerp_object , 'search', [
                    ('access_id', '=', access_id)])
                data = {
                    'ref': ref,
                    'name': ref,       # TODO not correct
                    'access_id': access_id,
                    'partner_id': 1,   # TODO not correct
                }
                if item:
                    quality_claim[access_id] = item[0]
                else:
                   try:
                       quality_claim[access_id] = sock.execute(
                           dbname, uid, pwd, openerp_object, 'create', data)
                       log_event("[INFO] %s. Create %s ref: %s" % (
                           counter['tot'], openerp_object, ref))
                   except:
                       log_event(
                           "[ERROR] Error creating, record: %s " % line)
    except:
        log_event('[ERROR] Error importing data!')
        raise

store = status(openerp_object)
if jump_because_imported:
    quality_claim = store.load()
else:
    store.store(quality_claim)
log_event("Total %(tot)s" % counter)

# NON CONFORMITA' -------------------------------------------------------------
jump_because_imported = True

file_input = os.path.expanduser('~/ETL/generalfood/Conformità.txt')
openerp_object = 'quality.conformed'
log_event("Start preload import %s" % openerp_object)
quality_conformed = {}
lines = csv.reader(open(file_input, 'rb'), delimiter=separator)
counter = {'tot': -1, 'new': 0, 'upd': 0}
max_col = 0

if not jump_because_imported:
    try:
        for line in lines:
            try:
                counter['tot'] += 1
                if counter['tot'] <= 0:
                    max_col = len(line)
                    continue
                if len(line):
                    if len(line) != max_col:
                        log_event("[ERROR] %s Different cols not %s but now %s! Jumped: %s" % (
                            counter['tot'], max_col, len(line), counter['tot']))
                        continue
                    access_id = line[0]
                    ref = "NC%05d" % (int(format_string(line[4]) or '0'))

                    item = sock.execute(dbname, uid, pwd, openerp_object , 'search', [
                        ('access_id', '=', access_id)])
                    data = {
                        'ref': ref,
                        'access_id': access_id,
                        'gravity_id': 2, #TODO da correggere
                        }
                    if item:
                        quality_conformed[access_id] = item[0]
                    else:
                       try:
                           quality_conformed[access_id] = sock.execute(
                               dbname, uid, pwd, openerp_object, 'create', data)
                           log_event("[INFO] %s. Create %s ref: %s" % (
                               counter['tot'], openerp_object, ref))
                       except:
                           log_event(
                               "[ERROR] Error creating, record: %s " % line)
            except:
                log_event('[ERROR] %s. Error importing data: %s' % (counter['tot'], sys.exc_info()))
                continue

    except:
        log_event('[ERROR] Error importing data!')
        raise
store = status(openerp_object)
if jump_because_imported:
    quality_conformed = store.load()
else:
    store.store(quality_conformed)
log_event("Total %(tot)s" % counter)

# CAMPIONAMENTI ---------------------------------------------------------------
jump_because_imported = True

file_input = os.path.expanduser('~/ETL/generalfood/Campionatura.txt')
openerp_object = 'quality.sampling'
log_event("Start preload import %s" % openerp_object)
quality_sampling = {}
lines = csv.reader(open(file_input, 'rb'), delimiter=separator)
counter = {'tot': -1, 'new': 0, 'upd': 0}
max_col = 0

if not jump_because_imported:
    try:
        for line in lines:
            counter['tot'] += 1
            if counter['tot'] <= 0:
                max_col = len(line)
                continue
            if len(line):
                if len(line) != max_col:
                    log_event("[ERROR] %s Different cols not %s but now %s! Jumped: %s" % (
                        counter['tot'], max_col, len(line), counter['tot']))
                    continue
                access_id = line[0]
                ref = "SAM%05d" % (int(format_string(line[4]) or '0'))
                fake_lot = 91131

                item = sock.execute(dbname, uid, pwd, openerp_object , 'search', [
                    ('access_id', '=', access_id)])
                data = {
                    'ref': ref,
                    'access_id': access_id,
                    'date': '2014-06-25',
                    'lot_id': fake_lot,
                }
                if item:
                    quality_sampling[access_id] = item[0]
                else:
                   try:
                       quality_sampling[access_id] = sock.execute(
                           dbname, uid, pwd, openerp_object, 'create', data)
                       log_event("[INFO] %s. Create %s ref: %s" % (
                           counter['tot'], openerp_object, ref))
                   except:
                       log_event(
                           "[ERROR] Error creating, record: %s " % line)
    except:
        log_event('[ERROR] Error importing data!')
        raise
store = status(openerp_object)
if jump_because_imported:
    quality_sampling = store.load()
else:
    store.store(quality_sampling)
log_event("Total %(tot)s" % counter)

# AZIONI ---------------------------------------------------------------
jump_because_imported = True

file_input = os.path.expanduser('~/ETL/generalfood/Azioni.txt')
openerp_object = 'quality.action'
log_event("Start preload import %s" % openerp_object)
quality_action = {}
lines = csv.reader(open(file_input, 'rb'), delimiter=separator)
counter = {'tot': -1, 'new': 0, 'upd': 0}
if not jump_because_imported:
    try:
        for line in lines:
            counter['tot'] += 1
            if counter['tot'] <= 0:
                continue
            if len(line):
                access_id = line[0]
                ref = "ACP%05d" % (int(format_string(line[1]) or '0'))

                item = sock.execute(dbname, uid, pwd, openerp_object , 'search', [
                    ('access_id', '=', access_id)])
                data = {
                    'ref': ref,
                    'access_id': access_id,
                }
                if item:
                    quality_action[access_id] = item[0]
                else:
                   try:
                       quality_action[access_id] = sock.execute(
                           dbname, uid, pwd, openerp_object, 'create', data)
                       log_event("[INFO] %s. Create %s ref: %s" % (
                           counter['tot'], openerp_object, ref))
                   except:
                       log_event(
                           "[ERROR] Error creating, record: %s " % line)
    except:
        log_event('[ERROR] Error importing data!')
        raise
store = status(openerp_object)
if jump_because_imported:
    quality_action = store.load()
else:
    store.store(quality_action)
log_event("Total %(tot)s" % counter)

# -----------------------------------------------------------------------------
#                         RECLAMI
# -----------------------------------------------------------------------------
only_create = False
jump_because_imported = True

file_input = os.path.expanduser('~/ETL/generalfood/Rapporti.txt')
openerp_object = 'quality.claim'
log_event("Start import %s" % openerp_object)
quality_claim = {}
lines = csv.reader(open(file_input, 'rb'), delimiter=separator)
counter = {'tot': -1, 'new': 0, 'upd': 0}
old_claim = False
try:
    lot = {1: {}, 2: {}, 3: {}, }
    for line in lines:
        if jump_because_imported:
            break
        if counter['tot'] < 0:
            counter['tot'] += 1
            continue
        if len(line):
            access_id = line[0]
            name = format_string(line[1])
            date = format_date(line[2])
            partner_code = format_string(line[3])
            partner_ref = format_string(line[6])
            receive_user_code = format_string(line[12])
            subject = format_string(line[13])
            request_return = format_boolean(line[14])
            RTR_request = format_boolean(line[16])
            analysis = format_string(line[17])
            origin_code = format_string(line[36])
            cause_code = format_string(line[37])
            responsability = format_string(line[38])
            solution = format_string(line[39])
            gravity_code = format_string(line[40])
            need_accredit = format_boolean(line[41])
            SFA_saw = format_boolean(line[42])
            NC_ref = format_string(line[43])
            closed_date = format_date(line[46])
            action_code = format_string(line[57])
            sampling_code = format_string(line[60])

            ref_claim = int(name or '0')
            if not old_claim:
                old_claim = ref_claim
            else:
                old_claim += 1

            if old_claim != ref_claim:
                log_event("[ERROR] old_rec=%s rec_claim=%s (hole in list)" % (
                    old_claim, ref_claim))
                old_claim = ref_claim

            ref = "REC%05d" % (ref_claim)
            customer_ref = False # non esiste il codice di rif NC cliente?
            if need_accredit and not NC_ref:
                NC_ref = "Nessun riferimento"

            lot[1]['lot'] = format_string(line[20])
            lot[2]['lot'] = format_string(line[26])
            lot[3]['lot'] = format_string(line[32])
            lot[1]['product'] = format_string(line[23])
            lot[2]['product'] = format_string(line[29])
            lot[3]['product'] = format_string(line[35])
            lot[1]['supplier'] = format_string(line[21])
            lot[2]['supplier'] = format_string(line[27])
            lot[3]['supplier'] = format_string(line[33])
            lot[1]['date'] = format_date(line[18])
            lot[2]['date'] = format_date(line[24])
            lot[3]['date'] = format_date(line[30])
            lot[1]['qty_return'] = format_currency(line[19])
            lot[2]['qty_return'] = format_currency(line[25])
            lot[3]['qty_return'] = format_currency(line[31])

            receive_user_id = 1

            # Anagrafiche semplici:
            origin_id = origin.get(origin_code, False)
            cause_id = cause.get(cause_code, False)
            gravity_id = gravity.get(gravity_code, False)

            # Documenti collegati:
            action_id = quality_action.get(action_code, False)
            sampling_id = quality_sampling.get(sampling_code, False)

            # Trova partner ed eventuale destinazione
            partner_id = False
            partner_address_id = False
            if partner_code[:2] == '06':
                partner_id = get_or_create_partner(partner_code, 'customer',
                    False, res_partner_customer, res_partner_supplier)
            elif partner_code[:2] == '07':
                partner_address_id = get_or_create_partner(partner_code,
                    'destination', False, res_partner_customer,
                    res_partner_supplier)
                partner_id = partner_address_id # TODO cercare il partner della destinazione

            if not partner_id:
                partner_id = 1
                log_event("[WARNING] [%s] Correggere il partner, reclamo: %s" % (
                    ref, partner_code))

            # Start of importation:
            counter['tot'] += 1

            data = {
                'name': "%s..." % subject[:50],
                'ref': ref,
                'customer_ref': customer_ref, # codice cliente della NC (non esiste)
                'date': date,
                'receive_user_id': receive_user_id,
                'subject': subject,
                'analysis': analysis,
                'responsability': responsability,
                'solution': solution,
                'partner_id': partner_id,
                'partner_ref': partner_ref, # contatto dal cliente
                'partner_address_id': partner_address_id,
                'request_return': request_return,
                'RTR_request': RTR_request,
                'NC_ref': NC_ref,
                'SFA_saw': SFA_saw,
                'origin_id': origin_id,
                'cause_id': cause_id,
                'gravity_id': gravity_id,
                'closed_date': closed_date,
                'action_id': action_id,
                'sampling_id': sampling_id,
                'need_accredit': need_accredit,
                'access_id': access_id,
            }
            # test if record exists (basing on Ref. as code of Partner)
            item = sock.execute(dbname, uid, pwd, openerp_object , 'search', [
                ('access_id', '=', access_id)])
            if item:  # already exist
               counter['upd'] += 1
               try:
                   if only_create:
                       log_event(
                           "[INFO]", counter['tot'], "Write",
                           openerp_object, " (jumped only_create clause: ",
                           ref)
                   else:
                       try:
                           item_mod = sock.execute(
                               dbname, uid, pwd, openerp_object, 'write',
                               item, data)
                           log_event(
                               "[INFO]", counter['tot'], "Write",
                               openerp_object, ref)
                       except:
                           log_event(
                               "[ERR] %s Write data %s", counter['tot'], data)

                   quality_claim[access_id] = item[0]
               except:
                   log_event("[ERROR] Modifing data, current record:", data)
            else:   # new
               counter['new'] += 1
               try:
                   openerp_id = sock.execute(
                       dbname, uid, pwd, openerp_object, 'create', data)
                   log_event(
                       "[INFO]", counter['tot'], "Create",
                       openerp_object, ref)
                   quality_claim[access_id] = openerp_id
               except:
                   log_event(
                       "[ERROR] Error creating data, current record: ", data)

            if action_id:
                sock.execute(dbname, uid, pwd, 'quality.action', 'write', action_id, {
                    'claim_id' : quality_claim[access_id], 'origin': 'claim',
                    })
            if sampling_id:
                sock.execute(dbname, uid, pwd, 'quality.sampling', 'write', sampling_id, {
                    'claim_id' : quality_claim[access_id], 'origin': 'claim',
                    })
            # NOTE: NC nel vecchio programma non c'erano quindi non sono state aggiornate le genesi

            #importazione dei lotti
            for key in lot:
                try:
                    lot_name = lot[key]['lot'] # number
                    if lot_name and lot_name != '0':
                        lot_id = stock_production_lot.get(lot_name)
                        if not lot_id:
                            #log_event("[ERROR] No Lot, jump: %s" % lot_name) # no comunication
                            continue
                        lot_access_id = '%s%s' % (access_id, key)
                        data = {
                            'lot_id': lot_id,
                            'return_date': lot[key]['date'],
                            'return_qty': lot[key]['qty_return'],
                            'claim_id': quality_claim[access_id],
                            'real_lot_id': lot_id,
                            'access_id': lot_access_id,
                            }
                        lot_id = sock.execute(dbname, uid, pwd,
                            'quality.claim.product' , 'search', [
                                ('access_id', '=', lot_access_id)])
                    else:
                        #log_event("[ERROR] No Lot, jump: %s" % lot_name) # no comunication
                        continue
                except:
                    log_event("[ERROR] generic error (lot part) %s" % (
                        sys.exc_info()))
                    continue

                if lot_id:  # already exist
                    try:
                       sock.execute(
                           dbname, uid, pwd, 'quality.claim.product', 'write',
                           lot_id, data)
                    except:
                        log_event("[ERROR] Modifing lot %s [%s]" % (
                            key, data))

                else:   # new
                    try:
                        sock.execute(
                            dbname, uid, pwd, 'quality.claim.product', 'create', data)
                    except:
                        log_event(
                            "[ERROR] Error creating lot %s [%s]" % (
                                key, data))
except:
    log_event('[ERROR] Error importing data!')
    raise
store = status(openerp_object)
if jump_because_imported:
    quality_claim = store.load()
else:
    store.store(quality_claim)
log_event("Total %(tot)s (N: %(new)s, U: %(upd)s)" % counter)

# -----------------------------------------------------------------------------
#                               NOT CONFORMED
# -----------------------------------------------------------------------------
only_create = False
jump_because_imported = True

file_input = os.path.expanduser('~/ETL/generalfood/Conformità.txt')
openerp_object = 'quality.conformed'
log_event("Start import %s" % openerp_object)
quality_conformed = {}
lines = csv.reader(open(file_input, 'rb'), delimiter=separator)
counter = {'tot': -1, 'new': 0, 'upd': 0}
max_col = 0

try:
    treatment = {
        1: {'type': 'accept_exception'},
        2: {'type': 'discard'},
        3: {'type': 'make_supplier'},
        }
    comunication = {
        1: {'type': 1}, # Customer
        2: {'type': 2}, # Supplier
        3: {'type': 3}, # ASL
        }
    for line in lines:
        if jump_because_imported:
            break
        if counter['tot'] < 0:
            counter['tot'] += 1
            max_col = len(line)
            continue
        if len(line):
            counter['tot'] += 1
            if len(line) != max_col:

               log_event("[ERROR] %s Different cols not %s but now %s! Jumped: %s" % (
                   counter['tot'], max_col, len(line), line))

               continue
            access_id = line[0]
            sampling_code = format_string(line[1])
            action_code = format_string(line[2])
            ref = "NC%05d" % (int(format_string(line[4]) or '0'))
            insert_date = format_date(line[5])
            quantity = format_boolean(line[6])
            sanitation = format_boolean(line[7])
            aesthetic_packaging = format_boolean(line[8])
            name = format_string(line[9])
            # origin = format_string(line[9]) # TODO (posizione?)
            #genesis_1 = format_boolean(line[11])
            #genesis_2 = format_boolean(line[12])

            treatment[1]['treatment'] = format_boolean(line[13])
            treatment[2]['treatment'] = format_boolean(line[14])
            treatment[3]['treatment'] = format_boolean(line[15])
            treatment[1]['qty'] = format_currency(line[18])
            treatment[2]['qty'] = format_currency(line[19])
            treatment[3]['qty'] = format_currency(line[20])
            treatment[1]['note'] = format_string(line[21])
            treatment[2]['note'] = format_string(line[22])
            treatment[3]['note'] = format_string(line[23])

            comunication[1]['comunication'] = format_boolean(line[25]) # Cli
            comunication[2]['comunication'] = format_boolean(line[24]) # For
            comunication[3]['comunication'] = format_boolean(line[26]) # ASL
            comunication[1]['protocol'] = format_string(line[29]) # Cli
            comunication[2]['protocol'] = format_string(line[27]) # For
            comunication[3]['protocol'] = format_string(line[28]) # ASL

            note_RAQ = format_string(line[30])
            lot_code = format_string(line[33])
            ddt_ref = format_string(line[34])
            #genesis_3 = format_boolean(line[36])
            cancel = format_boolean(line[37])
            stock_note = format_string(line[38])
            #genesis_4 = format_boolean(line[39])
            gravity_code = format_string(line[40])

            sampling_id = quality_sampling.get(sampling_code, False)
            action_id = quality_action.get(action_code, False)

            gravity_id = gravity.get(gravity_code, 2) #TODO da cambiare il default
            lot_id = stock_production_lot.get(lot_code)
            if not lot_id:
                log_event("[ERROR] %s Lot not found %s, temp replaced ID=%s" % (
                    counter['tot'], lot_code, ref))
                lot_id = default_lot_id

            '''if genesis_1:
                genesis = 'acceptance'
            elif genesis_2:
                genesis = 'sample'
            elif genesis_3:
                genesis = 'claim'
            elif genesis_4:
                genesis = 'packaging'
            else:
                genesis = 'other'
            '''
            # Start of importation:
            # test if record exists (basing on Ref. as code of Partner)
            item = sock.execute(dbname, uid, pwd, openerp_object , 'search', [
                ('access_id', '=', access_id)])
            data = {
                'name': name,
                'ref': ref,
                'insert_date': insert_date,
                'aesthetic_packaging': aesthetic_packaging,
                'quantity': quantity,
                'sanitation': sanitation,
                'gravity_id': gravity_id,
                #'genesis': genesis, #TODO Spostare tutto nel campo origin
                #'origin': origin, #TODO da ricavare alla fine
                'ddt_ref': ddt_ref,
                'lot_id': lot_id,
                'note_RAQ': note_RAQ,
                'cancel': cancel,
                #'claim_id': claim_id,
                'sampling_id': sampling_id,
                #'acceptation_id': acceptation_id,
                'action_id': action_id,
                'access_id': access_id,
                'stock_note': stock_note,
                }

            if item:  # already exist
               counter['upd'] += 1
               try:
                   if only_create:
                       log_event(
                           "[INFO]", counter['tot'], "Write",
                           openerp_object, " (jumped only_create clause: ",
                           name)
                   else:
                       item_mod = sock.execute(
                           dbname, uid, pwd, openerp_object, 'write', item, data)
                       log_event(
                           "[INFO]", counter['tot'], "Write", openerp_object, name)
                   quality_conformed[access_id] = item[0]
               except:
                   log_event("[ERROR] Modifing data, current record:", counter['tot'], data)
                   continue

            else:   # new
               counter['new'] += 1
               try:
                   openerp_id=sock.execute(
                       dbname, uid, pwd, openerp_object, 'create', data)
                   log_event(
                       "[INFO]", counter['tot'], "Create",
                       openerp_object, name)
                   quality_conformed[access_id] = openerp_id
               except:
                   log_event(
                       "[ERROR] Error creating data, current record: ",
                       counter['tot'], data)
                   continue

            if action_id:
                sock.execute(dbname, uid, pwd, 'quality.action', 'write', action_id, {
                    'conformed_id' : quality_conformed[access_id],  # non è parent_
                    'origin': 'nc', # TODO corretto?
                    })
            if sampling_id: # corretto manualmente
                sock.execute(dbname, uid, pwd, 'quality.sampling', 'write', sampling_id, {
                    'parent_conformed_id' : quality_conformed[access_id],
                    'origin': 'nc', # TODO corretto?
                    })

            #Creazione trattamenti:
            for key in treatment:
                if treatment[key]['treatment']:
                    treat_access_id = '%s%s' % (access_id, key)
                    data = {
                        'type': treatment[key]['type'],
                        'name': treatment[key]['note'],
                        'qty': treatment[key]['qty'],
                        'conformed_id': quality_conformed[access_id],
                        'access_id': treat_access_id,
                        }
                    treat_id = sock.execute(dbname, uid, pwd, 'quality.treatment' , 'search', [
                        ('access_id', '=', treat_access_id)])
                    if treat_id:  # already exist
                        try:
                           sock.execute(
                               dbname, uid, pwd, 'quality.treatment', 'write',
                               treat_id, data)
                        except:
                            log_event("[ERROR] Modifing treat%s" % key)

                    else:   # new
                        try:
                            sock.execute(
                                dbname, uid, pwd, 'quality.treatment', 'create', data)
                        except:
                            log_event(
                                "[ERROR] Error creating treat%s" % key)

            #Creazione comunicazioni
            for key in comunication:
                if comunication[key]['comunication']:
                    comunication_access_id = '%s%s' % (access_id, key)
                    data = {
                        'type_id': comunication[key]['type'],
                        'prot_number': comunication[key]['protocol'],
                        'prot_date': insert_date,
                        'conformed_id': quality_conformed[access_id],
                        'access_id': comunication_access_id,
                        }
                    comunication_id = sock.execute(dbname, uid, pwd, 'quality.comunication' , 'search', [
                        ('access_id', '=', comunication_access_id)])
                    if comunication_id:  # already exist
                        try:
                           sock.execute(
                               dbname, uid, pwd, 'quality.comunication', 'write',
                               comunication_id, data)
                        except:
                            log_event("[ERROR] Modifing comunication%s" % key)

                    else:   # new
                        try:
                            sock.execute(
                                dbname, uid, pwd, 'quality.comunication', 'create', data)
                        except:
                            log_event(
                                "[ERROR] Error creating comunication%s" % key)

except:
    log_event('[ERROR] Error importing data!')
    raise
store = status(openerp_object)
if jump_because_imported:
    quality_conformed = store.load()
else:
    store.store(quality_conformed)
log_event("Total %(tot)s (N: %(new)s, U: %(upd)s)" % counter)

# -----------------------------------------------------------------------------
#                               CAMPIONAMENTI
# -----------------------------------------------------------------------------
only_create = False
jump_because_imported = True

file_input = os.path.expanduser('~/ETL/generalfood/Campionatura.txt')
openerp_object = 'quality.sampling'
log_event("Start import %s" % openerp_object)
quality_sampling = {}
lines = csv.reader(open(file_input, 'rb'), delimiter=separator)
counter = {'tot': -1, 'new': 0, 'upd': 0}
max_col = 0

sample_passed = []
sample_notpassed = []
tasters = {1: '', 2: '', 3: '', 4: ''}
try:
    for line in lines:
        if jump_because_imported:
            break
        if counter['tot'] < 0:
            counter['tot'] += 1
            max_col = len(line)
            continue
        if len(line):
            if len(line) != max_col:
               log_event("[ERROR] %s Different cols not %s but now %s! Jump:" % (
                   counter['tot'], max_col, len(line)))
               continue
            access_id = line[0]
            closed = format_boolean(line[1]) # closed (sample)
            ref = format_string(line[2])
            date = format_date(line[3])
            lot_code = format_string(line[4])

            # Spunta per fare l'esame:
            do_visual = format_boolean(line[8])      # ex 8
            do_analysis = format_boolean(line[9])    # ex 10
            do_taste = format_boolean(line[10])      # ex 9
            do_glazing = format_boolean(line[11])    # ex 11

            # Spunta per esito esame:
            visual_state = format_boolean(line[12])  # ex 12
            analysis_state = format_boolean(line[13])# ex 14
            taste_state = format_boolean(line[14])   # ex 13
            glazing_state = format_boolean(line[15]) # ex 15

            # Descrizioni esami:
            analysis = format_string(line[16])
            taste = format_string(line[17])
            visual = format_string(line[18])
            weight_glazing = format_currency(line[19])
            weight_drained = format_currency(line[20])
            perc_glazing_indicated = format_currency(line[21])
            perc_glazing_calculated = format_currency(line[22])

            # Assaggiatori:
            tasters[1] = format_string(line[23])
            tasters[2] = format_string(line[24])
            tasters[3] = format_string(line[25])
            tasters[4] = format_string(line[26])

            passed = format_boolean(line[27]) # passed (sample)
            note = format_string(line[29])
            conformed_code = format_string(line[36])
            cancel = format_boolean(line[38])
            sampling_plan_code = format_string(line[39])

            ref = "SAM%05d" % (int(ref or '0'))
            lot_id = stock_production_lot.get(lot_code, False)
            if not lot_id:
                log_event("[ERROR] %s Lot not found (replaced with temp raplaced ID=%s) %s" % (
                    counter['tot'], lot_code, ref))
                lot_id = default_lot_id

            conformed_id = quality_conformed.get(conformed_code, False)
            sampling_plan_id = plan.get(sampling_plan_code, False)
            if not date:
                date = data.get('date', default_error_data)

            # Start of importation:
            counter['tot'] += 1

            # test if record exists (basing on Ref. as code of Partner)
            item = sock.execute(dbname, uid, pwd, openerp_object , 'search', [
                ('access_id', '=', access_id)])

            data = {
                'ref': ref,
                'date': date,
                'lot_id': lot_id,
                #'origin': origin, TODO (vedere se ricavabile per ora ci sono solo i reclami)
                'conformed_id': conformed_id,

                # Check to do:
                'do_visual': do_visual,
                'do_analysis': do_analysis,
                'do_glazing': do_glazing,
                'do_taste': do_taste,

                # Text info:
                'visual': visual,
                'analysis': analysis,
                'taste': taste,
                'weight_glazing': weight_glazing,
                'perc_glazing_indicated': perc_glazing_indicated,
                'weight_drained': weight_drained,
                'perc_glazing_calculated': perc_glazing_calculated,

                'note': note,
                'sampling_plan_id': sampling_plan_id,
                'cancel': cancel,
                'access_id': access_id,
            }
            if closed:
                data['visual_state'] = 'passed' if visual_state else 'not_passed'
                data['analysis_state'] = 'passed' if analysis_state else 'not_passed'
                data['taste_state'] = 'passed' if taste_state else 'not_passed'
                data['glazing_state'] = 'passed' if glazing_state else 'not_passed'
            else:
                data['visual_state'] = 'passed' if visual_state else 'to_examined'
                data['analysis_state'] = 'passed' if analysis_state else 'to_examined'
                data['taste_state'] = 'passed' if taste_state else 'to_examined'
                data['glazing_state'] = 'passed' if glazing_state else 'to_examined'

            if item:  # already exist
               counter['upd'] += 1
               try:
                   if only_create:
                       log_event(
                           "[INFO]", counter['tot'], "Write",
                           openerp_object, " (jumped only_create clause: ",
                           ref)
                   else:
                       item_mod = sock.execute(
                           dbname, uid, pwd, openerp_object, 'write',
                           item, data)
                       log_event(
                           "[INFO]", counter['tot'], "Write",
                           openerp_object, ref)
                   quality_sampling[access_id] = item[0]
               except:
                   log_event("[ERROR] Modifing data, current record:", data)

            else:   # new
               counter['new'] += 1
               try:
                   openerp_id = sock.execute(
                       dbname, uid, pwd, openerp_object, 'create', data)
                   log_event(
                       "[INFO]", counter['tot'], "Create",
                       openerp_object, ref)
                   quality_sampling[access_id] = openerp_id
               except:
                   log_event(
                       "[ERROR] Error creating data, current record: ", data)

            if conformed_id:
                sock.execute(dbname, uid, pwd, 'quality.conformed', 'write', conformed_id, {
                    'parent_sampling_id' : quality_sampling[access_id],
                    'origin': 'sampling',
                    })

            # Aggiunta assaggiatori:
            for taste_id, taster in tasters.iteritems():
                if taster:
                    taster_access_id = "%s%s" % (access_id, taste_id)
                    data = {
                        'name': taster,
                        'sample_id': quality_sampling[access_id] ,
                        'access_id': taster_access_id,
                        }
                    taster_ids = sock.execute(dbname, uid, pwd, 'quality.sampling.taster', 'search', [
                        ('access_id', '=', taster_access_id)])
                    if taster_ids:
                        taster_ids = sock.execute(dbname, uid, pwd,
                            'quality.sampling.taster' , 'write', taster_ids[0], data)
                    else:
                        taster_ids = sock.execute(dbname, uid, pwd,
                            'quality.sampling.taster', 'create', data)

            if closed: # test for WF (end of importation)
                if passed:
                    sample_passed.append(quality_sampling[access_id])
                else:
                    sample_notpassed.append(quality_sampling[access_id])
            else:
                if passed:
                    sample_passed.append(quality_sampling[access_id])

except:
    log_event('[ERROR] Error importing data!')
    raise
store = status(openerp_object)
if jump_because_imported:
    quality_sampling = store.load()
else:
    store.store(quality_sampling)
log_event("Total %(tot)s (N: %(new)s, U: %(upd)s)" % counter)

# -----------------------------------------------------------------------------
#                               ACTION
# -----------------------------------------------------------------------------
only_create = False
jump_because_imported = True

file_input = os.path.expanduser('~/ETL/generalfood/Azioni.txt')
openerp_object = 'quality.action'
log_event("Start import %s" % openerp_object)
#quality_action = {} # caricato nella fase pre (tolto perchè resetta e non ho il child)
lines = csv.reader(open(file_input, 'rb'), delimiter=separator)
counter = {'tot': -1, 'new': 0, 'upd': 0}
max_col = 0

try:
    for line in lines:
        if jump_because_imported:
            break
        if counter['tot'] < 0:
            counter['tot'] += 1
            max_col = len(line)
            continue
        if len(line):
            if len(line) != max_col:
               log_event("[ERROR] %s ] counter['tot'], ] not %s but now %s! Jump:" % (
                   counter['tot'], max_col, len(line)))
               continue

            counter['tot'] += 1
            access_id = line[0]
            ref = format_string(line[1])
            date = format_date(line[2])
            origin = format_string(line[3]) #TODO da fare alla fine
            note = format_string(line[4])
            proposed_subject = format_string(line[5])
            esit_date = format_date(line[6])
            esit_note = format_string(line[7])
            child_code = format_string(line[9])
            #closed 10
            closed_date = format_date(line[11])
            proposing_entity = format_string(line[13])
            action_type = format_string(line[16])

            ref = "ACP%05d" % (int(ref or '0'))
            if action_type == "Azione Preventiva":
                action_type_id = 'preventive'
            elif action_type == "Intervento di Miglioramento":
                action_type_id = 'enhance'
            else: # action_type == "Azione Correttiva" or ""
                action_type_id = 'corrective' # default

            child_id = quality_action.get(child_code, False)
            origin = origin_action.get(origin, False)

            # test if record exists (basing on Ref. as code of Partner)
            item = sock.execute(dbname, uid, pwd, openerp_object , 'search', [
                ('access_id', '=', access_id)])
            data = {
                'ref': ref,
                'date': date,
                'origin': origin,
                'note': note,
                'proposed_subject': proposed_subject,
                'proposing_entity': proposing_entity,
                'esit_date': esit_date,
                'closed_date': closed_date,
                'esit_note': esit_note,
                'child_id': child_id,
                'type': action_type_id,
                'access_id': access_id,
            }
            if item:  # already exist
               counter['upd'] += 1
               try:
                   if only_create:
                       log_event(
                           "[INFO]", counter['tot'], "Write",
                           openerp_object, " (jumped only_create clause: ",
                           ref)
                   else:
                       item_mod = sock.execute(
                           dbname, uid, pwd, openerp_object, 'write',
                           item, data)
                       log_event(
                           "[INFO]", counter['tot'], "Write",
                           openerp_object, ref)
                   quality_action[access_id] = item[0]
               except:
                   log_event("[ERROR] Modifing data, current record:", data)
            else:   # new
               counter['new'] += 1
               try:
                   openerp_id=sock.execute(
                       dbname, uid, pwd, openerp_object, 'create', data)
                   log_event(
                       "[INFO]", counter['tot'], "Create",
                       openerp_object, name)
                   quality_action[access_id] = openerp_id
               except:
                   log_event(
                       "[ERROR] Error creating data, current record: ", data)

            if child_id:
                sock.execute(dbname, uid, pwd, 'quality.action', 'write',
                    child_id, {
                        'parent_id' : quality_action[access_id],
                        'origin': data['origin'], # TODO Non importa
                        })

except:
    log_event('[ERROR] Error importing data!')
    raise
store = status(openerp_object)
if jump_because_imported:
    quality_action = store.load()
else:
    store.store(quality_action)
log_event("Total %(tot)s (N: %(new)s, U: %(upd)s)" % counter)

# -----------------------------------------------------------------------------
#                               ACTION INTERVENT
# -----------------------------------------------------------------------------
only_create = False
jump_because_imported = True

file_input = os.path.expanduser('~/ETL/generalfood/Interventi.txt')
openerp_object = 'quality.action.intervent'
log_event("Start import %s" % openerp_object)
quality_action_intervent = {}
lines = csv.reader(open(file_input, 'rb'), delimiter=separator)
counter = {'tot': -1, 'new': 0, 'upd': 0}
max_col = 0

try:
    for line in lines:
        if jump_because_imported:
            break
        if counter['tot'] < 0:
            counter['tot'] += 1
            max_col = len(line)
            continue
        if len(line):
            if len(line) != max_col:
               log_event("[ERROR] %s Different cols not %s but now %s! Jumped:" % (
                   counter['tot'], max_col, len(line)))
               continue
            access_id = line[0]
            action_code = format_string(line[1])
            name = format_string(line[2])
            manager_code = format_string(line[3])
            deadline = format_date(line[4])

            action_id = quality_action.get(action_code, False)
            manager_id = 1

            # Start of importation:
            counter['tot'] += 1

            # test if record exists (basing on Ref. as code of Partner)
            item = sock.execute(dbname, uid, pwd, openerp_object , 'search', [
                ('access_id', '=', access_id)])
            data = {
                'name': name,
                'manager_id': manager_id,
                'deadline': deadline,
                'action_id': action_id,
                'access_id': access_id,
                }
            if item:  # already exist
               counter['upd'] += 1
               try:
                   if only_create:
                       log_event(
                           "[INFO]", counter['tot'], "Write",
                           openerp_object, " (jumped only_create clause: ",
                           access_id)
                   else:
                       item_mod = sock.execute(
                           dbname, uid, pwd, openerp_object, 'write',
                           item, data)
                       log_event(
                           "[INFO]", counter['tot'], "Write",
                           openerp_object, access_id)
                   quality_action_intervent[access_id] = item[0]
               except:
                   log_event("[ERROR] Modifing data, current record:", data)

            else:   # new
               counter['new'] += 1
               try:
                   openerp_id = sock.execute(
                       dbname, uid, pwd, openerp_object, 'create', data)
                   log_event(
                       "[INFO]", counter['tot'], "Create",
                       openerp_object, access_id)
                   quality_action_intervent[access_id] = openerp_id
               except:
                   log_event(
                       "[ERROR] Error creating data, current record: ", data)
except:
    log_event('[ERROR] Error importing data!')
    raise
store = status(openerp_object)
if jump_because_imported:
    quality_action_intervent = store.load()
else:
    store.store(quality_action_intervent)
log_event("Total %(tot)s (N: %(new)s, U: %(upd)s)" % counter)

# -----------------------------------------------------------------------------
#                               ACCEPTATION
# -----------------------------------------------------------------------------
only_create = False
jump_because_imported = False

file_input = os.path.expanduser('~/ETL/generalfood/Accettazioni.txt')
openerp_object = 'quality.acceptation'
log_event("Start import %s" % openerp_object)
quality_acceptation = {}
lines = csv.reader(open(file_input, 'rb'), delimiter=separator)
counter = {'tot': -1, 'new': 0, 'upd': 0}
max_col = 0

try:
    for line in lines:
        if jump_because_imported:
            break
        if counter['tot'] < 0:
            counter['tot'] += 1
            max_col = len(line)
            continue

        if len(line):
            if len(line) != max_col:
               log_event("[ERROR] %s Different cols not %s but now %s! Jumped:" % (
                   counter['tot'], max_col, len(line)))
               continue
            counter['tot'] += 1

            access_id = line[0]
            name = format_string(line[1])
            date = format_date(line[2])
            partner_code = format_string(line[3])
            origin = format_string(line[5])
            note = format_string(line[6])
            cancel = format_boolean(line[11])

            if not date:
                date = data.get('date', default_error_data)

            ref = "ACPT%05d" % (int(name or '0'))
            if partner_code:
                partner_id = get_or_create_partner(partner_code, 'supplier', False,
                    res_partner_customer, res_partner_supplier)
            else:
                partner_id = False

            if not partner_id:
               log_event("[WARN] Partner not found in %s" % (ref))


            # test if record exists (basing on Ref. as code of Partner)
            item = sock.execute(dbname, uid, pwd, openerp_object , 'search', [
                ('access_id', '=', access_id)])
            data = {
                'ref': ref,
                'date': date,
                'origin': origin,
                'partner_id': partner_id,
                'note': note,
                'cancel': cancel,
                'access_id': access_id,
            }
            if item:  # already exist
               counter['upd'] += 1
               try:
                   if only_create:
                       log_event(
                           "[INFO]", counter['tot'], "Write",
                           openerp_object, " (jumped only_create clause: ",
                           name)
                   else:
                       item_mod = sock.execute(
                           dbname, uid, pwd, openerp_object, 'write',
                           item, data)
                       log_event(
                           "[INFO]", counter['tot'], "Write",
                           openerp_object, name)
                   quality_acceptation[access_id] = item[0]
               except:
                   log_event("[ERROR] Modifing data, current record:", data)

            else:   # new
               counter['new'] += 1
               try:
                   openerp_id = sock.execute(
                       dbname, uid, pwd, openerp_object, 'create', data)
                   log_event(
                       "[INFO]", counter['tot'], "Create",
                       openerp_object, name)
                   quality_acceptation[access_id] = openerp_id
               except:
                   log_event(
                       "[ERROR] Error creating data, current record: ", data)
except:
    log_event('[ERROR] Error importing data!')
    raise
store = status(openerp_object)
if jump_because_imported:
    quality_acceptation = store.load()
else:
    store.store(quality_acceptation)
log_event("Total %(tot)s (N: %(new)s, U: %(upd)s)" % counter)

# -----------------------------------------------------------------------------
#                            ACCEPTATION DETAILS
# -----------------------------------------------------------------------------
only_create = False
jump_because_imported = False

file_input = os.path.expanduser('~/ETL/generalfood/Dettagli.txt')
openerp_object = 'quality.acceptation.line'
log_event("Start import %s" % openerp_object)
quality_acceptation_line = {}
lines = csv.reader(open(file_input, 'rb'), delimiter=separator)
counter = {'tot': -1, 'new': 0, 'upd': 0}
max_col = 0

try:
    for line in lines:
        if jump_because_imported:
            break
        if counter['tot'] < 0:
            counter['tot'] += 1
            max_col = len(line)
            continue
        if len(line):
            if len(line) != max_col:
               log_event("[ERROR] Different col not %s but now %s! Jumped:" % (
                   max_col, len(line)))
               continue

            counter['tot'] += 1
            # Read line
            access_id = line[0]
            acceptation_code = format_string(line[1])
            lot_code = format_string(line[2])
            conformed_code = format_string(line[3])
            qty_arrived = format_currency(line[4])
            qty_expected = format_currency(line[5])
            temp = format_boolean(line[6])       # Motivo
            label = format_boolean(line[7])      # Etichetta
            package = format_boolean(line[8])    # Stato
            #visual = format_boolean(line[9])     # Visivo
            expired = format_boolean(line[10])   # Scadenza
            motivation = format_string(line[11])
            qty = format_boolean(line[12])        # Quantitativo

            quality = False # TODO esiste sul file da importare??
            lot_id = False

            if not lot_code or lot_code == '0':
                log_event("[ERROR] Lot empty, jumped:", acceptation_code)
                continue

            lot_id = stock_production_lot.get(lot_code, False)
            if not lot_id:
                log_event("[ERROR] Lot not found, temp created:", lot_code)
                # Create lot (after will be updated from syncro with MySQL)
                lot_id = sock.execute(dbname, uid, pwd, 'stock.production.lot',
                    'create', {
                        'name': lot_code,
                        'product_id': default_product_id,
                        'date': datetime.now().strftime("%Y-%m-%d"),
                        'default_supplier_id': False
                        })

            # test if record exists (basing on Ref. as code of Partner)
            item = sock.execute(dbname, uid, pwd, openerp_object , 'search', [
                ('access_id', '=', access_id)])

            if conformed_code and conformed_code != '0':
                conformed_id = quality_conformed.get('conformed_code', False)

                if not conformed_id:
                    conformed_ids = sock.execute(dbname, uid, pwd,
                        'quality.conformed', 'search', [
                            ('access_id', '=', conformed_code)])
                    if conformed_ids:
                        conformed_id = conformed_ids[0]
                    else:
                        log_event("[WARNING] Conformed_id not found, not write: %s" % counter['tot'])
            else:
                conformed_id = False #quality_conformed.get(conformed_code, False)

            acceptation_id = quality_acceptation.get(acceptation_code, False)
            if not acceptation_id:
                log_event("[ERROR] %s. No parent form: %s" % (
                    counter['tot'], acceptation_code))
                continue

            data = {
                'acceptation_id': acceptation_id,
                'lot_id': lot_id,
                'qty_arrived': qty_arrived,
                'qty_expected': qty_expected,
                # Motivi check:
                'qty': qty,
                'temp': temp,
                'label': label,
                'package': package,
                'expired': expired,

                #'qty_package': qty_package,
                'conformed_id': conformed_id,
                'motivation': motivation,
                'access_id': access_id,
            }

            if item:  # already exist
               counter['upd'] += 1
               try:
                   if only_create:
                       log_event(
                           "[INFO]", counter['tot'], "Write",
                           openerp_object, " (jumped only_create clause: ")
                   else:
                       item_mod = sock.execute(
                           dbname, uid, pwd, openerp_object, 'write',
                           item, data)
                       log_event(
                           "[INFO]", counter['tot'], "Write", openerp_object)
                   quality_acceptation_line[access_id] = item[0]
               except:
                   log_event("[ERROR] Modifing data, current record:", data)
            else:   # new
               counter['new'] += 1
               try:
                   openerp_id = sock.execute(
                       dbname, uid, pwd, openerp_object, 'create', data)
                   log_event(
                       "[INFO]", counter['tot'], "Create", openerp_object)
                   quality_acceptation_line[access_id] = openerp_id
               except:
                   log_event(
                       "[ERROR] Error creating data, current record: ", data)
            # Aggiorno il valore per il ritorno alla scheda accettazione
            if conformed_id:
                sock.execute(dbname, uid, pwd, 'quality.conformed', 'write',
                    conformed_id, {
                        'acceptation_id' : acceptation_id, # Padre della riga
                        'origin': 'acceptation',
                        })
except:
    log_event('[ERROR] Error importing data!')
    raise
store = status(openerp_object)
if jump_because_imported:
    quality_acceptation_line = store.load()
else:
    store.store(quality_acceptation_line)

# -----------------------------------------------------------------------------
#                                  Trigger events:
# -----------------------------------------------------------------------------
# ------------
# ACCEPTATION:
# ------------
# TODO

# -------
# CLAIMS:
# -------
# Claim (bozza > opened)
openerp_object = 'quality.claim'

domain = [('state','=','draft')]
field_list = ('id',)
log_event('Start trigger WF Claim (bozza > open)')
item_ids = sock.execute(dbname, uid, pwd, openerp_object, 'search', domain)
for item in sock.execute(dbname, uid, pwd, openerp_object, 'read', item_ids, field_list):
    try:
        item_id = item['id']
        sock.exec_workflow(dbname, uid, pwd, openerp_object,
            'trigger_claim_draft_opened', item_id)
        log_event('[INFO] bozza > opened, ID: %s' % item_id)
    except:
        log_event('[ERROR] Impossibile bozza > opened, ID: %s' % item_id)
log_event('End trigger WF Claim (bozza > open) record %s' % len(item_ids))

# Claim (opened > nc > done > close > saw )
domain = [('state', '=', 'opened'), ('need_accredit', '=', True)]
field_list = ('id')
log_event('Start trigger WF Claim (opened > nc > done > close > saw)')
item_ids = sock.execute(dbname, uid, pwd, openerp_object, 'search', domain)
for item in sock.execute(dbname, uid, pwd, openerp_object, 'read', item_ids, field_list):
    try:
        item_id = item['id']
        sock.exec_workflow(dbname, uid, pwd, openerp_object,
            'trigger_claim_opened_nc', item_id)
        sock.exec_workflow(dbname, uid, pwd, openerp_object,
            'trigger_claim_nc_done', item_id)
        sock.exec_workflow(dbname, uid, pwd, openerp_object,
            'trigger_claim_done_closed', item_id)
        sock.exec_workflow(dbname, uid, pwd, openerp_object,
            'trigger_claim_closed_saw', item_id)
        log_event('[INFO] opened > nc > done > close > saw, ID: %s' % item_id)
    except:
        log_event('[ERROR] Impossibile opened > nc > done > close > saw, ID: %s' % item_id)
log_event('End trigger WF Claim (opened > nc > done > close > saw) record %s' % len(item_ids))

# Claim (opened > closed > saw)
domain = [('state', '=', 'opened')]
field_list = ('id')
log_event('Start trigger WF Claim (opened > closed > saw)')
item_ids = sock.execute(dbname, uid, pwd, openerp_object, 'search', domain)
for item in sock.execute(dbname, uid, pwd, openerp_object, 'read', item_ids, field_list):
    try:
        item_id = item['id']
        sock.exec_workflow(dbname, uid, pwd, openerp_object,
            'trigger_claim_opened_closed', item_id)
        sock.exec_workflow(dbname, uid, pwd, openerp_object,
            'trigger_claim_closed_saw', item_id)
        log_event('[INFO] opened > closed > saw, ID: %s' % item_id)
    except:
        log_event('[ERROR] Impossibile opened > closed > saw, ID: %s' % item_id)
log_event('End trigger WF Claim (opened > closed > saw) record %s' % len(item_ids))

# -------
# Action:
# -------
# Action (draft > opened)
openerp_object = 'quality.action'

domain = [('state','=','draft')]
field_list = ('id',)
log_event('Start trigger WF Action (draft > opened)')
item_ids = sock.execute(dbname, uid, pwd, openerp_object, 'search', domain)
for item in sock.execute(dbname, uid, pwd, openerp_object, 'read', item_ids, field_list):
    try:
        item_id = item['id']
        sock.exec_workflow(dbname, uid, pwd, openerp_object,
            'trigger_action_draft_opened', item_id)
        log_event('[INFO] bozza > opened, ID: %s' % item_id)
    except:
        log_event('[ERROR] Impossibile bozza > opened, ID: %s' % item_id)
log_event('End trigger WF Claim (bozza > opened) record %s' % len(item_ids))

# Action (opened > closed > saw) > quelle con la data di chiusura
domain = [('state','=','opened'),('closed_date','!=',False)]
field_list = ('id',)
log_event('Start trigger WF Action (opened > closed > saw)')
item_ids = sock.execute(dbname, uid, pwd, openerp_object, 'search', domain)
for item in sock.execute(dbname, uid, pwd, openerp_object, 'read', item_ids, field_list):
    try:
        item_id = item['id']
        sock.exec_workflow(dbname, uid, pwd, openerp_object,
            'trigger_action_opened_closed', item_id)
        sock.exec_workflow(dbname, uid, pwd, openerp_object,
            'trigger_action_closed_saw', item_id)
        log_event('[INFO] opened > closed > saw, ID: %s' % item_id)
    except:
        log_event('[ERROR] Impossibile opened > closed > saw, ID: %s' % item_id)
log_event('End trigger WF Claim (opened > closed > saw) record %s' % len(item_ids))

# ----------
# Conformed:
# ----------
# Conformed (draft > opened > closed > saw) >> non cancellati
openerp_object = 'quality.conformed'

domain = [('state','=','draft'), ('cancel', '=', False)]
field_list = ('id', )
log_event('Start trigger WF Conformed (draft > opened > closed > saw)')
item_ids = sock.execute(dbname, uid, pwd, openerp_object, 'search', domain)
for item in sock.execute(dbname, uid, pwd, openerp_object, 'read', item_ids, field_list):
    try:
        item_id = item['id']
        sock.exec_workflow(dbname, uid, pwd, openerp_object,
            'trigger_conformed_draft_opened', item_id)
        sock.exec_workflow(dbname, uid, pwd, openerp_object,
            'trigger_conformed_opened_closed', item_id)
        sock.exec_workflow(dbname, uid, pwd, openerp_object,
            'trigger_conformed_closed_saw', item_id)
        log_event('[INFO] draft > opened > closed > saw, ID: %s' % item_id)
    except:
        log_event('[ERROR] Impossibile draft > opened > closed > saw, ID: %s' % item_id)
log_event('End trigger WF Claim (draft > opened > closed > saw) record %s' % len(item_ids))

domain = [('state','=','draft'), ('cancel', '=', True)]
field_list = ('id', )
log_event('Start trigger WF Conformed (draft > opened > cancel)')
item_ids = sock.execute(dbname, uid, pwd, openerp_object, 'search', domain)
for item in sock.execute(dbname, uid, pwd, openerp_object, 'read', item_ids, field_list):
    try:
        item_id = item['id']
        sock.exec_workflow(dbname, uid, pwd, openerp_object,
            'trigger_conformed_draft_opened', item_id)
        sock.exec_workflow(dbname, uid, pwd, openerp_object,
            'trigger_conformed_opened_cancel', item_id)
        log_event('[INFO] draft > opened > closed > saw, ID: %s' % item_id)
    except:
        log_event('[ERROR] Impossibile draft > opened > closed > saw, ID: %s' % item_id)
log_event('End trigger WF Claim (draft > opened > closed > saw) record %s' % len(item_ids))

# ---------
# Sampling:
# ---------
openerp_object = 'quality.sampling'


comment = "Sampling (draft > opened > passed) >> passati"
log_event('Start trigger WF %s' % comment)
for item_id in sample_passed:
    try:
        sock.exec_workflow(dbname, uid, pwd, openerp_object,
            'trigger_sampling_draft_opened', item_id)
    except:
        log_event('[WARNING] Impossibile %s, ID: %s' % (comment, item_id))

    try:
        sock.exec_workflow(dbname, uid, pwd, openerp_object,
            'trigger_sampling_opened_passed', item_id)
        log_event('[INFO] %s, ID: %s' % (comment, item_id))
    except:
        log_event('[ERROR] Impossibile %s, ID: %s' % (comment, item_id))

log_event('End trigger WF %s record %s' % (comment, len(item_ids)))

comment = "Sampling (draft > opened > notpassed) >> not passati"
log_event('Start trigger WF %s' % comment)
for item_id in sample_notpassed:
    try:
        sock.exec_workflow(dbname, uid, pwd, openerp_object,
            'trigger_sampling_draft_opened', item_id)
    except:
        log_event('[WARNING] Impossibile aprire il campionamento %s, ID: %s' % (comment, item_id))

    try:
        sock.exec_workflow(dbname, uid, pwd, openerp_object,
            'trigger_sampling_opened_notpassed', item_id)
        log_event('[INFO] %s, ID: %s' % (comment, item_id))
    except:
        log_event('[ERROR] Impossibile mettere non passato %s, ID: %s' % (comment, item_id))
log_event('End trigger WF %s record %s' % (comment, len(item_ids)))

comment = "Sampling (draft > opened) >> aperti"
domain = [('state','=','draft')]
field_list = ('id', )
log_event('Start trigger WF %s' % comment)
item_ids = sock.execute(dbname, uid, pwd, openerp_object, 'search', domain)
for item in sock.execute(dbname, uid, pwd, openerp_object, 'read', item_ids, field_list):
    try:
        item_id = item['id']
        sock.exec_workflow(dbname, uid, pwd, openerp_object,
            'trigger_sampling_draft_opened', item_id)
        log_event('[INFO] %s, ID: %s' % (comment, item_id))
    except:
        log_event('[ERROR] Impossibile %s, ID: %s' % (comment, item_id))
log_event('End trigger WF %s record %s' % (comment, len(item_ids)))


log_event("PROMEMORIA: Aggiornare i contatori nel programma, valori prossimi: ")   # TODO mettere il counter total
log_event("End of importation")
