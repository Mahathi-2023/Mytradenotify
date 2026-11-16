import os
import sys
from pathlib import Path

# This file is the sole writer for emails.txt.
BASE_DIR = Path(__file__).resolve().parent
EMAILS_FILE = BASE_DIR / 'emails.txt'
SCRIPT_NAME = Path(__file__).stem
DEBUG_MODE = (
    __name__ == '__main__'
    and (
        '--debug' in sys.argv[1:]
        or f'--debug-{SCRIPT_NAME}' in sys.argv[1:]
        or str(os.getenv(f'{SCRIPT_NAME.upper()}_DEBUG', '')).lower() in {'1', 'true', 'yes', 'on'}
    )
)


def debug_log(message):
    if DEBUG_MODE:
        print(f'[{SCRIPT_NAME}][DEBUG] {message}')


def read_emails():
    if not EMAILS_FILE.exists():
        debug_log(f"Email file not found at {EMAILS_FILE}")
        return []

    emails = []
    with EMAILS_FILE.open('r', encoding='utf-8') as file:
        for line in file:
            value = line.strip()
            if value and not value.startswith('#'):
                emails.append(value)
    debug_log(f"Loaded {len(emails)} email(s): {emails}")
    return emails


def write_emails(emails):
    cleaned = []
    seen = set()
    for email in emails:
        value = str(email).strip()
        if not value or value.startswith('#'):
            continue
        if value.lower() not in seen:
            cleaned.append(value)
            seen.add(value.lower())

    debug_log(f"Writing email list to {EMAILS_FILE}: {cleaned}")
    with EMAILS_FILE.open('w', encoding='utf-8') as file:
        if cleaned:
            file.write('\n'.join(cleaned) + '\n')

    return cleaned


def update_email_list(new_emails=None):
    if new_emails is None:
        cli_values = []
        for arg in sys.argv[1:]:
            cli_values.extend(part.strip() for part in arg.split(',') if part.strip())
        if cli_values:
            new_emails = cli_values

    if new_emails is None:
        print('Current email list:')
        current = read_emails()
        if current:
            for email in current:
                print(f'- {email}')
        else:
            print('No emails found.')

        raw_input = input('Enter emails separated by commas (or press Enter to keep current): ').strip()
        if not raw_input:
            return current
        new_emails = [item.strip() for item in raw_input.split(',') if item.strip()]

    debug_log(f"Updating emails with provided values: {new_emails}")
    return write_emails(new_emails)


if __name__ == '__main__':
    updated = update_email_list()
    print(f"Email list updated in {EMAILS_FILE}")
    print(updated)
