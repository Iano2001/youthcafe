from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
import os
import time
import pymysql

app = Flask(__name__)
CORS(app)

# ------------------ DATABASE CONFIG ------------------
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DATABASE_URL = "mysql+pymysql://root:iano2001@localhost/youthcafe"

# Fix Railway MySQL URL
if DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# ------------------ INITIALIZE DB ------------------
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ------------------ MODELS ------------------
class CountryMember(db.Model):
    __tablename__ = "country_members"
    id = db.Column(db.Integer, primary_key=True)
    country_name = db.Column(db.String(100), nullable=False)
    country_code = db.Column(db.String(10), unique=True, nullable=False)
    members = db.Column(db.Integer, nullable=False)
    iso_a3 = db.Column(db.String(3), unique=True, nullable=False)
    hubs = db.relationship("Hub", backref="country", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "country_name": self.country_name,
            "country_code": self.country_code,
            "members": self.members,
            "iso_a3": self.iso_a3,
            "hubs": [hub.name for hub in self.hubs]
        }

class Hub(db.Model):
    __tablename__ = "hubs"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    country_id = db.Column(db.Integer, db.ForeignKey("country_members.id"), nullable=False)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "country_id": self.country_id}

# ------------------ ROUTES ------------------

from flask import send_from_directory

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    if path != "" and os.path.exists("build/" + path):
        return send_from_directory("build", path)
    else:
        return send_from_directory("build", "index.html")
    
@app.route("/countries", methods=["PUT"])
def update_country_members():
    data = request.get_json()
    country_name = data.get("country_name")
    members = data.get("members")
    country = CountryMember.query.filter_by(country_name=country_name).first()
    if not country:
        return jsonify({"error": "Country not found"}), 404
    country.members = members
    db.session.commit()
    return jsonify({"message": f"Members updated for {country.country_name}", "members": country.members}), 200

@app.route("/members", methods=["GET"])
def get_countries():
    countries = CountryMember.query.all()
    return jsonify([{"country_name": c.country_name, "iso_a3": c.iso_a3, "members": c.members} for c in countries])

@app.route("/addhub", methods=["POST"])
def add_hub():
    data = request.get_json()
    country_name = data.get("country_name")
    hub_name = data.get("hub_name")
    country = CountryMember.query.filter_by(country_name=country_name).first()
    if not country:
        return jsonify({"error": "Country not found"}), 404
    new_hub = Hub(name=hub_name, country_id=country.id)
    db.session.add(new_hub)
    db.session.commit()
    return jsonify({"message": "Hub added successfully", "hub": new_hub.to_dict()})

@app.route("/countries-hubs", methods=["GET"])
def get_countries_hubs():
    countries = CountryMember.query.all()
    return jsonify([{"country_name": c.country_name, "members": c.members, "hubs": [h.name for h in c.hubs]} for c in countries])


@app.route("/create-tables")
def create_tables():
    with app.app_context():
        db.create_all()
    return "Tables created successfully!"

@app.route("/")
def home():
    return "Hello Flask"

# ------------------ HELPER: WAIT FOR DATABASE ------------------
def wait_for_db(retries=5, delay=3):
    for i in range(retries):
        try:
            with app.app_context():
                db.session.execute("SELECT 1")
            print("Database connected!")
            return True
        except Exception as e:
            print(f"DB connection failed (attempt {i+1}/{retries}), retrying in {delay}s...")
            time.sleep(delay)
    print("Could not connect to DB. Exiting.")
    return False

# ------------------ START APP ------------------
if __name__ == "__main__":
    if wait_for_db():
        with app.app_context():
            db.create_all()  # ✅ safely create tables
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))