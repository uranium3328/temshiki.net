import os
import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from PIL import Image
from .. import db
from ..models import Listing, Review, User, Order

listings_bp = Blueprint('listings', __name__, url_prefix='/listings')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file, folder='listings'):
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], folder)
    os.makedirs(upload_dir, exist_ok=True)
    path = os.path.join(upload_dir, filename)
    img = Image.open(file)
    img.thumbnail((800, 600))
    img.save(path)
    return f'uploads/{folder}/{filename}'


@listings_bp.route('/')
def catalog():
    category = request.args.get('category', '')
    listing_type = request.args.get('type', '')
    search = request.args.get('q', '').strip()
    sort = request.args.get('sort', 'new')
    page = request.args.get('page', 1, type=int)

    query = Listing.query.filter_by(is_active=True)

    if category:
        query = query.filter_by(category=category)
    if listing_type:
        query = query.filter_by(listing_type=listing_type)
    if search:
        query = query.filter(Listing.title.ilike(f'%{search}%'))

    if sort == 'price_asc':
        query = query.order_by(Listing.price.asc())
    elif sort == 'price_desc':
        query = query.order_by(Listing.price.desc())
    elif sort == 'popular':
        query = query.order_by(Listing.views.desc())
    else:
        query = query.order_by(Listing.created_at.desc())

    listings = query.paginate(page=page, per_page=12, error_out=False)
    categories = Listing.CATEGORIES

    return render_template('listings/catalog.html',
                           listings=listings,
                           categories=categories,
                           current_category=category,
                           current_type=listing_type,
                           search=search,
                           sort=sort)


@listings_bp.route('/<int:listing_id>')
def detail(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if not listing.is_active and (not current_user.is_authenticated or
                                   current_user.id != listing.seller_id):
        abort(404)
    listing.views += 1
    db.session.commit()
    reviews = Review.query.filter_by(listing_id=listing_id).order_by(
        Review.created_at.desc()).all()
    return render_template('listings/detail.html', listing=listing, reviews=reviews)


@listings_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if not current_user.is_seller:
        flash('Для создания объявлений нужно быть продавцом.', 'warning')
        return redirect(url_for('profile.edit'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '')
        listing_type = request.form.get('listing_type', 'service')
        price = request.form.get('price', 0)
        delivery_time = request.form.get('delivery_time', '').strip()

        if not title or not description or not category:
            flash('Заполните все обязательные поля.', 'danger')
            return render_template('listings/create.html', categories=Listing.CATEGORIES)

        try:
            price = float(price)
            if price <= 0:
                raise ValueError
        except (ValueError, TypeError):
            flash('Укажите корректную цену.', 'danger')
            return render_template('listings/create.html', categories=Listing.CATEGORIES)

        image_path = ''
        file = request.files.get('image')
        if file and file.filename and allowed_file(file.filename):
            image_path = save_image(file)

        listing = Listing(
            seller_id=current_user.id,
            title=title,
            description=description,
            category=category,
            listing_type=listing_type,
            price=price,
            delivery_time=delivery_time,
            image=image_path,
        )
        db.session.add(listing)
        db.session.commit()
        flash('Объявление опубликовано!', 'success')
        return redirect(url_for('listings.detail', listing_id=listing.id))

    return render_template('listings/create.html', categories=Listing.CATEGORIES)


@listings_bp.route('/<int:listing_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if listing.seller_id != current_user.id and not current_user.is_admin:
        abort(403)

    if request.method == 'POST':
        listing.title = request.form.get('title', '').strip()
        listing.description = request.form.get('description', '').strip()
        listing.category = request.form.get('category', listing.category)
        listing.listing_type = request.form.get('listing_type', listing.listing_type)
        listing.delivery_time = request.form.get('delivery_time', '').strip()
        listing.is_active = bool(request.form.get('is_active'))

        try:
            listing.price = float(request.form.get('price', 0))
        except (ValueError, TypeError):
            flash('Некорректная цена.', 'danger')
            return render_template('listings/edit.html', listing=listing,
                                   categories=Listing.CATEGORIES)

        file = request.files.get('image')
        if file and file.filename and allowed_file(file.filename):
            listing.image = save_image(file)

        db.session.commit()
        flash('Объявление обновлено.', 'success')
        return redirect(url_for('listings.detail', listing_id=listing.id))

    return render_template('listings/edit.html', listing=listing, categories=Listing.CATEGORIES)


@listings_bp.route('/<int:listing_id>/delete', methods=['POST'])
@login_required
def delete(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if listing.seller_id != current_user.id and not current_user.is_admin:
        abort(403)
    listing.is_active = False
    db.session.commit()
    flash('Объявление удалено.', 'info')
    return redirect(url_for('main.dashboard'))
