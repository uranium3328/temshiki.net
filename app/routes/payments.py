import uuid
import hmac
import hashlib
import requests
from flask import Blueprint, redirect, url_for, flash, request, current_app, abort, render_template
from flask_login import login_required, current_user
from .. import db
from ..models import Order, Listing, ChatRoom

payments_bp = Blueprint('payments', __name__, url_prefix='/payment')


def cryptocloud_create_invoice(amount_rub, order_id, email=''):
    """Создаёт инвойс в CryptoCloud. Сумма в рублях — они конвертируют сами."""
    api_key = current_app.config['CRYPTOCLOUD_API_KEY']
    shop_id = current_app.config['CRYPTOCLOUD_SHOP_ID']

    resp = requests.post(
        'https://api.cryptocloud.plus/v2/invoice/create',
        headers={'Authorization': f'Token {api_key}'},
        json={
            'amount': amount_rub,
            'shop_id': shop_id,
            'currency': 'RUB',
            'order_id': str(order_id),
            'email': email or None,
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get('status') != 'success':
        raise ValueError(data.get('message', 'CryptoCloud error'))
    return data['result']  # {'link': '...', 'uuid': '...'}


@payments_bp.route('/create/<int:listing_id>', methods=['GET', 'POST'])
@login_required
def create_payment(listing_id):
    listing = Listing.query.get_or_404(listing_id)

    if not listing.is_active:
        abort(404)
    if listing.seller_id == current_user.id:
        flash('Нельзя купить своё объявление.', 'warning')
        return redirect(url_for('listings.detail', listing_id=listing_id))

    if request.method == 'GET':
        return render_template('payments/checkout.html', listing=listing)

    comment = request.form.get('comment', '').strip()

    # Создаём или находим чат между покупателем и продавцом
    chat_room = ChatRoom.query.filter(
        ((ChatRoom.participant1_id == current_user.id) &
         (ChatRoom.participant2_id == listing.seller_id)) |
        ((ChatRoom.participant1_id == listing.seller_id) &
         (ChatRoom.participant2_id == current_user.id))
    ).first()
    if not chat_room:
        chat_room = ChatRoom(
            participant1_id=current_user.id,
            participant2_id=listing.seller_id,
        )
        db.session.add(chat_room)
        db.session.flush()

    order = Order(
        buyer_id=current_user.id,
        seller_id=listing.seller_id,
        listing_id=listing_id,
        amount=listing.price,
        buyer_comment=comment,
        chat_room_id=chat_room.id,
    )
    db.session.add(order)
    db.session.flush()

    db.session.commit()
    # Перенаправляем на страницу с инструкцией по оплате
    return redirect(url_for('payments.pay_instructions', order_id=order.id))


@payments_bp.route('/instructions/<int:order_id>')
@login_required
def pay_instructions(order_id):
    """Страница с инструкцией по оплате — покупатель видит куда платить."""
    order = Order.query.get_or_404(order_id)
    if order.buyer_id != current_user.id:
        abort(403)
    if order.status != 'pending':
        return redirect(url_for('orders.detail', order_id=order_id))
    donate_link = current_app.config.get('DONATE_LINK', '')
    return render_template('payments/instructions.html', order=order, donate_link=donate_link)


@payments_bp.route('/confirm-sent/<int:order_id>', methods=['POST'])
@login_required
def confirm_sent(order_id):
    """Покупатель нажимает 'Я оплатил' — продавец получает уведомление."""
    order = Order.query.get_or_404(order_id)
    if order.buyer_id != current_user.id:
        abort(403)
    if order.status != 'pending':
        flash('Статус заказа уже изменён.', 'warning')
        return redirect(url_for('orders.detail', order_id=order_id))

    proof = request.form.get('proof', '').strip()  # скрин или комментарий
    order.status = 'awaiting_confirm'
    if proof:
        order.buyer_comment = (order.buyer_comment or '') + f'\n[Подтверждение оплаты]: {proof}'
    db.session.commit()
    flash('Отлично! Ждём подтверждения от продавца.', 'success')
    return redirect(url_for('orders.detail', order_id=order_id))


@payments_bp.route('/success/<int:order_id>')
@login_required
def success(order_id):
    order = Order.query.get_or_404(order_id)
    if order.buyer_id != current_user.id:
        abort(403)
    return render_template('payments/success.html', order=order)
