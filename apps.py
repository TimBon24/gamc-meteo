import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
import os
from os.path import basename

from dotenv import load_dotenv

load_dotenv()
EMAIL_WORK = os.getenv('EMAIL_WORK')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD').strip('"')
EMAIL_SERVER = os.getenv('EMAIL_SERVER')
EMAIL_PORT = int(os.getenv('EMAIL_PORT'))

def send_mail(send_from, send_to, subject, text, files=None,
              server=EMAIL_SERVER):
    assert isinstance(send_to, list)

    msg = MIMEMultipart()
    msg['From'] = send_from
    msg['To'] = COMMASPACE.join(send_to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach(MIMEText(text))

    for f in files or []:
        with open(f, "rb") as fil:
            part = MIMEApplication(
                fil.read(),
                Name=basename(f)
            )
        # After the file is closed
        part['Content-Disposition'] = 'attachment; filename="%s"' % basename(f)
        msg.attach(part)

    smtp = smtplib.SMTP(server,EMAIL_PORT)
    smtp.starttls()
    smtp.login(EMAIL_WORK, EMAIL_PASSWORD)
    smtp.sendmail(send_from, send_to, msg.as_string())
    smtp.close()
