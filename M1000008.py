import json
import logging
import os
import threading
import time
from calendar import monthrange
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import Flask

import M1000001
from M1000010 import ensure_admin, load_environment_file
from M1000011 import login_bp
from M1000012 import create_dashboard_blueprint

LOG_FILE = Path(__file__).resolve().parent / 'M1000009.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8')],
)
logger = logging.getLogger('MyTradeNotify')

app = Flask(__name__)
load_environment_file()
app.secret_key = os.environ.get('MYTRADE_DASHBOARD_SECRET_KEY') or os.urandom(32)
STATE_FILE = Path(__file__).resolve().parent / 'service_state.json'
ensure_admin()

service_status = {
    'started_at': datetime.now().isoformat(timespec='seconds'),
    'last_daily_report': None,
    'last_monthly_report': None,
    'last_live_alert_check': None,
    'last_unusual_alert': None,
    'last_error': None,
    'running': True,
    'selected_country': 'US',
    'selected_country_name': 'United States',
    'background_action': None,
}


app.register_blueprint(login_bp)
app.register_blueprint(create_dashboard_blueprint(service_status))


def load_service_state():
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding='utf-8'))
    except Exception:
        return {}


def save_service_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding='utf-8')


def run_daily_jobs():
    eastern = ZoneInfo('America/New_York')
    persisted_state = load_service_state()

    startup_now = datetime.now(eastern)
    startup_key = f'close:{startup_now.date().isoformat()}' if startup_now.hour >= 16 else f'open:{startup_now.date().isoformat()}'
    startup_session_key = 'last_daily_close_key' if startup_now.hour >= 16 else 'last_daily_key'

    if startup_now.weekday() < 5 and persisted_state.get(startup_session_key) != startup_key:
        try:
            M1000001.run_report(report_type='day')
            persisted_state[startup_session_key] = startup_key
            save_service_state(persisted_state)
            service_status['last_daily_report'] = startup_now.isoformat(timespec='seconds')
            logger.info('Startup daily report triggered.')
        except Exception as exc:
            service_status['last_error'] = f'{type(exc).__name__}: {exc}'

    while service_status['running']:
        now = datetime.now(eastern)
        today_key = now.date().isoformat()
        month_key = now.strftime('%Y-%m')

        try:
            open_key = f'open:{today_key}'
            close_key = f'close:{today_key}'

            if (now.weekday() < 5 and now.hour == 9 and now.minute == 30 and
                    persisted_state.get('last_daily_key') != open_key):
                logger.info('Scheduled daily report started (market open).')
                M1000001.run_report(report_type='day')
                logger.info('Scheduled daily report completed (market open).')
                persisted_state['last_daily_key'] = open_key
                save_service_state(persisted_state)
                service_status['last_daily_report'] = now.isoformat(timespec='seconds')
                logger.info('Scheduled daily report triggered (morning).')

            if (now.weekday() < 5 and now.hour == 16 and now.minute == 5 and
                    persisted_state.get('last_daily_close_key') != close_key):
                logger.info('Scheduled daily report started (market close).')
                M1000001.run_report(report_type='day')
                logger.info('Scheduled daily report completed (market close).')
                persisted_state['last_daily_close_key'] = close_key
                save_service_state(persisted_state)
                service_status['last_daily_report'] = now.isoformat(timespec='seconds')
                logger.info('Scheduled daily report triggered (afternoon).')

            if (now.day == monthrange(now.year, now.month)[1] and
                    now.hour == 9 and now.minute == 30 and
                    persisted_state.get('last_monthly_key') != month_key):
                M1000001.run_report(report_type='month')
                persisted_state['last_monthly_key'] = month_key
                save_service_state(persisted_state)
                service_status['last_monthly_report'] = now.isoformat(timespec='seconds')
                logger.info('Scheduled monthly report triggered.')
        except Exception as exc:
            service_status['last_error'] = f'{type(exc).__name__}: {exc}'

        time.sleep(60)


def run_live_alert_jobs():
    sent_alert_keys = set()

    while service_status['running']:
        check_time = datetime.now().isoformat(timespec='seconds')
        try:
            stock_symbols = M1000001.get_stock_symbols()
            alerts = []

            for symbol in stock_symbols:
                df = M1000001.get_intraday_stock_data(symbol, interval='5m')
                alert = M1000001.detect_intraday_alert(symbol, df)
                if alert is None:
                    continue

                key = (alert['Symbol'], alert['Movement'], alert['Timestamp'])
                if key not in sent_alert_keys:
                    sent_alert_keys.add(key)
                    alerts.append(alert)

            if alerts:
                M1000001.send_alert_email(
                    html=M1000001.build_intraday_alert_html(alerts),
                    receiver_email=M1000001.get_receiver_emails(),
                    subject='URGENT: Live Unusual Stock Movement Alert',
                )
                service_status['last_unusual_alert'] = check_time
                logger.info('Live unusual-movement alert sent.')

            service_status['last_live_alert_check'] = check_time
            logger.info('Live alert check completed: %d stock(s), %d unusual alert(s).', len(stock_symbols), len(alerts))
        except Exception as exc:
            service_status['last_error'] = f'{type(exc).__name__}: {exc}'

        time.sleep(300)


def start_background_services():
    daily_thread = threading.Thread(target=run_daily_jobs, daemon=True, name='daily-scheduler')
    live_thread = threading.Thread(target=run_live_alert_jobs, daemon=True, name='live-alert-scheduler')
    maintenance_thread = threading.Thread(target=run_log_maintenance, daemon=True, name='log-maintenance')
    daily_thread.start()
    live_thread.start()
    maintenance_thread.start()
    logger.info('Background schedulers started: daily, live-alert, and log-maintenance.')


LOG_RETENTION_DAYS = 7


def prune_old_log_entries():
    if not LOG_FILE.exists():
        return

    cutoff_date = (datetime.now() - timedelta(days=LOG_RETENTION_DAYS)).date()
    retained_lines = []
    current_block_keep = False

    try:
        for line in LOG_FILE.read_text(encoding='utf-8', errors='replace').splitlines():
            timestamp_text = line[:10]
            try:
                line_date = datetime.strptime(timestamp_text, '%Y-%m-%d').date()
                current_block_keep = line_date >= cutoff_date
                if current_block_keep:
                    retained_lines.append(line)
            except ValueError:
                if current_block_keep:
                    retained_lines.append(line)

        LOG_FILE.write_text('\n'.join(retained_lines) + ('\n' if retained_lines else ''), encoding='utf-8')
        logger.info('Log retention cleanup complete: kept the last %d calendar days.', LOG_RETENTION_DAYS)
    except Exception as exc:
        logger.exception('Log retention cleanup failed: %s', exc)


def run_log_maintenance():
    last_prune_date = None

    while service_status['running']:
        today_key = datetime.now().date().isoformat()
        if last_prune_date != today_key:
            prune_old_log_entries()
            last_prune_date = today_key
        time.sleep(3600)


prune_old_log_entries()
start_background_services()


logger.info('My Trade Notify service application started.')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=False)
