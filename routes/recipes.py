from flask import Blueprint, jsonify, request

recipes = Blueprint("recipes", __name__)


@recipes.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("image")

    if file is None:
        return jsonify({"error": "No image uploaded"}), 400

    file.stream.seek(0, 2)
    file_size = file.stream.tell()
    file.stream.seek(0)

    # Identify the object in the image (this is a placeholder for actual image processing logic)

    print({
        "filename": file.filename,
        "content_type": file.content_type,
        "mimetype": file.mimetype,
        "size": file_size,
    })

    return jsonify({"message": "File details printed"}), 200
