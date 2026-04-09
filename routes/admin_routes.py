from math import ceil
from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import text

admin_bp = Blueprint('admin_bp', __name__)

MUSCLE_GROUPS = ['Chest', 'Legs', 'Bicep', 'Tricep', 'Shoulders', 'Back', 'Cardio', 'Abs']
EQUIPMENTS = ['Machine', 'Free Weight', 'Body Weight']

@admin_bp.route('/admin/test', methods=['GET'])
def admin_test():
    return jsonify({"message": "Routes to Admin are fine!"})

# Use Case 5.1 - Verify and Approve Coach Applications / Certifications

@admin_bp.route('/admin/coach-applications', methods=['GET'])
def coach_applications(): # Get the information on Coach Applications
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

    where_sql = "WHERE cc.status = 'pending' "
    params = {'limit': limit, 'offset': offset}

    if search:
        where_sql += (
            'AND ('
            'CONCAT(up.first_name, " ", up.last_name) LIKE :search '
            'OR CAST(cp.coach_id AS CHAR) LIKE :search '
            'OR CAST(cc.certification_id AS CHAR) LIKE :search'
            ') '
        )
        params['search'] = f'%{search}%'

    count_sql = text(
        'SELECT COUNT(*) AS total '
        'FROM coach_certifications cc '
        'JOIN coach_profiles cp ON cc.coach_id = cp.coach_id '
        'JOIN user_profiles up ON cp.user_id = up.user_id '
        f'{where_sql}'
    )

    data_sql = text(
        'SELECT '
        'cp.coach_id, CONCAT(up.first_name, " ", up.last_name) AS display_name, '
        'cc.certification_id, cc.status '
        'FROM coach_certifications cc '
        'JOIN coach_profiles cp ON cc.coach_id = cp.coach_id '
        'JOIN user_profiles up ON cp.user_id = up.user_id '
        f'{where_sql}'
        'ORDER BY cc.certification_id ASC '
        'LIMIT :limit OFFSET :offset'
    )

    try:
        total_applications = db.session.execute(count_sql, params).scalar() or 0
        result = db.session.execute(data_sql, params).fetchall()

        applications = []
        for row in result:
            applications.append({
                "coach_id": row.coach_id,
                "name": row.display_name,
                "certification_id": row.certification_id,
                "status": row.status
            })

        total_pages = max(ceil(total_applications / limit), 1)

        return jsonify({
            "applications": applications,
            "totalPages": total_pages,
            "currentPage": page,
            "totalApplications": total_applications
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/admin/coach-applications/<int:coach_id>', methods=['GET'])
def coach_application_details(coach_id): # Get the information for one Coach Application
    db = current_app.extensions['sqlalchemy']
    
    try:
        query_coach = """
                      SELECT CONCAT(up.first_name, ' ', up.last_name) AS display_name, cp.pricing, cp.bio
                      FROM coach_profiles cp
                      JOIN user_profiles up ON cp.user_id = up.user_id
                      WHERE cp.coach_id = :coach_id
                      """
        
        result = db.session.execute(db.text(query_coach), {"coach_id": coach_id}).fetchone()
        
        if not result:
            return jsonify({"error": "Coach Not Found"}), 404

        query_certs = """
                      SELECT certification_id, file_url, status
                      FROM coach_certifications
                      WHERE coach_id = :coach_id
                      ORDER BY certification_id ASC
                      """

        cert_rows = db.session.execute(db.text(query_certs), {"coach_id": coach_id}).fetchall()
        certifications = [
            {
                "certification_id": row.certification_id,
                "certification_url": row.file_url,
                "status": row.status
            }
            for row in cert_rows
        ]

        query_available = """
                          SELECT DOW, start_time, end_time
                          FROM coach_availability
                          WHERE coach_id = :coach_id
                          ORDER BY FIELD(DOW,'M','T','W','TH','F','SAT','SUN')
                          """
        
        availability_result = db.session.execute(db.text(query_available), {"coach_id": coach_id}).fetchall()
        availability = []
        
        for row in availability_result:
            availability.append({
                "day": row.DOW,
                "start_time": str(row.start_time),
                "end_time": str(row.end_time)
            })

        first_cert = certifications[0] if certifications else None

        return jsonify({
            "name": result.display_name,
            "payment": result.pricing,
            "bio": result.bio,
            # New plural fields for multiple certifications
            "certification_urls": [c["certification_url"] for c in certifications if c.get("certification_url")],
            "certification_ids": [c["certification_id"] for c in certifications],
            "certifications": certifications,
            "availability": availability
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/admin/coach-applications/<int:certification_id>/approve', methods=['PUT'])
def approve_certification(certification_id): # Update the Certification as Approved
    db = current_app.extensions['sqlalchemy']
    data = request.get_json()
    admin_id = data.get("admin_id")
    
    try:
        query_certification = """
                              UPDATE coach_certifications
                              SET status = 'accepted'
                              WHERE certification_id = :certification_id
                              """
        
        db.session.execute(db.text(query_certification), {"certification_id": certification_id})
        
        query_decision = """
                         INSERT INTO coach_application_decision (coach_id, certification_id, admin_id, decision)
                         SELECT coach_id, certification_id, :admin_id, 'accepted'
                         FROM coach_certifications
                         WHERE certification_id = :certification_id
                         """
        
        db.session.execute(db.text(query_decision), {"certification_id": certification_id, "admin_id": admin_id})
        db.session.commit()
        
        return jsonify({"message": "Coach Certification Approved"})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/admin/coach-applications/<int:certification_id>/reject', methods=['PUT'])
def reject_certification(certification_id): # Update the Certification as Rejected
    db = current_app.extensions['sqlalchemy']
    data = request.get_json()
    admin_id = data.get("admin_id")
    
    try:
        query_certification = """
                              UPDATE coach_certifications
                              SET status = 'rejected'
                              WHERE certification_id = :certification_id
                              """
        
        db.session.execute(db.text(query_certification), {"certification_id": certification_id})
        
        query_decision = """
                         INSERT INTO coach_application_decision (coach_id, certification_id, admin_id, decision)
                         SELECT coach_id, certification_id, :admin_id, 'rejected'
                         FROM coach_certifications
                         WHERE certification_id = :certification_id
                         """
        
        db.session.execute(db.text(query_decision), {"certification_id": certification_id, "admin_id": admin_id})
        db.session.commit()
        
        return jsonify({"message": "Coach Certification Rejected"})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Use Case 5.2 - Review Coach Reports

@admin_bp.route('/admin/coach-reports', methods=['GET'])
def coach_reports(): # Get the information on Coach Reports
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

    where_sql = "WHERE cr.status = 'pending' "
    params = {'limit': limit, 'offset': offset}

    if search:
        where_sql += (
            'AND ('
            'CONCAT(up.first_name, " ", up.last_name) LIKE :search '
            'OR cr.reason LIKE :search '
            'OR CAST(cr.report_id AS CHAR) LIKE :search '
            'OR CAST(cp.coach_id AS CHAR) LIKE :search'
            ') '
        )
        params['search'] = f'%{search}%'

    count_sql = text(
        'SELECT COUNT(*) AS total '
        'FROM coach_reports cr '
        'JOIN coach_profiles cp ON cr.coach_id = cp.coach_id '
        'JOIN user_profiles up ON cp.user_id = up.user_id '
        f'{where_sql}'
    )

    data_sql = text(
        'SELECT '
        'cr.report_id, cp.coach_id, CONCAT(up.first_name, " ", up.last_name) AS display_name, '
        'cr.reason, cr.status '
        'FROM coach_reports cr '
        'JOIN coach_profiles cp ON cr.coach_id = cp.coach_id '
        'JOIN user_profiles up ON cp.user_id = up.user_id '
        f'{where_sql}'
        'ORDER BY cr.report_id ASC '
        'LIMIT :limit OFFSET :offset'
    )

    try:
        total_reports = db.session.execute(count_sql, params).scalar() or 0
        result = db.session.execute(data_sql, params).fetchall()

        reports = []
        for row in result:
            reports.append({
                "report_id": row.report_id,
                "coach_id": row.coach_id,
                "name": row.display_name,
                "reason": row.reason,
                "status": row.status
            })

        total_pages = max(ceil(total_reports / limit), 1)

        return jsonify({
            "reports": reports,
            "totalPages": total_pages,
            "currentPage": page,
            "totalReports": total_reports
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/admin/coach-reports/<int:report_id>', methods=['GET'])
def coach_report_details(report_id): # Get the information for one Coach Report
    db = current_app.extensions['sqlalchemy']
    
    try:
        query = """
                SELECT cr.report_id, cr.reason, cr.status, cp.coach_id, cp.pricing, cp.is_active, cp.is_nutritionist, cp.bio,
                       up.user_id, CONCAT(up.first_name, ' ', up.last_name) AS display_name, up.profile_picture_url, AVG(crv.rating) as rating
                FROM coach_reports cr
                JOIN coach_profiles cp ON cr.coach_id = cp.coach_id
                JOIN user_profiles up ON cp.user_id = up.user_id
                JOIN coach_reviews crv ON cp.coach_id = crv.coach_id
                WHERE cr.report_id = :report_id
                """
        
        result = db.session.execute(db.text(query), {"report_id": report_id}).fetchone()
        
        if not result:
            return jsonify({"error": "Coach Report Not Found"}), 404
        
        return jsonify({
            "report_id": result.report_id,
            "status": result.status,
            "reason": result.reason,
            "coach": {
                "coach_id": result.coach_id,
                "user_id": result.user_id,
                "name": result.display_name,
                "profile_picture": result.profile_picture_url,
                "bio": result.bio,
                "pricing": float(result.pricing),
                "rating": float(result.rating) if result.rating is not None else None,
                "is_active": bool(result.is_active),
                "is_nutritionist": bool(result.is_nutritionist)
            }
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/admin/coach-reports/<int:report_id>/dismiss', methods=['PUT'])
def dismiss_report(report_id): # Update for Dismissed Report
    db = current_app.extensions['sqlalchemy']
    
    try:
        query_report = """
                       UPDATE coach_reports
                       SET status = 'dismissed'
                       WHERE report_id = :report_id
                       """
        
        db.session.execute(db.text(query_report), {"report_id": report_id})
        db.session.commit()
        
        return jsonify({"message": "Report Dismissed Successfully"})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Use Case 5.3 - Ban a Coach

@admin_bp.route('/admin/coach-reports/<int:report_id>/ban', methods=['PUT'])
def coach_ban(report_id): # Update for Coach Banned
    db = current_app.extensions['sqlalchemy']
    data = request.get_json()
    admin_id = data.get("user_id")
    reason = data.get("reason")
    
    if not all([admin_id, reason]):
        return jsonify({"error": "admin_id and reason are required"}), 400
    
    try:
        query_coach = """
                      SELECT cp.user_id
                      FROM coach_reports cr
                      JOIN coach_profiles cp ON cr.coach_id = cp.coach_id
                      WHERE cr.report_id = :report_id
                      """
        
        result = db.session.execute(db.text(query_coach), {"report_id": report_id}).fetchone()
        
        if not result:
            return jsonify({"error": "Coach Id Not Found"}), 404
        
        user_id = result.user_id
        
        query_ban = """
                    UPDATE users
                    SET is_banned = TRUE
                    WHERE user_id = :user_id
                    """
        
        db.session.execute(db.text(query_ban), {"user_id": user_id})
        
        query_insert = """
                       INSERT INTO user_ban (admin_id, user_id, reason)
                       VALUES (:admin_id, :user_id, :reason)
                       """
        
        db.session.execute(db.text(query_insert), {"admin_id": admin_id, "user_id": user_id, "reason": reason})
        
        query_report = """
                       UPDATE coach_reports
                       SET status = 'reviewed'
                       WHERE report_id = :report_id
                       """
        
        db.session.execute(db.text(query_report), {"report_id": report_id})
        db.session.commit()
        
        return jsonify({"message": "Coach Banned Successfully"})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Use Case 5.4 - Disable a Coach

@admin_bp.route('/admin/coach-reports/<int:report_id>/disable', methods=['PUT'])
def coach_disable(report_id): # Update for Coach Disabled
    db = current_app.extensions['sqlalchemy']
    data = request.get_json()
    admin_id = data.get("user_id")
    reason = data.get("reason")
    day = data.get("day")
    month = data.get("month")
    year = data.get("year")
    
    if not all([admin_id, reason, day, month, year]):
        return jsonify({"error": "admin_id, reason, day, month, and year are required"}), 400
    
    try:
        query_coach = """
                      SELECT cp.user_id
                      FROM coach_reports cr
                      JOIN coach_profiles cp ON cr.coach_id = cp.coach_id
                      WHERE cr.report_id = :report_id
                      """
        
        result = db.session.execute(db.text(query_coach), {"report_id": report_id}).fetchone()
        
        if not result:
            return jsonify({"error": "Coach Id Not Found"}), 404
        
        user_id = result.user_id
        
        query_disable = """
                        UPDATE users
                        SET is_disabled = TRUE
                        WHERE user_id = :user_id
                        """
        
        db.session.execute(db.text(query_disable), {"user_id": user_id})
        
        query_insert = """
                       INSERT INTO disable_account (admin_id, user_id, reason, day, month, year)
                       VALUES (:admin_id, :user_id, :reason, :day, :month, :year)
                       """
        
        db.session.execute(db.text(query_insert), {"admin_id": admin_id, "user_id": user_id, "reason": reason, "day": day, "month": month, "year": year})
        
        query_report = """
                       UPDATE coach_reports
                       SET status = 'reviewed'
                       WHERE report_id = :report_id
                       """
        
        db.session.execute(db.text(query_report), {"report_id": report_id})
        db.session.commit()
        
        return jsonify({"message": "Coach Disabled Successfully"})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Use Case 5.5 (adding a new exercise) + Use Case 5.6 (removing an exercise)

@admin_bp.route('/admin/exercises', methods=['GET'])
def exercises(): # Search by Name or Shows the Default List
    db = current_app.extensions['sqlalchemy']
    search = request.args.get('search')
    
    if search and search.strip() != "":
        
        query_search = """
                       SELECT exercise_id, name, muscle_group, equipment_needed, video_url
                       FROM exercises
                       WHERE is_removed = FALSE
                       AND LOWER(name) LIKE :search
                       ORDER BY name ASC
                       """
        
        result = db.session.execute(db.text(query_search), {"search": f"%{search.lower()}%"}).fetchall()
        exercises = []
        
        for row in result:
            exercises.append({
                "exercise_id": row.exercise_id,
                "name": row.name,
                "muscle_group": row.muscle_group,
                "equipment": row.equipment_needed,
                "video_url": row.video_url
            })
        
        return jsonify({
            "status": "success",
            "mode": "search",
            "data": exercises
        })
    
    query_default = """
                    SELECT exercise_id, name, muscle_group, equipment_needed, video_url
                    FROM exercises
                    WHERE is_removed = FALSE
                    """
    
    result = db.session.execute(db.text(query_default)).fetchall()
    
    grouped = {
        "Chest": [],
        "Legs": [],
        "Arms": [],
        "Back": [],
        "Cardio": [],
        "Core": []
    }
    
    for row in result:
        exercise = {
            "exercise_id": row.exercise_id,
            "name": row.name,
            "muscle_group": row.muscle_group,
            "equipment": row.equipment_needed,
            "video_url": row.video_url
        }
        
        if row.muscle_group in ["Bicep", "Tricep", "Shoulders","Forearms",]:
            grouped["Arms"].append(exercise)
        elif row.muscle_group == "Abs":
            grouped["Core"].append(exercise)
        elif row.muscle_group in ["Back","Lats","Traps","Lower Back"]:
            grouped["Back"].append(exercise)
        elif row.muscle_group in ["Legs","Glutes","Hamstrings","Quads","Calves"]:
            grouped["Legs"].append(exercise)
        elif row.muscle_group in grouped:
            grouped[row.muscle_group].append(exercise)
    
    return jsonify({
        "status": "success",
        "mode": "default",
        "data": grouped
    })

@admin_bp.route('/admin/exercises/add', methods=['POST'])
def exercise_add(): # Updated for Exercise Added
    db = current_app.extensions['sqlalchemy']
    data = request.get_json()
    admin_id = data.get("user_id")
    name = data.get("name")
    muscle_group = data.get("muscle_group")
    equipment = data.get("equipment_needed")
    video_url = data.get("video_url")
    
    if not all([admin_id, name, muscle_group, equipment]):
        return jsonify({"error": "admin_id, name, muscle_group, and equipment are required"}), 400
    
    if muscle_group not in MUSCLE_GROUPS:
        return jsonify({"error": "Invalid Muscle Groups"}), 400
    
    if equipment not in EQUIPMENTS:
        return jsonify({"error": "Invalid Equipments"}), 400
    
    try:
        query_exercise = """
                         INSERT INTO exercises (name, muscle_group, equipment_needed, video_url)
                         VALUES (:name, :muscle_group, :equipment, :video_url)
                         """
        
        result = db.session.execute(db.text(query_exercise), {"name": name, "muscle_group": muscle_group, "equipment": equipment, "video_url": video_url})
        exercise_id = result.lastrowid
        
        query_change = """
                       INSERT INTO exercise_changes (admin_id, exercise_id, event)
                       VALUES (:admin_id, :exercise_id, 'add')
                       """
        
        db.session.execute(db.text(query_change), {"admin_id": admin_id, "exercise_id": exercise_id})
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Exercise Added Successfully",
            "exercise_id": exercise_id
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/admin/exercises/remove/<int:exercise_id>', methods=['DELETE'])
def exercise_remove(exercise_id): # Updated for Exercise Removed
    db = current_app.extensions['sqlalchemy']
    data = request.get_json()
    admin_id = data.get("user_id")
    
    try:
        query_exercise = """
                         UPDATE exercises
                         SET is_removed = TRUE
                         WHERE exercise_id = :exercise_id
                         """
        
        db.session.execute(db.text(query_exercise), {"exercise_id": exercise_id})
        
        query_change = """
                       INSERT INTO exercise_changes (admin_id, exercise_id, event)
                       VALUES (:admin_id, :exercise_id, 'delete')
                       """
        
        db.session.execute(db.text(query_change), {"admin_id": admin_id, "exercise_id": exercise_id})
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Exercise Removed Successfully"
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/admin/exercises/update/<int:exercise_id>', methods=['PUT'])
def exercise_edit(exercise_id): # Updated for Exercise Edited
    db = current_app.extensions['sqlalchemy']
    data = request.get_json()
    admin_id = data.get("user_id")
    name = data.get("name")
    muscle_group = data.get("muscle_group")
    equipment = data.get("equipment_needed")
    video_url = data.get("video_url")
    
    if not all([admin_id, name, muscle_group, equipment]):
        return jsonify({"error": "admin_id, name, muscle_group, and equipment are required"}), 400
    
    if muscle_group not in MUSCLE_GROUPS:
        return jsonify({"error": "Invalid Muscle Groups"}), 400
    
    if equipment not in EQUIPMENTS:
        return jsonify({"error": "Invalid Equipments"}), 400
    
    try:
        query_exercise = """
                         UPDATE exercises
                         SET name = :name, muscle_group = :muscle_group, equipment_needed = :equipment_needed, video_url = :video_url
                         WHERE exercise_id = :exercise_id
                         """
        
        db.session.execute(db.text(query_exercise), {"exercise_id": exercise_id, "name": name, "muscle_group": muscle_group, "equipment_needed": equipment, "video_url": video_url})
        
        query_change = """
                       INSERT INTO exercise_changes (admin_id, exercise_id, event)
                       VALUES (:admin_id, :exercise_id, 'edit')
                       """
        
        db.session.execute(db.text(query_change), {"admin_id": admin_id, "exercise_id": exercise_id})
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Exercise Edited Successfully"
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Use Case Extra Requirements

@admin_bp.route('/admin/fetch-users', methods=['GET'])
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
