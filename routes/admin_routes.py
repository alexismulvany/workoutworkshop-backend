from flask import Blueprint, jsonify, request
from extensions import db

admin_bp = Blueprint('admin_bp', __name__)

MUSCLE_GROUPS = ['Chest', 'Legs', 'Bicep', 'Tricep', 'Shoulders', 'Back', 'Cardio', 'Abs']
EQUIPMENTS = ['Machine', 'Free Weight', 'Body Weight']

@admin_bp.route('/admin/test', methods=['GET'])
def admin_test():
    return jsonify({"message": "Routes to Admin are fine!"})

# Use Case 5.1 - Verify and Approve Coach Applications / Certifications

@admin_bp.route('/admin/coach-applications', methods=['GET'])
def coach_applications(): # Get the information on Coach Applications
    
    try:
        query = """
                SELECT cp.coach_id, CONCAT(up.first_name, ' ', up.last_name) AS display_name, cc.certification_id, cc.status
                FROM coach_certifications cc
                JOIN coach_profiles cp ON cc.coach_id = cp.coach_id
                JOIN user_profiles up ON cp.user_id = up.user_id
                WHERE cc.status = 'pending'
                """
        
        result = db.session.execute(db.text(query)).fetchall()
        applications = []
        
        for row in result:
            applications.append({
                "coach_id": row.coach_id,
                "name": row.display_name,
                "certification_id": row.certification_id,
                "status": row.status
            })
        
        return jsonify(applications)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/admin/coach-applications/<int:coach_id>', methods=['GET'])
def coach_application_details(coach_id): # Get the information for one Coach Application
    
    try:
        query = """
                SELECT CONCAT(up.first_name, ' ', up.last_name) AS display_name, cp.pricing, cp.bio, cc.file_url, cc.certification_id
                FROM coach_profiles cp
                JOIN user_profiles up ON cp.user_id = up.user_id
                JOIN coach_certifications cc ON cp.coach_id = cc.coach_id
                WHERE cp.coach_id = :coach_id
                """
        
        result = db.session.execute(db.text(query), {"coach_id": coach_id}).fetchone()
        
        if not result:
            return jsonify({"error": "Coach Not Found"}), 404
        
        return jsonify({
            "name": result.display_name,
            "payment": result.pricing,
            "bio": result.bio,
            "certification_url": result.file_url,
            "certification_id": result.certification_id
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/admin/coach-applications/<int:certification_id>/approve', methods=['PUT'])
def approve_certification(certification_id): # Update the Certification as Approved
    
    data = request.get_json()
    admin_id = data.get("user_id")
    
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
    
    try:
        query = """
                SELECT cr.report_id, cp.coach_id, CONCAT(up.first_name, ' ', up.last_name) AS display_name, cr.reason, cr.status
                FROM coach_reports cr
                JOIN coach_profiles cp ON cr.coach_id = cp.coach_id
                JOIN user_profiles up ON cp.user_id = up.user_id
                WHERE cr.status = 'pending'
                """
        
        result = db.session.execute(db.text(query)).fetchall()
        reports = []
        
        for row in result:
            reports.append({
                "report_id": row.report_id,
                "coach_id": row.coach_id,
                "name": row.display_name,
                "reason": row.reason,
                "status": row.status
            })
        
        return jsonify(reports)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/admin/coach-reports/<int:report_id>', methods=['GET'])
def coach_report_details(report_id): # Get the information for one Coach Report
    
    try:
        query = """
                SELECT cr.report_id, cr.reason, cr.status, cp.coach_id, cp.pricing, cp.is_active, cp.is_nutritionist, cp.bio,
                       up.user_id, CONCAT(up.first_name, ' ', up.last_name) AS display_name, up.profile_picture_url
                FROM coach_reports cr
                JOIN coach_profiles cp ON cr.coach_id = cp.coach_id
                JOIN user_profiles up ON cp.user_id = up.user_id
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
                "is_active": bool(result.is_active),
                "is_nutritionist": bool(result.is_nutritionist)
            }
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/admin/coach-reports/<int:report_id>/dismiss', methods=['PUT'])
def dismiss_report(report_id): # Update for Dismissed Report
    
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
    
    data = request.get_json()
    admin_id = data.get("admin_id")
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
    
    data = request.get_json()
    admin_id = data.get("admin_id")
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
        
        if row.muscle_group in ["Bicep", "Tricep", "Shoulders"]:
            grouped["Arms"].append(exercise)
        elif row.muscle_group == "Abs":
            grouped["Core"].append(exercise)
        elif row.muscle_group in grouped:
            grouped[row.muscle_group].append(exercise)
    
    return jsonify({
        "status": "success",
        "mode": "default",
        "data": grouped
    })

@admin_bp.route('/admin/exercises', methods=['POST'])
def exercise_add(): # Updated for Exercise Added
    
    data = request.get_json()
    admin_id = data.get("admin_id")
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

@admin_bp.route('/admin/exercises/<int:exercise_id>', methods=['DELETE'])
def exercise_remove(exercise_id): # Updated for Exercise Removed
    
    data = request.get_json()
    admin_id = data.get("admin_id")
    
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
