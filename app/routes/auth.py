from flask import Blueprint, render_template, redirect, url_for, flash, request
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
