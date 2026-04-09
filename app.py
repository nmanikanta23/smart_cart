from flask import Flask, request, jsonify, render_template, redirect, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import func

app = Flask(__name__)
app.secret_key = "secret123"

#codes
#dcaad45
#27a1d8b4
#1d84be6b
# ---------------- DATABASE ----------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
db = SQLAlchemy(app)

# ---------------- MODELS ----------------

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    price = db.Column(db.Float)
    uid = db.Column(db.String(50), unique=True)
    quantity = db.Column(db.Integer)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100))
    qty = db.Column(db.Integer)
    total = db.Column(db.Float)
    date = db.Column(db.DateTime, default=datetime.utcnow)

# ---------------- GLOBAL CART ----------------
cart = {}

# ---------------- HOME ----------------
@app.route('/')
def home():
    return render_template("index.html")

# ---------------- RFID SCAN API ----------------
@app.route('/scan', methods=['POST'])
def scan():
    data = request.json
    uid = data.get("uid", "").replace(" ", "").upper()

    item = Item.query.filter_by(uid=uid).first()

    if item:
        if item.name in cart:
            if cart[item.name]['qty'] < item.quantity:
                cart[item.name]['qty'] += 1
        else:
            cart[item.name] = {"price": item.price, "qty": 1}

        print("Added:", item.name)
        return jsonify({"status": "ok", "item": item.name})
    else:
        print("Invalid RFID")
        return jsonify({"status": "invalid"}), 400

# ---------------- USER ----------------
@app.route('/user')
def user():
    total = sum(v['price'] * v['qty'] for v in cart.values())
    return render_template("user.html", cart=cart, total=total)

# ➕ Increase
@app.route('/increase/<name>')
def increase(name):
    item = Item.query.filter_by(name=name).first()
    if name in cart and item:
        if cart[name]['qty'] < item.quantity:
            cart[name]['qty'] += 1
    return redirect('/user')

# ➖ Decrease
@app.route('/decrease/<name>')
def decrease(name):
    if name in cart:
        cart[name]['qty'] -= 1
        if cart[name]['qty'] <= 0:
            del cart[name]
    return redirect('/user')

# 💳 PAY
@app.route('/pay')
def pay():
    global cart

    for item_name, data in cart.items():
        item = Item.query.filter_by(name=item_name).first()

        if item and item.quantity >= data['qty']:
            item.quantity -= data['qty']

            db.session.add(Transaction(
                item_name=item_name,
                qty=data['qty'],
                total=data['price'] * data['qty']
            ))

    db.session.commit()
    cart = {}
    return redirect('/user')

# ---------------- ADMIN LOGIN ----------------
ADMIN_USER = "admin"
ADMIN_PASS = "1234"

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        user = request.form['username']
        pwd = request.form['password']

        if user == ADMIN_USER and pwd == ADMIN_PASS:
            session['admin'] = True
            return redirect('/admin')

    return render_template("login.html")

# ---------------- ADMIN PANEL ----------------
@app.route('/admin')
def admin():
    if 'admin' not in session:
        return redirect('/admin_login')

    items = Item.query.all()
    return render_template("admin.html", items=items)

# ➕ ADD ITEM
@app.route('/add', methods=['POST'])
def add():
    if 'admin' not in session:
        return redirect('/admin_login')

    name = request.form['name']
    price = float(request.form['price'])
    uid = request.form['uid'].replace(" ", "").upper()
    quantity = int(request.form['quantity'])

    new_item = Item(name=name, price=price, uid=uid, quantity=quantity)
    db.session.add(new_item)
    db.session.commit()

    return redirect('/admin')

# ✏ UPDATE ITEM
@app.route('/update/<int:id>', methods=['POST'])
def update(id):
    if 'admin' not in session:
        return redirect('/admin_login')

    item = Item.query.get(id)

    item.name = request.form['name']
    item.price = float(request.form['price'])
    item.quantity = int(request.form['quantity'])

    db.session.commit()
    return redirect('/admin')

# ❌ DELETE ITEM
@app.route('/delete/<int:id>')
def delete(id):
    if 'admin' not in session:
        return redirect('/admin_login')

    item = Item.query.get(id)
    db.session.delete(item)
    db.session.commit()

    return redirect('/admin')

# ---------------- TRANSACTIONS ----------------
@app.route('/transactions')
def transactions():
    if 'admin' not in session:
        return redirect('/admin_login')

    data = Transaction.query.order_by(Transaction.date.desc()).all()
    return render_template("transactions.html", data=data)

# ---------------- ANALYTICS ----------------
@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect('/admin_login')

    return render_template("dashboard.html")

@app.route('/stats/<mode>')
def stats(mode):
    from sqlalchemy import func

    if mode == "daily":
        group = func.date(Transaction.date)

    elif mode == "monthly":
        group = func.strftime("%Y-%m", Transaction.date)

    elif mode == "yearly":
        group = func.strftime("%Y", Transaction.date)

    elif mode == "weekly":
        group = func.strftime("%Y-%W", Transaction.date)

    else:
        group = func.date(Transaction.date)

    data = db.session.query(
        group,
        func.sum(Transaction.total)
    ).group_by(group).all()

    labels = [str(d[0]) for d in data]
    values = [d[1] for d in data]

    return jsonify({"labels": labels, "values": values})

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/')

# ---------------- RUN ----------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True, host='0.0.0.0')