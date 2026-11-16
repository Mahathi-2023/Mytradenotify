import os
import smtplib
import sys
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

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


def send_stock_report_email(file_paths, receiver_email='umamaheshwar.chevuru@gmail.com', subject='Stock Price Report'):
    sender_email = 'admin.mytradenotify@gmail.com'

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

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            debug_log('Connecting to Gmail SMTP server')
            server.starttls()
            server.login(sender_email, 'uybxfodwyrejlfsb')
            debug_log('Sending report email')
            server.sendmail(sender_email, recipients, msg.as_string())
            debug_log('Email sent successfully')
    finally:
        for attachment_path in attachment_paths:
            if attachment_path.exists():
                attachment_path.unlink()
                debug_log(f"Deleted temp file after sending: {attachment_path}")

    return True
