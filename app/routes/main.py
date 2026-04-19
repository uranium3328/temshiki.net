from flask import Blueprint, render_template
from flask_login import login_required, current_user
from ..models import Listing, Order, ChatRoom, Review, User

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    featured = Listing.query.filter_by(is_active=True).order_by(
        Listing.views.desc()).limit(8).all()
    top_sellers = User.query.filter_by(role='seller').limit(6).all()
    total_listings = Listing.query.filter_by(is_active=True).count()
    total_sellers = User.query.filter(User.role.in_(['seller', 'admin'])).count()
    total_orders = Order.query.filter_by(status='completed').count()
    return render_template('index.html',
                           featured=featured,
                           top_sellers=top_sellers,
                           total_listings=total_listings,
                           total_sellers=total_sellers,
                           total_orders=total_orders)


@main_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_seller:
        orders = Order.query.filter_by(seller_id=current_user.id).order_by(
            Order.created_at.desc()).limit(10).all()
        listings = Listing.query.filter_by(seller_id=current_user.id).order_by(
            Listing.created_at.desc()).all()
        income = sum(o.amount * 0.9 for o in
                     Order.query.filter_by(seller_id=current_user.id, status='completed').all())
    else:
        orders = Order.query.filter_by(buyer_id=current_user.id).order_by(
            Order.created_at.desc()).limit(10).all()
        listings = []
        income = 0

    unread_chats = 0
    rooms = ChatRoom.query.filter(
        (ChatRoom.participant1_id == current_user.id) |
        (ChatRoom.participant2_id == current_user.id)
    ).all()
    for room in rooms:
        unread_chats += room.unread_count(current_user.id)

    return render_template('dashboard.html',
                           orders=orders,
                           listings=listings,
                           income=income,
                           unread_chats=unread_chats)
