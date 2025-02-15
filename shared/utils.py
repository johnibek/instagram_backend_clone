import re
import threading
import phonenumbers
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from rest_framework.exceptions import ValidationError


email_regex = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')
username_regex = re.compile(r'^[a-zA-Z0-9_.-]+$')
# phone_number_regex = re.compile(r"^(\+?[0-9]{1,3})?[-.\s]?(\(?[0-9]{3}\)?)[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$")

def check_user_input(user_input):
    try:
        phone_number_obj = phonenumbers.parse(user_input)
    except:
        phone_number_obj = None

    if re.fullmatch(email_regex, user_input):
        user_input = 'email'

    elif phone_number_obj and phonenumbers.is_valid_number(phone_number_obj):
        user_input = 'phone_number'

    elif re.fullmatch(username_regex, user_input):
        user_input = 'username'

    else:
        detail = {
            'success': False,
            'message': 'Invalid data. Please enter email or phone number.'
        }
        raise ValidationError(detail=detail)

    return user_input


class EmailThread(threading.Thread):
    def __init__(self, email):
        super().__init__()
        self.email = email

    def run(self):
        self.email.send()


class Email:
    @staticmethod
    def send_email(data):
        email = EmailMessage(
            subject=data['subject'],
            body=data['body'],
            to=[data['to_email']]
        )
        if data.get('content_type') == 'html':
            email.content_subtype = 'html'
        EmailThread(email).start()


def send_email(email, code):
    html_content = render_to_string(
        'email/authentication/activate_account.html',
        context={'code': code}
    )
    Email.send_email(
        {
            'subject': 'Registration',
            'body': html_content,
            'to_email': email,
            'content_type': 'html'
        }
    )
