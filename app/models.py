from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db


class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='buyer')  # buyer, seller, admin
    avatar = db.Column(db.String(256), default='')
    bio = db.Column(db.Text, default='')
    telegram = db.Column(db.String(100), default='')
    # Реквизиты продавца для получения оплаты
    payment_phone = db.Column(db.String(20), default='')   # номер телефона / СБП
    payment_card = db.Column(db.String(30), default='')    # номер карты
    payment_bank = db.Column(db.String(50), default='')    # банк (Сбер, Тинькофф и т.д.)
    payment_comment = db.Column(db.String(200), default='')  # доп. инструкция
    balance = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    listings = db.relationship('Listing', backref='seller', lazy=True,
                               foreign_keys='Listing.seller_id')
    purchases = db.relationship('Order', backref='buyer', lazy=True,
                                foreign_keys='Order.buyer_id')
    sales = db.relationship('Order', backref='seller_user', lazy=True,
                            foreign_keys='Order.seller_id')
    reviews_received = db.relationship('Review', backref='reviewed_user', lazy=True,
                                       foreign_keys='Review.reviewed_id')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def avg_rating(self):
        reviews = Review.query.filter_by(reviewed_id=self.id).all()
        if not reviews:
            return 0
        return round(sum(r.rating for r in reviews) / len(reviews), 1)

    @property
    def reviews_count(self):
        return Review.query.filter_by(reviewed_id=self.id).count()

    @property
    def is_seller(self):
        return self.role in ('seller', 'admin')

    @property
    def is_admin(self):
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.username}>'


class Listing(db.Model):
    __tablename__ = 'listing'

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    listing_type = db.Column(db.String(20), nullable=False)  # service, guide
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(256), default='')
    delivery_time = db.Column(db.String(100), default='')
    is_active = db.Column(db.Boolean, default=True)
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship('Order', backref='listing', lazy=True)
    reviews = db.relationship('Review', backref='listing', lazy=True)

    @property
    def avg_rating(self):
        if not self.reviews:
            return 0
        return round(sum(r.rating for r in self.reviews) / len(self.reviews), 1)

    @property
    def sales_count(self):
        return Order.query.filter_by(listing_id=self.id, status='completed').count()

    CATEGORIES = [
        ('earning', 'Заработок'),
        ('gaming', 'Игры'),
        ('tech', 'Технические услуги'),
        ('guides', 'Гайды и обучение'),
        ('promo', 'Продвижение'),
        ('scripts', 'Скрипты и боты'),
        ('consult', 'Консультации'),
        ('other', 'Другое'),
    ]

    def __repr__(self):
        return f'<Listing {self.title}>'


class Order(db.Model):
    __tablename__ = 'order'

    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id'), nullable=False)
    status = db.Column(db.String(30), default='pending')
    # pending -> paid -> in_progress -> completed | cancelled | disputed
    payment_id = db.Column(db.String(256), default='')
    amount = db.Column(db.Float, nullable=False)
    buyer_comment = db.Column(db.Text, default='')
    chat_room_id = db.Column(db.Integer, db.ForeignKey('chat_room.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chat_room = db.relationship('ChatRoom', backref='order', foreign_keys=[chat_room_id])
    review = db.relationship('Review', backref='order', uselist=False)

    STATUS_LABELS = {
        'pending':              ('Ожидает оплаты',          'warning'),
        'awaiting_confirm':     ('Ожидает подтверждения',   'orange'),
        'paid':                 ('Подтверждён',              'info'),
        'in_progress':          ('Выполняется',              'primary'),
        'completed':            ('Завершён',                 'success'),
        'cancelled':            ('Отменён',                  'secondary'),
        'disputed':             ('Спор',                     'danger'),
    }

    def __repr__(self):
        return f'<Order {self.id} {self.status}>'


class ChatRoom(db.Model):
    __tablename__ = 'chat_room'

    id = db.Column(db.Integer, primary_key=True)
    participant1_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    participant2_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    participant1 = db.relationship('User', foreign_keys=[participant1_id])
    participant2 = db.relationship('User', foreign_keys=[participant2_id])
    messages = db.relationship('Message', backref='room', lazy=True,
                               order_by='Message.created_at')

    def other_participant(self, current_user_id):
        if self.participant1_id == current_user_id:
            return self.participant2
        return self.participant1

    @property
    def last_message(self):
        return Message.query.filter_by(room_id=self.id).order_by(
            Message.created_at.desc()).first()

    def unread_count(self, user_id):
        return Message.query.filter_by(room_id=self.id, is_read=False).filter(
            Message.sender_id != user_id).count()


class Message(db.Model):
    __tablename__ = 'message'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_room.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', backref='sent_messages')


class Review(db.Model):
    __tablename__ = 'review'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False, unique=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reviewed_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reviewer = db.relationship('User', foreign_keys=[reviewer_id], backref='reviews_given')


class WithdrawalRequest(db.Model):
    __tablename__ = 'withdrawal_request'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    details = db.Column(db.Text, nullable=False)  # реквизиты
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='withdrawal_requests')
