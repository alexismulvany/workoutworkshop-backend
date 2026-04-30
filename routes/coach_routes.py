from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import text

coach_bp = Blueprint('coach_bp', __name__, url_prefix='/coach')

@coach_bp.route('/coach-data', methods=['GET'])
def get_coach_data():
    """
    Get All Coach Data
    ---
    tags:
        - Coach - Coach Data
    responses:
        200:
            description: All Coach Data Retrieved
        500:
            description: Error in the database
    """
    db = current_app.extensions['sqlalchemy']
    try:
        # Main Query to get coach data
        query = """SELECT c_p.coach_id, u_p.user_id, u_p.first_name, u_p.last_name, c_p.bio, c_p.is_nutritionist, c_p.is_active, c_p.pricing, u_p.profile_picture_url, AVG(c_r.rating) as rating FROM coach_profiles as c_p
        JOIN user_profiles AS u_p ON c_p.user_ID = u_p.user_id
		left JOIN coach_reviews AS c_r ON c_p.coach_id = c_r.coach_id 
        GROUP BY c_p.coach_id"""
        coaches = db.session.execute(db.text(query)).fetchall()
        coach_list = [{"Coach ID": c[0], "User ID": c[1], "Name": c[2]+' '+c[3],  "bio": c[4], "is_nutritionist": c[5], "is_active": c[6], "pricing": c[7], "URL": c[8], "rating": c[9]} for c in coaches]
        return jsonify({
            "status": "success",
            "data": coach_list
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@coach_bp.route('/coach-data/<int:coach_id>', methods=['GET'])
def get_single_coach_data(coach_id):
    """
    Get a single Coach Data
    ---
    tags:
        - Coach - Coach Data
    parameters:
        - name: coach_id
          in: path
          type: integer
          required: true
    responses:
        200:
            description: Single Coach Data Retrieved
        500:
            description: Error in the database
    """
    db = current_app.extensions['sqlalchemy']
    try:
        # Main Query to get coach data
        query = """SELECT c_p.coach_id, u_p.user_id, u_p.first_name, u_p.last_name, c_p.bio, c_p.is_nutritionist, c_p.is_active, c_p.pricing, u_p.profile_picture_url, AVG(c_r.rating) as rating FROM coach_profiles as c_p
        JOIN user_profiles AS u_p ON c_p.user_ID = u_p.user_id
		left JOIN coach_reviews AS c_r ON c_p.coach_id = c_r.coach_id 
        WHERE c_p.coach_id = :coach_id
        GROUP BY c_p.coach_id"""
        coach= db.session.execute(db.text(query), {"coach_id":coach_id}).fetchall()
        coachData = [{"Coach ID": c[0], "User ID": c[1], "Name": c[2]+' '+c[3],  "bio": c[4], "is_nutritionist": c[5], "is_active": c[6], "pricing": c[7], "URL": c[8], "rating": c[9]} for c in coach]
        return jsonify({
            "status": "success",
            "data": coachData
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

#get the reviews of a coach
@coach_bp.route('/coach-reviews/<int:coach_id>', methods=['GET'])
def get_coach_reviews(coach_id):
    """
    Get reviews of a coach
    ---
    tags:
        - Coach - Coach Reviews
    parameters:
        - name: coach_id
          in: path
          type: integer
          required: true
    responses:
        200:
            description: Coach review retrieved
        404:
            description: Coach not found
        500:
            description: Error in the database
    """
    db = current_app.extensions['sqlalchemy']
    try:
        # Main Query to get a single coach data
        query = """SELECT u_p.first_name, u_p.last_name, c_r.rating, c_r.comment, c_r.review_id
        FROM coach_reviews c_r 
        JOIN user_profiles u_p on c_r.user_id = u_p.user_id
        WHERE c_r.coach_id = :coach_id"""
        review = db.session.execute(db.text(query), {"coach_id": coach_id}).fetchall()
        if review:
            review_data = [{"reviewer": r[0]+' '+r[1], "rating": r[2], "comment": r[3], "review_id":r[4]} for r in review]
            return jsonify({
                "status": "success",
                "data": review_data
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Coach not found"
            }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@coach_bp.route('/user-coach-sub/<int:user_id>/<int:coach_id>', methods=['GET'])
def user_coach_sub(user_id, coach_id):
    """
    Get user-coach subscription status
    ---
    tags:
        - Coach - User-Coach Subscription Status
    parameters:
        - name: user_id
          in: path
          type: integer
          required: true
        - name: coach_id
          in: path
          type: integer
          required: true
    responses:
        200:
            description: Status retrieved
        500:
            description: Error in the database
    """
    db = current_app.extensions['sqlalchemy']
    try:
        # Main Query to get a single coach data
        query = """SELECT * from coach_subscriptions c_s
        WHERE c_s.user_id = :user_id and c_s.coach_id = :coach_id
        """
        subscription = db.session.execute(db.text(query), {"user_id": user_id, "coach_id": coach_id}).fetchone()

        query = """SELECT * FROM coach_subscriptions c_s
        WHERE c_s.user_id = :user_id"""
        
        hasCoach = db.session.execute(db.text(query), {"user_id": user_id}).fetchone()
        if hasCoach:
            if subscription:
                return jsonify({
                    "status": "success",
                    "hired": True,
                    "hasCoach": True
                }), 200

            return jsonify({
                "status": "success",
                "hasCoach": True
            }), 200
        
        else:
            return jsonify({
                "status": "success",
                "hired": False
            }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@coach_bp.route('/coach-availibility/<int:coach_id>', methods=['GET'])
def coach_availibility(coach_id):
    """
    Get a coach's availibility
    ---
    tags:
        - Coach - User Options
    parameters:
        - name: coach_id
          in: path
          type: integer
          required: true
    responses:
        200:
            description: Coach availibility retrieved
        500:
            description: Error in the database
    """
    db = current_app.extensions['sqlalchemy']
    try:
        # Main Query to get coach data
        query = """select DOW from coach_availability ca 
        where coach_id = :coach_id;"""
        coach = db.session.execute(db.text(query), {"coach_id": coach_id}).fetchall()
        coach_list = [{"DOW":c[0]} for c in coach]
        daysofWeek=["SUN", "M", "T", "W", "TH", "F", "SAT"]
        coach_availibility={}

        for i in daysofWeek:
            coach_availibility[i] = False
        
        for i in coach_list:
            coach_availibility[i["DOW"]] = True

        
        return jsonify({
            "status": "success",
            "data": coach_availibility
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@coach_bp.route('/send-user-coach-app', methods=["POST"])
def send_user_coach_app():
    """
    Sends User-Coach Application
    ---
    tags:
        - Coach - Coach Applications
    parameters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            required:
                - user_id
                - coach_id
                - comment
            properties:
                user_id:
                    type: integer
                coach_id:
                    type: integer
                comment:
                    type: string
    responses:
        200:
            description: Application successfully sent
        400:
            description: Error sending application/missing fields
    """
    payload = request.get_json(silent=True) or {}

    try:
        user_id = payload.get('user_id')
        coach_id = payload.get('coach_id')
        comment = payload.get('comment')

        if not all([user_id, coach_id, comment]):
            return jsonify({
                'status':  'error',
                'message': 'user_id, coach_id, and comment are required.'
            }), 400

        db  = current_app.extensions['sqlalchemy']
        session = db.session

        session.execute(
            text(
                'insert into Coach_requests (user_id, coach_id, comment) values (:user_id, :coach_id, :comment)'
            ),
                {'user_id': user_id, 'coach_id': coach_id, 'comment': comment}
        )

        session.commit()

        return jsonify({"message":"Application successfull"}), 200
        
    except:
        return jsonify({"message":"Error sending application"}), 400

@coach_bp.route('/send-coach-report', methods=["POST"])
def send_coach_report():
    """
    Sends Coach Report
    ---
    tags:
        - Coach - User Options
    parameters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            required:
                - reporter_id
                - coach_id
                - message
            properties:
                reporter_id:
                    type: integer
                coach_id:
                    type: integer
                message:
                    type: string
    responses:
        200:
            description: Report successfully sent
        400:
            description: Error sending report/missing fields
    """
    payload = request.get_json(silent=True) or {}

    try:
        reporter_id = payload.get('reporter_id')
        coach_id = payload.get('coach_id')
        message = payload.get('message')

        if not all([reporter_id, coach_id, message]):
            return jsonify({
                'status':  'error',
                'message': 'reporter_id, coach_id, and message are required.'
            }), 400

        db  = current_app.extensions['sqlalchemy']
        session = db.session

        session.execute(
            text(
                'insert into Coach_reports (reporter_id, coach_id, reason) values (:reporter_id, :coach_id, :message)'
            ),
                {'reporter_id': reporter_id, 'coach_id': coach_id, 'message': message}
        )

        session.commit()

        return jsonify({"message":"Application successfull"}), 200
        
    except:
        return jsonify({"message":"Error sending application"}), 400

@coach_bp.route('/fire-coach', methods=["POST"])
def fire_coach():
    """
    Fires Coach
    ---
    tags:
        - Coach - User Options
    parameters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            required:
                - user_id
                - coach_id
            properties:
                user_id:
                    type: integer
                coach_id:
                    type: integer
    responses:
        200:
            description: Coach successfully fired
        400:
            description: Error firing coach/missing fields
    """
    payload = request.get_json(silent=True) or {}

    try:
        user_id = payload.get('user_id')
        coach_id = payload.get('coach_id')

        if not all([user_id, coach_id]):
            return jsonify({
                'status':  'error',
                'message': 'user_id coach_id are required.'
            }), 400

        db  = current_app.extensions['sqlalchemy']
        session = db.session

        session.execute(
            text(
                'delete from coach_subscriptions where coach_id = :coach_id and user_id = :user_id'
            ),
                {'coach_id': coach_id, 'user_id': user_id,}
        )

        session.commit()

        return jsonify({"message":"Application successfull"}), 200
        
    except:
        return jsonify({"message":"Error sending application"}), 400

@coach_bp.route('/submit-coach-review', methods=['POST'])
def submit_review():
    """
    Sends Coach Review
    ---
    tags:
        - Coach - Coach Reviews
    parameters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            required:
                - user_id
                - coach_id
                - rating
                - message
            properties:
                user_id:
                    type: integer
                coach_id:
                    type: integer
                rating:
                    type: integer
                message:
                    type: string
    responses:
        200:
            description: Review successfully sent
        400:
            description: Error sending review/missing fields
    """

    payload = request.get_json(silent=True) or {}

    try:
        user_id = payload.get('user_id')
        coach_id = payload.get('coach_id')
        rating = payload.get('rating')
        message = payload.get('message')

        if not all([user_id, coach_id, rating]):
            print("missing data")
            return jsonify({
                'status':  'error',
                'message': 'user_id, rating, and coach_id are required.'
            }), 400

        db  = current_app.extensions['sqlalchemy']
        session = db.session

        if message:
            print("got message")
            message = payload.get('message')

            session.execute(
            text(
                'insert into coach_reviews (user_id, coach_id, rating, comment) values (:user_id, :coach_id, :rating, :message)'
            ),
                {'user_id': user_id, 'coach_id': coach_id, 'rating': rating, 'message': message}
            )

        else:
            session.execute(
            text(
                'insert into coach_reviews (user_id, coach_id, rating) values (:user_id, :coach_id, :rating)'
            ),
                {'user_id': user_id, 'coach_id': coach_id, 'rating': rating}
            )

        session.commit()
        return jsonify({"message":"Application successfull"}), 200

    except: 
        return jsonify({"message":"Error sending application"}), 400
        
 # -------------------------------------------------------------------------------------------------------------------
       
@coach_bp.route('/requests/<int:coach_id>', methods=['GET'])
def get_coach_requests(coach_id):
    """
    Get Coach Requests for a coach
    ---
    tags:
        - Coach - Coach Applications
    parameters:
        - name: coach_id
          in: path
          type: integer
          required: true
    responses:
        200:
            description: Request list successfully retrieved
        500:
            description: Error in the database
    """
    db = current_app.extensions['sqlalchemy']
    try:
        query = """
            SELECT cr.request_id, cr.user_id, cr.status, cr.comment,
            up.first_name, up.last_name, up.profile_picture_url,
            g.goal_type
            FROM coach_requests cr
            JOIN user_profiles up ON cr.user_id = up.user_id
            LEFT JOIN goals g ON cr.user_id = g.user_id
            WHERE cr.coach_id = :coach_id AND cr.status = 'pending'
            ORDER BY cr.create_date ASC
        """
        requests = db.session.execute(db.text(query), {"coach_id": coach_id}).fetchall()
        request_list = [
            {
                "request_id": r[0],
                "user_id": r[1],
                "status": r[2],
                "comment": r[3],
                "first_name": r[4],
                "last_name": r[5],
                "profile_picture_url": r[6],
                "goal_type": r[7]
            } for r in requests
        ]
        return jsonify({"status": "success", "data": request_list}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@coach_bp.route('/requests/<int:request_id>/decision', methods=['POST'])
def decide_coach_request(request_id):
    """
    Sends Coach Application Decision
    ---
    tags:
        - Coach - Coach Applications
    parameters:
        - name: request_id
          in: path
          type: integer
          required: true
        - name: body
          in: body
          required: true
          schema:
            type: object
            required:
                - decision
                - coach_id
            properties:
                decision:
                    type: string
                    example: 'accepted, rejected'
                coach_id:
                    type: integer
    responses:
        200:
            description: Decision successfully sent
        400:
            description: Error sending decision/missing fields
        404:
            description: Request not found
        500:
            description: Error in the database
    """
    payload = request.get_json(silent=True) or {}
    try:
        decision = payload.get('decision')
        coach_id = payload.get('coach_id')

        if not all([decision, coach_id]):
            return jsonify({"status": "error", "message": "decision and coach_id are required."}), 400

        if decision not in ('accepted', 'rejected'):
            return jsonify({"status": "error", "message": "decision must be accepted or rejected."}), 400

        db = current_app.extensions['sqlalchemy']
        session = db.session

        req_row = session.execute(
            db.text("SELECT user_id, status FROM coach_requests WHERE request_id = :rid AND coach_id = :cid LIMIT 1"),
            {"rid": request_id, "cid": coach_id}
        ).fetchone()

        if not req_row:
            return jsonify({"status": "error", "message": "Request not found."}), 404

        if req_row[1] != 'pending':
            return jsonify({"status": "error", "message": "Request has already been decided."}), 400

        client_user_id = req_row[0]

        session.execute(
            db.text("UPDATE coach_requests SET status = :decision, last_update = NOW() WHERE request_id = :rid"),
            {"decision": decision, "rid": request_id}
        )

        if decision == 'accepted':
            session.execute(
                db.text("INSERT INTO coach_subscriptions (user_id, coach_id) VALUES (:uid, :cid)"),
                {"uid": client_user_id, "cid": coach_id}
            )

        session.commit()
        return jsonify({"status": "success", "message": f"Request {decision} successfully."}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@coach_bp.route('/clients/<int:coach_id>', methods=['GET'])
def get_coach_clients(coach_id):
    """
    Get a coach's clients
    ---
    tags:
        - Coach - Coach Clients
    parameters:
        - name: coach_id
          in: path
          type: integer
          required: true
    responses:
        200:
            description: Client list successfully retrieved
        500:
            description: Error in the database
    """
    db = current_app.extensions['sqlalchemy']
    try:
        query = """
            SELECT cs.user_id, up.first_name, up.last_name,
            up.profile_picture_url, g.goal_type
            FROM coach_subscriptions cs
            JOIN user_profiles up ON cs.user_id = up.user_id
            LEFT JOIN goals g ON cs.user_id = g.user_id
            WHERE cs.coach_id = :coach_id
        """
        clients = db.session.execute(db.text(query), {"coach_id": coach_id}).fetchall()
        client_list = [
            {
                "user_id": c[0],
                "first_name": c[1],
                "last_name": c[2],
                "profile_picture_url": c[3],
                "goal_type": c[4]
            } for c in clients
        ]
        return jsonify({"status": "success", "data": client_list}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@coach_bp.route('/profile/<int:coach_id>', methods=['GET'])
def get_coach_profile(coach_id):
    """
    Get a coach's profile
    ---
    tags:
        - Coach - Coach Profile
    parameters:
        - name: coach_id
          in: path
          type: integer
          required: true
    responses:
        200:
            description: Coach profile successfully retrieved
        500:
            description: Error in the database
    """
    db = current_app.extensions['sqlalchemy']
    try:
        profile = db.session.execute(
            db.text("SELECT coach_id, bio, pricing, is_nutritionist FROM coach_profiles WHERE coach_id = :cid LIMIT 1"),
            {"cid": coach_id}
        ).fetchone()

        if not profile:
            return jsonify({"status": "error", "message": "Coach profile not found."}), 404

        availability = db.session.execute(
            db.text("SELECT DOW, start_time, end_time FROM coach_availability WHERE coach_id = :cid"),
            {"cid": coach_id}
        ).fetchall()

        return jsonify({
            "status": "success",
            "data": {
                "coach_id": profile[0],
                "bio": profile[1],
                "pricing": float(profile[2]),
                "is_nutritionist": profile[3],
                "availability": [{"dow": a[0], "start_time": str(a[1])[:5], "end_time": str(a[2])[:5]} for a in availability]
            }
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@coach_bp.route('/profile/<int:coach_id>', methods=['PUT'])
def update_coach_profile(coach_id):
    """
    Updates Coach Profile
    ---
    tags:
        - Coach - Coach Profile
    parameters:
        - name: coach_id
          in: path
          type: integer
          required: true
        - name: body
          in: body
          schema:
            type: object
            required:
                - bio
                - pricing
                - availibility
            properties:
                bio:
                    type: string
                pricing:
                    type: string
                availibility:
                    type: array
                    items:
                        properties:
                            dow:
                                type: string
                            end_time:
                                type: string
                            start_time:
                                type: string
    responses:
        200:
            description: Coach Profile successfully updated
        500:
            description: Error in the database
    """
    payload = request.get_json(silent=True) or {}
    try:
        bio = payload.get('bio')
        pricing = payload.get('pricing')
        availability = payload.get('availability')

        db = current_app.extensions['sqlalchemy']
        session = db.session

        if bio is not None or pricing is not None:
            session.execute(
                db.text("UPDATE coach_profiles SET bio = COALESCE(:bio, bio), pricing = COALESCE(:pricing, pricing), last_update = NOW() WHERE coach_id = :cid"),
                {"bio": bio, "pricing": float(pricing) if pricing is not None else None, "cid": coach_id}
            )

        if availability is not None:
            session.execute(
                db.text("DELETE FROM coach_availability WHERE coach_id = :cid"),
                {"cid": coach_id}
            )
            for slot in availability:
                session.execute(
                    db.text("INSERT INTO coach_availability (coach_id, DOW, start_time, end_time) VALUES (:cid, :dow, :start, :end)"),
                    {"cid": coach_id, "dow": slot.get('dow'), "start": slot.get('start_time'), "end": slot.get('end_time')}
                )

        session.commit()
        return jsonify({"status": "success", "message": "Profile updated successfully."}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@coach_bp.route('/coach-id/<int:user_id>', methods=['GET'])
def get_coach_id(user_id):
    """
    Get Coach ID from User ID
    ---
    tags:
        - Coach - Coach Data
    parameters:
        - name: user_id
          in: path
          type: integer
          required: true
    responses:
        200:
            description: Coach ID successfully retrieved
        404:
            description: Coach profile not found
        500:
            description: Error in the database
    """
    db = current_app.extensions['sqlalchemy']
    try:
        result = db.session.execute(
            db.text("SELECT coach_id FROM coach_profiles WHERE user_id = :uid LIMIT 1"),
            {"uid": user_id}
        ).fetchone()
        if not result:
            return jsonify({"status": "error", "message": "Coach profile not found."}), 404
        return jsonify({"status": "success", "coach_id": result[0]}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@coach_bp.route('/meal-plan/<int:coach_id>/<int:user_id>', methods=['GET'])
def get_meal_plan(coach_id, user_id):
    """
    Get meal plan
    ---
    tags:
        - Coach - Meal Plan
    parameters:
        - name: coach_id
          in: path
          type: integer
          required: true
        - name: user_id
          in: path
          type: integer
          required: true
    responses:
        200:
            description: Meal Plan successfully retrieved
        500:
            description: Error in the database
    """
    db = current_app.extensions['sqlalchemy']
    try:
        weekly = db.session.execute(
            db.text(
                'SELECT weekly_meals_id FROM weekly_meals '
                'WHERE coach_id = :cid AND user_id = :uid LIMIT 1'
            ),
            {'cid': coach_id, 'uid': user_id}
        ).fetchone()

        if not weekly:
            return jsonify({'status': 'success', 'data': None}), 200

        weekly_id = weekly[0]

        meals = db.session.execute(
            db.text(
                'SELECT meal_id, DOW, meal FROM meal_plans '
                'WHERE weekly_meal_id = :wid'
            ),
            {'wid': weekly_id}
        ).fetchall()

        meal_list = [{'meal_id': m[0], 'dow': m[1], 'meal': m[2]} for m in meals]

        return jsonify({'status': 'success', 'data': meal_list}), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@coach_bp.route('/meal-plan/<int:coach_id>/<int:user_id>', methods=['POST'])
def save_meal_plan(coach_id, user_id):
    """
    Uploads Meal Plan
    ---
    tags:
        - Coach - Meal Plan
    parameters:
        - name: coach_id
          in: path
          type: integer
          required: true
        - name: user_id
          in: path
          type: integer
          required: true
        - name: body
          in: body
          schema:
            type: object
            required:
                - dow
                - meal
                - weekly_id
            properties:
                dow:
                    type: string
                meal:
                    type: string
                weekly_id:
                    type: integer
    responses:
        200:
            description: Meal Plan successfully saved
        400:
            description: No meals provided
        500:
            description: Error in the database
    """
    payload = request.get_json(silent=True) or {}
    meals = payload.get('meals')

    if not meals:
        return jsonify({'status': 'error', 'message': 'No meals provided.'}), 400

    db = current_app.extensions['sqlalchemy']
    session = db.session

    try:
        weekly = session.execute(
            db.text(
                'SELECT weekly_meals_id FROM weekly_meals '
                'WHERE coach_id = :cid AND user_id = :uid LIMIT 1'
            ),
            {'cid': coach_id, 'uid': user_id}
        ).fetchone()

        if weekly:
            weekly_id = weekly[0]
            session.execute(
                db.text('DELETE FROM meal_plans WHERE weekly_meal_id = :wid'),
                {'wid': weekly_id}
            )
        else:
            session.execute(
                db.text(
                    'INSERT INTO weekly_meals (coach_id, user_id) '
                    'VALUES (:cid, :uid)'
                ),
                {'cid': coach_id, 'uid': user_id}
            )
            weekly_id = session.execute(db.text('SELECT LAST_INSERT_ID()')).scalar()

        for meal in meals:
            session.execute(
                db.text(
                    'INSERT INTO meal_plans (DOW, meal, weekly_meal_id) '
                    'VALUES (:dow, :meal, :wid)'
                ),
                {'dow': meal.get('dow'), 'meal': meal.get('meal'), 'wid': weekly_id}
            )

        session.commit()
        return jsonify({'status': 'success', 'message': 'Meal plan saved.'}), 200

    except Exception as e:
        session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@coach_bp.route('/update-plan-title/<int:plan_id>', methods=['PUT'])
def update_plan_title(plan_id):
    """
    Update Workout Plan title
    ---
    tags:
        - Coach - Coach Workout
    parameters:
        - name: plan_id
          in: path
          type: integer
          required: true
        - name: body
          in: body
          schema:
            type: object
            required:
                - title
            properties:
                title:
                    type: string
    responses:
        200:
            description: Workout plan title successfully updated
        400:
            description: Title is required
        500:
            description: Error in the database
    """
    payload = request.get_json(silent=True) or {}
    title = payload.get('title')
    if not title:
        return jsonify({'status': 'error', 'message': 'Title is required.'}), 400
    db = current_app.extensions['sqlalchemy']
    try:
        db.session.execute(
            db.text('UPDATE workout_plans SET title = :title WHERE plan_id = :pid'),
            {'title': title, 'pid': plan_id}
        )
        db.session.commit()
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@coach_bp.route('/delete-plan/<int:plan_id>', methods=['DELETE'])
def delete_workout_plan(plan_id):
    """
    Delete Workout Plan
    ---
    tags:
        - Coach - Coach Workout
    parameters:
        - name: plan_id
          in: path
          type: integer
          required: true
    responses:
        200:
            description: Workout Plan successfully deleted
        500:
            description: Error in the database
    """
    db = current_app.extensions['sqlalchemy']
    session = db.session
    try:
        session.execute(
            db.text('DELETE FROM plan_exercise WHERE plan_id = :pid'),
            {'pid': plan_id}
        )
        session.execute(
            db.text('DELETE FROM workout_plans WHERE plan_id = :pid'),
            {'pid': plan_id}
        )
        session.commit()
        return jsonify({'status': 'success', 'message': 'Plan deleted.'}), 200
    except Exception as e:
        session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@coach_bp.route('/my-coach/<int:user_id>', methods=['GET'])
def get_user_coach(user_id):
    db = current_app.extensions['sqlalchemy']
    try:
        result = db.session.execute(
            db.text("""
                SELECT cs.coach_id FROM coach_subscriptions cs
                WHERE cs.user_id = :uid LIMIT 1
            """),
            {"uid": user_id}
        ).fetchone()
        if not result:
            return jsonify({"status": "success", "coach_id": None}), 200
        return jsonify({"status": "success", "coach_id": result[0]}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500