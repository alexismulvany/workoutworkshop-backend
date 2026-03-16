from flask import Blueprint, jsonify, request, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import text
import jwt
import datetime
import traceback

auth_bp = Blueprint('auth_bp', __name__, url_prefix='/auth')

# Password check helper function
def verify_password(stored: str, provided: str) -> bool:
    if not stored:
        return False
    try:
        return check_password_hash(stored, provided)
    except (ValueError, TypeError):
        return stored == provided

#login Route
@auth_bp.route('/login', methods=['POST'])
def login():
    payload  = request.get_json(silent=True) or {}
    username = (payload.get('username') or '').strip()
    password = payload.get('password')

    # Validate input
    if not username or not password:
        return jsonify({
            'status':  'error',
            'message': 'Username and password are required.'
        }), 400

    db = current_app.extensions['sqlalchemy']

    # Read user
    try:
        sql = text(
            'SELECT '
            'ul.user_id, ul.username, ul.password_hash, '
            'u.role, u.is_banned, u.is_disabled, u.create_date, '
            'up.first_name, up.last_name, up.profile_picture_url, up.current_weight '
            'FROM User_login ul '
            'JOIN Users u ON ul.User_id = u.User_id '
            'JOIN User_Profiles up ON u.User_id = up.user_id '
            'WHERE ul.username = :username '
            'LIMIT 1'
        )
        row = db.session.execute(sql, {'username': username}).mappings().first()
    except Exception as e:
        return jsonify({
            'status':  'error',
            'message': 'Database error.',
            'detail':  str(e)
        }), 500

    if not row:
        return jsonify({
            'status':  'error',
            'message': 'Invalid username or password.'
        }), 401

    # Verify password
    stored_pw = row.get('password_hash')
    if not verify_password(stored_pw, password):
        return jsonify({
            'status':  'error',
            'message': 'Invalid username or password.'
        }), 401

    # Build user data
    HIDDEN = {'password_hash'}
    user_data = {k: v for k, v in dict(row).items() if k not in HIDDEN}

    # JWT
    secret = current_app.config['JWT_SECRET_KEY']
    token_payload = {
        'sub':      str(row.get('user_id')),
        'username': row.get('username'),
        'role':     row.get('role'),
        'iat':      datetime.datetime.now(datetime.timezone.utc),
        'exp':      datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
    }
    token = jwt.encode(token_payload, secret, algorithm='HS256')

    return jsonify({
        'status':  'success',
        'message': 'Login successful.',
        'token':   token,
        'user':    user_data
    }), 200

@auth_bp.route('/check-username', methods=['POST'])
def checkusername():
    payload = request.get_json(silent=True) or {}
    username = (payload.get('username') or '').strip()

    if not username:
        return jsonify({
            'status': 'error',
            'message': 'Username is required.',
            'available': False
        }), 400

    db = current_app.extensions['sqlalchemy']

    try:
        sql = text(
            'SELECT 1 '
            'FROM User_login ul '
            'WHERE ul.username = :username '
            'LIMIT 1'
        )
        existing = db.session.execute(sql, {'username': username}).first()
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Database error.',
            'detail': str(e)
        }), 500

    is_available = existing is None
    return jsonify({
        'status': 'success',
        'available': is_available
    }), 200


# Register Route
@auth_bp.route('/register', methods=['POST'])
def register():
    payload = request.get_json(silent=True) or {}

    # --- Required fields ---
    username   = (payload.get('username') or '').strip()
    password   = payload.get('password') or ''
    first_name = (payload.get('first_name') or '').strip()
    last_name  = (payload.get('last_name') or '').strip()
    birthday   = payload.get('birthday')
    is_coach   = bool(payload.get('is_coach', False))
    current_weight = payload.get('current_weight')
    goal_weight = payload.get('goal_weight')
    goal_type = payload.get('goal_type')

    if not all([username, password, first_name, last_name, birthday, current_weight, goal_weight]):
        return jsonify({
            'status':  'error',
            'message': 'username, password, first_name, last_name, and birthday are required.'
        }), 400

    # Optional payment fields
    cardName = payload.get('cardName')
    cardNumber = payload.get('cardNumber')
    cardExpMonth = payload.get('cardExpMonth')
    cardExpYear = payload.get('cardExpYear')
    cardCVC = payload.get('cardCVC')

    #  Coach-only fields
    certifications = payload.get('certifications')
    pricing  = payload.get('pricing')
    bio = payload.get('bio')
    availability = payload.get('availability')

    db  = current_app.extensions['sqlalchemy']
    session = db.session

    try:
        # 1. Check username is not already taken
        taken = session.execute(
            text('SELECT 1 FROM User_login WHERE username = :u LIMIT 1'),
            {'u': username}
        ).first()
        if taken:
            return jsonify({
                'status':  'error',
                'message': 'Username is already taken.'
            }), 409

        # 2. Insert into Users — role based on is_coach flag
        role = 'C' if is_coach else 'U'
        session.execute(
            text(
                'INSERT INTO Users (role, is_banned, is_disabled, create_date) '
                'VALUES (:role, 0, 0, NOW())'
            ),
            {'role': role}
        )
        user_id = session.execute(text('SELECT LAST_INSERT_ID()')).scalar()

        # 3. Insert into User_login
        password_hash = generate_password_hash(password)
        session.execute(
            text(
                'INSERT INTO User_login (user_id, username, password_hash) '
                'VALUES (:uid, :username, :pw)'
            ),
            {'uid': user_id, 'username': username, 'pw': password_hash}
        )

        # 4. Insert into User_Profiles
        session.execute(
            text(
                'INSERT INTO User_Profiles '
                '(user_id, first_name, last_name, birthday, current_weight) '
                'VALUES (:uid, :fn, :ln, :bday, :cw)'
            ),
            {
                'uid':  user_id,
                'fn':   first_name,
                'ln':   last_name,
                'bday': birthday,
                'cw':   current_weight,
            }
        )

        #insert goals
        session.execute(
            text(
                'INSERT INTO goals '
                '(user_id, goal_weight, goal_type) '
                'VALUES (:uid, :fn, :ln)'
            ),
            {
                'uid': user_id,
                'fn': goal_weight,
                'ln': goal_type
            }
        )

        # 5. If coach, insert into Coach_Profiles
        if is_coach:
            session.execute(
                text(
                    'INSERT INTO Coach_Profiles '
                    '(user_id, pricing, bio, is_active, is_nutritionist) '
                    'VALUES (:uid, :price, :bio, :is_active, :is_nutritionist)'
                ),
                {
                    'uid':   user_id,
                    'price': pricing,
                    'bio':   bio,
                    'is_active': 0 , # New coaches start as inactive until approved by admin
                    'is_nutritionist': 1 if (certifications and 'nutritionist' in certifications) else 0
                }
            )

        # 6. If payment info provided, insert into Payment_details
        if cardName:
            session.execute(
                text(
                    'INSERT INTO Payment_Info '
                    '(user_id, card_num, exp_month, exp_year, CVV) '
                    'VALUES (:uid, :number, :exp_month ,:exp_year, :cvc)'
                ),
                {
                    'uid':    user_id,
                    'number': cardNumber,
                    'exp_month':    cardExpMonth,
                    'exp_year':    cardExpYear,
                    'cvc':    cardCVC
                }
            )

        session.commit()

        # 7. Issue JWT
        secret = current_app.config['JWT_SECRET_KEY']
        token_payload = {
            'sub':      str(user_id),
            'username': username,
            'role':     role,
            'iat':      datetime.datetime.now(datetime.timezone.utc),
            'exp':      datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
        }
        token = jwt.encode(token_payload, secret, algorithm='HS256')

        return jsonify({
            'status':  'success',
            'message': 'Registration successful.',
            'token':   token,
            'user': {
                'id':         user_id,
                'username':   username,
                'role':       role,
                'first_name': first_name,
                'last_name':  last_name,
                'birthday':   birthday,
                'current_weight': current_weight,
                'goal_weight':    goal_weight
            }
        }), 201

    except Exception as e:
        session.rollback()
        traceback.print_exc()
        return jsonify({
            'status':  'error',
            'message': 'Registration failed.',
            'detail':  str(e)
        }), 500

