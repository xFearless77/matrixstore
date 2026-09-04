from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'matrixstore_gizli_anahtar'  # Sepet oturumu için gerekli

# Örnek Ürün Listesi ve Stoklar
products = [
    {"id": 1, "name": "Siyah Matrix Tişört", "price": 450, "stock": 10},
    {"id": 2, "name": "Cyberpunk Sweatshirt", "price": 850, "stock": 5},
    {"id": 3, "name": "Yazılımcı Kupası", "price": 200, "stock": 15}
]

@app.route('/')
def home():
    if 'cart' not in session:
        session['cart'] = []
    
    # Sepetteki toplam ürün sayısı
    cart_count = len(session['cart'])
    return render_template('index.html', products=products, cart_count=cart_count)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    # Ürünü bul ve stoku kontrol et
    for product in products:
        if product['id'] == product_id:
            if product['stock'] > 0:
                product['stock'] -= 1  # Stoğu 1 azalt
                
                # Sepete ekle
                cart = session.get('cart', [])
                cart.append(product)
                session['cart'] = cart
            break
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

if __name__ == '__main__':
    app.run(debug=True)