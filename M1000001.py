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
# Updates to emails.txt and Stock_US.txt must happen through M1000004.py and M1000005.py.
from M1000002 import get_intraday_stock_data, get_stock_data, save_stock_csv
from M1000003 import send_alert_email, send_stock_report_email
from M1000007 import (
    build_alert_html,
    build_intraday_alert_html,
    detect_unusual_movement,
)

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


def get_stock_symbols(country='US'):
    file_name = 'Stock_IN.txt' if str(country).upper() == 'IN' else 'Stock_US.txt'
    return read_list_from_txt(file_name)


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


@lru_cache(maxsize=256)
def get_stock_name(stock_symbol):
    symbol = str(stock_symbol).strip().upper()
    if not symbol:
        return 'Unknown'

    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), contextlib.suppress(Exception):
            info = yf.Ticker(symbol).info or {}
        name = str(info.get('longName') or info.get('shortName') or '').strip()
        if name:
            return name
    except Exception:
        pass

    return symbol


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
        'Stock': get_stock_name(stock_symbol),
        'Type': get_instrument_type(stock_symbol),
        'Start Date': str(summary.iloc[0]['Date']),
        'Start Price': round(start_open, 2),
        'End Date': str(summary.iloc[-1]['Date']),
        'End Price': round(end_close, 2),
        'Difference': round(difference, 2),
        'Trend': trend,
        'Percentage Change': f'{percentage_change:+.2f}%',
    }


def get_latest_trading_date(stock_symbols=None):
    symbols = stock_symbols or get_stock_symbols()
    candidate_end = date.today()
    candidate_start = candidate_end - timedelta(days=14)

    for symbol in symbols:
        df = get_stock_data(stock_symbol=symbol, start_date=candidate_start, end_date=candidate_end)
        if df is not None and not df.empty:
            dates = sorted({str(value)[:10] for value in df['Date'].tolist()})
            if dates:
                parsed = date.fromisoformat(dates[-1])
                if parsed <= candidate_end:
                    return parsed

    latest = candidate_end
    while latest.weekday() >= 5:
        latest -= timedelta(days=1)
    return latest


def run_alert(stock_symbols=None, period='month', reference_date=None, send_no_activity_email=False):
    if stock_symbols is None:
        stock_symbols = get_stock_symbols()

    receiver_emails = get_receiver_emails() or ['umamaheshwar.chevuru@gmail.com']
    today = reference_date if isinstance(reference_date, date) else date.today()
    normalized_period = str(period).strip().lower()
    start_date = today if normalized_period == 'day' else today - timedelta(days=29)
    alerts = []

    for symbol in stock_symbols:
        df = get_stock_data(stock_symbol=symbol, start_date=start_date, end_date=today)
        if df is None or df.empty:
            continue

        alert = detect_unusual_movement(
            symbol,
            df,
            get_stock_name=get_stock_name,
            get_instrument_type=get_instrument_type,
        )
        if alert is not None:
            alerts.append(alert)

    if not alerts:
        period_text = 'today' if normalized_period == 'day' else 'the past month'
        print(f'No unusual stock movements detected for {period_text}.')
        if send_no_activity_email:
            date_range = str(today) if normalized_period == 'day' else 'past 30 days'
            send_alert_email(
                html=(
                    f"<html><body style=\"font-family:Arial,sans-serif;color:#172033\">"
                    f"<h2 style=\"text-align:center;color:#166534\">Unusual Stock Movement Alert</h2>"
                    f"<p style=\"margin:0 0 8px 0\">Report period: {date_range}</p>"
                    "<p>No unusual stock movements were detected in this period.</p>"
                    "</body></html>"
                ),
                receiver_email=receiver_emails,
                subject='Daily Unusual Stock Movement Alert',
            )
            print(f"No-activity unusual movement alert sent to {receiver_emails}")
            return True
        return False

    send_alert_email(
        html=build_alert_html(alerts, date_range=str(today) if normalized_period == 'day' else 'past 30 days'),
        receiver_email=receiver_emails,
        subject='ATTENTION: Daily Unusual Stock Movement Alert' if normalized_period == 'day' else 'ATTENTION: Unusual Stock Movement Alert'
    )
    print(f"Unusual stock movement alert sent to {receiver_emails}")
    return True


INTRADAY_ALERT_PERCENT = 5.0


def detect_intraday_alert(stock_symbol, df):
    if df is None or df.empty:
        return None

    latest_row = df.iloc[-1]
    prior_rows = df.iloc[:-1]
    if prior_rows.empty:
        return None

    latest_close = float(latest_row['Close'])
    previous_close = float(prior_rows.iloc[-1]['Close'])
    if not previous_close:
        return None

    interval_change = ((latest_close - previous_close) / previous_close) * 100
    if abs(interval_change) < INTRADAY_ALERT_PERCENT:
        return None

    movement = 'Sharp Profit' if interval_change > 0 else 'Sharp Loss'
    return {
        'Stock': get_stock_name(stock_symbol),
        'Symbol': str(stock_symbol).strip().upper(),
        'Movement': movement,
        'Interval Change': round(interval_change, 2),
        'Timestamp': str(latest_row['Datetime']),
        'Previous Close': round(previous_close, 2),
        'Latest Close': round(latest_close, 2),
    }


def run_intraday_alerts(stock_symbols=None):
    if stock_symbols is None:
        stock_symbols = get_stock_symbols()

    receiver_emails = get_receiver_emails() or ['umamaheshwar.chevuru@gmail.com']
    alerts = []

    for symbol in stock_symbols:
        df = get_intraday_stock_data(symbol, interval='5m')
        alert = detect_intraday_alert(symbol, df)
        if alert is not None:
            alerts.append(alert)

    if not alerts:
        return False

    send_alert_email(
        html=build_intraday_alert_html(alerts),
        receiver_email=receiver_emails,
        subject='URGENT: Live Unusual Stock Movement Alert'
    )
    return True


def monitor_intraday_alerts(stock_symbols=None, interval_seconds=300):
    import time

    if stock_symbols is None:
        stock_symbols = get_stock_symbols()

    print(f"Starting 5-minute stock monitoring for {len(stock_symbols)} stocks. Press Ctrl+C to stop.")
    sent_alerts = set()

    try:
        while True:
            receiver_emails = get_receiver_emails() or ['umamaheshwar.chevuru@gmail.com']
            alerts = []

            for symbol in stock_symbols:
                df = get_intraday_stock_data(symbol, interval='5m')
                alert = detect_intraday_alert(symbol, df)
                if alert is None:
                    continue

                alert_key = (alert['Symbol'], alert['Movement'], alert['Timestamp'])
                if alert_key not in sent_alerts:
                    sent_alerts.add(alert_key)
                    alerts.append(alert)

            if alerts:
                send_alert_email(
                    html=build_intraday_alert_html(alerts),
                    receiver_email=receiver_emails,
                    subject='URGENT: Live Unusual Stock Movement Alert'
                )

            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print('Intraday stock monitoring stopped.')


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
            if start_date == end_date:
                summary_row['DT'] = start_date.strftime('%Y-%m-%d')
            else:
                summary_row['DT'] = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
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


def run_report(report_type='day', stock_symbols=None, force_month=False):
    normalized_type = normalize_report_type(report_type)
    if stock_symbols is None:
        stock_symbols = get_stock_symbols()

    receiver_emails = get_receiver_emails() or ['umamaheshwar.chevuru@gmail.com']
    debug_log(f"Preparing {normalized_type} report for {len(stock_symbols)} symbols to {receiver_emails}")

    today = date.today()

    if normalized_type == 'day':
        report_date = get_latest_trading_date(stock_symbols)
        end_date = report_date
        start_date = report_date
        rows = collect_rows_for_period(stock_symbols, start_date, end_date)
        report_files = build_report_files(rows, file_prefix='daily')

        # Daily report includes the same 30-day unusual-movement scan shown in the dashboard text.
        # The standalone 'alert' command remains available for manual runs.
        alert_sent = run_alert(
            stock_symbols=stock_symbols,
            period='month',
            reference_date=report_date,
            send_no_activity_email=True,
        )

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
                    subject='Daily and Monthly Profit and Loss Stocks Report',
                    report_date=today,
                )
                print(f'Combined daily and monthly profit and loss report sent to {receiver_emails}')
                return {'report_sent': True, 'alert_sent': alert_sent}

        if report_files:
            debug_log(f"Sending report email with attachments: {report_files}")
            send_stock_report_email(
                file_paths=report_files,
                receiver_email=receiver_emails,
                subject='Daily Profit and Loss Stocks Report',
                report_date=report_date,
            )
            print(f'Daily profit and loss report sent to {receiver_emails}')
            return {'report_sent': True, 'alert_sent': alert_sent}
        else:
            print('No profit or loss rows found for the selected daily period.')
            return {'report_sent': False, 'alert_sent': alert_sent}

    if normalized_type == 'month':
        last_day = monthrange(today.year, today.month)[1]
        if today.day != last_day and not force_month:
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
                subject='Monthly Profit and Loss Stocks Report',
                report_date=end_date,
            )
            print(f'Monthly profit and loss report sent to {receiver_emails}')
            return {'report_sent': True}
        else:
            print('No profit or loss rows found for the selected monthly period.')
            return {'report_sent': False}

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
        if command in {'alert', 'alerts'}:
            run_alert()
            raise SystemExit(0)
        if command in {'live-alert', 'live-alerts', 'monitor'}:
            monitor_intraday_alerts()
            raise SystemExit(0)

    run_report(report_type='day')
