import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'matrixstore_gizli_anahtar'

# Veritabanı Ayarları (SQLite)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'store.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- VERİTABANI MODELLERİ ---
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)

# Veritabanını oluştur ve başlangıç ürünlerini ekle
with app.app_context():
    db.create_all()
    if Product.query.count() == 0:
        p1 = Product(name="Siyah Matrix Tişört", price=450.0, stock=10)
        p2 = Product(name="Cyberpunk Sweatshirt", price=850.0, stock=5)
        p3 = Product(name="Yazılımcı Kupası", price=200.0, stock=15)
        db.session.add_all([p1, p2, p3])
        db.session.commit()

# --- MÜŞTERİ ROTALARI ---
@app.route('/')
def home():
    if 'cart' not in session:
        session['cart'] = []
    
    products = Product.query.all()
    cart_count = len(session['cart'])
    return render_template('index.html', products=products, cart_count=cart_count)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    if product.stock > 0:
        product.stock -= 1  # Stok veritabanında 1 düşer (KALICI)
        db.session.commit()
        
        cart = session.get('cart', [])
        cart.append({"id": product.id, "name": product.name, "price": product.price})
        session['cart'] = cart
    return redirect(url_for('home'))

@app.route('/cart')
def view_cart():
    cart = session.get('cart', [])
    total_price = sum(item['price'] for item in cart)
    return render_template('cart.html', cart=cart, total_price=total_price)

@app.route('/clear_cart')
def clear_cart():
    session.pop('cart', None)
    return redirect(url_for('home'))

# --- ADMIN PANELİ ROTALARI ---
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "123"  # İstediğin şifreyle değiştirebilirsin

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_panel'))
        else:
            flash("Hatalı kullanıcı adı veya şifre!")
    return render_template('admin_login.html')

@app.route('/admin')
def admin_panel():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    products = Product.query.all()
    return render_template('admin.html', products=products)

@app.route('/admin/update_stock/<int:product_id>', methods=['POST'])
def update_stock(product_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    new_stock = int(request.form.get('stock'))
    product = Product.query.get_or_404(product_id)
    product.stock = new_stock
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/add_product', methods=['POST'])
def add_product():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    name = request.form.get('name')
    price = float(request.form.get('price'))
    stock = int(request.form.get('stock'))
    
    new_p = Product(name=name, price=price, stock=stock)
    db.session.add(new_p)
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(debug=True)