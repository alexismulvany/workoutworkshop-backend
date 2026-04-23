from flask import Blueprint, jsonify, current_app, request
from sqlalchemy import text

workout_bp = Blueprint('workout', __name__, url_prefix='/api/workouts')


# fetch list of exercises
@workout_bp.route('/exercises', methods=['GET'])
def get_exercises():
    db = current_app.extensions['sqlalchemy']

    try:
        # Grab all exercises that are available
        query = text("""
                     SELECT exercise_id, name, muscle_group, equipment_needed, video_url, thumbnail
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


# get daily workout plan
@workout_bp.route('/daily-plan/<int:user_id>/<DOW>', methods=['GET'])
def get_daily_plan(user_id, DOW):
    db = current_app.extensions['sqlalchemy']
    dayofweek = str(DOW)
    try:
        # Grab all exercises that are available
        query = text("""
                     select pe.plan_id,
                            pe.plan_exercise_id,
                            pe.exercise_id,
                            e.name,
                            e.video_url,
                            e.thumbnail,
                            e.equipment_needed,
                            pe.sets,
                            pe.reps,
                            pe.weight,
                            pe.completed
                     from workout_plans wp
                              join plan_exercise pe
                                   on wp.plan_id = pe.plan_id
                              join exercises e
                                   on e.exercise_id = pe.exercise_id
                     where wp.user_id = :user_id
                       and wp.planned_date like :DOW
                     group by pe.plan_exercise_id;
                     """)

        result = db.session.execute(query, {"user_id": user_id, "DOW": dayofweek}).mappings().fetchall()

        # Convert result to list of dicts
        exercises = [dict(row) for row in result]
        if len(result) > 0:
            hasPlan = True
        else:
            hasPlan = False

        return jsonify({'status': 'success', 'data': exercises, 'hasPlan': hasPlan}), 200

    except Exception as e:
        print("DATABASE ERROR:", str(e))
        return jsonify({'status': 'error', 'message': 'Failed to fetch exercises'}), 500


@workout_bp.route('/save', methods=['POST'])
def save_workout():
    db = current_app.extensions['sqlalchemy']

    # Get data from Payload
    data = request.get_json()

    user_id = data.get('user_id')
    planned_date = data.get('date')
    workout_name = data.get('workout_name')
    exercises = data.get('exercises', [])

    # Validates all fields are in the payload
    if not all([user_id, planned_date, exercises]):
        return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400

    try:
        # Insert plan into workout_plans
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
                                     INSERT INTO plan_exercise (plan_id, exercise_id, `sets`, reps, weight)
                                     VALUES (:plan_id, :exercise_id, :sets, :reps, :weight)
                                     """)

        # Defaults sets, reps, weight to 0 if empty
        for exercise in exercises:
            db.session.execute(insert_exercise_query, {
                "plan_id": plan_id,
                "exercise_id": exercise['exercise_id'],
                "sets": exercise.get('sets', 0),
                "reps": exercise.get('reps', 0),
                "weight": exercise.get('weight', 0)
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
                     SELECT pe.exercise_id, e.name as exercise_name, e.video_url, pe.sets, pe.reps, pe.weight, e.thumbnail
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
        # Loop through exercise and update each one in the plan_exercise table
        for ex in exercises:
            update_query = text("""
                                UPDATE plan_exercise
                                SET reps   = :reps,
                                    `sets`   = :sets,
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
def remove_exercise_from_log(plan_id, exercise_id):
    db = current_app.extensions['sqlalchemy']

    try:
        # Delete the exercise from the plan_exercise table for the given plan_id and exercise_id
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


# Change '/log/<int:plan_id>' to '/plan/<int:plan_id>'
@workout_bp.route('/plan/<int:plan_id>', methods=['DELETE'])
def remove_workout_from_log(plan_id):
    db = current_app.extensions['sqlalchemy']

    try:
        # Delete all exercises to prevent foreign key constraint issues
        delete_exercises_query = text("""
                                      DELETE
                                      FROM plan_exercise
                                      WHERE plan_id = :plan_id
                                      """)
        db.session.execute(delete_exercises_query, {"plan_id": plan_id})

        # Delete workout plan
        delete_plan_query = text("""
                                 DELETE
                                 FROM workout_plans
                                 WHERE plan_id = :plan_id
                                 """)
        db.session.execute(delete_plan_query, {"plan_id": plan_id})

        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Workout deleted successfully!'}), 200

    except Exception as e:
        db.session.rollback()
        print("DATABASE ERROR:", str(e))
        return jsonify({'status': 'error', 'message': 'Failed to delete workout'}), 500


# add individual exercise from daily-workout plan
@workout_bp.route('/add-workout', methods=["POST"])
def add_workout_to_plan():
    payload = request.get_json(silent=True) or {}

    try:
        planned_date = payload.get("planned_date")
        user_id = payload.get("user_id")
        exercise_id = payload.get("exercise_id")

        if not all([planned_date, user_id, exercise_id]):
            return jsonify({
                'status': 'error',
                'message': 'failed to recieve date or exercise_id or user_id'
            }), 400

        db = current_app.extensions['sqlalchemy']
        session = db.session

        # check if user has a plan already made for that date
        query = text("""
                     select *
                     from workout_plans
                     where user_id = :user_id
                       and planned_date like :planned_date
                    """)

        result = db.session.execute(query, {"user_id": user_id, "planned_date": planned_date}).mappings().fetchall()
        if (len(result) > 0):
            plan_id = result[0]["plan_id"]
        else:
            query = text("""
                         insert into workout_plans (user_id, title, planned_date)
                         values (:user_id, :title, :planned_date)
                         """)
            result = db.session.execute(query,
                                        {"user_id": user_id, "title": planned_date, "planned_date": planned_date})
            session.commit()
            plan_id = result.lastrowid  # get the id of the new row

        db.session.execute(
            text("""
                 insert into plan_exercise (plan_id, exercise_id)
                 values (:plan_id, :exercise_id)
                 """),
            {"plan_id": plan_id, "exercise_id": exercise_id}
        )

        session.commit()
        return jsonify({"message": "Exercise Added"}), 200

    except Exception as e:
        print("DATABASE ERROR:", str(e))
        return jsonify({"message": "Error Adding Exercise"}), 403


# remove individual exercise from daily-workout plan
@workout_bp.route('/remove', methods=["POST"])
def remove_exercise_from_plan():
    payload = request.get_json(silent=True) or {}

    try:
        plan_id = payload.get('plan_id')
        exercise_id = payload.get('exercise_id')

        if not all([plan_id, exercise_id]):
            return jsonify({
                'status': 'error',
                'message': 'failed to recieve plan_id or exercise_id'
            }), 400

        db = current_app.extensions['sqlalchemy']
        session = db.session

        session.execute(
            text(
                'delete from plan_exercise where plan_id=:plan_id and exercise_id=:exercise_id'
            ),
            {'plan_id': plan_id, 'exercise_id': exercise_id}
        )

        session.commit()
        return jsonify({"message": "Exercise Removed"}), 200

    except Exception as e:
        print("DATABASE ERROR:", str(e))
        return jsonify({"message": "Error Removing Exercise"}), 400


# update the reps, sets, and weight of a planned exercise
@workout_bp.route('/update-planned-exercise', methods=["POST"])
def edit_exercise():
    payload = request.get_json(silent=True) or {}

    try:
        exercise_id = payload.get("exercise_id")
        plan_id = payload.get("plan_id")
        reps = payload.get("reps") or None
        sets = payload.get("sets") or None
        weight = payload.get("weight") or None

        if not all([exercise_id, plan_id]):
            return jsonify({
                'status': 'error',
                'message': 'failed to recieve data'
            }), 400

        db = current_app.extensions['sqlalchemy']
        session = db.session

        query = text("""
                     update plan_exercise
                     set sets=:sets,
                         reps=:reps,
                         weight=:weight
                     where exercise_id = :exercise_id
                       and plan_id = :plan_id;
                     """)
        db.session.execute(query, {"sets": sets, "reps": reps, "weight": weight, "exercise_id": exercise_id,
                                   "plan_id": plan_id})
        session.commit()

        return jsonify({"message": "Exercise Updated"}), 200

    except Exception as e:
        print("DATABASE ERROR:", str(e))
        return jsonify({"message": "Error Updating Exercise"}), 403


# toggle complete flag on exercise for home page
@workout_bp.route('/complete-exercise', methods=['POST'])
def complete_workout():
    payload = request.get_json(silent=True) or {}

    try:
        plan_exercise_id = payload.get("plan_exercise_id")
        complete = payload.get("complete")

        if plan_exercise_id is None or complete is None:
            return jsonify({
                'status': 'error',
                'message': 'failed to recieve plan_exercise_id or completed flag'
            }), 400

        db = current_app.extensions['sqlalchemy']
        session = db.session

        session.execute(
            text(
                'UPDATE plan_exercise set completed=:complete WHERE plan_exercise_id=:plan_exercise_id'
            ),
            {'complete': complete, 'plan_exercise_id': plan_exercise_id}
        )

        session.commit()
        return jsonify({"message": "Exercise Completion Toggled"}), 200

    except Exception as e:
        print("DATABASE ERROR:", str(e))
        return jsonify({"message": "Error Toggling Exercise Completion"}), 400