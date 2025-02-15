# Instagram backend clone

## Prerequisites
### Create virtual envirenment and activate it.
```shell
python3 -m venv venv  # Creates virtual envirenment

source venv/bin/activate  # Activates virtual envirenment
```

### Create `.env` file and enter following information in it.
```python
SECRET_KEY  # secret key inside your django settings file
DEBUG  # True in development env, False in Production
DB_NAME  # created database name
DB_USER
DB_PASSWORD
DB_HOST  # localhost
DB_PORT  # 5432 if you are using postgresql
ACCOUNT_SID  # information taken from twilio
AUTH_TOKEN  # information taken from twilio
TWILIO_FROM_NUMBER  # information taken from twilio
EMAIL_HOST_USER  # your email address
EMAIL_HOST_PASSWORD  # password taken from your google account apps
```

### Install requirements.
```shell
pip install -r requirements.txt
```

### Run migrations.
```shell
python manage.py makemigrations
python manage.py migrate
```

### Run server
```shell
python manage.py runserver
```

### In another teerminal tab, run celery. You must have rabbitmq installed.
```shell
celery -A instagram_clone worker --loglevel=INFO
```

#### You are all done. Happy coding🥳