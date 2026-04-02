from flask import Blueprint, jsonify, current_app
from sqlalchemy import text

workout_bp = Blueprint('workout', __name__, url_prefix='/api/workouts')

@workout_bp.route('/exercises', methods=['GET'])
def get_exercises():
    db = current_app.extensions['sqlalchemy']

    try:
        #Grab all exercises that are available
        query = text("""
                     SELECT exercise_id, name, muscle_group, equipment_needed, video_url
                     FROM exercises
                     WHERE is_removed = 0
                     """)

        result = db.session.execute(query).mappings().fetchall()

        # Convert result to list of dicts
        exercises = [dict(row) for row in result]

        return jsonify({'status': 'success', 'data': exercises}), 200

    except Exception as e:
        print("DATABASE ERROR:", str(e))
        return jsonify({'status': 'error', 'message': 'Failed to fetch exercises'}), 500

@workout_bp.route('/daily-plan/<int:user_id>/<DOW>', methods=['GET'])
def get_daily_plan(user_id, DOW):
    db = current_app.extensions['sqlalchemy']
    dayofweek=str(DOW)
    print(DOW)
    try:
        #Grab all exercises that are available
        query = text("""
                    select wp.plan_id, pe.exercise_id, e.name, e.equipment_needed, pe.sets, pe.reps, pe.weight from workout_plans wp
                    join plan_exercise pe
                    on wp.plan_id = pe.plan_id
                    join exercises e
                    on e.exercise_id = pe.exercise_id 
                    where wp.user_id = :user_id and wp.planned_date like :DOW
                    group by pe.plan_exercise_id;
                     """)

        result = db.session.execute(query, {"user_id": user_id, "DOW": dayofweek}).mappings().fetchall()

        # Convert result to list of dicts
        exercises = [dict(row) for row in result]

        return jsonify({'status': 'success', 'data': exercises}), 200

    except Exception as e:
        print("DATABASE ERROR:", str(e))
        return jsonify({'status': 'error', 'message': 'Failed to fetch exercises'}), 500