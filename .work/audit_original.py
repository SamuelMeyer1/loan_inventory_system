"""Read-only audit of source; all database changes use fresh temporary databases."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import ast
import json
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from unittest.mock import patch

import backend.database as database
import backend.services.loans as loans
import backend.services.inventory as inventory
import backend.services.notifications as notifications

RESULTS = []
START = date.today().isoformat()
END = (date.today() + timedelta(days=7)).isoformat()

def record(name, result):
    RESULTS.append({'check': name, 'result': result})
    print(json.dumps(RESULTS[-1], ensure_ascii=True))

def setup(folder):
    database.DATA_DIR = Path(folder)
    database.DATABASE_PATH = Path(folder) / 'audit.db'
    database.initialize_database()
    with database.connect() as db:
        db.execute("INSERT INTO users(user_id,name,active) VALUES('U1','Audit User',1)")
        for key in ('notify_new_job', 'notify_returned_loan', 'notify_low_stock', 'notify_empty_stock', 'smtp_enabled', 'teams_enabled'):
            db.execute('INSERT INTO system_settings(key,value) VALUES(?, ?)', (key, '0'))

def obj(identifier='T1', quantity=2):
    payload = dict(object_id=identifier, name='Audit Tool', category='Tools', location='A1', tornado_id='A', door_id='1', total_quantity=quantity, available_quantity=quantity, min_quantity=0)
    inventory.add_object(payload)
    return payload

def checkout(identifier='T1', **extra):
    payload = dict(user_id='U1', object_id=identifier, quantity=1, lending_date=START, due_time=END)
    payload.update(extra)
    return loans.checkout(payload)

def state(identifier='T1'):
    stock = database.row('SELECT total_quantity,available_quantity FROM objects WHERE object_id=?', (identifier,))
    stock['active_quantity'] = database.row("SELECT COALESCE(SUM(quantity),0) AS value FROM loans WHERE object_id=? AND status='active'", (identifier,))['value']
    return stock

def rejected(action):
    try:
        value = action()
        return {'accepted': value}
    except Exception as error:
        return {'exception': type(error).__name__, 'message': str(error)}

def scenario(name, action):
    with tempfile.TemporaryDirectory(prefix='loan_original_audit_') as folder:
        setup(folder)
        try:
            record(name, action())
        except Exception as error:
            record(name, {'audit_error': repr(error)})

def happy_path():
    obj()
    loan = checkout()
    during = state()
    loans.return_item({'identifier': str(loan['loan_id'])})
    return {'after_checkout': during, 'after_return': state(), 'duplicate_return': rejected(lambda: loans.return_item({'identifier': str(loan['loan_id'])}))}

def checkout_race():
    obj(quantity=1)
    barrier = threading.Barrier(2)
    validate = loans.validate_loan_period
    def rendezvous(*args, **kwargs):
        validate(*args, **kwargs)
        barrier.wait(timeout=3)
    with patch.object(loans, 'validate_loan_period', rendezvous):
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(lambda _: rejected(checkout), range(2)))
    return {'requests': results, 'stock': state()}

def return_race():
    obj(quantity=1)
    loan = checkout()
    barrier = threading.Barrier(2)
    normal_row = loans.row
    def delayed_lookup(query, params=()):
        result = normal_row(query, params)
        if "WHERE l.status = 'active'" in query:
            index = barrier.wait(timeout=3)
            if index == 0:
                time.sleep(.25)
        return result
    with patch.object(loans, 'row', delayed_lookup):
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(lambda _: rejected(lambda: loans.return_item({'identifier': str(loan['loan_id'])})), range(2)))
    return {'requests': results, 'stock': state()}

def numeric_object():
    obj('12345')
    loan = checkout('12345')
    return {'loan': loan, 'return_by_object_code': rejected(lambda: loans.return_item({'identifier': '12345'}))}

def ambiguous_object():
    obj()
    first = checkout()
    second = checkout()
    returned = loans.return_item({'identifier': 'T1'})
    return {'loans': [first, second], 'returned_without_selection': returned}

def timezone_dates():
    obj()
    saved = checkout(lending_date=START + 'T08:00:00+02:00', due_time=END + 'T16:00:00+02:00')
    return {'saved': saved, 'list_loans': rejected(loans.list_active_loans)}

def reversed_times():
    obj()
    return rejected(lambda: checkout(lending_date=START + 'T16:00:00', due_time=START + 'T08:00:00'))

def stock_edit():
    payload = obj(quantity=1)
    loan = checkout()
    inventory.update_object(payload)
    loans.return_item({'identifier': str(loan['loan_id'])})
    return state()

def request_fallback():
    obj()
    original_loan = checkout()
    request = loans.create_loan_request(dict(user_id='U1', object_id='T1', quantity=1, lending_date=START, due_time=END))
    loans.update_loan_request_status(dict(request_id=request['request_id'], status='returned'))
    return {'unrelated_loan': database.row('SELECT loan_id,status FROM loans WHERE loan_id=?', (original_loan['loan_id'],)), 'stock': state()}

def invalid_stock():
    obj(quantity=1)
    return {'excess': rejected(lambda: checkout(quantity=2)), 'negative': rejected(lambda: checkout(quantity=-1)), 'stock': state()}

def fractional_quantity():
    obj()
    saved = checkout(quantity=1.9)
    return {'response': saved, 'stored_quantity': database.row('SELECT quantity FROM loans WHERE loan_id=?', (saved['loan_id'],))}

def inactive_user():
    obj()
    with database.connect() as db:
        db.execute("UPDATE users SET active=0 WHERE user_id='U1'")
    return rejected(checkout)

def delete_requested_object():
    obj()
    loans.create_loan_request(dict(user_id='U1', object_id='T1', quantity=1, lending_date=START, due_time=END))
    return rejected(lambda: inventory.delete_object('T1'))

def secret_read():
    with database.connect() as db:
        db.execute("INSERT INTO system_settings(key,value) VALUES('smtp_password','AUDIT_SENTINEL')")
    return {'sentinel_exposed_by_get_system_settings': notifications.get_system_settings().get('smtp_password') == 'AUDIT_SENTINEL'}

for path in list((ROOT / 'backend').rglob('*.py')) + [ROOT / 'main.py']:
    ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
record('Python source parsing', 'PASS')

with patch.object(loans, 'notify_rule_recipients', side_effect=AssertionError('External notifications prohibited')), patch.object(loans, 'send_email', side_effect=AssertionError('External email prohibited')):
    for name, action in [
        ('Checkout + return + duplicate return', happy_path),
        ('Insufficient and negative quantity', invalid_stock),
        ('Inactive borrower', inactive_user),
        ('Concurrent checkout of last item', checkout_race),
        ('Concurrent return of same loan', return_race),
        ('Numeric object code return', numeric_object),
        ('Ambiguous object code return', ambiguous_object),
        ('ISO offset dates accepted then list crashes', timezone_dates),
        ('Return time before checkout on same day', reversed_times),
        ('Stock edit while loan active', stock_edit),
        ('Returning unfulfilled request returns unrelated loan', request_fallback),
        ('Fractional quantity', fractional_quantity),
        ('Delete object with outstanding request', delete_requested_object),
        ('Secret setting exposed in service/API response', secret_read),
    ]:
        scenario(name, action)

(ROOT / '.work' / 'audit_original_results.json').write_text(json.dumps(RESULTS, ensure_ascii=False, indent=2), encoding='utf-8')
