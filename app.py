import os
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = 'matrixstore_gizli_anahtar'

db_path = os.path.join('/tmp', 'store.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- VERİTABANI MODELLERİ ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), nullable=False, default="Genel")
    image_url = db.Column(db.String(300), nullable=True)
    reviews = db.relationship('Review', backref='product', lazy=True)

    @property
    def average_rating(self):
        if not self.reviews:
            return 0
        return round(sum(r.rating for r in self.reviews) / len(self.reviews), 1)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    user_name = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False) # 1 - 5 Yıldız
    comment = db.Column(db.Text, nullable=False)

class Coupon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    discount_percent = db.Column(db.Integer, nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    items_summary = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default="Hazırlanıyor")

with app.app_context():
    db.create_all()
    if Product.query.count() == 0:
        p1 = Product(name="Siyah Matrix Tişört", price=450.0, stock=10, category="Giyim", image_url="https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=400")
        p2 = Product(name="Cyberpunk Sweatshirt", price=850.0, stock=5, category="Giyim", image_url="https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=400")
        p3 = Product(name="Yazılımcı Kupası", price=200.0, stock=15, category="Aksesuar", image_url="https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=400")
        db.session.add_all([p1, p2, p3])
        db.session.commit()

# --- MÜŞTERİ ROTALARI ---
@app.route('/')
def home():
    if 'cart' not in session:
        session['cart'] = []
    
    selected_category = request.args.get('category')
    search_query = request.args.get('q')
    
    query = Product.query
    if selected_category:
        query = query.filter_by(category=selected_category)
    if search_query:
        query = query.filter(Product.name.contains(search_query))
        
    products = query.all()
    categories = [c[0] for c in db.session.query(Product.category).distinct().all()]
    cart_count = len(session['cart'])
    user_name = session.get('user_name')
    
    return render_template('index.html', products=products, categories=categories, cart_count=cart_count, selected_category=selected_category, user_name=user_name, search_query=search_query)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_detail.html', product=product)

@app.route('/add_review/<int:product_id>', methods=['POST'])
def add_review(product_id):
    if 'user_name' not in session:
        flash("Yorum yapabilmek için giriş yapmalısınız!", "error")
        return redirect(url_for('login'))
        
    rating = int(request.form.get('rating'))
    comment = request.form.get('comment')
    
    new_rev = Review(product_id=product_id, user_name=session['user_name'], rating=rating, comment=comment)
    db.session.add(new_rev)
    db.session.commit()
    
    flash("Yorumunuz başarıyla eklendi!", "success")
    return redirect(url_for('product_detail', product_id=product_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash("Bu e-posta adresi zaten kayıtlı!", "error")
            return redirect(url_for('register'))
            
        hashed_pw = generate_password_hash(password, method='scrypt')
        new_user = User(name=name, email=email, password_hash=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        
        flash("Kayıt başarılı! Şimdi giriş yapabilirsiniz.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_email'] = user.email
            flash(f"Hoş geldin, {user.name}!", "success")
            return redirect(url_for('home'))
        else:
            flash("E-posta veya şifre hatalı!", "error")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    if product.stock > 0:
        product.stock -= 1
        db.session.commit()
        cart = session.get('cart', [])
        cart.append({"id": product.id, "name": product.name, "price": product.price, "image_url": product.image_url})
        session['cart'] = cart
    return redirect(url_for('home'))

@app.route('/cart')
def view_cart():
    cart = session.get('cart', [])
    subtotal = sum(item['price'] for item in cart)
    discount = session.get('discount', 0)
    total_price = subtotal * (1 - discount / 100)
    return render_template('cart.html', cart=cart, subtotal=subtotal, discount=discount, total_price=total_price)

@app.route('/apply_coupon', methods=['POST'])
def apply_coupon():
    code = request.form.get('code').strip().upper()
    coupon = Coupon.query.filter_by(code=code).first()
    if coupon:
        session['discount'] = coupon.discount_percent
        flash(f"%{coupon.discount_percent} indirim kuponu uygulandı!", "success")
    else:
        flash("Geçersiz kupon kodu!", "error")
    return redirect(url_for('view_cart'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        flash("Sipariş verebilmek için lütfen önce giriş yapın!", "error")
        return redirect(url_for('login'))
        
    cart = session.get('cart', [])
    if not cart:
        return redirect(url_for('home'))
        
    subtotal = sum(item['price'] for item in cart)
    discount = session.get('discount', 0)
    total_price = subtotal * (1 - discount / 100)
    
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        address = request.form.get('address')
        phone = request.form.get('phone')
        items_summary = ", ".join([item['name'] for item in cart])
        
        new_order = Order(
            user_id=session['user_id'],
            full_name=full_name,
            address=address,
            phone=phone,
            total_price=total_price,
            items_summary=items_summary
        )
        db.session.add(new_order)
        db.session.commit()

        session.pop('cart', None)
        session.pop('discount', None)
        
        flash("Siparişiniz başarıyla alındı! Teşekkür ederiz.", "success")
        return redirect(url_for('my_orders'))
        
    return render_template('checkout.html', total_price=total_price)

@app.route('/my_orders')
def my_orders():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    orders = Order.query.filter_by(user_id=session['user_id']).order_by(Order.id.desc()).all()
    return render_template('my_orders.html', orders=orders)

@app.route('/download_invoice/<int:order_id>')
def download_invoice(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    order = Order.query.get_or_404(order_id)
    if order.user_id != session['user_id']:
        return "Yetkisiz erişim", 403
        
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # PDF İçeriği
    p.setFont("Helvetica-Bold", 20)
    p.drawString(100, 750, "MATRIXSTORE RESMI SIPARIS FATURASI")
    p.line(100, 740, 500, 740)
    
    p.setFont("Helvetica", 12)
    p.drawString(100, 700, f"Siparis No: #{order.id}")
    p.drawString(100, 680, f"Musteri Ad Soyad: {order.full_name}")
    p.drawString(100, 660, f"Telefon: {order.phone}")
    p.drawString(100, 640, f"Adres: {order.address}")
    p.drawString(100, 610, f"Urunler: {order.items_summary}")
    
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, 560, f"Toplam Tutar: {order.total_price} TL")
    p.drawString(100, 540, f"Siparis Durumu: {order.status}")
    
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(100, 480, "Bizi tercih ettiginiz icin tesekkur ederiz!")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"Fatura_MatrixStore_Siparis_{order.id}.pdf", mimetype='application/pdf')

@app.route('/clear_cart')
def clear_cart():
    session.pop('cart', None)
    session.pop('discount', None)
    return redirect(url_for('home'))

# --- ADMIN PANELİ ROTALARI ---
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "123"

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
    coupons = Coupon.query.all()
    orders = Order.query.order_by(Order.id.desc()).all()
    
    # İSTATİSTİKLER (Ciro & Satış Adedi)
    total_revenue = sum(o.total_price for o in orders)
    total_sales_count = len(orders)
    
    return render_template('admin.html', products=products, coupons=coupons, orders=orders, total_revenue=total_revenue, total_sales_count=total_sales_count)

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
    category = request.form.get('category')
    image_url = request.form.get('image_url')
    
    new_p = Product(name=name, price=price, stock=stock, category=category, image_url=image_url)
    db.session.add(new_p)
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/add_coupon', methods=['POST'])
def add_coupon():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    code = request.form.get('code').strip().upper()
    discount = int(request.form.get('discount'))
    
    new_c = Coupon(code=code, discount_percent=discount)
    db.session.add(new_c)
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/update_order/<int:order_id>', methods=['POST'])
def update_order(order_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    status = request.form.get('status')
    order = Order.query.get_or_404(order_id)
    order.status = status
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(debug=True)