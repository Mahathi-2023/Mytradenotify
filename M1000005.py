import json
import os
import sys
import urllib.request
from pathlib import Path

# This file is the sole writer for stocks.txt.
BASE_DIR = Path(__file__).resolve().parent
STOCKS_FILE = BASE_DIR / 'stocks.txt'
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


FALLBACK_STOCKS = [
    'AAPL', 'MSFT', 'GOOGL', 'NVDA', 'AMZN', 'META', 'TSLA', 'AMD', 'INTC', 'NFLX',
    'AVGO', 'PLTR', 'CRM', 'ADBE', 'ORCL', 'QCOM', 'PDD', 'SHOP', 'UBER', 'DIS',
    'CAT', 'NKE', 'JPM', 'V', 'MA', 'WMT', 'COST', 'XOM', 'CVX', 'UNH', 'PEP',
    'KO', 'MCD', 'HD', 'IBM', 'MMM', 'AMGN', 'ABBV', 'ABNB', 'C', 'BAC', 'X', 'GM',
    'T', 'KHC', 'BA', 'LMT', 'RTX', 'NOC', 'HON', 'CVS', 'PFE', 'MRK', 'GILD',
    'LLY', 'JNJ', 'DHR', 'GE', 'SLB', 'SPY', 'QQQ', 'DIA', 'IWM', 'VOO', 'VTI',
    'IVV', 'VTV', 'XLF', 'XLK', 'XLE', 'XLC', 'ES=F', 'NQ=F', 'YM=F', 'RTY=F',
    'CL=F', 'GC=F', 'SI=F', 'NG=F'
]


def read_stocks():
    if not STOCKS_FILE.exists():
        debug_log(f"Stock file not found at {STOCKS_FILE}")
        return []

    stocks = []
    with STOCKS_FILE.open('r', encoding='utf-8') as file:
        for line in file:
            value = line.strip()
            if value and not value.startswith('#'):
                stocks.append(value)
    debug_log(f"Loaded {len(stocks)} stock(s): {stocks}")
    return stocks


def fetch_live_stock_symbols(limit=200):
    endpoint = (
        'https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved'
        '?formatted=true&lang=en-US&region=US&corsDomain=finance.yahoo.com&scrIds=all'
    )

    debug_log(f"Fetching live screener symbols from Yahoo Finance (limit={limit})")
    try:
        request = urllib.request.Request(
            endpoint,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode('utf-8'))

        results = payload.get('finance', {}).get('result', [])
        quotes = []
        for item in results:
            quotes.extend(item.get('quotes', []))

        symbols = []
        seen = set()
        for item in quotes:
            symbol = str(item.get('symbol', '')).strip()
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            symbols.append(symbol)
            if len(symbols) >= limit:
                break

        if symbols:
            debug_log(f"Live fetch succeeded: {len(symbols)} symbols collected")
            return symbols
    except Exception as exc:
        debug_log(f"Live fetch failed: {type(exc).__name__}: {exc}. Falling back to built-in list.")
        pass

    debug_log(f"Using fallback list of {len(FALLBACK_STOCKS[:limit])} symbols")
    return FALLBACK_STOCKS[:limit]


def write_stocks(stocks):
    cleaned = []
    seen = set()
    for stock in stocks:
        value = str(stock).strip()
        if not value or value.startswith('#'):
            continue
        value = value.upper()
        if value not in seen:
            cleaned.append(value)
            seen.add(value)

    debug_log(f"Writing stock list to {STOCKS_FILE}: {cleaned}")
    with STOCKS_FILE.open('w', encoding='utf-8') as file:
        if cleaned:
            file.write('\n'.join(cleaned) + '\n')

    return cleaned


def update_stock_list(new_stocks=None, refresh_live=False):
    if refresh_live:
        debug_log('Refresh requested; calling live market source')
        new_stocks = fetch_live_stock_symbols(limit=200)

    if new_stocks is None:
        cli_values = []
        for arg in sys.argv[1:]:
            if arg.lower() in {'live', 'refresh'}:
                debug_log('Live flag detected via CLI; fetching fresh list')
                new_stocks = fetch_live_stock_symbols(limit=200)
                break
            cli_values.extend(part.strip() for part in arg.split(',') if part.strip())
        if cli_values:
            new_stocks = cli_values

    if new_stocks is None:
        print('Current stock list:')
        current = read_stocks()
        if current:
            for stock in current:
                print(f'- {stock}')
        else:
            print('No stocks found.')

        raw_input = input('Enter stock symbols separated by commas (or press Enter to keep current): ').strip()
        if not raw_input:
            return current
        new_stocks = [item.strip() for item in raw_input.split(',') if item.strip()]

    debug_log(f"Final stock update payload: {new_stocks}")
    return write_stocks(new_stocks)


if __name__ == '__main__':
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else None
    if mode in {'live', 'refresh'}:
        updated = update_stock_list(refresh_live=True)
    else:
        updated = update_stock_list()

    print(f"Stock list updated in {STOCKS_FILE}")
    print(updated)
