import os
import smtplib
import sys
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


def load_environment_file(env_file_path=None):
    env_file = Path(env_file_path) if env_file_path else Path(__file__).resolve().parent / '.env'
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = [part.strip() for part in line.split('=', 1)]
        if key and not os.getenv(key):
            os.environ[key] = value

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


def get_sender_credentials():
    load_environment_file()
    sender_email = os.getenv('MYTRADE_NOTIFY_SENDER_EMAIL')
    sender_password = os.getenv('MYTRADE_NOTIFY_PASSWORD')

    if not sender_email or not sender_password:
        raise RuntimeError(
            'Gmail credentials are missing. Set MYTRADE_NOTIFY_SENDER_EMAIL and MYTRADE_NOTIFY_PASSWORD in your shell '
            'or create a .env file with those values before sending the report.'
        )

    return sender_email, sender_password


def send_alert_email(summary=None, receiver_email='umamaheshwar.chevuru@gmail.com', subject='ATTENTION: Unusual Stock Movement Alert', html=None):
    sender_email, sender_password = get_sender_credentials()
    recipients = receiver_email if isinstance(receiver_email, list) else [receiver_email]

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = ', '.join(recipients)

    if html:
        msg.attach(MIMEText(html, 'html'))
    else:
        msg.attach(MIMEText(summary, 'plain'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    try:
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipients, msg.as_string())
        debug_log(f"Alert email sent successfully to {recipients}")
        return True
    finally:
        try:
            server.quit()
        except smtplib.SMTPResponseException as exc:
            if exc.smtp_code != 235:
                raise
        except (smtplib.SMTPServerDisconnected, OSError):
            pass


def send_stock_report_email(file_paths, receiver_email='umamaheshwar.chevuru@gmail.com', subject='Stock Price Report'):
    sender_email, sender_password = get_sender_credentials()

    if isinstance(file_paths, (str, Path)):
        file_paths = [file_paths]

    recipients = receiver_email if isinstance(receiver_email, list) else [receiver_email]
    debug_log(f"Building email for {recipients} with subject '{subject}'")

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = ', '.join(recipients)
    msg.attach(MIMEText('Profit and loss stock details are attached in the CSV files.', 'plain'))

    attachment_paths = [Path(path) for path in file_paths]
    debug_log(f"Attachments to send: {[p.name for p in attachment_paths]}")
    server = None
    try:
        for attachment_path in attachment_paths:
            with attachment_path.open('rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {attachment_path.name}'
                )
                msg.attach(part)
            debug_log(f"Attached file: {attachment_path.name}")

        server = smtplib.SMTP('smtp.gmail.com', 587)
        debug_log('Connecting to Gmail SMTP server')
        server.starttls()
        server.login(sender_email, sender_password)
        debug_log('Sending report email')
        server.sendmail(sender_email, recipients, msg.as_string())
        debug_log('Email sent successfully')
        return True
    finally:
        if server is not None:
            try:
                server.quit()
            except smtplib.SMTPResponseException as exc:
                if exc.smtp_code == 235:
                    debug_log(f"Gmail accepted the mail but returned an unexpected quit response: {exc}")
                else:
                    raise
            except (smtplib.SMTPServerDisconnected, OSError):
                pass

        for attachment_path in attachment_paths:
            if attachment_path.exists():
                attachment_path.unlink()
                debug_log(f"Deleted temp file after sending: {attachment_path}")
