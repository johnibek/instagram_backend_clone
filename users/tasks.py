from instagram_clone.celery import app
from decouple import config
from twilio.rest import Client


@app.task()
def send_phone_verification_code(phone_number, code):
    account_sid = config('ACCOUNT_SID')
    auth_token = config('AUTH_TOKEN')

    client = Client(account_sid, auth_token)

    # Sending verification code to user
    message = client.messages.create(
        to=f'{phone_number}',
        from_=f'{config('TWILIO_FROM_NUMBER')}',
        body=f'Your instagram verification code: {code}'
    )

