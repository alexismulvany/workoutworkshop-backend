import datetime
import unittest
import json
from io import BytesIO

from app import app
from sqlalchemy import text, bindparam


class TestAuthRoutes(unittest.TestCase):

    #clears out user registration test data to ensure consistent test results and avoid conflicts with existing users
    def setUp(self):
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["TESTING"] = True
        app.config["JWT_SECRET_KEY"] = "test_secret_key"
        self.client = app.test_client()

        with app.app_context():
            db = app.extensions['sqlalchemy']
            test_usernames = ["new_unit_tester2", "coach_tester"]
            test_exercise_names = ["UnitTest Exercise"]

            def _exec_in(sql: str, key: str, values: list):
                if not values:
                    return
                stmt = text(sql).bindparams(bindparam(key, expanding=True))
                db.session.execute(stmt, {key: values})

            try:
                # Remove any exercises created by the mock admin test user first.
                exercise_ids = db.session.execute(
                    text("SELECT exercise_id FROM exercises WHERE name IN :names").bindparams(
                        bindparam("names", expanding=True)
                    ),
                    {"names": test_exercise_names}
                ).scalars().all()

                if exercise_ids:
                    _exec_in("DELETE FROM plan_exercise WHERE exercise_id IN :ids", "ids", exercise_ids)
                    _exec_in("DELETE FROM exercise_changes WHERE exercise_id IN :ids", "ids", exercise_ids)
                    _exec_in("DELETE FROM exercises WHERE exercise_id IN :ids", "ids", exercise_ids)

                user_ids = db.session.execute(
                    text("SELECT user_id FROM User_login WHERE username IN :names").bindparams(
                        bindparam("names", expanding=True)
                    ),
                    {"names": test_usernames}
                ).scalars().all()

                if not user_ids:
                    db.session.commit()
                    return

                coach_ids = db.session.execute(
                    text("SELECT coach_id FROM Coach_Profiles WHERE user_id IN :uids").bindparams(
                        bindparam("uids", expanding=True)
                    ),
                    {"uids": user_ids}
                ).scalars().all()

                if coach_ids:
                    _exec_in("DELETE FROM coach_application_decision WHERE coach_id IN :ids", "ids", coach_ids)
                    _exec_in("DELETE FROM coach_certifications WHERE coach_id IN :ids", "ids", coach_ids)
                    _exec_in("DELETE FROM coach_availability WHERE coach_id IN :ids", "ids", coach_ids)
                    _exec_in("DELETE FROM coach_subscriptions WHERE coach_id IN :ids", "ids", coach_ids)
                    _exec_in("DELETE FROM coach_requests WHERE coach_id IN :ids", "ids", coach_ids)
                    _exec_in("DELETE FROM coach_reports WHERE coach_id IN :ids", "ids", coach_ids)
                    _exec_in("DELETE FROM coach_reviews WHERE coach_id IN :ids", "ids", coach_ids)
                    _exec_in("DELETE FROM Coach_Profiles WHERE coach_id IN :ids", "ids", coach_ids)

                _exec_in("DELETE FROM message WHERE sender_id IN :ids OR receiver_id IN :ids", "ids", user_ids)
                _exec_in("DELETE FROM payment_details WHERE user_id IN :ids", "ids", user_ids)
                _exec_in("DELETE FROM weight_logs WHERE user_id IN :ids", "ids", user_ids)
                _exec_in("DELETE FROM goals WHERE user_id IN :ids", "ids", user_ids)
                _exec_in("DELETE FROM user_profiles WHERE user_id IN :ids", "ids", user_ids)
                _exec_in("DELETE FROM coach_subscriptions WHERE user_id IN :ids", "ids", user_ids)
                _exec_in("DELETE FROM coach_requests WHERE user_id IN :ids", "ids", user_ids)
                _exec_in("DELETE FROM coach_reports WHERE reporter_id IN :ids", "ids", user_ids)
                _exec_in("DELETE FROM coach_reviews WHERE user_id IN :ids", "ids", user_ids)
                _exec_in("DELETE FROM User_login WHERE user_id IN :ids", "ids", user_ids)
                _exec_in("DELETE FROM Users WHERE user_id IN :ids", "ids", user_ids)

                db.session.commit()
            except Exception:
                db.session.rollback()
                raise

    # --- Login Tests ---

    def test_login_success(self):
        """Test successful login with valid credentials."""
        payload = {
            "username": "Dylan",
            "password": "Password1"
        }
        response = self.client.post("/auth/login", json=payload)
        data = response.get_json()

        self.assertIn(response.status_code, [200])
        if response.status_code == 200:
            self.assertEqual(data["status"], "success")
            self.assertIn("token", data)

    def test_login_missing_fields(self):
        payload = {"username": "testuser"}
        response = self.client.post("/auth/login", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["message"], "Username and password are required.")

    def test_login_invalid_credentials(self):
        payload = {"username": "testuseghjksdfhjgldfghkljr", "password": "wrongpassdgffdgdword12"}
        response = self.client.post("/auth/login", json=payload)
        self.assertEqual(response.status_code, 401)

    # --- Username Availability ---

    def test_check_username_available(self):
        payload = {"username": "unique_user_999"}
        response = self.client.post("/auth/check-username", json=payload)
        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["available"])

    # --- Registration Tests ---

    def test_register_user_success(self):
        """Test standard user registration (Multipart Form)."""
        payload = {
            "username": "new_unit_tester2",
            "password": "password123",
            "first_name": "Unit",
            "last_name": "Tester",
            "birthday": "2000-01-01",
            "current_weight": "150",
            "goal_weight": "145",
            "goal_type": "Strength",
            "goal_text": "Stay fit"
        }
        response = self.client.post("/auth/register", data=payload)
        data = response.get_json()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(data["status"], "success")

    def test_register_coach_with_file(self):
        """Test coach registration including a dummy certification file."""
        payload = {
            "username": "coach_tester",
            "password": "password123",
            "first_name": "Coach",
            "last_name": "Test",
            "birthday": "1990-01-01",
            "is_coach": "true",
            "current_weight": "200",
            "goal_weight": "190",
            "pricing": "50.00",
            "bio": "Expert trainer",
            "availability": json.dumps([{"dow": "M", "start_time": "09:00", "end_time": "17:00"}]),
            "certifications": ["NASM-CPT"],
            "certificationFile_0": (BytesIO(b"dummy file content"), "cert.jpeg")
        }
        response = self.client.post("/auth/register", data=payload, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 201)

    def test_register_missing_fields(self):
        payload = {"username": "incomplete_user"}
        response = self.client.post("/auth/register", data=payload)
        self.assertEqual(response.status_code, 400)

    # --- Password Change Tests ---

    def test_change_password_no_token(self):
        payload = {"current_password": "old", "new_password": "new"}
        response = self.client.patch("/auth/change-password", json=payload)
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()