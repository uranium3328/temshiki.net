import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO(async_mode='gevent', cors_allowed_origins='*')


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Войдите в аккаунт для доступа к этой странице.'
    login_manager.login_message_category = 'warning'

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    from .routes.auth import auth_bp
    from .routes.main import main_bp
    from .routes.listings import listings_bp
    from .routes.orders import orders_bp
    from .routes.chat import chat_bp
    from .routes.payments import payments_bp
    from .routes.profile import profile_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(listings_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(profile_bp)

    # импортируем SocketIO события
    from .routes import chat as chat_events  # noqa

    with app.app_context():
        db.create_all()

    return app
