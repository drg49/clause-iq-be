from flask import Blueprint

# Import the route handlers from other files
from .authentication import authentication

# Create the blueprints
routes = Blueprint('routes', __name__)

# Register the blueprints with the Flask app
routes.register_blueprint(authentication, url_prefix='/authentication')
