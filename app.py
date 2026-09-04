from flask import Flask, render_template

app = Flask(__name__)

urunler = [
    {"id": 1, "ad": "Python Otomasyon Botu", "fiyat": 250, "stok": 10},
    {"id": 2, "ad": "E-Ticaret HTML Teması", "fiyat": 150, "stok": 5},
    {"id": 3, "ad": "C++ Başlangıç Rehberi", "fiyat": 100, "stok": 20}
]

@app.route("/")
def anasayfa():
    return render_template("index.html", urun_listesi=urunler)

if __name__ == "__main__":
    app.run(debug=True)