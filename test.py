import smtplib, ssl
from email.mime.text import MIMEText

FROM = "lilian@blsuntechdynamics.com"
TO = "kiraka9@gmail.com"  # test inbox
PASSWORD = "Leokesho@1"

msg = MIMEText("SMTP test works from Hostinger!")
msg["Subject"] = "Test"
msg["From"] = FROM
msg["To"] = TO

context = ssl.create_default_context()
with smtplib.SMTP_SSL("smtp.hostinger.com", 465, context=context) as server:
    server.login(FROM, PASSWORD)
    server.sendmail(FROM, [TO], msg.as_string())

