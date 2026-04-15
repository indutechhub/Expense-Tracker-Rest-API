from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime
from sqlalchemy import func, extract

app = Flask(__name__)

#  Configuration
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///expenses.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = "secret-key"

#  Initialize
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    amount = db.Column(db.Float)
    category = db.Column(db.String(50))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

#  Create Database
with app.app_context():
    db.drop_all()
    db.create_all()

# Register
@app.route("/register", methods=["POST"])
def register():
    data = request.json

    if not data.get("username") or not data.get("password"):
        return jsonify({"error": "Missing fields"}), 400

    hashed_pw = bcrypt.generate_password_hash(data["password"]).decode("utf-8")

    user = User(username=data["username"], password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User created"})

# Login
@app.route("/login", methods=["POST"])
def login():
    data = request.json

    user = User.query.filter_by(username=data["username"]).first()

    if user and bcrypt.check_password_hash(user.password, data["password"]):
        token = create_access_token(identity=str(user.id))
        return jsonify({"access_token": token})

    return jsonify({"message": "Invalid credentials"}), 401

#  Add Expense
@app.route("/expenses", methods=["POST"])
@jwt_required()
def add_expense():
    user_id = int(get_jwt_identity())
    data = request.json

    if not data.get("title") or not data.get("amount"):
        return jsonify({"error": "Missing fields"}), 400

    expense = Expense(
        title=data["title"],
        amount=data["amount"],
        category=data.get("category", "General"),
        user_id=user_id
    )

    db.session.add(expense)
    db.session.commit()

    return jsonify({"message": "Expense added"})

#  Get All Expenses
@app.route("/expenses", methods=["GET"])
@jwt_required()
def get_expenses():
    user_id = int(get_jwt_identity())
    expenses = Expense.query.filter_by(user_id=user_id).all()

    result = []
    for e in expenses:
        result.append({
            "id": e.id,
            "title": e.title,
            "amount": e.amount,
            "category": e.category,
            "date": e.date.strftime("%Y-%m-%d")
        })

    return jsonify(result)

#  Update Expense
@app.route("/expenses/<int:id>", methods=["PUT"])
@jwt_required()
def update_expense(id):
    data = request.json
    expense = Expense.query.get(id)

    if not expense:
        return jsonify({"error": "Expense not found"}), 404

    expense.title = data.get("title", expense.title)
    expense.amount = data.get("amount", expense.amount)
    expense.category = data.get("category", expense.category)

    db.session.commit()

    return jsonify({"message": "Updated"})

# Delete Expense
@app.route("/expenses/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_expense(id):
    expense = Expense.query.get(id)

    if not expense:
        return jsonify({"error": "Expense not found"}), 404

    db.session.delete(expense)
    db.session.commit()

    return jsonify({"message": "Deleted"})

# Monthly Summary
@app.route("/summary/<int:month>", methods=["GET"])
@jwt_required()
def monthly_summary(month):
    user_id = int(get_jwt_identity())
    total = db.session.query(func.sum(Expense.amount)).filter(
        Expense.user_id == user_id,
        extract('month', Expense.date) == month
    ).scalar()

    return jsonify({"total_spent": total or 0})

# Run App
if __name__ == "__main__":
    app.run(debug=True)

