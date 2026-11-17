import contextlib
import csv
import io
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import yfinance as yf

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


def get_stock_data(stock_symbol='AAPL', start_date=None, end_date=None):
    if start_date is None or end_date is None:
        raise ValueError('start_date and end_date are required.')

    debug_log(f"Fetching {stock_symbol} from {start_date} to {end_date}")
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        ticker = yf.Ticker(stock_symbol)
        data = ticker.history(start=start_date.strftime('%Y-%m-%d'), end=(end_date + pd.Timedelta(days=1)).strftime('%Y-%m-%d'), interval='1d')

    if data.empty:
        debug_log(f"yfinance returned no rows for {stock_symbol}")
        return pd.DataFrame(columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])

    df = data.reset_index()
    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
    df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
    debug_log(f"Fetched {len(df)} rows for {stock_symbol}")
    return df


def save_stock_csv(rows, file_name='apple_stock_report.csv'):
    temp_dir = Path(tempfile.gettempdir())
    file_path = temp_dir / file_name

    fieldnames = [
        'Stock',
        'Type',
        'Start Date',
        'Start Price',
        'End Date',
        'End Price',
        'Difference',
        'Trend',
        'Percentage Change',
    ]

    debug_log(f"Writing CSV: {file_path} with {len(rows)} rows")
    with file_path.open('w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return str(file_path)
