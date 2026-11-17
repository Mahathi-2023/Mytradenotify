import contextlib
import io
import os
import sys
from calendar import monthrange
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

import yfinance as yf

# Read-only access to the text files.
# Updates to emails.txt and stocks.txt must happen through M1000004.py and M1000005.py.
from M1000002 import get_stock_data, save_stock_csv
from M1000003 import send_stock_report_email

BASE_DIR = Path(__file__).resolve().parent
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


def read_list_from_txt(file_name):
    file_path = BASE_DIR / file_name
    if not file_path.exists():
        return []

    values = []
    with file_path.open('r', encoding='utf-8') as file:
        for line in file:
            value = line.strip()
            if value and not value.startswith('#'):
                values.append(value)
    return values


def get_receiver_emails():
    return read_list_from_txt('emails.txt') or ['umamaheshwar.chevuru@gmail.com']


def get_stock_symbols():
    return read_list_from_txt('stocks.txt')


@lru_cache(maxsize=256)
def get_instrument_type(stock_symbol):
    symbol = str(stock_symbol).strip().upper()
    if not symbol:
        return 'Stock'

    if symbol.endswith('=F'):
        return 'F&O'

    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            info = yf.Ticker(symbol).info or {}
        quote_type = str(info.get('quoteType', '') or '').upper()

        if quote_type in {'ETF', 'ETP'}:
            return 'ETF'
        if quote_type in {'FUTURE', 'FUTURES'}:
            return 'F&O'
        if quote_type in {'EQUITY', 'STOCK'}:
            return 'Stock'
    except Exception:
        pass

    return 'Stock'


def build_summary_row(stock_symbol, df):
    if df.empty:
        return None

    summary = df.iloc[[0, -1]].copy()
    start_open = float(summary.iloc[0]['Open'])
    end_close = float(summary.iloc[-1]['Close'])
    difference = end_close - start_open
    percentage_change = (difference / start_open) * 100 if start_open else 0.0

    if difference > 0:
        trend = 'Profit'
    elif difference < 0:
        trend = 'Loss'
    else:
        trend = 'No Change'

    return {
        'Stock': stock_symbol,
        'Type': get_instrument_type(stock_symbol),
        'Start Date': str(summary.iloc[0]['Date']),
        'Start Price': round(start_open, 2),
        'End Date': str(summary.iloc[-1]['Date']),
        'End Price': round(end_close, 2),
        'Difference': round(difference, 2),
        'Trend': trend,
        'Percentage Change': f'{percentage_change:+.2f}%',
    }


def sort_percentage_rows(rows, for_profit=True):
    def numeric_value(row):
        value = float(row['Percentage Change'].replace('%', ''))
        return value if for_profit else abs(value)

    return sorted(rows, key=numeric_value, reverse=True)


def is_last_day_of_month(current_date):
    return current_date.day == monthrange(current_date.year, current_date.month)[1]


def collect_rows_for_period(stock_symbols, start_date, end_date):
    rows = []
    for symbol in stock_symbols:
        debug_log(f"Fetching data for symbol: {symbol}")
        df = get_stock_data(stock_symbol=symbol, start_date=start_date, end_date=end_date)

        if df.empty:
            debug_log(f"No market data returned for {symbol}")
            continue

        summary_row = build_summary_row(symbol, df)
        if summary_row is not None:
            rows.append(summary_row)
            debug_log(f"Row prepared for {symbol}: {summary_row}")

    return rows


def build_report_files(rows, file_prefix=''):
    profit_rows = sort_percentage_rows([row for row in rows if row['Trend'] == 'Profit'], for_profit=True)
    loss_rows = sort_percentage_rows([row for row in rows if row['Trend'] == 'Loss'], for_profit=False)
    debug_log(f"Profit rows: {len(profit_rows)} | Loss rows: {len(loss_rows)}")

    report_files = []
    prefix = f'{file_prefix}_' if file_prefix else ''

    if profit_rows:
        profit_file = save_stock_csv(profit_rows, f'{prefix}profit_report.csv')
        report_files.append(profit_file)
        debug_log(f"Saved profit csv: {profit_file}")

    if loss_rows:
        loss_file = save_stock_csv(loss_rows, f'{prefix}loss_report.csv')
        report_files.append(loss_file)
        debug_log(f"Saved loss csv: {loss_file}")

    return report_files


def normalize_report_type(report_type):
    normalized = str(report_type).strip().lower()
    aliases = {
        'day': 'day',
        'daily': 'day',
        'month': 'month',
        'monthly': 'month',
    }
    if normalized not in aliases:
        raise ValueError("report_type must be 'day'/'daily' or 'month'/'monthly'")
    return aliases[normalized]


def run_report(report_type='day', stock_symbols=None):
    normalized_type = normalize_report_type(report_type)
    if stock_symbols is None:
        stock_symbols = get_stock_symbols()

    receiver_emails = get_receiver_emails() or ['umamaheshwar.chevuru@gmail.com']
    debug_log(f"Preparing {normalized_type} report for {len(stock_symbols)} symbols to {receiver_emails}")

    today = date.today()

    if normalized_type == 'day':
        end_date = today
        start_date = today
        rows = collect_rows_for_period(stock_symbols, start_date, end_date)
        report_files = build_report_files(rows, file_prefix='daily')

        if is_last_day_of_month(today):
            month_start = date(today.year, today.month, 1)
            month_rows = collect_rows_for_period(stock_symbols, month_start, today)
            month_files = build_report_files(month_rows, file_prefix='monthly')
            if report_files or month_files:
                combined_files = report_files + month_files
                debug_log(f"Sending combined daily and monthly report email with attachments: {combined_files}")
                send_stock_report_email(
                    file_paths=combined_files,
                    receiver_email=receiver_emails,
                    subject='Daily and Monthly Profit and Loss Stocks Report'
                )
                print(f'Combined daily and monthly profit and loss report sent to {receiver_emails}')
                return

        if report_files:
            debug_log(f"Sending report email with attachments: {report_files}")
            send_stock_report_email(
                file_paths=report_files,
                receiver_email=receiver_emails,
                subject='Daily Profit and Loss Stocks Report'
            )
            print(f'Daily profit and loss report sent to {receiver_emails}')
        else:
            print('No profit or loss rows found for the selected daily period.')
        return

    if normalized_type == 'month':
        last_day = monthrange(today.year, today.month)[1]
        if today.day != last_day:
            print(f"Skipping monthly report for {today}: not the end of the month ({today.day}/{last_day}).")
            return

        end_date = today
        start_date = date(today.year, today.month, 1)
        debug_log(f"Date range: {start_date} -> {end_date}")

        rows = collect_rows_for_period(stock_symbols, start_date, end_date)
        report_files = build_report_files(rows, file_prefix='monthly')

        if report_files:
            debug_log(f"Sending report email with attachments: {report_files}")
            send_stock_report_email(
                file_paths=report_files,
                receiver_email=receiver_emails,
                subject='Monthly Profit and Loss Stocks Report'
            )
            print(f'Monthly profit and loss report sent to {receiver_emails}')
        else:
            print('No profit or loss rows found for the selected monthly period.')
        return

    raise ValueError("report_type must be 'day'/'daily' or 'month'/'monthly'")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == 'update-emails':
            from M1000004 import update_email_list
            update_email_list()
            raise SystemExit(0)
        if command == 'update-stocks':
            from M1000005 import update_stock_list
            update_stock_list(refresh_live=True)
            raise SystemExit(0)
        if command in {'day', 'daily'}:
            run_report(report_type='day')
            raise SystemExit(0)
        if command in {'month', 'monthly'}:
            run_report(report_type='month')
            raise SystemExit(0)

    run_report(report_type='day')
