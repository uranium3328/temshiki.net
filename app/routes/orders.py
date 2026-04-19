from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from .. import db
from ..models import Order, Listing, ChatRoom, Review, User

orders_bp = Blueprint('orders', __name__, url_prefix='/orders')


@orders_bp.route('/')
@login_required
def list_orders():
    tab = request.args.get('tab', 'all')
    if current_user.is_seller:
        base_q = Order.query.filter_by(seller_id=current_user.id)
    else:
        base_q = Order.query.filter_by(buyer_id=current_user.id)

    if tab == 'active':
        orders = base_q.filter(Order.status.in_(['paid', 'in_progress'])).order_by(
            Order.created_at.desc()).all()
    elif tab == 'completed':
        orders = base_q.filter_by(status='completed').order_by(
            Order.created_at.desc()).all()
    elif tab == 'pending':
        orders = base_q.filter_by(status='pending').order_by(
            Order.created_at.desc()).all()
    else:
        orders = base_q.order_by(Order.created_at.desc()).all()

    return render_template('orders/list.html', orders=orders, tab=tab)


@orders_bp.route('/<int:order_id>')
@login_required
def detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.buyer_id != current_user.id and order.seller_id != current_user.id \
            and not current_user.is_admin:
        abort(403)
    return render_template('orders/detail.html', order=order)


@orders_bp.route('/<int:order_id>/confirm-payment', methods=['POST'])
@login_required
def confirm_payment(order_id):
    """Продавец подтверждает что получил оплату."""
    order = Order.query.get_or_404(order_id)
    if order.seller_id != current_user.id:
        abort(403)
    if order.status != 'awaiting_confirm':
        flash('Нечего подтверждать.', 'warning')
        return redirect(url_for('orders.detail', order_id=order_id))
    order.status = 'paid'
    db.session.commit()
    flash('Оплата подтверждена! Теперь возьми заказ в работу.', 'success')
    return redirect(url_for('orders.detail', order_id=order_id))


@orders_bp.route('/<int:order_id>/reject-payment', methods=['POST'])
@login_required
def reject_payment(order_id):
    """Продавец отклоняет — оплата не поступила."""
    order = Order.query.get_or_404(order_id)
    if order.seller_id != current_user.id:
        abort(403)
    if order.status != 'awaiting_confirm':
        flash('Нечего отклонять.', 'warning')
        return redirect(url_for('orders.detail', order_id=order_id))
    order.status = 'pending'
    db.session.commit()
    flash('Оплата отклонена. Покупатель может попробовать снова.', 'info')
    return redirect(url_for('orders.detail', order_id=order_id))


@orders_bp.route('/<int:order_id>/accept', methods=['POST'])
@login_required
def accept(order_id):
    order = Order.query.get_or_404(order_id)
    if order.seller_id != current_user.id:
        abort(403)
    if order.status != 'paid':
        flash('Сначала подтверди оплату.', 'warning')
        return redirect(url_for('orders.detail', order_id=order_id))
    order.status = 'in_progress'
    db.session.commit()
    flash('Вы взяли заказ в работу.', 'success')
    return redirect(url_for('orders.detail', order_id=order_id))


@orders_bp.route('/<int:order_id>/complete', methods=['POST'])
@login_required
def complete(order_id):
    order = Order.query.get_or_404(order_id)
    if order.seller_id != current_user.id:
        abort(403)
    if order.status not in ('paid', 'in_progress'):
        flash('Нельзя завершить этот заказ.', 'warning')
        return redirect(url_for('orders.detail', order_id=order_id))

    order.status = 'completed'
    # Начисляем продавцу 90% суммы
    from flask import current_app
    commission = current_app.config.get('PLATFORM_COMMISSION', 0.10)
    seller = User.query.get(order.seller_id)
    seller.balance += order.amount * (1 - commission)
    db.session.commit()
    flash('Заказ завершён! Средства зачислены на баланс.', 'success')
    return redirect(url_for('orders.detail', order_id=order_id))


@orders_bp.route('/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel(order_id):
    order = Order.query.get_or_404(order_id)
    if order.buyer_id != current_user.id and order.seller_id != current_user.id \
            and not current_user.is_admin:
        abort(403)
    if order.status not in ('pending', 'paid'):
        flash('Нельзя отменить этот заказ.', 'warning')
        return redirect(url_for('orders.detail', order_id=order_id))
    order.status = 'cancelled'
    db.session.commit()
    flash('Заказ отменён.', 'info')
    return redirect(url_for('orders.detail', order_id=order_id))


@orders_bp.route('/<int:order_id>/dispute', methods=['POST'])
@login_required
def dispute(order_id):
    order = Order.query.get_or_404(order_id)
    if order.buyer_id != current_user.id:
        abort(403)
    if order.status not in ('paid', 'in_progress'):
        flash('Нельзя открыть спор.', 'warning')
        return redirect(url_for('orders.detail', order_id=order_id))
    order.status = 'disputed'
    db.session.commit()
    flash('Спор открыт. Администратор рассмотрит ситуацию.', 'warning')
    return redirect(url_for('orders.detail', order_id=order_id))


@orders_bp.route('/<int:order_id>/review', methods=['POST'])
@login_required
def leave_review(order_id):
    order = Order.query.get_or_404(order_id)
    if order.buyer_id != current_user.id:
        abort(403)
    if order.status != 'completed':
        flash('Отзыв можно оставить только после завершения заказа.', 'warning')
        return redirect(url_for('orders.detail', order_id=order_id))
    if order.review:
        flash('Вы уже оставили отзыв.', 'warning')
        return redirect(url_for('orders.detail', order_id=order_id))

    rating = request.form.get('rating', 5, type=int)
    comment = request.form.get('comment', '').strip()
    rating = max(1, min(5, rating))

    review = Review(
        order_id=order_id,
        reviewer_id=current_user.id,
        reviewed_id=order.seller_id,
        listing_id=order.listing_id,
        rating=rating,
        comment=comment,
    )
    db.session.add(review)
    db.session.commit()
    flash('Отзыв опубликован!', 'success')
    return redirect(url_for('orders.detail', order_id=order_id))
