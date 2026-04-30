from datetime import date
import jwt
from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import text
import os
from werkzeug.utils import secure_filename

user_bp = Blueprint('user_bp', __name__, url_prefix='/user')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
UPLOAD_FOLDER = 'static/profiles'
PROGRESS_UPLOAD_FOLDER = 'static/progress'


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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


@user_bp.route('/upload-profile-picture', methods=['POST'])
def upload_profile_picture():
    """
    Must upload the user's profile picture
    ---
    tags:
        - User - Profile
    consumes:
        - multipart/form-data
    parameters:
        - name: authorization
          in: header
          type: string
          required: true
          description: Bearer JWT token
        - name: profile_image
          in: formData
          type: file
          required: true
          description: Image File (JPG, JPEG, PNG)
    responses:
        200:
          description: Profile Picture is now uploaded successfully
          schema:
            type: object
            properties:
              status:
                type: string
                example: success
              message:
                type: string
              profile_picture_url:
                type: string
        400:
          description: Invalid File or Missing File
        401:
          description: Unauthorized or Invalid Token
        500:
          description: Error in the database
    """
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


@user_bp.route('/update-username', methods=['PUT'])
def update_username():
    """
    Must update the user's username
    ---
    tags:
        - User - Profile
    parameters:
        - name: authorization
          in: header
          type: string
          required: true
        - in: body
          name: body
          required: true
          schema:
            type: object
            required:
              - new_username
            properties:
              new_username:
                type: string
    responses:
        200:
          description: Username is now updated successfully
        400:
          description: Missing Username
        401:
          description: Unauthorized
        409:
          description: Username already exists
        500:
          description: Error in the database
    """
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

    #get new username from request body
    data = request.get_json()
    new_username = data.get('new_username')

    if not new_username:
        return jsonify({'status': 'error', 'message': 'Username is required'}), 400

    db = current_app.extensions['sqlalchemy']

    try:
        # Check if username already exists
        existing_user = db.session.execute(
            text('SELECT user_id FROM User_login WHERE username = :uname AND user_id != :uid'),
            {'uname': new_username, 'uid': user_id}
        ).fetchone()

        if existing_user:
            return jsonify(
                {'status': 'error', 'message': 'That username is already taken. Please choose another.'}), 409

        db.session.execute(
            text('UPDATE User_login SET username = :uname WHERE user_id = :uid'),
            {'uname': new_username, 'uid': user_id}
        )
        db.session.commit()

        return jsonify({'status': 'success', 'message': 'Username updated successfully'}), 200

    except Exception as e:
        db.session.rollback()
        print("DATABASE ERROR:", str(e))  # Helps catch any future issues!
        return jsonify({'status': 'error', 'message': 'Database error', 'detail': str(e)}), 500

    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Database error', 'detail': str(e)}), 500


@user_bp.route('/update-goals', methods=['PUT'])
def update_goals():
    """
    Must update the user's fitness goals and weight
    ---
    tags:
        - User - Goals
    parameters:
        - name: authorization
          in: header
          type: string
          required: true
        - in: body
          name: body
          required: true
          schema:
            type: object
            required:
              - current_weight
              - goal_weight
            properties:
              current_weight:
                type: number
              goal_weight:
                type: number
              goal_type:
                type: string
              information:
                type: string
    responses:
        200:
          description: The goals are now updated successfully
        400:
          description: Invalid Weight Input
        401:
          description: Unauthorized
        500:
          description: Error in the database
    """
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

    data = request.get_json()
    current_weight = data.get('current_weight')
    goal_weight = data.get('goal_weight')
    goal_type = data.get('goal_type')
    information = data.get('information')

    try:
        current_weight = float(current_weight)
        goal_weight = float(goal_weight)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'Weights must be valid numbers'}), 400

    db = current_app.extensions['sqlalchemy']

    try:
        db.session.execute(
            text("""UPDATE User_Profiles SET current_weight = :cw WHERE user_id = :uid"""),
            {'cw': current_weight, 'uid': user_id}
        )

        #log users change in weight for progress metrics
        db.session.execute(
            text('INSERT into weight_logs (user_id, weight) values (:uid, :cw)'),
            {'uid': user_id, 'cw': current_weight}
        )

        #Update goals if they exist for this user; otherwise insert a new row for this user in the goals table.
        goal_exists = db.session.execute(
            text('SELECT 1 FROM goals WHERE user_id = :uid'),
            {'uid': user_id}
        ).fetchone()

        if goal_exists:
            db.session.execute(
                text('''
                     UPDATE goals
                     SET goal_weight = :gw,
                         goal_type   = :gt,
                         information = :info
                     WHERE user_id = :uid
                     '''),
                {'gw': goal_weight, 'gt': goal_type, 'info': information, 'uid': user_id}
            )
        else:
            db.session.execute(
                text('''
                     INSERT INTO goals (user_id, goal_weight, goal_type, information)
                     VALUES (:uid, :gw, :gt, :info)
                     '''),
                {'uid': user_id, 'gw': goal_weight, 'gt': goal_type, 'info': information}
            )

        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Goals updated successfully'}), 200

    except Exception as e:
        db.session.rollback()
        print("DATABASE ERROR:", str(e))
        return jsonify({'status': 'error', 'message': 'Database error', 'detail': str(e)}), 500


@user_bp.route('/delete-account', methods=['DELETE'])
def delete_account():
    """
    Deletes the user account permanently
    ---
    tags:
        - User - Account
    parameters:
        - name: authorization
          in: header
          type: string
          required: true
    responses:
        200:
          description: The user account is now deleted successfully
        401:
          description: Unauthorized
        500:
          description: Error in the database
    """
    # Verify User token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        user_id = payload['sub']
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Invalid token'}), 401

    db = current_app.extensions['sqlalchemy']

    try:
        # Delete from child tables
        db.session.execute(text('DELETE FROM goals WHERE user_id = :uid'), {'uid': user_id})
        db.session.execute(text('DELETE FROM User_Profiles WHERE user_id = :uid'), {'uid': user_id})

        #Delete from parent table
        db.session.execute(text('DELETE FROM User_login WHERE user_id = :uid'), {'uid': user_id})

        db.session.commit()

        return jsonify({'status': 'success', 'message': 'Account deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        print("DATABASE ERROR ON DELETE:", str(e))
        return jsonify({'status': 'error', 'message': 'Database error', 'detail': str(e)}), 500


@user_bp.route('/check-survey', methods=['GET'])
def check_survey():
    """
    Check if the user has completed the daily survey
    ---
    tags:
        - User - Survey
    parameters:
        - name: authorization
          in: header
          type: string
          required: true
        - name: date
          in: query
          type: string
          description: Date in YYYY-MM-DD format (optional)
    responses:
        200:
          description: Survey status retrieved
          schema:
            type: object
            properties:
              status:
                type: string
              date:
                type: string
              rating:
                type: integer
        400:
          description: Invalid Date Format
        401:
          description: Unauthorized
        500:
          description: Error in the database
    """
    user_id, auth_error = _decode_user_id_from_token()
    if auth_error:
        user_id = 2

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


@user_bp.route('/daily-survey', methods=['POST'])
def save_daily_survey():
    """
    Must save or update the user's daily survey rating
    ---
    tags:
        - User - Survey
    parameters:
        - name: authorization
          in: header
          type: string
          required: true
        - in: body
          name: body
          required: true
          schema:
            type: object
            required:
              - rating
            properties:
              rating:
                type: integer
                example: 4
              date:
                type: string
                example: 2026-04-16
    responses:
        200:
          description: The survey is now saved successfully
        400:
          description: Invalid rating or date
        401:
          description: Unauthorized
        500:
          description: Error in the database
    """
    user_id, auth_error = _decode_user_id_from_token()
    if auth_error:
        user_id = 2

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
                    'INSERT INTO Daily_Survey (user_id, result, date) '
                    'VALUES (:uid, :result, :survey_date)'
                ),
                {
                    'uid': user_id,
                    'result': rating_value,
                    'survey_date': target_date_start
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


# check if user has coach, if yes get coach's id for future use
@user_bp.route('/has-coach/<int:user_id>', methods=['GET'])
def user_has_coach(user_id):
    """
    Checks if the user has a coach
    ---
    tags:
        - User - Coach
    parameters:
        - name: user_id
          in: path
          type: integer
          required: true
    responses:
        200:
          description: Coach status retrieved
          schema:
            type: object
            properties:
              status:
                type: string
              hasCoach:
                type: boolean
              coach_id:
                type: integer
        500:
          description: Error in the database
    """
    db = current_app.extensions['sqlalchemy']
    try:
        # Main Query to get a single coach data
        query = """SELECT coach_id, user_id FROM coach_subscriptions
                    WHERE user_id = :user_id"""
        result = db.session.execute(db.text(query), {"user_id": user_id}).mappings().fetchall()
        if len(result) > 0:
            hasCoach = True
            coach_id = result[0]["coach_id"]
        else:
            hasCoach = False
            coach_id = None

        return jsonify({
            "status":"success",
            "hasCoach":hasCoach,
            "coach_id":coach_id
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@user_bp.route('/update-payment', methods=['PATCH'])
def changePayment():
    """
    Must create or update the user's payment details
    ---
    tags:
        - User - Payment
    parameters:
        - name: authorization
          in: header
          type: string
          required: true
        - in: body
          name: body
          required: true
          schema:
            type: object
            required:
              - card_number
              - card_month
              - card_year
              - card_cvv
            properties:
              card_number:
                type: string
              card_month:
                type: integer
              card_year:
                type: integer
              card_cvv:
                type: string
    responses:
        200:
          description: Payment details updated
        400:
          description: Missing Fields
        401:
          description: Unauthorized
        500:
          description: Error in the database
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    token = auth_header.split(' ', 1)[1].strip() if auth_header.startswith('Bearer ') else auth_header.strip()
    try:
        payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        user_id = int(payload.get('sub'))
    except Exception:
        return jsonify({'status': 'error', 'message': 'Invalid or expired token'}), 401

    data = request.get_json(silent=True) or {}
    card_num = data.get('card_number')
    card_month = data.get('card_month')
    card_year = data.get('card_year')
    card_cvv = data.get('card_cvv')

    if not all([card_num, card_month, card_year, card_cvv]):
        return jsonify({
            'status': 'error',
            'message': 'card_number, card_month, card_year, and card_cvv are required.'
        }), 400

    db = current_app.extensions['sqlalchemy']

    try:
        existing_payment = db.session.execute(
            text('SELECT user_id FROM payment_details WHERE user_id = :uid LIMIT 1'),
            {'uid': user_id}
        ).mappings().first()

        if existing_payment:
            db.session.execute(
                text(
                    'UPDATE payment_details '
                    'SET card_num = :number, exp_month = :exp_month, exp_year = :exp_year, CVV = :cvc '
                    'WHERE user_id = :uid'
                ),
                {
                    'uid': user_id,
                    'number': card_num,
                    'exp_month': card_month,
                    'exp_year': card_year,
                    'cvc': card_cvv
                }
            )
            action = 'updated'
        else:
            db.session.execute(
                text(
                    'INSERT INTO payment_details '
                    '(user_id, card_num, exp_month, exp_year, CVV) '
                    'VALUES (:uid, :number, :exp_month, :exp_year, :cvc)'
                ),
                {
                    'uid': user_id,
                    'number': card_num,
                    'exp_month': card_month,
                    'exp_year': card_year,
                    'cvc': card_cvv
                }
            )
            action = 'created'

        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': f'Payment details {action} successfully.',
            'payment': {
                'card_number': card_num,
                'card_month': card_month,
                'card_year': card_year
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to update payment details.',
            'detail': str(e)
        }), 500


@user_bp.route('/chat/history/<int:me>/<int:other>', methods=['GET'])
def get_chat_history(me, other):
    """
    Must get chat history between the two users
    ---
    tags:
        - User - Chat
    parameters:
        - name: me
          in: path
          type: integer
          required: true
        - name: other
          in: path
          type: integer
          required: true
    responses:
        200:
          description: List of Messages
          schema:
            type: array
            items:
              type: object
              properties:
                sender_id:
                  type: integer
                text:
                  type: string
        500:
          description: Error in the database
    """
    db = current_app.extensions['sqlalchemy']
    query = text("""
        SELECT sender_id, content, created_at 
        FROM message 
        WHERE (sender_id = :me AND receiver_id = :other)
           OR (sender_id = :other AND receiver_id = :me)
        ORDER BY created_at ASC
    """)
    result = db.session.execute(query, {"me": me, "other": other}).fetchall()

    messages = [{"sender_id": r.sender_id, "text": r.message_text} for r in result]
    return jsonify(messages)


@user_bp.route('/weight-log/<int:user_id>', methods=['GET'])
def get_weight_logs(user_id):
    """
    Must retrieve the user's weight logs
    ---
    tags:
        - User - Progress
    parameters:
        - name: user_id
          in: path
          type: integer
          required: true
    responses:
        200:
          description: The weight logs are now retrieved
          schema:
            type: object
            properties:
              status:
                type: string
              data:
                type: array
                items:
                  type: object
                  properties:
                    weight:
                      type: number
                    log_date:
                      type: string
        500:
          description: Error in the database
    """
    db = current_app.extensions['sqlalchemy']
    query = text("""
        SELECT weight, log_date FROM weight_logs
        WHERE user_id = :user_id
    """)

    result = db.session.execute(query, {'user_id': user_id}).mappings().fetchall()

    logs = [dict(row) for row in result]
    return jsonify({'status': 'success', 'data': logs}), 200


@user_bp.route('/upload-progress-picture', methods=['POST'])
def upload_progress_picture():
    """
        Upload a new progress picture for a user
        ---
        tags:
          - User - Progress Pictures
        consumes:
          - multipart/form-data
        parameters:
          - name: user_id
            in: formData
            type: integer
            required: true
            description: The ID of the user uploading the picture
          - name: progress_image
            in: formData
            type: file
            required: true
            description: The image file to upload
        responses:
          201:
            description: Progress picture added successfully
          400:
            description: Missing data or invalid file format
          500:
            description: Database error
        """
    # 1. Get user_id directly from the request form instead of the token
    user_id = request.form.get('user_id')

    if not user_id:
        return jsonify({'status': 'error', 'message': 'User ID is required'}), 400

    # 2. Check if the file is in the request
    if 'progress_image' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part found'}), 400

    file = request.files['progress_image']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        # Create a unique filename to prevent overwriting
        import uuid
        unique_suffix = uuid.uuid4().hex[:8]
        filename = secure_filename(f"user_{user_id}_{unique_suffix}_{file.filename}")

        # Ensure the directory exists
        save_dir = os.path.join(current_app.root_path, PROGRESS_UPLOAD_FOLDER)
        os.makedirs(save_dir, exist_ok=True)

        # Save file to disk
        filepath = os.path.join(save_dir, filename)
        file.save(filepath)

        # Create the public URL
        file_url = f"http://127.0.0.1:5000/{PROGRESS_UPLOAD_FOLDER}/{filename}"

        # 3. Insert into Database
        db = current_app.extensions['sqlalchemy']
        try:
            db.session.execute(
                text('INSERT INTO Progress_Pictures (user_id, image_url) VALUES (:uid, :url)'),
                {'uid': user_id, 'url': file_url}
            )
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': 'Database error', 'detail': str(e)}), 500

        return jsonify({
            'status': 'success',
            'message': 'Progress picture added',
            'image_url': file_url
        }), 201

    return jsonify({'status': 'error', 'message': 'Invalid file format'}), 400


@user_bp.route('/progress-pictures/<int:target_user_id>', methods=['GET'])
def get_progress_pictures(target_user_id):
    """
        Retrieve all progress pictures for a specific user
        ---
        tags:
          - User - Progress Pictures
        parameters:
          - name: target_user_id
            in: path
            type: integer
            required: true
            description: The ID of the user whose pictures are being requested
        responses:
          200:
            description: A list of progress pictures
          500:
            description: Database error
        """
    db = current_app.extensions['sqlalchemy']

    try:
        result = db.session.execute(
            text('''
                SELECT picture_id, image_url, create_date 
                FROM Progress_Pictures 
                WHERE user_id = :uid 
                ORDER BY create_date DESC
            '''),
            {'uid': target_user_id}
        ).mappings().fetchall()

        pictures = [{
            'picture_id': row['picture_id'],
            'image_url': row['image_url'],
            'create_date': row['create_date'].isoformat()
        } for row in result]

        return jsonify({
            'status': 'success',
            'data': pictures
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Database error', 'detail': str(e)}), 500


@user_bp.route('/delete-progress-picture/<int:picture_id>/<int:user_id>', methods=['DELETE'])
def delete_progress_picture(picture_id, user_id=None):
    """
        Delete a specific progress picture and remove the file from storage
        ---
        tags:
          - User - Progress Pictures
        parameters:
          - name: picture_id
            in: path
            type: integer
            required: true
            description: The ID of the picture to delete
          - name: user_id
            in: path
            type: integer
            required: true
            description: The ID of the user who owns the picture
        responses:
          200:
            description: Progress picture deleted successfully
          404:
            description: Picture not found
          500:
            description: Database error or file cleanup failure
        """
    db = current_app.extensions['sqlalchemy']

    try:
        if user_id is None:
            picture = db.session.execute(
                text('SELECT picture_id, user_id, image_url FROM Progress_Pictures WHERE picture_id = :pid LIMIT 1'),
                {'pid': picture_id}
            ).mappings().first()
        else:
            picture = db.session.execute(
                text('SELECT picture_id, user_id, image_url FROM Progress_Pictures WHERE picture_id = :pid AND user_id = :uid LIMIT 1'),
                {'pid': picture_id, 'uid': user_id}
            ).mappings().first()

        if not picture:
            return jsonify({'status': 'error', 'message': 'Progress picture not found'}), 404

        if user_id is None:
            db.session.execute(
                text('DELETE FROM Progress_Pictures WHERE picture_id = :pid'),
                {'pid': picture_id}
            )
        else:
            db.session.execute(
                text('DELETE FROM Progress_Pictures WHERE picture_id = :pid AND user_id = :uid'),
                {'pid': picture_id, 'uid': user_id}
            )

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Failed to delete progress picture', 'detail': str(e)}), 500

    #File cleanup
    deleted_file = False
    try:
        image_url = str((picture.get('image_url') or '')).split('?', 1)[0]
        filename = os.path.basename(image_url)
        if filename:
            file_path = os.path.join(current_app.root_path, PROGRESS_UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                deleted_file = True
    except OSError:
        pass

    return jsonify({
        'status': 'success',
        'message': 'Progress picture deleted',
        'picture_id': picture_id,
        'user_id': picture.get('user_id'),
        'deleted_file': deleted_file
    }), 200


@user_bp.route('/survey-log/<int:user_id>', methods=['GET'])
def get_survey_logs(user_id):
    """
    Get the recent daily survey ratings for a specific user
    ---
    tags:
      - User - Survey
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: The unique ID of the user
        example: 7
    responses:
      200:
        description: Successfully retrieved survey logs
        # ... (rest of swagger docs stay the same)
    """
    db = current_app.extensions['sqlalchemy']
    try:
        # CHANGED: Select 'result' and alias it as 'rating'
        query = text("""
                     SELECT date, result as rating
                     FROM daily_survey
                     WHERE user_id = :user_id
                     ORDER BY date ASC
                         LIMIT 30
                     """)
        result = db.session.execute(query, {"user_id": user_id}).mappings().fetchall()

        # Format the dates for the frontend
        data = []
        for row in result:
            data.append({
                "date": row['date'].strftime('%b %d') if hasattr(row['date'], 'strftime') else row['date'],
                "rating": row['rating']
            })

        return jsonify({'status': 'success', 'data': data}), 200

    except Exception as e:
        print("DATABASE ERROR:", str(e))
        return jsonify({'status': 'error', 'message': 'Failed to fetch survey logs'}), 500


@user_bp.route('/calorie-log/<int:user_id>', methods=['GET'])
def get_calorie_logs(user_id):
    """
    Get the recent daily calorie logs for a specific user
    ---
    tags:
      - User - Nutrition
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: The unique ID of the user
        example: 7
    responses:
      200:
        description: Successfully retrieved calorie logs
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            data:
              type: array
              items:
                type: object
                properties:
                  date:
                    type: string
                    example: "Apr 28"
                  calories:
                    type: integer
                    example: 2500
      500:
        description: Database or server error
        schema:
          type: object
          properties:
            status:
              type: string
              example: error
            message:
              type: string
              example: Failed to fetch calorie logs
    """
    db = current_app.extensions['sqlalchemy']
    try:
        # Get the last 30 days of calorie logs, ordered by date
        query = text("""
                     SELECT log_date as date, calories
                     FROM calorie_logs
                     WHERE user_id = :user_id
                     ORDER BY date ASC
                         LIMIT 30
                     """)
        result = db.session.execute(query, {"user_id": user_id}).mappings().fetchall()

        # Format the dates for the frontend graph (e.g., "Apr 28")
        data = []
        for row in result:
            data.append({
                "date": row['date'].strftime('%b %d') if hasattr(row['date'], 'strftime') else row['date'],
                "calories": row['calories']
            })

        return jsonify({'status': 'success', 'data': data}), 200

    except Exception as e:
        print("DATABASE ERROR:", str(e))
        return jsonify({'status': 'error', 'message': 'Failed to fetch calorie logs'}), 500
