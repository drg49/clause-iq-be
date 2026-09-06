import os
import uuid

import boto3
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from models.contract import Contract
from models import db


contracts = Blueprint("contracts", __name__)

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

S3_BUCKET = "drg-clauses"


@contracts.route("", methods=["GET"])
@jwt_required()
def get_contracts():

    # Get the logged-in user's ID
    user_id = get_jwt_identity()

    # Get pagination parameters
    try:
        limit = int(request.args.get("limit", 10))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return jsonify({
            "error": "Limit and offset must be integers"
        }), 400

    # Validate pagination parameters
    if limit < 1:
        return jsonify({
            "error": "Limit must be greater than 0"
        }), 400

    if offset < 0:
        return jsonify({
            "error": "Offset cannot be negative"
        }), 400

    try:
        # Get this user's contracts
        contracts_query = Contract.query.filter_by(
            user_id=user_id
        ).order_by(
            Contract.created_at.desc()
        )

        # Get total number of contracts
        total = contracts_query.count()

        # Apply pagination
        contracts_list = contracts_query.offset(
            offset
        ).limit(
            limit
        ).all()

        return jsonify({
            "contracts": [
                {
                    "id": contract.id,
                    "name": contract.name,
                    "s3_key": contract.s3_key,
                    "status": contract.status,
                    "created_at": contract.created_at
                }
                for contract in contracts_list
            ],
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total
            }
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@contracts.route("/upload", methods=["POST"])
@jwt_required()
def upload_contract():

    # Get the logged-in user's ID
    user_id = get_jwt_identity()

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
        # Upload PDF to S3
        s3.upload_fileobj(
            file,
            S3_BUCKET,
            s3_key,
            ExtraArgs={
                "ContentType": "application/pdf"
            }
        )

        # Create database record
        contract = Contract(
            user_id=user_id,
            name=file.filename,
            s3_key=s3_key
        )

        db.session.add(contract)
        db.session.commit()

        return jsonify({
            "message": "Contract uploaded successfully",
            "contract": {
                "id": contract.id,
                "name": contract.name,
                "s3_key": contract.s3_key,
                "status": contract.status,
                "created_at": contract.created_at
            }
        }), 201

    except Exception as e:
        db.session.rollback()

        return jsonify({
            "error": str(e)
        }), 500


@contracts.route("/<int:contract_id>/analyze", methods=["POST"])
@jwt_required()
def analyze_contract(contract_id):

    # Get the logged-in user's ID
    user_id = get_jwt_identity()

    try:
        # Find the contract belonging to the logged-in user
        contract = Contract.query.filter_by(
            id=contract_id,
            user_id=user_id
        ).first()

        # Contract doesn't exist or doesn't belong to this user
        if not contract:
            return jsonify({
                "error": "Contract not found"
            }), 404

        # Don't start analysis if the contract is already being analyzed
        if contract.status == "ANALYZING":
            return jsonify({
                "error": "Contract analysis is already in progress"
            }), 409

        # Don't analyze a contract that has already been analyzed
        if contract.status == "ANALYZED":
            return jsonify({
                "error": "Contract has already been analyzed"
            }), 409

        # Update contract status
        contract.status = "ANALYZING"

        db.session.commit()

        return jsonify({
            "message": "Contract analysis started",
            "contract": {
                "id": contract.id,
                "name": contract.name,
                "status": contract.status
            }
        }), 202

    except Exception as e:
        db.session.rollback()

        return jsonify({
            "error": str(e)
        }), 500


@contracts.route("/<int:contract_id>", methods=["DELETE"])
@jwt_required()
def delete_contract(contract_id):

    # Get the logged-in user's ID
    user_id = get_jwt_identity()

    try:
        # Find the contract belonging to the logged-in user
        contract = Contract.query.filter_by(
            id=contract_id,
            user_id=user_id
        ).first()

        # Contract doesn't exist or doesn't belong to this user
        if not contract:
            return jsonify({
                "error": "Contract not found"
            }), 404

        # Delete the PDF from S3
        s3.delete_object(
            Bucket=S3_BUCKET,
            Key=contract.s3_key
        )

        # Delete the database record
        db.session.delete(contract)
        db.session.commit()

        return jsonify({
            "message": "Contract deleted successfully"
        }), 200

    except Exception as e:
        db.session.rollback()

        return jsonify({
            "error": str(e)
        }), 500