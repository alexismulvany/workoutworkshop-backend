from datetime import date
import jwt
from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import text
import os
from werkzeug.utils import secure_filename

user_bp = Blueprint('user_bp', __name__, url_prefix='/user')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
UPLOAD_FOLDER = 'static/profiles'


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@user_bp.route('/upload-profile-picture', methods=['POST'])
def upload_profile_picture():

    #verify user token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({'status': 'error', 'message': 'Missing or invalid authorization header'}), 401

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        user_id = payload['sub']
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Invalid or expired token'}), 401

    #
    if 'profile_image' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part found in request'}), 400

    file = request.files['profile_image']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(f"user_{user_id}_{file.filename}")

        # Ensure the static/profiles directory exists
        save_dir = os.path.join(current_app.root_path, UPLOAD_FOLDER)
        os.makedirs(save_dir, exist_ok=True)

        # Saves the file to your computer/server
        filepath = os.path.join(save_dir, filename)
        file.save(filepath)

        file_url = f"http://127.0.0.1:5000/static/profiles/{filename}"

        db = current_app.extensions['sqlalchemy']
        try:
            db.session.execute(
                text('UPDATE User_Profiles SET profile_picture_url = :url WHERE user_id = :uid'),
                {'url': file_url, 'uid': user_id}
            )
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': 'Database error', 'detail': str(e)}), 500

        return jsonify({
            'status': 'success',
            'message': 'Profile picture updated',
            'profile_picture_url': file_url
        }), 200

    return jsonify({'status': 'error', 'message': 'Invalid file format. Only JPG and PNG are allowed.'}), 400

def _decode_user_id_from_token() -> tuple[int | None, str | None]:
    token = request.headers.get('Authorization')
    if not token:
        return None, 'Missing Authorization token.'

    try:
        payload = jwt.decode(
            token,
            current_app.config['JWT_SECRET_KEY'],
            algorithms=['HS256']
        )
    except jwt.ExpiredSignatureError:
        return None, 'Token expired.'
    except jwt.InvalidTokenError:
        return None, 'Invalid token.'

    sub = payload.get('sub')
    try:
        return int(sub), None
    except (TypeError, ValueError):
        return None, 'Invalid token subject.'


@user_bp.route('/user/check-survey', methods=['GET'])
def check_survey():
    user_id, auth_error = _decode_user_id_from_token()
    if auth_error:
        return jsonify({'status': 'error', 'message': auth_error}), 401

    raw_date = (request.args.get('date') or '').strip()
    if not raw_date:
        target_day = date.today()
    else:
        try:
            target_day = date.fromisoformat(raw_date)
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid date. Use YYYY-MM-DD.'
            }), 400

    target_date_start = f'{target_day.isoformat()} 00:00:00'
    target_date_end = f'{target_day.isoformat()} 23:59:59'

    db = current_app.extensions['sqlalchemy']

    query = text(
        'SELECT result AS rating '
        'FROM Daily_Survey '
        'WHERE user_id = :uid '
        'AND date >= :start_time '
        'AND date <= :end_time '
        'ORDER BY date DESC '
        'LIMIT 1'
    )

    try:
        row = db.session.execute(
            query,
            {'uid': user_id, 'start_time': target_date_start, 'end_time': target_date_end}
        ).mappings().first()
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Database error.',
            'detail': str(e)
        }), 500

    return jsonify({
        'status': 'success',
        'date': target_day.isoformat(),
        'rating': row.get('rating') if row else None
    }), 200

@user_bp.route('/user/daily-survey', methods=['POST'])
def save_daily_survey():
    user_id, auth_error = _decode_user_id_from_token()
    if auth_error:
        return jsonify({'status': 'error', 'message': auth_error}), 401

    payload = request.get_json(silent=True) or {}
    raw_date = (payload.get('date') or '').strip()

    if not raw_date:
        target_day = date.today()
    else:
        try:
            target_day = date.fromisoformat(raw_date)
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid date. Use YYYY-MM-DD.'
            }), 400

    rating = payload.get('rating')
    try:
        rating_value = int(rating)
    except (TypeError, ValueError):
        return jsonify({
            'status': 'error',
            'message': 'rating must be an integer from 1 to 5.'
        }), 400

    if rating_value < 1 or rating_value > 5:
        return jsonify({
            'status': 'error',
            'message': 'rating must be an integer from 1 to 5.'
        }), 400

    target_date_start = f'{target_day.isoformat()} 00:00:00'
    target_date_end = f'{target_day.isoformat()} 23:59:59'

    db = current_app.extensions['sqlalchemy']
    session = db.session

    try:
        # Update row if it exists for this day; otherwise insert one row for that day.
        update_result = session.execute(
            text(
                'UPDATE Daily_Survey '
                'SET result = :rating '
                'WHERE user_id = :uid '
                'AND date >= :start_time '
                'AND date <= :end_time'
            ),
            {
                'uid': user_id,
                'rating': rating_value,
                'start_time': target_date_start,
                'end_time': target_date_end
            }
        )

        created = False
        if update_result.rowcount == 0:
            session.execute(
                text(
                    'INSERT INTO Daily_Survey (user_id, result) '
                    'VALUES (:uid, :result)'
                ),
                {
                    'uid': user_id,
                    'result': rating_value,
                }
            )
            created = True

        session.commit()
    except Exception as e:
        session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to save daily rating.',
            'detail': str(e)
        }), 500

    return jsonify({
        'status': 'success',
        'rating': rating_value,
        'date': target_day.isoformat(),
        'created': created
    }), 200


