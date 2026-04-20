import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///marketplace.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CRYPTOCLOUD_API_KEY = os.environ.get('CRYPTOCLOUD_API_KEY', '')
    CRYPTOCLOUD_SHOP_ID = os.environ.get('CRYPTOCLOUD_SHOP_ID', '')
    BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')
    # Ссылка куда покупатель переводит деньги (DonationAlerts, крипто-кошелёк и т.д.)
    DONATE_LINK = os.environ.get('DONATE_LINK', '')

    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    PLATFORM_COMMISSION = 0.10  # 10% комиссия платформы

    # Почта для сброса пароля
    MAIL_SERVER   = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT     = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS  = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@temshiki.net')
