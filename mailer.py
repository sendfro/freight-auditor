import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st

def fire_dispute_email(carrier_email, subject, body):
    # The app looks in your secure vault for your email credentials
    sender_email = st.secrets["SENDER_EMAIL"]
    sender_password = st.secrets["SENDER_PASSWORD"]

    # Construct the digital envelope
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = carrier_email
    msg['Subject'] = subject

    # Put the AI-drafted text inside the envelope
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Connect to Gmail's server and hit send
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls() # Secure the connection
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True, "Email successfully dispatched to carrier!"
    except Exception as e:
        return False, f"Failed to send email: {e}"