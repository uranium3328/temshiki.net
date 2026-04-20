import random
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from .. import db
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


# ── Сброс пароля через код ──────────────────────────────────────────────────

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()

        if not user:
            flash('Пользователь с таким email не найден.', 'danger')
            return render_template('auth/forgot_password.html')

        # Генерируем 6-значный код
        code = str(random.randint(100000, 999999))
        session['reset_email']   = email
        session['reset_code']    = code
        session['reset_expires'] = (datetime.utcnow() + timedelta(minutes=10)).isoformat()

        # Если MAIL_USERNAME не задан — используем email пользователя как отправителя
        sender = current_app.config.get('MAIL_USERNAME') or email

        try:
            from flask_mail import Message
            from .. import mail
            msg = Message(
                subject='Код сброса пароля — Темщики.net',
                sender=sender,
                recipients=[email],
                html=f'''
<div style="font-family:sans-serif;max-width:420px">
  <h2 style="color:#8b5cf6">Темщики.net</h2>
  <p>Привет, <b>{user.username}</b>!</p>
  <p>Твой код для сброса пароля:</p>
  <div style="font-size:2.5rem;font-weight:bold;letter-spacing:8px;color:#8b5cf6;margin:16px 0">
    {code}
  </div>
  <p>Код действителен <b>10 минут</b>.<br>
  Если ты ничего не запрашивал — просто игнорируй это письмо.</p>
</div>
''',
            )
            mail.send(msg)
            flash('Код отправлен на твой email. Проверь папку "Спам" если не видишь.', 'success')
        except Exception as e:
            current_app.logger.warning(f'Ошибка отправки письма: {e}')
            flash('Не удалось отправить письмо. Почта не настроена на сервере.', 'danger')
            return render_template('auth/forgot_password.html')

        return redirect(url_for('auth.verify_reset_code'))

    return render_template('auth/forgot_password.html')


@auth_bp.route('/verify-code', methods=['GET', 'POST'])
def verify_reset_code():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    # Нет активного запроса — отправляем назад
    if 'reset_code' not in session:
        flash('Сначала введи email.', 'warning')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        entered_code = request.form.get('code', '').strip()
        password     = request.form.get('password', '')
        confirm      = request.form.get('confirm_password', '')

        # Проверяем срок действия
        expires = datetime.fromisoformat(session.get('reset_expires', '2000-01-01'))
        if datetime.utcnow() > expires:
            session.pop('reset_code', None)
            flash('Код истёк. Запроси новый.', 'danger')
            return redirect(url_for('auth.forgot_password'))

        if entered_code != session.get('reset_code'):
            flash('Неверный код. Попробуй ещё раз.', 'danger')
            return render_template('auth/verify_reset_code.html')

        if len(password) < 6:
            flash('Пароль должен быть не менее 6 символов.', 'danger')
            return render_template('auth/verify_reset_code.html')

        if password != confirm:
            flash('Пароли не совпадают.', 'danger')
            return render_template('auth/verify_reset_code.html')

        # Всё ок — меняем пароль
        email = session.pop('reset_email', None)
        session.pop('reset_code', None)
        session.pop('reset_expires', None)

        user = User.query.filter_by(email=email).first()
        if user:
            user.set_password(password)
            db.session.commit()
            flash('Пароль успешно изменён! Можешь войти.', 'success')
            return redirect(url_for('auth.login'))

        flash('Что-то пошло не так. Попробуй снова.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    return render_template('auth/verify_reset_code.html')
