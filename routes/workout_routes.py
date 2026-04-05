from flask import Blueprint, jsonify, current_app, request
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
                    select pe.exercise_id, e.name, e.equipment_needed, pe.sets, pe.reps, pe.weight from workout_plans wp
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


@workout_bp.route('/save', methods=['POST'])
def save_workout():
    db = current_app.extensions['sqlalchemy']

    #Get data from Payload
    data = request.get_json()

    user_id = data.get('user_id')
    planned_date = data.get('date')
    workout_name = data.get('workout_name')
    exercises = data.get('exercises', [])

    # Validates all fields are in the payload
    if not all([user_id, planned_date, exercises]):
        return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400

    try:
        #Insert plan into workout_plans
        insert_plan_query = text("""
                                INSERT INTO workout_plans (user_id, planned_date, title)
                                VALUES (:user_id, :planned_date, :title)
                                """)

        result = db.session.execute(insert_plan_query, {
            "user_id": user_id,
            "planned_date": planned_date,
            "title": workout_name
        })

        # get plan_id
        plan_id = result.lastrowid

        # Insert into plan_exercise for each exercise in the workout
        insert_exercise_query = text("""
                                    INSERT INTO plan_exercise (plan_id, exercise_id, sets, reps, weight)
                                    VALUES (:plan_id, :exercise_id, :sets, :reps, :weight)
                                    """)

        for exercise in exercises:
            db.session.execute(insert_exercise_query, {
                "plan_id": plan_id,
                "exercise_id": exercise['exercise_id'],
                "sets": 0,
                "reps": 0,
                "weight": 0
            })

        db.session.commit()

        return jsonify({'status': 'success', 'message': 'Workout saved successfully!'}), 201

    except Exception as e:
        db.session.rollback()
        print("DATABASE ERROR:", str(e))
        return jsonify({'status': 'error', 'message': 'Failed to save workout'}), 500


@workout_bp.route('/log/<int:user_id>', methods=['GET'])
def get_workout_log(user_id):
    db = current_app.extensions['sqlalchemy']

    try:
        # Grab workouts, newest first
        query = text("""
            SELECT plan_id as id, planned_date as date, title 
            FROM workout_plans 
            WHERE user_id = :user_id
            ORDER BY plan_id DESC
        """)

        result = db.session.execute(query, {"user_id": user_id}).mappings().fetchall()

        # Convert result to list of dicts
        workouts = [dict(row) for row in result]

        return jsonify({'status': 'success', 'data': workouts}), 200

    except Exception as e:
        print("DATABASE ERROR:", str(e))
        return jsonify({'status': 'error', 'message': 'Failed to fetch workout log'}), 500


@workout_bp.route('/plan/<int:plan_id>', methods=['GET'])
def get_workout_plan_details(plan_id):
    db = current_app.extensions['sqlalchemy']

    try:
        # Join the plan_exercise table with the exercises table to get the names/urls
        query = text("""
            SELECT pe.exercise_id, e.name as exercise_name, e.video_url, pe.sets, pe.reps, pe.weight
            FROM plan_exercise pe
            JOIN exercises e ON pe.exercise_id = e.exercise_id
            WHERE pe.plan_id = :plan_id
        """)

        result = db.session.execute(query, {"plan_id": plan_id}).mappings().fetchall()
        exercises = [dict(row) for row in result]

        return jsonify({'status': 'success', 'data': exercises}), 200

    except Exception as e:
        print("DATABASE ERROR:", str(e))
        return jsonify({'status': 'error', 'message': 'Failed to fetch plan details'}), 500


@workout_bp.route('/plan/<int:plan_id>', methods=['PUT'])
def update_workout_plan(plan_id):
    db = current_app.extensions['sqlalchemy']
    data = request.json
    exercises = data.get('exercises', [])

    try:
        #Loop through exercise and update each one in the plan_exercise table
        for ex in exercises:
            update_query = text("""
                                UPDATE plan_exercise
                                SET reps   = :reps,
                                    sets   = :sets,
                                    weight = :weight
                                WHERE plan_id = :plan_id
                                  AND exercise_id = :exercise_id
                                """)

            db.session.execute(update_query, {
                "reps": ex.get('reps'),
                "sets": ex.get('sets'),
                "weight": ex.get('weight'),
                "plan_id": plan_id,
                "exercise_id": ex.get('exercise_id')
            })

        db.session.commit()

        return jsonify({'status': 'success', 'message': 'Workout updated successfully!'}), 200

    except Exception as e:
        db.session.rollback()
        print("DATABASE ERROR:", str(e))
        return jsonify({'status': 'error', 'message': 'Failed to update workout'}), 500


@workout_bp.route('/plan/<int:plan_id>/exercise/<int:exercise_id>', methods=['DELETE'])
def remove_exercise_from_plan(plan_id, exercise_id):
    db = current_app.extensions['sqlalchemy']

    try:
        #Delete the exercise from the plan_exercise table for the given plan_id and exercise_id
        delete_query = text("""
                            DELETE
                            FROM plan_exercise
                            WHERE plan_id = :plan_id
                              AND exercise_id = :exercise_id
                            """)

        db.session.execute(delete_query, {
            "plan_id": plan_id,
            "exercise_id": exercise_id
        })

        db.session.commit()

        return jsonify({'status': 'success', 'message': 'Exercise removed from workout!'}), 200

    except Exception as e:
        db.session.rollback()
        print("DATABASE ERROR:", str(e))
        return jsonify({'status': 'error', 'message': 'Failed to remove exercise'}), 500