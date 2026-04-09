from flask import request, current_app, jsonify
from flask_socketio import emit, join_room, leave_room
from sqlalchemy import text


def register_chat_events(socketio, app):

    @app.route('/api/contacts/<int:user_id>', methods=['GET'])
    def get_contacts(user_id):
        db = current_app.extensions['sqlalchemy']
        try:
            # First, get the role of the current user
            role_sql = text("SELECT role FROM Users WHERE user_id = :uid")
            user_role = db.session.execute(role_sql, {"uid": user_id}).scalar()
            contacts = []

            # CASE A: User is a Client  -> Show their subscribed Coaches
            if user_role == 'U':
                query = text("""
                    SELECT u.user_id, up.first_name, up.last_name, u.role
                    FROM Users u
                    JOIN User_Profiles up ON u.user_id = up.user_id
                    JOIN coach_profiles cp ON u.user_id = cp.user_id
                    JOIN coach_subscriptions cs ON cp.coach_id = cs.coach_id
                    WHERE cs.user_id = :uid
                """)
                results = db.session.execute(query, {"uid": user_id}).mappings().all()

            # CASE B: User is a Coach  -> Show their active Clients
            elif user_role == 'C':
                query = text("""
                    SELECT u.user_id, up.first_name, up.last_name, u.role
                    FROM Users u
                    JOIN User_Profiles up ON u.user_id = up.user_id
                    JOIN coach_subscriptions cs ON u.user_id = cs.user_id
                    JOIN coach_profiles cp ON cs.coach_id = cp.coach_id
                    WHERE cp.user_id = :uid
                """)
                results = db.session.execute(query, {"uid": user_id}).mappings().all()

            # CASE C: User is an Admin -> Show EVERYONE
            else:
                query = text("""
                    SELECT u.user_id, up.first_name, up.last_name, u.role
                    FROM Users u
                    JOIN User_Profiles up ON u.user_id = up.user_id
                    WHERE u.user_id != :uid
                """)
                results = db.session.execute(query, {"uid": user_id}).mappings().all()

            # Format the results
            contacts = [
                {
                    "user_id": r['user_id'],
                    "full_name": f"{r['first_name']} {r['last_name']}",
                    "role": r['role'] # Added the role as requested
                }
                for r in results
            ]

            # Always add System Admin (User ID 2) at the top for non-admins
            if user_role != 'A':
                contacts.insert(0, {
                    "user_id": 2,
                    "full_name": "SYSTEM",
                    "role": "A"
                })

            return jsonify(contacts)
        except Exception as e:
            print(f"Error in get_contacts: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/chat/history/<int:user_id>/<int:contact_id>', methods=['GET'])
    def get_chat_history(user_id, contact_id):
        db = current_app.extensions['sqlalchemy']
        try:
            query = text("""
                SELECT sender_id, receiver_id, content as text, timestamp 
                FROM message 
                WHERE (sender_id = :u AND receiver_id = :c) 
                   OR (sender_id = :c AND receiver_id = :u)
                ORDER BY timestamp ASC
            """)

            # Add .mappings() here to get dictionaries automatically
            result = db.session.execute(query, {"u": user_id, "c": contact_id}).mappings().all()

            return jsonify([dict(row) for row in result])

        except Exception as e:
            print(f"Error in get_chat_history: {e}")
            return jsonify({"error": str(e)}), 500

    @socketio.on('connect')
    def handle_connect():
        user_id = request.args.get('user_id')
        if user_id:
            join_room(f"user_{user_id}")
            print(f"User {user_id} connected and joined private room.")
        else:
            return False

    @socketio.on('send_message')
    def handle_send_message(data):
        sender_id = data.get('sender_id')
        receiver_id = data.get('receiver_id')
        message_text = data.get('text')

        if not all([sender_id, receiver_id, message_text]):
            return

        db = current_app.extensions['sqlalchemy']
        try:
            # Save to Database
            query = text("""
                INSERT INTO message (sender_id, receiver_id, content)
                VALUES (:sender_id, :receiver_id, :content)
            """)
            db.session.execute(query, {
                "sender_id": sender_id,
                "receiver_id": receiver_id,
                "content": message_text
            })
            db.session.commit()

            # Emit to Receiver's Private Room
            emit('receive_message', {
                'sender_id': sender_id,
                'text': message_text,
                'timestamp': 'Just now'
            }, room=f"user_{receiver_id}")

        except Exception as e:
            db.session.rollback()
            print(f"Chat Error: {str(e)}")

    @socketio.on('admin_notification')
    def handle_admin_notification(data):
        admin_msg = data.get('message')
        emit('admin_announcement', {
            'message': admin_msg,
            'sender': 'SYSTEM'
        }, broadcast=True)

    @socketio.on('disconnect')
    def handle_disconnect():
        user_id = request.args.get('user_id')
        if user_id:
            leave_room(f"user_{user_id}")
            print(f"User {user_id} disconnected.")