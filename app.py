from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
import os   # ✅ added

app = Flask(__name__)

# ✅ Railway-ready database config
DATABASE_URL = os.getenv("DATABASE_URL")

# Optional: fallback for local development
if not DATABASE_URL:
    DATABASE_URL = "mysql+pymysql://root:iano2001@localhost/youthcafe"

# Fix for Railway MySQL URL format (important)
if DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

CORS(app)

# Initialize database
db = SQLAlchemy(app)

# Initialize migration
migrate = Migrate(app, db)


# ------------------ MODEL ------------------
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
        return {
            "id": self.id,
            "name": self.name,
            "country_id": self.country_id
        }


# ------------------ ROUTES ------------------

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

    return jsonify({
        "message": f"Members updated for {country.country_name}",
        "members": country.members
    }), 200


@app.route("/members", methods=["GET"])
def get_countries():
    countries = CountryMember.query.all()

    results = []
    for country in countries:
        results.append({
            "country_name": country.country_name,
            "iso_a3": country.iso_a3,
            "members": country.members
        })

    return jsonify(results)


@app.route("/addhub", methods=["POST"])
def add_hub():
    data = request.get_json()

    country_name = data.get("country_name")
    hub_name = data.get("hub_name")

    country = CountryMember.query.filter_by(country_name=country_name).first()

    if not country:
        return jsonify({"error": "Country not found"}), 404

    new_hub = Hub(
        name=hub_name,
        country_id=country.id
    )

    db.session.add(new_hub)
    db.session.commit()

    return jsonify({
        "message": "Hub added successfully",
        "hub": new_hub.to_dict()
    })


@app.route("/countries-hubs", methods=["GET"])
def get_countries_hubs():
    countries = CountryMember.query.all()

    results = []
    for country in countries:
        results.append({
            "country_name": country.country_name,
            "members": country.members,
            "hubs": [hub.name for hub in country.hubs]
        })

    return jsonify(results)


@app.route("/")
def home():
    return "Hello Flask"


# ✅ Production-ready run
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)