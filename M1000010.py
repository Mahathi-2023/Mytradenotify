import json
import os
import re
from pathlib import Path

from openpyxl import Workbook, load_workbook
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
ACCOUNTS_FILE = BASE_DIR / 'M1000010_accounts.xlsx'
LEGACY_ACCOUNTS_FILE = BASE_DIR / 'M1000010_accounts.json'
GMAIL_PATTERN = re.compile(r'^[^\s@]+@gmail\.com$', re.IGNORECASE)
ACCOUNT_HEADERS = [
    'Email',
    'First Name',
    'Last Name',
    'Role',
    'Active',
    'Password Hash',
]


def load_environment_file():
    env_file = BASE_DIR / '.env'
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = [part.strip() for part in line.split('=', 1)]
        if key and not os.getenv(key):
            os.environ[key] = value


def load_accounts():
    accounts = {}

    if ACCOUNTS_FILE.exists():
        try:
            workbook = load_workbook(ACCOUNTS_FILE, read_only=True)
            sheet = workbook.active
            headers = [str(cell.value).strip() if cell.value is not None else '' for cell in sheet[1]]
            if headers:
                for values in sheet.iter_rows(min_row=2, values_only=True):
                    row = dict(zip(headers, values))
                    email = normalize_email(row.get('Email'))
                    if not email:
                        continue
                    accounts[email] = {
                        'email': email,
                        'first_name': str(row.get('First Name') or ''),
                        'last_name': str(row.get('Last Name') or ''),
                        'role': str(row.get('Role') or 'user').lower(),
                        'active': str(row.get('Active') or 'True').lower() in {'true', '1', 'yes'},
                        'password_hash': str(row.get('Password Hash') or ''),
                    }
            workbook.close()
            return accounts
        except Exception:
            return {}

    if LEGACY_ACCOUNTS_FILE.exists():
        try:
            accounts = json.loads(LEGACY_ACCOUNTS_FILE.read_text(encoding='utf-8'))
            if isinstance(accounts, dict):
                save_accounts(accounts)
                return accounts
        except Exception:
            pass

    return {}


def save_accounts(accounts):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Accounts'

    for column, header in enumerate(ACCOUNT_HEADERS, start=1):
        cell = sheet.cell(row=1, column=column, value=header)
        cell.font = cell.font.copy(bold=True)

    for row_number, (email, account) in enumerate(sorted(accounts.items()), start=2):
        values = [
            normalize_email(account.get('email') or email),
            str(account.get('first_name') or ''),
            str(account.get('last_name') or ''),
            str(account.get('role') or 'user'),
            'True' if account.get('active', True) else 'False',
            str(account.get('password_hash') or ''),
        ]
        for column, value in enumerate(values, start=1):
            sheet.cell(row=row_number, column=column, value=value)

    for column_number, header in enumerate(ACCOUNT_HEADERS, start=1):
        width = max(len(header) + 2, 12)
        for row in sheet.iter_rows(min_col=column_number, max_col=column_number):
            value = row[0].value
            width = max(width, min(len(str(value or '')), 80))
        sheet.column_dimensions[chr(64 + column_number)].width = width

    workbook.save(ACCOUNTS_FILE)


def normalize_email(email):
    return str(email or '').strip().lower()


def ensure_admin():
    load_environment_file()
    accounts = load_accounts()
    email = normalize_email(os.getenv('MYTRADE_DASHBOARD_ADMIN_EMAIL', ''))
    password = os.getenv('MYTRADE_DASHBOARD_ADMIN_PASSWORD', '')

    if not email or not GMAIL_PATTERN.match(email):
        return accounts

    existing = accounts.get(email)
    if existing is None:
        existing = {
            'first_name': os.getenv('MYTRADE_DASHBOARD_ADMIN_FIRST_NAME', 'Admin'),
            'last_name': os.getenv('MYTRADE_DASHBOARD_ADMIN_LAST_NAME', ''),
            'email': email,
            'role': 'admin',
        }

    existing['first_name'] = existing.get('first_name') or os.getenv('MYTRADE_DASHBOARD_ADMIN_FIRST_NAME', 'Admin')
    existing['last_name'] = existing.get('last_name') or os.getenv('MYTRADE_DASHBOARD_ADMIN_LAST_NAME', '')
    existing['email'] = email
    existing['role'] = 'admin'
    existing['active'] = True

    if password:
        existing['password_hash'] = generate_password_hash(password)

    accounts[email] = existing
    save_accounts(accounts)
    return accounts


def validate_registration(first_name, last_name, email, password):
    first_name = str(first_name or '').strip()
    last_name = str(last_name or '').strip()
    email = normalize_email(email)

    if not first_name:
        return 'First name is required.'
    if not email:
        return 'Gmail address is required.'
    if not GMAIL_PATTERN.match(email):
        return 'Enter a valid Gmail address.'
    if len(password or '') < 8:
        return 'Password must be at least 8 characters.'

    accounts = load_accounts()
    if email in accounts:
        return 'An account already exists for this Gmail address.'
    return None


def register_user(first_name, last_name, email, password):
    error = validate_registration(first_name, last_name, email, password)
    if error:
        return None, error

    email = normalize_email(email)
    accounts = load_accounts()
    accounts[email] = {
        'first_name': str(first_name).strip(),
        'last_name': str(last_name).strip(),
        'email': email,
        'password_hash': generate_password_hash(password),
        'role': 'user',
        'active': True,
    }
    save_accounts(accounts)
    return accounts[email], None


def authenticate(email, password):
    ensure_admin()
    email = normalize_email(email)
    account = load_accounts().get(email)
    if not account or not account.get('active'):
        return None
    if not check_password_hash(account.get('password_hash', ''), password or ''):
        return None
    return account


def set_account_role(email, role):
    email = normalize_email(email)
    if role not in {'admin', 'user'}:
        return False
    accounts = load_accounts()
    if email not in accounts:
        return False
    accounts[email]['role'] = role
    save_accounts(accounts)
    return True


def set_account_active(email, active):
    email = normalize_email(email)
    accounts = load_accounts()
    if email not in accounts:
        return False
    if accounts[email].get('role') == 'admin':
        return False
    accounts[email]['active'] = bool(active)
    save_accounts(accounts)
    return True


def delete_account(email):
    email = normalize_email(email)
    accounts = load_accounts()
    account = accounts.get(email)
    if not account or account.get('role') == 'admin':
        return False
    accounts.pop(email, None)
    save_accounts(accounts)
    return True
