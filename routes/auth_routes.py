from flask import Blueprint, jsonify
from extensions import db

auth_bp = Blueprint('auth_bp', __name__)
