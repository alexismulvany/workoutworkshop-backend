from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import text

coach_bp = Blueprint('coach_bp', __name__, url_prefix='/coach')

@coach_bp.route('/coach-data', methods=['GET'])
def get_coach_data():
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

#get the reviews of a coach
@coach_bp.route('/coach-reviews/<int:coach_id>', methods=['GET'])
def get_coach_reviews(coach_id):
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
        



    

