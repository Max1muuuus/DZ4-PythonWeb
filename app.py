import os
import secrets

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from flask_login import (
    LoginManager,
    login_required,
    login_user,
    logout_user,
)
from models import Category, DeliveryOrder, Dish, User, db


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-trattoria-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///trattoria.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@app.before_request
def validate_csrf_token():
    if request.method == 'POST':
        token = session.get('_csrf_token')
        submitted_token = request.form.get('_csrf_token', '')
        if not token or not secrets.compare_digest(token, submitted_token):
            abort(400)


@app.context_processor
def inject_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_urlsafe(32)
    return {'csrf_token': session['_csrf_token']}


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not username or not email or not password:
            flash("Будь ласка, заповніть усі поля.", "error")
            return render_template('register.html', username=username, email=email)
        if len(username) > 50 or len(email) > 120:
            flash("Ім'я має містити до 50 символів, а email — до 120.", "error")
            return render_template('register.html', username=username, email=email)

        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing_user:
            flash("Користувач із таким ім'ям або email вже існує.", "error")
            return render_template('register.html', username=username, email=email)

        user = User(username=username, email=email, role='user')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Реєстрацію успішно завершено. Вітаємо!", "success")
        return redirect(url_for('menu'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash("Ви успішно увійшли.", "success")
            return redirect(url_for('menu'))

        flash("Неправильний email або пароль.", "error")

    return render_template('login.html')


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash("Ви вийшли з облікового запису.", "success")
    return redirect(url_for('menu'))


@app.route('/delivery', methods=['GET', 'POST'])
def delivery():
    dishes = Dish.query.filter_by(is_available=True).order_by(Dish.name).all()
    selected_dish_id = request.values.get('dish_id', '')

    if request.method == 'POST':
        customer_name = request.form.get('customer_name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        notes = request.form.get('notes', '').strip()
        dish = db.session.get(Dish, request.form.get('dish_id', type=int))
        quantity = request.form.get('quantity', type=int)

        if (
            not customer_name
            or len(customer_name) > 100
            or not phone
            or len(phone) > 32
            or not address
            or len(address) > 255
            or not dish
            or not dish.is_available
            or not quantity
            or quantity < 1
            or quantity > 99
        ):
            flash("Перевірте заповнення форми та оберіть доступну страву.", "error")
            return render_template(
                'delivery.html',
                dishes=dishes,
                selected_dish_id=selected_dish_id,
                form_data=request.form,
            )

        order = DeliveryOrder(
            customer_name=customer_name,
            phone=phone,
            address=address,
            notes=notes,
            dish_id=dish.id,
            dish_name=dish.name,
            unit_price=dish.price,
            quantity=quantity,
        )
        db.session.add(order)
        db.session.commit()
        flash(f"Замовлення №{order.id} прийнято. Дякуємо!", "success")
        return redirect(url_for('delivery'))

    return render_template(
        'delivery.html',
        dishes=dishes,
        selected_dish_id=selected_dish_id,
        form_data=request.form,
    )


@app.route('/manage/dishes')
def manage_dishes():
    dishes = Dish.query.order_by(Dish.category_id, Dish.name).all()
    return render_template('manage_dishes.html', dishes=dishes)


def render_dish_form(dish=None):
    categories = Category.query.order_by(Category.name).all()
    if not categories:
        flash("Спочатку додайте категорію страви до бази даних.", "error")
        return redirect(url_for('manage_dishes'))
    return render_template(
        'dish_form.html',
        dish=dish,
        categories=categories,
        form_data=request.form,
        available_checked=(
            request.form.get('is_available') == 'on'
            if request.method == 'POST'
            else dish.is_available if dish else True
        ),
    )


def save_dish(dish):
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    emoji = request.form.get('emoji', '').strip() or '🍽️'
    category_id = request.form.get('category_id', type=int)
    price = request.form.get('price', type=int)
    category = db.session.get(Category, category_id)

    if (
        not name
        or len(name) > 50
        or len(emoji) > 8
        or price is None
        or price <= 0
        or not category
    ):
        flash("Перевірте назву, ціну, категорію та емодзі страви.", "error")
        return render_dish_form(dish)

    dish.name = name
    dish.description = description
    dish.emoji = emoji
    dish.price = price
    dish.category = category
    dish.is_available = request.form.get('is_available') == 'on'
    db.session.add(dish)
    db.session.commit()
    flash("Страву збережено.", "success")
    return redirect(url_for('manage_dishes'))


@app.route('/manage/dishes/new', methods=['GET', 'POST'])
def create_dish():
    if request.method == 'POST':
        return save_dish(Dish())
    return render_dish_form()


@app.route('/manage/dishes/<int:dish_id>/edit', methods=['GET', 'POST'])
def edit_dish(dish_id):
    dish = db.get_or_404(Dish, dish_id)
    if request.method == 'POST':
        return save_dish(dish)
    return render_dish_form(dish)


@app.route('/manage/dishes/<int:dish_id>/delete', methods=['POST'])
def delete_dish(dish_id):
    dish = db.get_or_404(Dish, dish_id)
    DeliveryOrder.query.filter_by(dish_id=dish.id).update(
        {DeliveryOrder.dish_id: None}
    )
    db.session.delete(dish)
    db.session.commit()
    flash("Страву видалено.", "success")
    return redirect(url_for('manage_dishes'))


@app.route('/')
def index():  # put application's code here
    return redirect(url_for("menu"))

@app.route('/menu')
@app.route('/menu/<slug>')
def menu(slug=None):
    categories = Category.query.order_by(Category.id).all()
    current = None
    query = Dish.query.filter_by(is_available=True)

    if slug:
        current = Category.query.filter_by(slug=slug).first_or_404()
        query = query.filter_by(category_id=current.id)

    q = request.args.get('q',"").strip()
    if q:
        query = query.filter(Dish.name.ilike(f"%{q}%"))

    dishes = query.order_by(Dish.category_id, Dish.name).all()
    return render_template('menu.html', categories=categories, current=current, dishes=dishes, q=q)

@app.route('/dish/<int:dish_id>')
def dish_detail(dish_id):
    dish = db.get_or_404(Dish, dish_id)
    return render_template('dish.html', dish=dish)

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


if __name__ == '__main__':
    app.run()
