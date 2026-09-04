from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
from routes import routes
from models import db
import os

# Load environment variables before reading them
load_dotenv()

app = Flask(__name__)

database_uri = os.environ.get("DATABASE_URI")
jwt_secret = os.environ.get("JWT_SECRET")
frontend_url = os.environ.get("FRONTEND_URL")

# Flask configuration
app.config["SQLALCHEMY_DATABASE_URI"] = database_uri

# JWT configuration
app.config["JWT_SECRET_KEY"] = jwt_secret

# Access token expiration: 24 hours
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 60 * 60 * 24

# Refresh token expiration: 30 days
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = 60 * 60 * 24 * 30


# Initialize extensions
db.init_app(app)

jwt = JWTManager(app)


# Allow frontend requests
CORS(
    app,
    origins=[frontend_url],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"]
)


app.register_blueprint(routes)


@app.get("/")
def index():
    return "The server is running."


if __name__ == "__main__":
    app.run(host="localhost", port=5000, debug=True)