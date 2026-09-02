from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from models import db
from models.user import Users
from validation.authentication import (
    validate_email,
    validate_password,
    validate_first_name,
    validate_last_name
)

authentication = Blueprint("authentication", __name__)


def perform_login(user):
    # Creates JWT token instead of Flask session cookie
    access_token = create_access_token(identity=str(user.id))

    return (
        jsonify({
            "message": "User logged in successfully.",
            "access_token": access_token,
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone_number": user.phone_number,
                "bio": user.bio,
                "location": user.location,
            }
        }),
        200
    )


@authentication.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json() or {}

        if not data:
            return jsonify({"message": "Request body must be valid JSON."}), 400

        validation_methods = {
            "email": validate_email,
            "password": validate_password,
            "first_name": validate_first_name,
            "last_name": validate_last_name,
        }

        for key, method in validation_methods.items():
            value = data.get(key)
            is_valid, message = method(value)

            if not is_valid:
                return jsonify({"message": message}), 400

        new_user = Users(
            password=generate_password_hash(data["password"]),
            email=data["email"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            phone_number=data.get("phone_number"),
            bio=data.get("bio"),
            location=data.get("location"),
            created_at=datetime.now()
        )

        db.session.add(new_user)
        db.session.commit()

        return perform_login(
            new_user
        )

    except Exception as e:
        print(f"An exception occurred: {e}")
        db.session.rollback()
        return jsonify({"message": "Failed to register."}), 500


@authentication.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json() or {}

        user = Users.query.filter_by(
            email=data.get("email")
        ).first()

        if not user or not check_password_hash(
            user.password,
            data.get("password")
        ):
            return jsonify({"message": "Invalid credentials."}), 401

        return perform_login(
            user
        )

    except Exception as e:
        print(f"An exception occurred: {e}")
        return jsonify({"message": "Failed to log in."}), 500


@authentication.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    try:
        # JWTs are stateless.
        # Token removal happens on the frontend.
        return jsonify({
            "message": "Logged out successfully."
        }), 200

    except Exception as e:
        print(f"An exception occurred: {e}")
        return jsonify({"message": "Failed to log out."}), 500


def get_current_user():
    user_id = get_jwt_identity()

    return Users.query.get(int(user_id))


def serialize_user(user):
    return {
        "id": user.id,
        "email": user.email,
        "firstName": user.first_name,
        "lastName": user.last_name,
        "phoneNumber": user.phone_number,
        "bio": user.bio,
        "location": user.location,
        "isActive": getattr(user, "is_active", True)
    }


@authentication.route("/validate-user", methods=["GET"])
@jwt_required()
def validate_user():
    try:
        user = get_current_user()

        if not user:
            return jsonify({
                "message": "User not found."
            }), 404

        return jsonify({
            "message": "User successfully validated.",
            "user": serialize_user(user)
        }), 200

    except Exception as e:
        print(f"An exception occurred during validation: {e}")
        return jsonify({
            "message": "Validation failed."
        }), 500


@authentication.route("/update-user", methods=["PUT"])
@jwt_required()
def update_user():
    try:
        user = get_current_user()

        if not user:
            return jsonify({
                "message": "User not found."
            }), 404

        data = request.get_json() or {}

        if "email" in data and data["email"] != user.email:

            is_valid, message = validate_email(data["email"])

            if not is_valid:
                return jsonify({
                    "message": message
                }), 400

            existing_email = Users.query.filter_by(
                email=data["email"]
            ).first()

            if existing_email:
                return jsonify({
                    "message": "Email is already taken."
                }), 400

            user.email = data["email"]


        if "first_name" in data and data["first_name"] != user.first_name:
            is_valid, message = validate_first_name(data["first_name"])

            if not is_valid:
                return jsonify({
                    "message": message
                }), 400

            user.first_name = data["first_name"]

        if "last_name" in data and data["last_name"] != user.last_name:
            is_valid, message = validate_last_name(data["last_name"])

            if not is_valid:
                return jsonify({
                    "message": message
                }), 400

            user.last_name = data["last_name"]

        if "password" in data:

            is_valid, message = validate_password(data["password"])

            if not is_valid:
                return jsonify({
                    "message": message
                }), 400

            user.password = generate_password_hash(
                data["password"]
            )


        for field in [
            "phone_number",
            "bio",
            "location"
        ]:
            if field in data:
                setattr(user, field, data[field])


        db.session.commit()

        return jsonify({
            "message": "Profile updated successfully.",
            "user": serialize_user(user)
        }), 200


    except Exception as e:
        print(f"An exception occurred during profile update: {e}")
        db.session.rollback()

        return jsonify({
            "message": "Failed to update user profile."
        }), 500