from flask import Flask, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from routes.admin_routes import admin_bp
from routes.auth_routes import auth_bp
from routes.coach_routes import coach_bp
from routes.user_routes import user_bp
app = Flask(__name__)
CORS(app)

#DB Config
# Replace 'root', 'password', and 'fitness_db' with your actual MySQL info
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password123@localhost/fitness_db'

db = SQLAlchemy(app)

app.register_blueprint(admin_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(coach_bp)
app.register_blueprint(user_bp)


if __name__ == '__main__':
    app.run(debug=True, port=8080, host='localhost')
