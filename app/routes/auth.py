from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from .. import db, mail
from ..models import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        role = request.form.get('role', 'buyer')

        if not username or not email or not password:
            flash('Заполните все поля.', 'danger')
            return render_template('auth/register.html')

        if password != confirm:
            flash('Пароли не совпадают.', 'danger')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('Пароль должен быть не менее 6 символов.', 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(username=username).first():
            flash('Это имя пользователя уже занято.', 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('Этот email уже зарегистрирован.', 'danger')
            return render_template('auth/register.html')

        if role not in ('buyer', 'seller'):
            role = 'buyer'

        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash(f'Добро пожаловать, {username}!', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        login_val = request.form.get('login', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = User.query.filter(
            (User.username == login_val) | (User.email == login_val)
        ).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))

        flash('Неверный логин или пароль.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из аккаунта.', 'info')
    return redirect(url_for('main.index'))


def _get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()

        # Всегда показываем одно сообщение — чтобы не светить, есть ли такой email
        flash('Если такой email зарегистрирован, письмо со ссылкой уже отправлено.', 'info')

        if user:
            token = _get_serializer().dumps(email, salt='password-reset')
            reset_url = url_for('auth.reset_password', token=token, _external=True)

            try:
                msg = Message(
                    subject='Сброс пароля — Темщики.net',
                    recipients=[email],
                    html=f'''
<p>Привет, {user.username}!</p>
<p>Ты запросил сброс пароля на <strong>Темщики.net</strong>.</p>
<p><a href="{reset_url}" style="color:#8b5cf6">Нажми здесь чтобы сбросить пароль</a></p>
<p>Ссылка действительна 1 час. Если ты не запрашивал сброс — просто игнорируй это письмо.</p>
<hr>
<small>Темщики.net</small>
''',
                )
                mail.send(msg)
            except Exception:
                # Если почта не настроена — просто логируем, не ломаем сайт
                current_app.logger.warning('Не удалось отправить письмо сброса пароля.')

        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    try:
        email = _get_serializer().loads(token, salt='password-reset', max_age=3600)
    except (SignatureExpired, BadSignature):
        flash('Ссылка недействительна или истекла. Запроси новую.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash('Пользователь не найден.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if len(password) < 6:
            flash('Пароль должен быть не менее 6 символов.', 'danger')
            return render_template('auth/reset_password.html', token=token)

        if password != confirm:
            flash('Пароли не совпадают.', 'danger')
            return render_template('auth/reset_password.html', token=token)

        user.set_password(password)
        db.session.commit()
        flash('Пароль успешно изменён! Можешь войти.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token)
