# utils/email_service.py
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def send_otp_email(email, otp_code):
    subject = 'کد تأیید ثبت‌نام'
    html_message = f"""
    <html>
        <body>
            <h2>کد تأیید شما</h2>
            <p>کد تأیید ثبت‌نام شما:</p>
            <h1 style="color: #4CAF50; font-size: 32px;">{otp_code}</h1>
            <p>این کد تا ۵ دقیقه معتبر است.</p>
        </body>
    </html>
    """
    plain_message = f"کد تأیید شما: {otp_code}\nاین کد تا ۵ دقیقه معتبر است."
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        html_message=html_message,
        fail_silently=False,
    )