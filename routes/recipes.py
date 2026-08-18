from flask import Blueprint, jsonify, request
from PIL import Image

recipes = Blueprint("recipes", __name__)


@recipes.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("image")

    if file is None:
        return jsonify({"error": "No image uploaded"}), 400

    image = Image.open(file.stream)

    print({
        "filename": file.filename,
        "size": image.size,
        "mode": image.mode,
    })

    return jsonify({"message": "Image successfully opened"}), 200
