from flask import Blueprint, jsonify, request, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import text
import jwt
import datetime
import traceback
import os
import json

auth_bp = Blueprint('auth_bp', __name__, url_prefix='/auth')

CERT_UPLOAD_FOLDER = 'static/certifications'

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


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {'1', 'true', 't', 'yes', 'y', 'on'}


def _normalize_optional(value):
    if value is None:
        return None
    text_value = str(value).strip()
    if text_value.lower() in {'', 'none', 'null', 'undefined'}:
        return None
    return text_value


def _parse_form_availability(form) -> list:
    parsed = []
    for raw in form.getlist('availability'):
        if not raw:
            continue
        try:
            item = json.loads(raw)
        except (TypeError, ValueError):
            continue

        if isinstance(item, list):
            parsed.extend([x for x in item if isinstance(x, (dict, str))])
        elif isinstance(item, (dict, str)):
            parsed.append(item)

    return parsed


def _normalize_registration_availability(availability) -> list:
    if not availability:
        return []

    allowed_dow = {'SUN', 'M', 'T', 'W', 'TH', 'F', 'SAT'}

    def normalize_time(value, fallback):
        v = str(value).strip() if value is not None else ''
        if not v:
            return fallback
        if len(v) == 5 and v.count(':') == 1:
            return f'{v}:00'
        return v

    slots = []

    # Primary supported format:
    # [
    #   {"dow":"M","start_time":"09:00:00","end_time":"11:00:00"},
    #   {"dow":"W","start_time":"10:00:00","end_time":"12:00:00"}
    # ]
    if isinstance(availability, list):
        for item in availability:
            if not isinstance(item, dict):
                continue
            dow = str(item.get('dow') or '').strip().upper()
            if dow not in allowed_dow:
                continue
            slots.append({
                'dow': dow,
                'start_time': normalize_time(item.get('start_time'), '00:00:00'),
                'end_time': normalize_time(item.get('end_time'), '23:59:59')
            })
        return slots


def _extract_registration_input():
    form = request.form

    certifications = [c for c in form.getlist('certifications') if c]
    availability = _parse_form_availability(form)
    files = [
        file for key, file in sorted(request.files.items())
        if key.startswith('certificationFile_') and file and file.filename
    ]

    return {
        'username': (form.get('username') or '').strip(),
        'password': form.get('password') or '',
        'first_name': (form.get('first_name') or '').strip(),
        'last_name': (form.get('last_name') or '').strip(),
        'birthday': form.get('birthday'),
        'is_coach': _to_bool(form.get('is_coach', False)),
        'current_weight': form.get('current_weight'),
        'goal_weight': form.get('goal_weight'),
        'goal_type': form.get('goal_type'),
        'goal_text': form.get('goal_text'),
        'certifications': certifications,
        'availability': availability,
        'pricing': _normalize_optional(form.get('pricing')),
        'bio': _normalize_optional(form.get('bio')),
        'cardNumber': _normalize_optional(form.get('cardNumber')),
        'cardExpMonth': _normalize_optional(form.get('cardExpMonth')),
        'cardExpYear': _normalize_optional(form.get('cardExpYear')),
        'cardCVC': _normalize_optional(form.get('cardCVC')),
        'certification_files': files
    }


def _save_certification_files(files, username: str) -> list:
    urls = []
    if not files:
        return urls

    save_dir = os.path.join(current_app.root_path, CERT_UPLOAD_FOLDER)
    os.makedirs(save_dir, exist_ok=True)

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')
    for idx, file in enumerate(files):
        filename = secure_filename(file.filename or f'cert_{idx}')
        final_name = f'{username}_{timestamp}_{idx}_{filename}'
        file_path = os.path.join(save_dir, final_name)
        file.save(file_path)
        urls.append(f"{request.host_url.rstrip('/')}/static/certifications/{final_name}")

    return urls


def _insert_coach_certifications(session, coach_id: int, certifications: list, file_urls: list):
    if not file_urls and not certifications:
        return

    columns = {
        row[0].lower()
        for row in session.execute(text('SHOW COLUMNS FROM coach_certifications')).fetchall()
    }

    has_name_col = 'certification_name' in columns
    has_file_col = 'file_url' in columns
    has_status_col = 'status' in columns

    entries = max(len(file_urls), len(certifications), 1)
    for idx in range(entries):
        data = {'coach_id': coach_id}
        if has_status_col:
            data['status'] = 'pending'
        if has_name_col and idx < len(certifications):
            data['certification_name'] = certifications[idx]
        if has_file_col and idx < len(file_urls):
            data['file_url'] = file_urls[idx]

        col_sql = ', '.join(data.keys())
        val_sql = ', '.join(f':{k}' for k in data.keys())
        session.execute(
            text(f'INSERT INTO coach_certifications ({col_sql}) VALUES ({val_sql})'),
            data
        )

# Register Route
@auth_bp.route('/register', methods=['POST'])
def register():
    payload = _extract_registration_input()

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
    cardNumber = payload.get('cardNumber')
    cardExpMonth = payload.get('cardExpMonth')
    cardExpYear = payload.get('cardExpYear')
    cardCVC = payload.get('cardCVC')

    #  Coach-only fields
    certifications = payload.get('certifications') or []
    if isinstance(certifications, str):
        certifications = [certifications]
    pricing  = payload.get('pricing')
    bio = payload.get('bio')
    availability = payload.get('availability') or []
    availability = _normalize_registration_availability(availability)
    certification_files = payload.get('certification_files') or []

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
                    'is_nutritionist': 1 if any('nutritionist' in str(c).lower() for c in certifications) else 0
                }
            )
            coach_profile_id = session.execute(text('SELECT LAST_INSERT_ID()')).scalar()

        #6 if coach, insert avalibility
            if availability:
                for slot in availability:
                    session.execute(
                        text(
                            'INSERT INTO Coach_Availability '
                            '(coach_id, DOW, start_time, end_time) '
                            'VALUES (:cid, :dow, :start, :end)'
                        ),
                        {
                            'cid': coach_profile_id,
                            'dow': slot.get('dow') or slot.get('day_of_week'),
                            'start': slot.get('start_time'),
                            'end': slot.get('end_time')
                        }
                    )

            cert_urls = _save_certification_files(certification_files, username)
            _insert_coach_certifications(session, coach_profile_id, certifications, cert_urls)

        # 7. If payment info provided, insert into Payment_details
        if cardNumber:
            session.execute(
                text(
                    'INSERT INTO payment_details '
                    '(user_id, card_num, exp_month, exp_year, CVV) '
                    'VALUES (:uid, :number, :exp_month ,:exp_year, :cvc)'
                ),
                {
                    'uid':    user_id,
                    'number': cardNumber,
                    'exp_month': cardExpMonth,
                    'exp_year': cardExpYear,
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

@auth_bp.route('/change-password', methods=['PATCH'])
def changePassword():
    # verify user token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        user_id = payload['sub']
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Invalid token'}), 401

    # get old password and new password from request body
    data = request.get_json()
    old_password = data.get('current_password')
    new_password = data.get('new_password')

    if not old_password or not new_password:
        return jsonify({'status': 'error', 'message': 'Password is required'}), 400

    db = current_app.extensions['sqlalchemy']

    # Read user
    try:
        sql = text(
            'SELECT '
            'ul.user_id, ul.password_hash '
            'FROM User_login ul '
            'WHERE ul.user_id = :user_id '
            'LIMIT 1'
        )
        row = db.session.execute(sql, {'user_id': user_id}).mappings().first()
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Database error.',
            'detail': str(e)
        }), 500

    if not row:
        return jsonify({
            'status': 'error',
            'message': 'Invalid password.'
        }), 401

    # Verify password
    stored_pw = row.get('password_hash')
    if not verify_password(stored_pw, old_password):
        return jsonify({
            'status': 'error',
            'message': 'Invalid password.'
        }), 401

    # Update to new password
    try:
        new_password_hash = generate_password_hash(new_password)
        db.session.execute(
            text('UPDATE User_login SET password_hash = :pw WHERE user_id = :uid'),
            {'pw': new_password_hash, 'uid': user_id}
        )
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Password changed successfully.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to change password.',
            'detail': str(e)
        }), 500