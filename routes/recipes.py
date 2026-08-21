from flask import Blueprint, jsonify, request
from PIL import Image
from ultralytics import YOLO

recipes = Blueprint("recipes", __name__)

# Load the YOLO model once when this file is loaded
# This should be done outside of the route to avoid reloading the model on every request
model = YOLO("yolo11n.pt")

@recipes.route("/upload", methods=["POST"])
def upload():
    # Get the uploaded file from the frontend request
    file = request.files.get("image")

    # Throw an error if no file is uploaded
    if file is None:
        return jsonify({"error": "No image uploaded"}), 400

    # Open the image using PIL to verify it's a valid image
    image = Image.open(file.stream)

   # Send the image through the YOLO model
    results = model(image)

    # Extract unique detected class names
    detected_classes = set()
    for result in results:
        for box in result.boxes:
            class_id = int(box.cls[0])           # Get index (e.g., 46)
            class_name = model.names[class_id]   # Map index to name (e.g., 'banana')
            detected_classes.add(class_name)

    detected_list = list(detected_classes)

    # Print to your server console
    print("\n--- DETECTED CLASSES ---")
    print(detected_list)
    print("------------------------\n")

    # Return the detected list in the API response
    return jsonify({
        "message": "Detection complete",
        "detected_classes": detected_list
    }), 200
