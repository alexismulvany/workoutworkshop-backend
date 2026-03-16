from flask import Flask, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from routes.admin_routes import admin_bp
from routes.auth_routes import auth_bp
from routes.coach_routes import coach_bp
from routes.user_routes import user_bp
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
CORS(app)

# DB Config
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
db_name = os.getenv('DB_NAME')

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}'
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'change-me-in-production')

db = SQLAlchemy(app)

app.register_blueprint(admin_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(coach_bp)
app.register_blueprint(user_bp)

@app.route('/test-db')
def test_db():
    try:
        # We use db.text() to run a raw SQL 'ping'
        result = db.session.execute(db.text("SELECT 1")).fetchone()
        return jsonify({
            "status": "success",
            "message": "Flask is talking to MySQL!",
            "result": result[0]
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='localhost')
