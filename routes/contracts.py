import os
import uuid

import boto3
from flask import Blueprint, request, jsonify


contracts = Blueprint("contracts", __name__)

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

S3_BUCKET = "drg-clauses"


@contracts.route("/upload", methods=["POST"])
def upload_contract():

    # Check that a file was included in the request
    if "file" not in request.files:
        return jsonify({
            "error": "No file provided"
        }), 400

    file = request.files["file"]

    # Check that the user actually selected a file
    if file.filename == "":
        return jsonify({
            "error": "No file selected"
        }), 400

    # Make sure the file is a PDF
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({
            "error": "Only PDF files are allowed"
        }), 400

    # Generate a unique filename for S3
    file_id = str(uuid.uuid4())
    s3_key = f"contracts/{file_id}.pdf"

    try:
        s3.upload_fileobj(
            file,
            S3_BUCKET,
            s3_key,
            ExtraArgs={
                "ContentType": "application/pdf"
            }
        )

        return jsonify({
            "message": "Contract uploaded successfully",
            "s3_key": s3_key
        }), 201

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500