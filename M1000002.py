import contextlib
import csv
import io
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import yfinance as yf

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
except ImportError:
    Workbook = None

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


def get_intraday_stock_data(stock_symbol='AAPL', interval='5m'):
    debug_log(f"Fetching intraday {interval} data for {stock_symbol}")
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), contextlib.suppress(Exception):
        ticker = yf.Ticker(stock_symbol)
        data = ticker.history(period='5d', interval=interval)

    if data is None or data.empty:
        return pd.DataFrame(columns=['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume'])

    df = data.reset_index()
    datetime_column = 'Datetime' if 'Datetime' in df.columns else 'Date'
    df['Datetime'] = pd.to_datetime(df[datetime_column])
    df['Datetime'] = df['Datetime'].dt.strftime('%Y-%m-%d %H:%M')
    df = df[['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']]
    return df


def save_stock_excel(rows, file_name='apple_stock_report.xlsx'):
    if Workbook is None:
        raise ImportError("openpyxl is not installed, cannot generate Excel report. Please install openpyxl or use CSV export.")

    temp_dir = Path(tempfile.gettempdir())
    file_path = temp_dir / file_name

    report_name = 'Stock'
    lower_name = file_name.lower()
    if 'daily' in lower_name:
        report_name = 'Daily'
    elif 'monthly' in lower_name:
        report_name = 'Monthly'

    trend_name = 'Profit' if 'profit' in lower_name else 'Loss'
    report_title = f'{report_name} {trend_name} Report'

    debug_log(f"Writing Excel: {file_path} with {len(rows)} rows")
    wb = Workbook()
    ws = wb.active
    ws.title = report_title

    # Add report title
    last_column = get_column_letter(len(rows[0]))
    ws.merge_cells(f'A1:{last_column}1')
    title_cell = ws['A1']
    title_cell.value = report_title
    title_cell.alignment = Alignment(horizontal='center', vertical='center')
    title_cell.font = Font(size=14, bold=True)

    # Define column headers and widths
    if 'daily' in lower_name:
        fieldnames = [
            'DT',
            'Stock',
            'Type',
            'Start Price',
            'End Price',
            'Difference',
            'Trend',
            'Percentage Change',
        ]
        column_widths = [18, 20, 15, 15, 15, 15, 15, 20]
    else:
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
        column_widths = [20, 15, 15, 15, 15, 15, 15, 15, 20]

    # Write header row
    for col_num, (header, width) in enumerate(zip(fieldnames, column_widths), start=1):
        cell = ws.cell(row=2, column=col_num)
        cell.value = header
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
        ws.column_dimensions[get_column_letter(col_num)].width = width

    # Write data rows
    for row_num, row_data in enumerate(rows, start=3):
        for col_num, header_name in enumerate(fieldnames, start=1):
            cell = ws.cell(row=row_num, column=col_num, value=row_data.get(header_name, ''))
            cell.alignment = Alignment(horizontal='center', vertical='center')

    wb.save(file_path)
    return str(file_path)


def save_stock_csv(rows, file_name='apple_stock_report.csv'):
    temp_dir = Path(tempfile.gettempdir())

    if Workbook is None:
        fallback_name = file_name if file_name.lower().endswith('.csv') else file_name.replace('.xlsx', '.csv')
        file_path = temp_dir / fallback_name
        lower_name = fallback_name.lower()

        if 'daily' in lower_name:
            fieldnames = ['DT', 'Stock', 'Type', 'Start Price', 'End Price', 'Difference', 'Trend', 'Percentage Change']
        else:
            fieldnames = ['Stock', 'Type', 'Start Date', 'Start Price', 'End Date', 'End Price', 'Difference', 'Trend', 'Percentage Change']

        report_name = 'Daily' if 'daily' in lower_name else 'Monthly' if 'monthly' in lower_name else 'Stock'
        trend_name = 'Profit' if 'profit' in lower_name else 'Loss'

        with file_path.open('w', newline='', encoding='utf-8') as csv_file:
            csv_file.write(f'{report_name} {trend_name} Report\n')
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)

        debug_log(f"openpyxl unavailable; wrote CSV fallback: {file_path}")
        return str(file_path)

    file_name = file_name.replace('.csv', '.xlsx')
    file_path = temp_dir / file_name

    report_name = 'Stock'
    lower_name = file_name.lower()
    if 'daily' in lower_name:
        report_name = 'Daily'
    elif 'monthly' in lower_name:
        report_name = 'Monthly'

    trend_name = 'Profit' if 'profit' in lower_name else 'Loss'
    report_title = f'{report_name} {trend_name} Report'

    if 'daily' in lower_name:
        fieldnames = ['DT', 'Stock', 'Type', 'Start Price', 'End Price', 'Difference', 'Trend', 'Percentage Change']
    else:
        fieldnames = ['Stock', 'Type', 'Start Date', 'Start Price', 'End Date', 'End Price', 'Difference', 'Trend', 'Percentage Change']

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = f'{report_name} {trend_name}'

    last_column = get_column_letter(len(fieldnames))
    worksheet.merge_cells(f'A1:{last_column}1')
    title_cell = worksheet['A1']
    title_cell.value = report_title
    title_cell.font = Font(name='Calibri', size=30, bold=True)
    title_cell.alignment = Alignment(horizontal='center', vertical='center')
    worksheet.row_dimensions[1].height = 48

    header_row = 3
    for column_number, header_name in enumerate(fieldnames, start=1):
        cell = worksheet.cell(row=header_row, column=column_number, value=header_name)
        cell.font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
        cell.fill = PatternFill(fill_type='solid', fgColor='4472C4')
        cell.alignment = Alignment(horizontal='center', vertical='center')

    for row_number, row in enumerate(rows, start=header_row + 1):
        for column_number, header_name in enumerate(fieldnames, start=1):
            cell = worksheet.cell(row=row_number, column=column_number, value=row.get(header_name, ''))
            cell.alignment = Alignment(horizontal='center', vertical='center')

    worksheet.freeze_panes = f'A{header_row + 1}'
    worksheet.auto_filter.ref = f'A{header_row}:{last_column}{header_row + len(rows)}'

    for column_number, header_name in enumerate(fieldnames, start=1):
        max_length = len(str(header_name))
        for row in worksheet.iter_rows(min_col=column_number, max_col=column_number, min_row=header_row, max_row=header_row + len(rows)):
            value = row[0].value
            max_length = max(max_length, len(str(value)) if value is not None else 0)
        worksheet.column_dimensions[get_column_letter(column_number)].width = min(max_length + 2, 30)

    workbook.save(file_path)
    debug_log(f"Writing Excel report: {file_path} with {len(rows)} rows")
    return str(file_path)
