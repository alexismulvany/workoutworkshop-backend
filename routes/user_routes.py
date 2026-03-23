from flask import Blueprint, jsonify
from extensions import db

user_bp = Blueprint('user_bp', __name__)