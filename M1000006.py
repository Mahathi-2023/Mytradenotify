import os
import smtplib
import unittest
from datetime import date

import pandas as pd

import M1000001


class FakeDate(date):
    _today = date(2026, 11, 10)

    @classmethod
    def today(cls):
        return cls._today


class ReportLogicTests(unittest.TestCase):
    def test_monthly_report_skips_when_not_end_of_month(self):
        FakeDate._today = date(2026, 11, 10)
        original_date = M1000001.date
        original_symbols = M1000001.get_stock_symbols
        original_receiver_emails = M1000001.get_receiver_emails
        original_stock_data = M1000001.get_stock_data
        original_send = M1000001.send_stock_report_email
        original_save = M1000001.save_stock_csv

        try:
            M1000001.date = FakeDate
            M1000001.get_stock_symbols = lambda: ['AAPL']
            M1000001.get_receiver_emails = lambda: ['vinaykumarchevuru@gmail.com']
            M1000001.get_stock_data = lambda **kwargs: pd.DataFrame([
                {'Date': '2026-11-09', 'Open': 100.0, 'High': 101.0, 'Low': 99.0, 'Close': 101.0, 'Volume': 1000},
                {'Date': '2026-11-10', 'Open': 101.0, 'High': 102.0, 'Low': 100.0, 'Close': 102.0, 'Volume': 1000},
            ])
            calls = {'count': 0}

            def fake_send(**kwargs):
                calls['count'] += 1

            M1000001.send_stock_report_email = fake_send
            M1000001.save_stock_csv = lambda rows, file_name='apple_stock_report.csv': f'/tmp/{file_name}'

            M1000001.run_report(report_type='month')
            self.assertEqual(calls['count'], 0)
        finally:
            M1000001.date = original_date
            M1000001.get_stock_symbols = original_symbols
            M1000001.get_receiver_emails = original_receiver_emails
            M1000001.get_stock_data = original_stock_data
            M1000001.send_stock_report_email = original_send
            M1000001.save_stock_csv = original_save

    def test_daily_report_uses_open_to_close_for_selected_day(self):
        FakeDate._today = date(2026, 11, 15)
        original_date = M1000001.date
        original_symbols = M1000001.get_stock_symbols
        original_receiver_emails = M1000001.get_receiver_emails
        original_stock_data = M1000001.get_stock_data
        original_send = M1000001.send_stock_report_email
        original_save = M1000001.save_stock_csv

        try:
            M1000001.date = FakeDate
            M1000001.get_stock_symbols = lambda: ['AAPL']
            M1000001.get_receiver_emails = lambda: ['vinaykumarchevuru@gmail.com']
            M1000001.get_stock_data = lambda **kwargs: pd.DataFrame([
                {'Date': '2026-11-15', 'Open': 101.0, 'High': 102.0, 'Low': 100.0, 'Close': 102.0, 'Volume': 1000},
            ])
            captured = {}

            def fake_send(**kwargs):
                captured['email'] = kwargs

            def fake_save(rows, file_name='apple_stock_report.csv'):
                captured['rows'] = rows
                return f'/tmp/{file_name}'

            M1000001.send_stock_report_email = fake_send
            M1000001.save_stock_csv = fake_save

            M1000001.run_report(report_type='daily')
            self.assertEqual(captured['rows'][0]['Start Price'], 101.0)
            self.assertEqual(captured['rows'][0]['End Price'], 102.0)
            self.assertEqual(captured['rows'][0]['Difference'], 1.0)
        finally:
            M1000001.date = original_date
            M1000001.get_stock_symbols = original_symbols
            M1000001.get_receiver_emails = original_receiver_emails
            M1000001.get_stock_data = original_stock_data
            M1000001.send_stock_report_email = original_send
            M1000001.save_stock_csv = original_save

    def test_last_day_of_month_sends_combined_daily_and_monthly_report(self):
        FakeDate._today = date(2026, 11, 30)
        original_date = M1000001.date
        original_symbols = M1000001.get_stock_symbols
        original_receiver_emails = M1000001.get_receiver_emails
        original_stock_data = M1000001.get_stock_data
        original_send = M1000001.send_stock_report_email
        original_save = M1000001.save_stock_csv

        try:
            M1000001.date = FakeDate
            M1000001.get_stock_symbols = lambda: ['AAPL']
            M1000001.get_receiver_emails = lambda: ['vinaykumarchevuru@gmail.com']

            def fake_stock_data(**kwargs):
                start_date = kwargs['start_date']
                end_date = kwargs['end_date']
                if start_date == date(2026, 11, 30) and end_date == date(2026, 11, 30):
                    return pd.DataFrame([
                        {'Date': '2026-11-30', 'Open': 101.0, 'High': 102.0, 'Low': 100.0, 'Close': 102.0, 'Volume': 1000},
                    ])
                return pd.DataFrame([
                    {'Date': '2026-11-01', 'Open': 90.0, 'High': 91.0, 'Low': 89.0, 'Close': 95.0, 'Volume': 1000},
                    {'Date': '2026-11-30', 'Open': 100.0, 'High': 105.0, 'Low': 99.0, 'Close': 110.0, 'Volume': 1000},
                ])

            captured = {}

            def fake_send(**kwargs):
                captured['kwargs'] = kwargs

            def fake_save(rows, file_name='apple_stock_report.csv'):
                return f'/tmp/{file_name}'

            M1000001.get_stock_data = fake_stock_data
            M1000001.send_stock_report_email = fake_send
            M1000001.save_stock_csv = fake_save

            M1000001.run_report(report_type='daily')
            self.assertEqual(captured['kwargs']['subject'], 'Daily and Monthly Profit and Loss Stocks Report')
            self.assertGreater(len(captured['kwargs']['file_paths']), 1)
        finally:
            M1000001.date = original_date
            M1000001.get_stock_symbols = original_symbols
            M1000001.get_receiver_emails = original_receiver_emails
            M1000001.get_stock_data = original_stock_data
            M1000001.send_stock_report_email = original_send
            M1000001.save_stock_csv = original_save

    def test_daily_excel_has_centered_title_and_no_date_columns(self):
        from openpyxl import load_workbook

        rows = [{
            'Stock': 'Apple Inc.', 'Type': 'Stock', 'Start Date': '2026-11-21',
            'Start Price': 100.0, 'End Date': '2026-11-21', 'End Price': 105.0,
            'Difference': 5.0, 'Trend': 'Profit', 'Percentage Change': '+5.00%',
        }]

        file_path = M1000001.save_stock_csv(rows, 'daily_profit_report.csv')
        try:
            workbook = load_workbook(file_path)
            worksheet = workbook.active
            self.assertEqual(worksheet['A1'].value, 'Daily Profit Report')
            self.assertTrue(worksheet['A1'].font.bold)
            self.assertEqual(worksheet['A1'].font.size, 30)
            self.assertEqual(worksheet['A1'].alignment.horizontal, 'center')
            headers = [worksheet.cell(row=3, column=column).value for column in range(1, 8)]
            self.assertEqual(headers, ['Stock', 'Type', 'Start Price', 'End Price', 'Difference', 'Trend', 'Percentage Change'])
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    def test_monthly_excel_has_title_and_date_columns(self):
        from openpyxl import load_workbook

        rows = [{
            'Stock': 'Apple Inc.', 'Type': 'Stock', 'Start Date': '2026-11-01',
            'Start Price': 100.0, 'End Date': '2026-11-30', 'End Price': 105.0,
            'Difference': 5.0, 'Trend': 'Profit', 'Percentage Change': '+5.00%',
        }]

        file_path = M1000001.save_stock_csv(rows, 'monthly_profit_report.csv')
        try:
            workbook = load_workbook(file_path)
            worksheet = workbook.active
            self.assertEqual(worksheet['A1'].value, 'Monthly Profit Report')
            headers = [worksheet.cell(row=3, column=column).value for column in range(1, 10)]
            self.assertEqual(headers, ['Stock', 'Type', 'Start Date', 'Start Price', 'End Date', 'End Price', 'Difference', 'Trend', 'Percentage Change'])
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    def test_get_instrument_type_reuses_cached_lookup(self):
        original_cache = M1000001.get_instrument_type.cache_clear if hasattr(M1000001.get_instrument_type, 'cache_clear') else None
        original_ticker = M1000001.yf.Ticker
        calls = {'count': 0}

        class FakeTicker:
            def __init__(self, symbol):
                calls['count'] += 1
                self.symbol = symbol
                self.info = {'quoteType': 'EQUITY'}

        try:
            M1000001.yf.Ticker = FakeTicker
            M1000001.get_instrument_type.cache_clear()
            self.assertEqual(M1000001.get_instrument_type('AAPL'), 'Stock')
            self.assertEqual(M1000001.get_instrument_type('AAPL'), 'Stock')
            self.assertEqual(calls['count'], 1)
        finally:
            M1000001.yf.Ticker = original_ticker
            if original_cache is not None:
                M1000001.get_instrument_type.cache_clear()

    def test_smtp_quit_235_response_does_not_crash_report(self):
        import M1000003

        class FakeSMTP:
            def __init__(self, host, port):
                self.host = host
                self.port = port

            def starttls(self):
                return None

            def login(self, username, password):
                return None

            def sendmail(self, sender, recipients, msg):
                return None

            def quit(self):
                raise smtplib.SMTPResponseException(235, b'2.7.0 Accepted')

        original_smtp = smtplib.SMTP
        original_password = os.environ.get('MYTRADE_NOTIFY_PASSWORD')
        original_sender = os.environ.get('MYTRADE_NOTIFY_SENDER_EMAIL')
        temp_file = '/tmp/test_stock_report.csv'
        try:
            os.environ['MYTRADE_NOTIFY_PASSWORD'] = 'test_password'
            os.environ['MYTRADE_NOTIFY_SENDER_EMAIL'] = 'admin.mytradenotify@gmail.com'
            smtplib.SMTP = FakeSMTP
            with open(temp_file, 'w', encoding='utf-8') as fh:
                fh.write('test')
            self.assertTrue(M1000003.send_stock_report_email([temp_file], receiver_email=['vinaykumarchevuru@gmail.com']))
        finally:
            smtplib.SMTP = original_smtp
            if original_password is None:
                os.environ.pop('MYTRADE_NOTIFY_PASSWORD', None)
            else:
                os.environ['MYTRADE_NOTIFY_PASSWORD'] = original_password

            if original_sender is None:
                os.environ.pop('MYTRADE_NOTIFY_SENDER_EMAIL', None)
            else:
                os.environ['MYTRADE_NOTIFY_SENDER_EMAIL'] = original_sender

            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass

    def test_missing_smtp_credentials_raise_clear_error(self):
        import M1000003

        original_password = os.environ.get('MYTRADE_NOTIFY_PASSWORD')
        original_sender = os.environ.get('MYTRADE_NOTIFY_SENDER_EMAIL')
        original_loader = M1000003.load_environment_file
        try:
            os.environ.pop('MYTRADE_NOTIFY_PASSWORD', None)
            os.environ.pop('MYTRADE_NOTIFY_SENDER_EMAIL', None)
            M1000003.load_environment_file = lambda *args, **kwargs: None
            with self.assertRaises(RuntimeError):
                M1000003.get_sender_credentials()
        finally:
            M1000003.load_environment_file = original_loader
            if original_password is None:
                os.environ.pop('MYTRADE_NOTIFY_PASSWORD', None)
            else:
                os.environ['MYTRADE_NOTIFY_PASSWORD'] = original_password

            if original_sender is None:
                os.environ.pop('MYTRADE_NOTIFY_SENDER_EMAIL', None)
            else:
                os.environ['MYTRADE_NOTIFY_SENDER_EMAIL'] = original_sender

    def test_alert_detects_high_monthly_profit(self):
        original_name = M1000001.get_stock_name
        try:
            M1000001.get_stock_name = lambda symbol: 'Apple Inc.'
            df = pd.DataFrame([
                {'Date': '2026-10-23', 'Open': 100.0, 'Close': 100.0},
                {'Date': '2026-11-21', 'Open': 100.0, 'Close': 112.0},
            ])
            alert = M1000001.detect_unusual_movement('AAPL', df)
            self.assertIsNotNone(alert)
            self.assertEqual(alert['Movement'], 'High Profit')
            self.assertEqual(alert['Monthly Change'], 12.0)
        finally:
            M1000001.get_stock_name = original_name

    def test_alert_run_sends_summary_without_attachments(self):
        original_symbols = M1000001.get_stock_symbols
        original_receiver_emails = M1000001.get_receiver_emails
        original_stock_data = M1000001.get_stock_data
        original_alert_email = M1000001.send_alert_email

        try:
            M1000001.get_stock_symbols = lambda: ['AAPL']
            M1000001.get_receiver_emails = lambda: ['vinaykumarchevuru@gmail.com']
            M1000001.get_stock_data = lambda **kwargs: pd.DataFrame([
                {'Date': '2026-10-23', 'Open': 100.0, 'Close': 100.0},
                {'Date': '2026-11-21', 'Open': 100.0, 'Close': 85.0},
            ])

            captured = {}

            def fake_alert_email(**kwargs):
                captured.update(kwargs)
                return True

            M1000001.send_alert_email = fake_alert_email

            self.assertTrue(M1000001.run_alert())
            self.assertEqual(captured['subject'], 'ATTENTION: Unusual Stock Movement Alert')
            self.assertIn('ATTENTION:', captured['summary'])
            self.assertNotIn('file_paths', captured)
        finally:
            M1000001.get_stock_symbols = original_symbols
            M1000001.get_receiver_emails = original_receiver_emails
            M1000001.get_stock_data = original_stock_data
            M1000001.send_alert_email = original_alert_email

    def test_intraday_alert_detects_sharp_move(self):
        df = pd.DataFrame([
            {'Datetime': '2026-11-21 10:00', 'Open': 100.0, 'Close': 100.0},
            {'Datetime': '2026-11-21 10:15', 'Open': 100.0, 'Close': 106.0},
        ])
        alert = M1000001.detect_intraday_alert('AAPL', df)
        self.assertIsNotNone(alert)
        self.assertEqual(alert['Movement'], 'Sharp Profit')
        self.assertEqual(alert['Interval Change'], 6.0)


if __name__ == '__main__':
    unittest.main()
