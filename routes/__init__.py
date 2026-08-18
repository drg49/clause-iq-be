from flask import Blueprint

# Import the route handlers from other files
from .authentication import authentication
from .recipes import recipes

# Create the blueprints
routes = Blueprint('routes', __name__)

# Register the blueprints with the Flask app
routes.register_blueprint(authentication, url_prefix='/authentication')
routes.register_blueprint(recipes, url_prefix='/recipes')
