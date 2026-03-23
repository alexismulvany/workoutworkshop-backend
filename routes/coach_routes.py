from flask import Blueprint, jsonify
from extensions import db

coach_bp = Blueprint('coach_bp', __name__)