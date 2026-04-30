from flask import Blueprint, jsonify, current_app, request
from sqlalchemy import text

workout_bp = Blueprint('workout', __name__, url_prefix='/api/workouts')


# fetch list of exercises
@workout_bp.route('/exercises', methods=['GET'])
def get_exercises():
    """
    Must get all of the available exercises
    ---
    tags:
      - Workout - Exercises
    responses:
      200:
        description: Get the list of exercises
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
                  exercise_id:
                    type: integer
                    example: 1
                  name:
                    type: string
                    example: Bench Press
                  muscle_group:
                    type: string
                    example: Chest
                  equipment_needed:
                    type: string
                    example: Barbell
                  video_url:
                    type: string
                  thumbnail:
                    type: string
      500:
        description: Error in the database
    """
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
    """
    Must get the user's daily workout plan
    ---
    tags:
      - Workout - Daily Plan
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
        example: 1
      - name: DOW
        in: path
        type: string
        required: true
        example: MON
    responses:
      200:
        description: Get the daily workout plan
        schema:
          type: object
          properties:
            status:
              type: string
            hasPlan:
              type: boolean
            data:
              type: array
              items:
                type: object
      500:
        description: Error in the database
    """
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
    """
    Must create a new workout plan
    ---
    tags:
      - Workout - Create Plan
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - user_id
            - date
            - exercises
          properties:
            user_id:
              type: integer
              example: 1
            date:
              type: string
              example: MON
            workout_name:
              type: string
              example: Push Day
            exercises:
              type: array
              items:
                type: object
                properties:
                  exercise_id:
                    type: integer
                    example: 1
                  sets:
                    type: integer
                    example: 3
                  reps:
                    type: integer
                    example: 15
                  weight:
                    type: integer
                    example: 124
    responses:
      201:
        description: The workout is now saved successfully
      400:
        description: Missing Fields
      500:
        description: Error in the database
    """
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
    """
    Must get the user's workout history
    ---
    tags:
      - Workout - History
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
        example: 1
    responses:
      200:
        description: Get the user's workout history
      500:
        description: Error in the database
    """
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
    """
        Fetch the list of exercises assigned to a specific workout plan
        ---
        tags:
          - Workout - Plans
        parameters:
          - name: plan_id
            in: path
            type: integer
            required: true
            description: The ID of the workout plan
        responses:
          200:
            description: A list of exercises in the plan
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
                      exercise_id:
                        type: integer
                        example: 10
                      exercise_name:
                        type: string
                        example: Bench Press
                      video_url:
                        type: string
                        example: "http://example.com/video"
                      thumbnail:
                        type: string
                      sets:
                        type: integer
                        example: 3
                      reps:
                        type: integer
                        example: 10
                      weight:
                        type: integer
                        example: 135
          500:
            description: Database error
        """
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
    """
        Update the sets, reps, and weight for exercises in a specific plan
        ---
        tags:
          - Workout - Plans
        parameters:
          - name: plan_id
            in: path
            type: integer
            required: true
            description: The ID of the workout plan to update
          - in: body
            name: body
            required: true
            schema:
              type: object
              properties:
                exercises:
                  type: array
                  items:
                    type: object
                    required:
                      - exercise_id
                    properties:
                      exercise_id:
                        type: integer
                        example: 5
                      sets:
                        type: integer
                        example: 3
                      reps:
                        type: integer
                        example: 12
                      weight:
                        type: integer
                        example: 50
        responses:
          200:
            description: Workout plan updated successfully
          400:
            description: No exercises provided in the request
          500:
            description: Database error
        """
    db = current_app.extensions['sqlalchemy']
    data = request.json
    exercises = data.get('exercises', [])

    if not exercises:
        return jsonify({'status': 'error', 'message': 'No exercises provided for update'}), 400
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
    """
        Remove a specific exercise from a workout plan
        ---
        tags:
          - Workout - Plans
        parameters:
          - name: plan_id
            in: path
            type: integer
            required: true
            description: The ID of the workout plan
          - name: exercise_id
            in: path
            type: integer
            required: true
            description: The ID of the exercise to remove from the plan
        responses:
          200:
            description: Exercise successfully removed from the plan
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: success
                message:
                  type: string
                  example: Exercise removed from workout!
          500:
            description: Database error
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: error
                message:
                  type: string
                  example: Failed to remove exercise
        """
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
    """
    Must delete a workout plan
    ---
    tags:
      - Workout - Delete Plan
    parameters:
      - name: plan_id
        in: path
        type: integer
        required: true
        example: 8
    responses:
      200:
        description: The workout plan is now deleted
      500:
        description: Error in the database
    """
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
    """
    Must add a single exercise to the workout plan (creates for not exists)
    ---
    tags:
      - Workout - Add Exercise
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - planned_date
            - user_id
            - exercise_id
          properties:
            planned_date:
              type: string
              example: MON
            user_id:
              type: integer
              example: 1
            exercise_id:
              type: integer
              example: 5
    responses:
      200:
        description: Get exercise added to the workout plan
      400:
        description: Missing Fields
      403:
        description: Error in adding exercise
    """
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
    """
    Must remove an exercise from the workout plan
    ---
    tags:
      - Workout - Remove Exercise
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - plan_id
            - exercise_id
          properties:
            plan_id:
              type: integer
              example: 10
            exercise_id:
              type: integer
              example: 3
    responses:
      200:
        description: The exercise is now removed from the workout plan
      400:
        description: Missing Data
    """
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
    """
    Must update (sets, reps, weight) for the exercise in a plan
    ---
    tags:
      - Workout - Update Exercise
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - exercise_id
            - plan_id
          properties:
            exercise_id:
              type: integer
              example: 2
            plan_id:
              type: integer
              example: 8
            reps:
              type: integer
              example: 12
            sets:
              type: integer
              example: 4
            weight:
              type: integer
              example: 152
    responses:
      200:
        description: The exercise is now updated
      400:
        description: Missing Data
      403:
        description: Update Failed
    """
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
    """
        Toggle the completion status of an exercise in a workout plan
        ---
        tags:
          - Workout - Execution
        parameters:
          - in: body
            name: body
            required: true
            schema:
              type: object
              required:
                - plan_exercise_id
                - complete
              properties:
                plan_exercise_id:
                  type: integer
                  description: The unique ID for the exercise entry in the plan
                  example: 15
                complete:
                  type: boolean
                  description: The new completion status (true for finished, false for unfinished)
                  example: true
        responses:
          200:
            description: Exercise completion status updated successfully
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: Exercise Completion Toggled
          400:
            description: Invalid request - missing fields or database error
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: error
                message:
                  type: string
                  example: failed to recieve plan_exercise_id or completed flag
        """
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


@workout_bp.route('/weekly-stats/<int:user_id>', methods=['GET'])
def get_weekly_workout_stats(user_id):
    """
    Get the number of workouts per week for a specific user
    ---
    tags:
      - Workout - Stats
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: The unique ID of the user
        example: 7
    responses:
      200:
        description: Successfully retrieved weekly workout stats
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
                  week:
                    type: string
                    example: "2026-W16"
                  workouts:
                    type: integer
                    example: 4
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
              example: Failed to fetch weekly stats
    """
    db = current_app.extensions['sqlalchemy']
    try:
        # Groups workouts by week and counts how many occurred
        query = text("""
                     SELECT DATE_FORMAT(STR_TO_DATE(planned_date, '%m-%d-%Y'), '%x-W%v') AS week,
                            COUNT(*)                                                     as workouts
                     FROM workout_plans
                     WHERE user_id = :user_id
                     GROUP BY week
                     ORDER BY week ASC LIMIT 12
                     """)
        result = db.session.execute(query, {"user_id": user_id}).mappings().fetchall()
        data = [dict(row) for row in result]

        return jsonify({'status': 'success', 'data': data}), 200

    except Exception as e:
        print("DATABASE ERROR:", str(e))
        return jsonify({'status': 'error', 'message': 'Failed to fetch weekly stats'}), 500
