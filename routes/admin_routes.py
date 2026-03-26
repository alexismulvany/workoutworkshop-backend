from math import ceil

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import text

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')


@admin_bp.route('/fetch-users', methods=['GET'])
def fetch_users():
    db = current_app.extensions['sqlalchemy']

    try:
        page = max(int(request.args.get('page', 1)), 1)
    except (TypeError, ValueError):
        page = 1

    try:
        limit = int(request.args.get('limit', 10))
    except (TypeError, ValueError):
        limit = 10
    limit = min(max(limit, 1), 100)

    search = (request.args.get('search') or '').strip()
    offset = (page - 1) * limit

    where_sql = ''
    params = {'limit': limit, 'offset': offset}

    if search:
        where_sql = (
            'WHERE '
            'ul.username LIKE :search '
            'OR up.first_name LIKE :search '
            'OR up.last_name LIKE :search '
            'OR CAST(u.user_id AS CHAR) LIKE :search '
        )
        params['search'] = f'%{search}%'

    count_sql = text(
        'SELECT COUNT(*) AS total '
        'FROM Users u '
        'LEFT JOIN User_login ul ON ul.user_id = u.user_id '
        'LEFT JOIN User_Profiles up ON up.user_id = u.user_id '
        f'{where_sql}'
    )

    data_sql = text(
        'SELECT '
        'u.user_id, u.role, u.is_banned, u.is_disabled, u.create_date, '
        'ul.username, '
        'up.first_name, up.last_name, up.birthday, up.current_weight '
        'FROM Users u '
        'LEFT JOIN User_login ul ON ul.user_id = u.user_id '
        'LEFT JOIN User_Profiles up ON up.user_id = u.user_id '
        f'{where_sql}'
        'ORDER BY u.user_id ASC '
        'LIMIT :limit OFFSET :offset'
    )

    try:
        total_users = db.session.execute(count_sql, params).scalar() or 0
        rows = db.session.execute(data_sql, params).mappings().all()
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Failed to fetch users.',
            'detail': str(e)
        }), 500

    users = [
        {
            'id': r.get('user_id'),
            'username': r.get('username'),
            'role': r.get('role'),
            'is_banned': r.get('is_banned'),
            'is_disabled': r.get('is_disabled'),
            'create_date': r.get('create_date'),
            'first_name': r.get('first_name'),
            'last_name': r.get('last_name'),
            'birthday': r.get('birthday'),
            'current_weight': r.get('current_weight')
        }
        for r in rows
    ]

    total_pages = max(ceil(total_users / limit), 1)

    return jsonify({
        'users': users,
        'totalPages': total_pages,
        'currentPage': page,
        'totalUsers': total_users
    }), 200
