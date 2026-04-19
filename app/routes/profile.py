import os
import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from PIL import Image
from .. import db
from ..models import User, Listing, Review, WithdrawalRequest

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@profile_bp.route('/<username>')
def view(username):
    user = User.query.filter_by(username=username).first_or_404()
    listings = Listing.query.filter_by(seller_id=user.id, is_active=True).order_by(
        Listing.created_at.desc()).all()
    reviews = Review.query.filter_by(reviewed_id=user.id).order_by(
        Review.created_at.desc()).all()
    return render_template('profile/view.html', user=user, listings=listings, reviews=reviews)


@profile_bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
    if request.method == 'POST':
        bio = request.form.get('bio', '').strip()
        telegram = request.form.get('telegram', '').strip()
        role = request.form.get('role', current_user.role)

        if role in ('buyer', 'seller'):
            current_user.role = role
        current_user.bio = bio
        current_user.telegram = telegram

        # Реквизиты для оплаты (только продавцы)
        current_user.payment_phone = request.form.get('payment_phone', '').strip()
        current_user.payment_card = request.form.get('payment_card', '').strip()
        current_user.payment_bank = request.form.get('payment_bank', '').strip()
        current_user.payment_comment = request.form.get('payment_comment', '').strip()
        # Автоответчик
        current_user.auto_reply_enabled = bool(request.form.get('auto_reply_enabled'))
        current_user.auto_reply_text = request.form.get('auto_reply_text', '').strip()

        file = request.files.get('avatar')
        if file and file.filename and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'avatars')
            os.makedirs(upload_dir, exist_ok=True)
            path = os.path.join(upload_dir, filename)
            img = Image.open(file)
            img.thumbnail((200, 200))
            img.save(path)
            current_user.avatar = f'uploads/avatars/{filename}'

        db.session.commit()
        flash('Профиль обновлён!', 'success')
        return redirect(url_for('profile.view', username=current_user.username))

    return render_template('profile/edit.html')


@profile_bp.route('/withdraw', methods=['POST'])
@login_required
def withdraw():
    if not current_user.is_seller:
        abort(403)

    amount = request.form.get('amount', 0, type=float)
    details = request.form.get('details', '').strip()

    if amount <= 0 or amount > current_user.balance:
        flash('Некорректная сумма вывода.', 'danger')
        return redirect(url_for('main.dashboard'))

    if not details:
        flash('Укажите реквизиты для вывода.', 'danger')
        return redirect(url_for('main.dashboard'))

    current_user.balance -= amount
    wr = WithdrawalRequest(user_id=current_user.id, amount=amount, details=details)
    db.session.add(wr)
    db.session.commit()
    flash(f'Заявка на вывод {amount:.2f} ₽ создана. Обработка в течение 24 часов.', 'success')
    return redirect(url_for('main.dashboard'))
