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

# JWT generation helper function for login and registration
def issue_auth_token(user_id: int, username: str, role: str) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    token_payload = {
        'sub': str(user_id),
        'username': username,
        'role': role,
        'iat': now,
        'exp': now + datetime.timedelta(hours=24)
    }
    return jwt.encode(token_payload, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')

# Helper to build consistent user payload for auth responses
def build_auth_user_payload(row) -> dict:
    data = dict(row or {})
    return {
        'id': data.get('user_id'),
        'username': data.get('username'),
        'role': data.get('role'),
        'is_banned': data.get('is_banned'),
        'is_disabled': data.get('is_disabled'),
        'create_date': data.get('create_date'),
        'first_name': data.get('first_name'),
        'last_name': data.get('last_name'),
        'birthday': data.get('birthday'),
        'profile_picture_url': data.get('profile_picture_url'),
        'current_weight': data.get('current_weight'),
        'goal_weight': data.get('goal_weight'),
        'goal_type': data.get('goal_type'),
        'information': data.get('information')
    }

# Helper to build consistent auth success response
def build_auth_success_response(token: str, user_payload: dict, status_code: int):
    return jsonify({
        'status': 'success',
        'message': 'Authentication successful.',
        'token': token,
        'user': user_payload
    }), status_code

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
            'up.first_name, up.last_name, up.birthday, up.profile_picture_url, up.current_weight, '
            'g.goal_weight, g.goal_type, g.information '
            'FROM User_login ul '
            'JOIN Users u ON ul.User_id = u.User_id '
            'JOIN User_Profiles up ON u.User_id = up.user_id '
            'LEFT JOIN goals g ON g.user_id = u.user_id '
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
    user_data = build_auth_user_payload(row)

    # JWT
    token = issue_auth_token(
        user_id=row.get('user_id'),
        username=row.get('username'),
        role=row.get('role')
    )

    return build_auth_success_response(token=token, user_payload=user_data, status_code=200)

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
    information = payload.get('goal_text')

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
                '(user_id, goal_weight, goal_type, information) '
                'VALUES (:uid, :fn, :ln, :goal_text)'
            ),
            {
                'uid': user_id,
                'fn': goal_weight,
                'ln': goal_type,
                'goal_text': information
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
            coach_profile_id = session.execute(text('SELECT LAST_INSERT_ID()')).scalar()

        #6 if coach, insert avalibility
            if is_coach and availability:
                for slot in availability:
                    session.execute(
                        text(
                            'INSERT INTO Coach_Availability '
                            '(coach_id, DOW, start_time, end_time) '
                            'VALUES (:cid, :dow, :start, :end)'
                        ),
                        {
                            'cid': coach_profile_id,
                            'dow': slot.get('dow'),
                            'start': slot.get('start_time'),
                            'end': slot.get('end_time')
                        }
                    )

        # 7. If payment info provided, insert into Payment_details
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

        # 8. Issue JWT
        token = issue_auth_token(
            user_id=user_id,
            username=username,
            role=role
        )

        # Return the same user payload shape as /auth/login.
        user_row = session.execute(
            text(
                'SELECT '
                'ul.user_id, ul.username, '
                'u.role, u.is_banned, u.is_disabled, u.create_date, '
                'up.first_name, up.last_name, up.birthday, up.profile_picture_url, up.current_weight, '
                'g.goal_weight, g.goal_type, g.information '
                'FROM User_login ul '
                'JOIN Users u ON ul.User_id = u.User_id '
                'JOIN User_Profiles up ON u.User_id = up.user_id '
                'LEFT JOIN goals g ON g.user_id = u.user_id '
                'WHERE ul.user_id = :uid '
                'LIMIT 1'
            ),
            {'uid': user_id}
        ).mappings().first()

        return build_auth_success_response(
            token=token,
            user_payload=build_auth_user_payload(user_row),
            status_code=201
        )

    except Exception as e:
        session.rollback()
        traceback.print_exc()
        return jsonify({
            'status':  'error',
            'message': 'Registration failed.',
            'detail':  str(e)
        }), 500

