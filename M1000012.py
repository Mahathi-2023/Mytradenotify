import contextlib
import importlib
import io
import json
import re
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import Blueprint, jsonify, render_template_string, request
import yfinance as yf

import M1000001
from M1000002 import get_stock_data
from M1000011 import current_account, login_required
from M1000014 import DASHBOARD_TEMPLATE


STATE_FILE = Path(__file__).resolve().parent / 'M1000013.json'


def _clean_text(value):
    if value is None:
        return ''
    return str(value).strip()


def _split_sentences(text):
    cleaned = _clean_text(text)
    if not cleaned:
        return []
    parts = re.split(r'(?<=[.!?])\s+', cleaned)
    return [p.strip() for p in parts if p.strip()]


def _pick_sentences(summary_text, keywords, limit=3):
    keywords_lower = [k.lower() for k in keywords]
    picked = []
    for sentence in _split_sentences(summary_text):
        lowered = sentence.lower()
        if any(k in lowered for k in keywords_lower):
            picked.append(sentence)
        if len(picked) >= limit:
            break
    return picked


def _keyword_hits(summary_text, keywords):
    lowered = _clean_text(summary_text).lower()
    if not lowered:
        return 0
    return sum(1 for keyword in keywords if keyword.lower() in lowered)


def _confidence_label(sentence_count, keyword_hits):
    if sentence_count >= 2 or keyword_hits >= 5:
        return 'high'
    if sentence_count >= 1 or keyword_hits >= 2:
        return 'medium'
    return 'low'


def _confidence_reason(sentence_count, keyword_hits):
    return f'Matched {sentence_count} summary sentence(s) and {keyword_hits} keyword signal(s).'


def _classify_business_model(sector, industry, summary_text):
    base = ' '.join(filter(None, [_clean_text(sector), _clean_text(industry), _clean_text(summary_text)])).lower()

    service_keywords = {
        'service', 'services', 'consulting', 'consultancy', 'outsourcing', 'advisory', 'agency',
        'banking', 'insurance', 'logistics', 'saas', 'subscription', 'platform', 'cloud services',
        'it services', 'managed services', 'support services', 'brokerage', 'payments'
    }
    product_keywords = {
        'product', 'products', 'manufacture', 'manufactures', 'manufacturing', 'device', 'devices',
        'hardware', 'software', 'equipment', 'pharmaceutical', 'drugs', 'semiconductor', 'vehicles',
        'consumer goods', 'apparel', 'electronics', 'machinery', 'producer'
    }

    service_score = sum(1 for k in service_keywords if k in base)
    product_score = sum(1 for k in product_keywords if k in base)

    if service_score == 0 and product_score == 0:
        return 'mixed/unclear', service_score, product_score
    if service_score > product_score + 1:
        return 'service-based', service_score, product_score
    if product_score > service_score + 1:
        return 'product-based', service_score, product_score
    return 'mixed', service_score, product_score


def _extract_business_details(info):
    summary = _clean_text(info.get('longBusinessSummary'))

    service_keywords = [
        'service', 'services', 'consulting', 'outsourcing', 'advisory', 'support',
        'managed', 'platform', 'cloud', 'subscription', 'analytics', 'banking', 'insurance'
    ]
    product_keywords = [
        'product', 'products', 'manufacture', 'manufactures', 'sells', 'develops', 'device',
        'equipment', 'software', 'platform', 'drug', 'semiconductor', 'vehicle'
    ]
    customer_keywords = [
        'customer', 'customers', 'client', 'clients', 'enterprise', 'enterprises',
        'organization', 'organizations', 'businesses', 'retail', 'institutional',
        'serves', 'used by', 'sold to', 'supplies', 'partners'
    ]

    service_sentences = _pick_sentences(
        summary,
        service_keywords,
    )
    product_sentences = _pick_sentences(
        summary,
        product_keywords,
    )
    customer_sentences = _pick_sentences(
        summary,
        customer_keywords,
    )

    model, service_model_hits, product_model_hits = _classify_business_model(info.get('sector'), info.get('industry'), summary)
    service_hits = _keyword_hits(summary, service_keywords)
    product_hits = _keyword_hits(summary, product_keywords)
    customer_hits = _keyword_hits(summary, customer_keywords)

    service_customer_segments = customer_sentences if model in {'service-based', 'mixed', 'mixed/unclear'} else []
    product_customer_segments = customer_sentences if model in {'product-based', 'mixed', 'mixed/unclear'} else []

    model_confidence = 'low'
    if service_model_hits or product_model_hits:
        if abs(service_model_hits - product_model_hits) >= 3:
            model_confidence = 'high'
        else:
            model_confidence = 'medium'

    model_reason = (
        f'Service signals: {service_model_hits}, product signals: {product_model_hits} '
        f'from sector/industry/summary text.'
    )

    service_offerings_confidence = _confidence_label(len(service_sentences), service_hits)
    service_customer_confidence = _confidence_label(len(service_customer_segments), customer_hits)
    product_offerings_confidence = _confidence_label(len(product_sentences), product_hits)
    product_customer_confidence = _confidence_label(len(product_customer_segments), customer_hits)

    disclosure = (
        'Public market data usually describes customer segments, but often does not publish a verified '
        'list of specific customer companies for every stock.'
    )

    return {
        'business_model': model,
        'business_model_confidence': model_confidence,
        'business_model_confidence_reason': model_reason,
        'service_offerings': service_sentences,
        'service_offerings_confidence': service_offerings_confidence,
        'service_offerings_confidence_reason': _confidence_reason(len(service_sentences), service_hits),
        'service_customer_segments': service_customer_segments,
        'service_customer_segments_confidence': service_customer_confidence,
        'service_customer_segments_confidence_reason': _confidence_reason(len(service_customer_segments), customer_hits),
        'product_offerings': product_sentences,
        'product_offerings_confidence': product_offerings_confidence,
        'product_offerings_confidence_reason': _confidence_reason(len(product_sentences), product_hits),
        'product_customer_segments': product_customer_segments,
        'product_customer_segments_confidence': product_customer_confidence,
        'product_customer_segments_confidence_reason': _confidence_reason(len(product_customer_segments), customer_hits),
        'customer_disclosure_note': disclosure,
    }


def _load_persisted_state():
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _persist_runtime_status(service_status):
    state = _load_persisted_state()
    for key in (
        'last_daily_report',
        'last_monthly_report',
        'last_live_alert_check',
        'last_unusual_alert',
        'selected_country',
        'selected_country_name',
    ):
        state[key] = service_status.get(key)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding='utf-8')


def create_dashboard_blueprint(service_status):
    dashboard_bp = Blueprint('dashboard', __name__)
    trigger_lock = threading.Lock()

    persisted_state = _load_persisted_state()
    for key in (
        'last_daily_report',
        'last_monthly_report',
        'last_live_alert_check',
        'last_unusual_alert',
        'selected_country',
        'selected_country_name',
    ):
        if service_status.get(key) is None and persisted_state.get(key) is not None:
            service_status[key] = persisted_state[key]


    @dashboard_bp.route('/')
    @login_required
    def dashboard():
        account = current_account()
        account_name = f"User: {account.get('first_name','')} {account.get('last_name','')}".strip() if account else ''
        return render_template_string(DASHBOARD_TEMPLATE,
            account_role=account.get('role') if account else 'user',
            account_name=account_name)

    @dashboard_bp.route('/api/status')
    @login_required
    def status():
        expires_at = service_status.get('dashboard_notice_expires_at')
        if expires_at:
            try:
                if datetime.now() >= datetime.fromisoformat(expires_at):
                    service_status['dashboard_notice'] = None
                    service_status['dashboard_notice_level'] = None
                    service_status['dashboard_notice_expires_at'] = None
            except ValueError:
                service_status['dashboard_notice'] = None
                service_status['dashboard_notice_level'] = None
                service_status['dashboard_notice_expires_at'] = None
        return jsonify(service_status)

    @dashboard_bp.route('/api/country', methods=['POST'])
    @login_required
    def set_country():
        data = request.get_json(silent=True) or {}
        country = str(data.get('country','')).upper()
        if country not in {'US','IN'}:
            return jsonify({'success':False,'message':'Choose United States or India.'}),400
        country_name = 'United States' if country == 'US' else 'India'
        service_status['selected_country'] = country
        service_status['selected_country_name'] = country_name
        _persist_runtime_status(service_status)
        return jsonify({'success':True,'country':country,'country_name':country_name})

    @dashboard_bp.route('/api/stocks')
    @login_required
    def stocks():
        country = str(request.args.get('country') or service_status.get('selected_country') or 'US').upper()
        if country not in {'US', 'IN'}:
            country = 'US'
        symbols = M1000001.get_stock_symbols(country)
        return jsonify({'success': True, 'country': country, 'symbols': symbols})

    @dashboard_bp.route('/api/stock-details')
    @login_required
    def stock_details():
        symbol = str(request.args.get('symbol', '')).strip().upper()
        if not symbol:
            return jsonify({'success': False, 'message': 'Choose a stock symbol first.'}), 400

        end_date = date.today()
        start_date = end_date - timedelta(days=45)
        df = get_stock_data(stock_symbol=symbol, start_date=start_date, end_date=end_date)
        if df is None or df.empty:
            return jsonify({'success': False, 'message': 'No recent stock data available.'}), 404

        latest = df.iloc[-1]
        previous_close = float(df.iloc[-2]['Close']) if len(df) > 1 else float(latest['Open'])
        close_price = float(latest['Close'])
        change = close_price - previous_close
        change_percent = (change / previous_close) * 100 if previous_close else 0.0

        return jsonify(
            {
                'success': True,
                'symbol': symbol,
                'name': M1000001.get_stock_name(symbol),
                'instrument_type': M1000001.get_instrument_type(symbol),
                'latest_date': str(latest['Date']),
                'open_price': round(float(latest['Open']), 2),
                'close_price': round(close_price, 2),
                'high_price': round(float(latest['High']), 2),
                'low_price': round(float(latest['Low']), 2),
                'volume': int(float(latest['Volume'])),
                'change': round(change, 2),
                'change_percent': round(change_percent, 2),
            }
        )

    @dashboard_bp.route('/api/stock-history')
    @login_required
    def stock_history():
        try:
            symbol = str(request.args.get('symbol', '')).strip().upper()
            if not symbol:
                return jsonify({'success': False, 'message': 'Choose a stock symbol first.'}), 400

            allowed_periods = {'1d', '5d', '1mo', '3mo', '6mo', '1y', '2y'}
            allowed_intervals = {'1m', '5m', '15m', '30m', '1h', '1d', '1wk'}
            period = str(request.args.get('period', '1mo')).strip().lower()
            interval = str(request.args.get('interval', '1d')).strip().lower()

            if period not in allowed_periods:
                period = '1mo'
            if interval not in allowed_intervals:
                interval = '1d'

            interval_to_yf = {
                '1m': '1m',
                '5m': '5m',
                '15m': '15m',
                '30m': '30m',
                '1h': '60m',
                '1d': '1d',
                '1wk': '1wk',
            }
            yf_interval = interval_to_yf.get(interval, '1d')

            if interval in {'1m', '5m', '15m', '30m', '1h'} and period in {'1y', '2y'}:
                period = '1mo'
            if interval == '1m' and period in {'1mo', '3mo', '6mo'}:
                period = '5d'
            if interval in {'5m', '15m', '30m', '1h'} and period == '6mo':
                period = '3mo'

            try:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    history = yf.Ticker(symbol).history(period=period, interval=yf_interval)
            except Exception:
                return jsonify({'success': False, 'message': 'Chart provider error. Try a larger range or different interval.'}), 502

            if history is None or history.empty:
                return jsonify({'success': False, 'message': 'No chart data available for this selection.'}), 404

            frame = history.reset_index()
            time_col = 'Datetime' if 'Datetime' in frame.columns else 'Date'
            sampled = frame[[time_col, 'Open', 'High', 'Low', 'Close']].dropna()
            if sampled.empty:
                return jsonify({'success': False, 'message': 'No chart data available for this selection.'}), 404

            max_points = 360
            if len(sampled) > max_points:
                step = max(1, len(sampled) // max_points)
                sampled = sampled.iloc[::step]

            points = [
                {
                    't': str(row[time_col])[:16],
                    'o': round(float(row['Open']), 4),
                    'h': round(float(row['High']), 4),
                    'l': round(float(row['Low']), 4),
                    'c': round(float(row['Close']), 4),
                }
                for _, row in sampled.iterrows()
            ]

            return jsonify({'success': True, 'symbol': symbol, 'period': period, 'interval': interval, 'points': points})
        except Exception:
            return jsonify({'success': False, 'message': 'Unexpected chart service error. Please try again.'}), 500

    @dashboard_bp.route('/api/stock-company-info')
    @login_required
    def stock_company_info():
        symbol = str(request.args.get('symbol', '')).strip().upper()
        if not symbol:
            return jsonify({'success': False, 'message': 'Choose a stock symbol first.'}), 400

        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                info = yf.Ticker(symbol).info or {}
        except Exception:
            info = {}

        company_name = M1000001.get_stock_name(symbol)
        ceo_name = None

        officers = info.get('companyOfficers')
        if isinstance(officers, list):
            for officer in officers:
                if not isinstance(officer, dict):
                    continue
                title = str(officer.get('title', '')).lower()
                name = str(officer.get('name', '')).strip()
                if name and ('ceo' in title or 'chief executive' in title):
                    ceo_name = name
                    break

        if not ceo_name:
            ceo_name = str(info.get('ceo') or info.get('CEO') or 'Not available').strip() or 'Not available'

        business_details = _extract_business_details(info)

        return jsonify(
            {
                'success': True,
                'symbol': symbol,
                'company_name': company_name,
                'ceo': ceo_name,
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'country': info.get('country'),
                'city': info.get('city'),
                'state': info.get('state'),
                'exchange': info.get('exchange') or info.get('fullExchangeName'),
                'currency': info.get('currency'),
                'website': info.get('website'),
                'market_cap': info.get('marketCap'),
                'enterprise_value': info.get('enterpriseValue'),
                'employees': info.get('fullTimeEmployees'),
                'beta': info.get('beta'),
                'trailing_pe': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'dividend_yield': info.get('dividendYield'),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                'previous_close': info.get('previousClose'),
                'open_price': info.get('open'),
                'volume': info.get('volume'),
                'average_volume': info.get('averageVolume'),
                'business_summary': info.get('longBusinessSummary'),
                'business_model': business_details.get('business_model'),
                'business_model_confidence': business_details.get('business_model_confidence'),
                'business_model_confidence_reason': business_details.get('business_model_confidence_reason'),
                'service_offerings': business_details.get('service_offerings'),
                'service_offerings_confidence': business_details.get('service_offerings_confidence'),
                'service_offerings_confidence_reason': business_details.get('service_offerings_confidence_reason'),
                'service_customer_segments': business_details.get('service_customer_segments'),
                'service_customer_segments_confidence': business_details.get('service_customer_segments_confidence'),
                'service_customer_segments_confidence_reason': business_details.get('service_customer_segments_confidence_reason'),
                'product_offerings': business_details.get('product_offerings'),
                'product_offerings_confidence': business_details.get('product_offerings_confidence'),
                'product_offerings_confidence_reason': business_details.get('product_offerings_confidence_reason'),
                'product_customer_segments': business_details.get('product_customer_segments'),
                'product_customer_segments_confidence': business_details.get('product_customer_segments_confidence'),
                'product_customer_segments_confidence_reason': business_details.get('product_customer_segments_confidence_reason'),
                'customer_disclosure_note': business_details.get('customer_disclosure_note'),
            }
        )

    @dashboard_bp.route('/api/trigger/<action>', methods=['POST'])
    @login_required
    def trigger_action(action):
        account = current_account()
        if account.get('role') != 'admin':
            return jsonify({'success':False,'message':'Only administrators can trigger reports and alerts.'}),403
        if not trigger_lock.acquire(blocking=False):
            return jsonify({'success':False,'message':'Another action is already running.'}),409
        if action not in {'daily','monthly','alert','live-alert'}:
            trigger_lock.release()
            return jsonify({'success':False,'message':'Unknown action.'}),400

        def run_action():
            try:
                # Ensure dashboard-triggered actions run the latest edited logic.
                import M1000007
                import M1000003
                importlib.reload(M1000007)
                importlib.reload(M1000003)
                importlib.reload(M1000001)

                country = service_status.get('selected_country', 'US')
                action_time = datetime.now().isoformat(timespec='seconds')
                monthly_report_sent = None
                if action == 'daily':
                    result = M1000001.run_report(report_type='day',stock_symbols=M1000001.get_stock_symbols(country))
                    # Daily action reached completion without exception; update dashboard timestamp.
                    service_status['last_daily_report'] = action_time
                    alert_sent = isinstance(result, dict) and result.get('alert_sent')
                    if alert_sent:
                        service_status['last_unusual_alert'] = action_time
                    else:
                        forced_alert_sent = M1000001.run_alert(
                            stock_symbols=M1000001.get_stock_symbols(country),
                            period='month',
                            send_no_activity_email=True,
                        )
                        if forced_alert_sent:
                            service_status['last_unusual_alert'] = action_time
                elif action == 'monthly':
                    result = M1000001.run_report(report_type='month',force_month=True,stock_symbols=M1000001.get_stock_symbols(country))
                    monthly_report_sent = isinstance(result, dict) and result.get('report_sent')
                    if monthly_report_sent:
                        service_status['last_monthly_report'] = action_time
                    else:
                        service_status['last_error'] = 'Monthly run completed, but no profit/loss rows were found for the selected period.'
                elif action == 'alert':
                    M1000001.run_alert(stock_symbols=M1000001.get_stock_symbols(country))
                    service_status['last_unusual_alert'] = action_time
                elif action == 'live-alert':
                    live_alert_sent = M1000001.run_intraday_alerts(stock_symbols=M1000001.get_stock_symbols(country))
                    service_status['last_live_alert_check'] = action_time
                    if live_alert_sent:
                        service_status['dashboard_notice'] = None
                        service_status['dashboard_notice_level'] = None
                        service_status['dashboard_notice_expires_at'] = None
                    else:
                        service_status['dashboard_notice'] = 'No unusual live stock movement detected in the latest 5-minute check.'
                        service_status['dashboard_notice_level'] = 'info'
                        service_status['dashboard_notice_expires_at'] = (
                          datetime.now() + timedelta(seconds=10)
                        ).isoformat(timespec='seconds')
                _persist_runtime_status(service_status)
                if action != 'monthly' or monthly_report_sent:
                    service_status['last_error'] = None
            except Exception as exc:
                service_status['last_error'] = f'{type(exc).__name__}: {exc}'
            finally:
                trigger_lock.release()
                service_status['background_action'] = None

        service_status['background_action'] = action
        threading.Thread(target=run_action,daemon=True,name=f'dashboard-{action}').start()
        action_labels = {
          'daily': 'Daily report',
          'monthly': 'Monthly report',
          'alert': '30-day unusual activity check',
          'live-alert': 'Live unusual activity check',
        }
        action_label = action_labels.get(action, 'Requested action')
        return jsonify({'success':True,'message':f'{action_label} is running now. You will receive an email shortly.'})

    return dashboard_bp
