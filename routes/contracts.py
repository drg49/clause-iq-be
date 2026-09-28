import os
import uuid

import boto3
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from models.contract import Contract
from models.contract_chunk import ContractChunk
from models.contract_finding import ContractFinding
from models.finding_chunk import FindingChunk
from models import db

from tasks.executor import executor
from tasks.contract_analysis import analyze_contract


contracts = Blueprint("contracts", __name__)

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

S3_BUCKET = "drg-clauses"


def get_contract_risk_summary(contract):

    if contract.status != "ANALYZED":
        return {
            "overall_risk": None,
            "findings_count": None
        }

    findings = ContractFinding.query.filter_by(
        contract_id=contract.id
    ).all()

    if not findings:
        return {
            "overall_risk": "LOW",
            "findings_count": 0
        }

    severity_order = {
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3
    }

    highest_severity = max(
        findings,
        key=lambda finding: severity_order.get(
            finding.severity,
            0
        )
    ).severity

    return {
        "overall_risk": highest_severity,
        "findings_count": len(findings)
    }


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

        contracts_response = []

        for contract in contracts_list:

            risk_summary = get_contract_risk_summary(contract)

            contracts_response.append({
                "id": contract.id,
                "name": contract.name,
                "s3_key": contract.s3_key,
                "status": contract.status,
                "overall_risk": risk_summary["overall_risk"],
                "findings_count": risk_summary["findings_count"],
                "created_at": contract.created_at
            })

        return jsonify({
            "contracts": contracts_response,
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
            s3_key=s3_key,
            status="PENDING"
        )

        db.session.add(contract)
        db.session.commit()

        # Submit the contract analysis to the thread pool
        executor.submit(
            analyze_contract,
            contract.id
        )

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


@contracts.route("/<int:contract_id>/analysis", methods=["GET"])
@jwt_required()
def get_contract_analysis(contract_id):

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

        risk_summary = get_contract_risk_summary(contract)

        # Get all findings for this contract
        findings = ContractFinding.query.filter_by(
            contract_id=contract.id
        ).order_by(
            ContractFinding.id.asc()
        ).all()

        findings_response = []

        for finding in findings:

            # Get the evidence mappings for this finding
            evidence_mappings = FindingChunk.query.filter_by(
                finding_id=finding.id
            ).order_by(
                FindingChunk.evidence_order.asc()
            ).all()

            evidence = []

            for mapping in evidence_mappings:

                # Get the actual contract chunk
                chunk = db.session.get(
                    ContractChunk,
                    mapping.chunk_id
                )

                if chunk:
                    evidence.append({
                        "chunk_id": chunk.id,
                        "chunk_index": chunk.chunk_index,
                        "content": chunk.content,
                        "evidence_order": mapping.evidence_order
                    })

            findings_response.append({
                "id": finding.id,
                "type": finding.type,
                "severity": finding.severity,
                "title": finding.title,
                "explanation": finding.explanation,
                "recommendation": finding.recommendation,
                "created_at": finding.created_at,
                "evidence": evidence
            })

        return jsonify({
            "contract": {
                "id": contract.id,
                "name": contract.name,
                "status": contract.status,
                "overall_risk": risk_summary["overall_risk"],
                "findings_count": risk_summary["findings_count"],
                "created_at": contract.created_at
            },
            "findings": findings_response
        }), 200

    except Exception as e:
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
