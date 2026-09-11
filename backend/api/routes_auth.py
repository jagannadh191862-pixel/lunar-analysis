"""
Authentication Routes for Lunar Correspondence AI
Session management and user authentication for planetary science teams.
"""

from flask import Blueprint, request, jsonify, session
from backend.db.database import (
    create_user,
    get_user_by_username,
    get_user_by_id,
    verify_password
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    institution = data.get("institution", "Planetary Remote Sensing Laboratory").strip()

    if not username or len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters long."}), 400
    if not email or "@" not in email:
        return jsonify({"error": "A valid email address is required for scientific correspondence."}), 400
    if not password or len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long."}), 400

    existing = get_user_by_username(username)
    if existing:
        return jsonify({"error": "Username or email is already registered."}), 409

    user_id = create_user(username, email, password, role="researcher", institution=institution)
    if not user_id:
        return jsonify({"error": "Registration failed due to database constraint."}), 500

    session["user_id"] = user_id
    user = get_user_by_id(user_id)
    return jsonify({
        "message": "User registered successfully.",
        "user": user
    }), 201

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Both username/email and password are required."}), 400

    user = get_user_by_username(username)
    if not user:
        return jsonify({"error": "Invalid scientific credentials."}), 401

    if not verify_password(user["password_hash"], user["salt"], password):
        return jsonify({"error": "Invalid scientific credentials."}), 401

    session["user_id"] = user["id"]
    return jsonify({
        "message": "Authentication successful.",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
            "institution": user["institution"]
        }
    }), 200

@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return jsonify({"message": "Session terminated."}), 200

@auth_bp.route("/me", methods=["GET"])
def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        # Provide default guest researcher identity so users can test immediately without friction
        return jsonify({
            "authenticated": False,
            "user": {
                "id": None,
                "username": "guest_researcher",
                "role": "Guest Observer",
                "institution": "Lunar Remote Sensing Lab"
            }
        }), 200

    user = get_user_by_id(user_id)
    if not user:
        session.pop("user_id", None)
        return jsonify({
            "authenticated": False,
            "user": {
                "id": None,
                "username": "guest_researcher",
                "role": "Guest Observer",
                "institution": "Lunar Remote Sensing Lab"
            }
        }), 200

    return jsonify({
        "authenticated": True,
        "user": user
    }), 200
