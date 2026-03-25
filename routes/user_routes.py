from datetime import date
import jwt
from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import text

user_bp = Blueprint('user_bp', __name__)

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
