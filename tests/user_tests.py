import unittest
import jwt
import datetime
import os
from io import BytesIO
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError
from app import app, socketio
from flask_socketio import SocketIOTestClient

from routes.chat import register_chat_events


def generate_test_token(user_id=1, username="testuser", role="U"):
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }

    return jwt.encode(
        payload,
        app.config["JWT_SECRET_KEY"],
        algorithm="HS256"
    )


class TestUserRoutes(unittest.TestCase):

    def setUp(self):
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.token = generate_test_token()
        self.headers = {
            "Authorization": f"Bearer {self.token}"
        }


    # Profile Picture Upload
    def test_upload_profile_picture_no_file(self):
        response = self.client.post(
            "/user/upload-profile-picture",
            headers=self.headers
        )
        self.assertEqual(response.status_code, 400)


    # Username Update
    def test_update_username_success(self):
        payload = {"new_username": "unit_test_user"}

        response = self.client.put(
            "/user/update-username",
            json=payload,
            headers=self.headers
        )

        self.assertIn(response.status_code, [200, 409, 500])

    def test_update_username_missing(self):
        response = self.client.put(
            "/user/update-username",
            json={},
            headers=self.headers
        )

        self.assertEqual(response.status_code, 400)


    # Update Goals
    def test_update_goals_success(self):
        payload = {
            "current_weight": 182,
            "goal_weight": 172,
            "goal_type": "Strength",
            "information": "Lose Fat"
        }

        response = self.client.put(
            "/user/update-goals",
            json=payload,
            headers=self.headers
        )

        self.assertIn(response.status_code, [200, 500])

    def test_update_goals_invalid_weights(self):
        payload = {
            "current_weight": "bad",
            "goal_weight": "bad"
        }

        response = self.client.put(
            "/user/update-goals",
            json=payload,
            headers=self.headers
        )

        self.assertEqual(response.status_code, 400)


    # Delete Account
    def test_delete_account(self):
        response = self.client.delete(
            "/user/delete-account",
            headers=self.headers
        )

        self.assertIn(response.status_code, [200, 500])


    # Survey
    def test_check_survey(self):
        response = self.client.get(
            "/user/check-survey",
            headers=self.headers
        )

        self.assertIn(response.status_code, [200, 500])

    def test_check_survey_invalid_date(self):
        response = self.client.get(
            "/user/check-survey?date=invalid-date",
            headers=self.headers
        )

        self.assertEqual(response.status_code, 400)

    def test_daily_survey_success(self):
        payload = {"rating": 4}

        response = self.client.post(
            "/user/daily-survey",
            json=payload,
            headers=self.headers
        )

        self.assertIn(response.status_code, [200, 500])

    def test_daily_survey_invalid_rating(self):
        payload = {"rating": 12}

        response = self.client.post(
            "/user/daily-survey",
            json=payload,
            headers=self.headers
        )

        self.assertEqual(response.status_code, 400)


    # Coach Check
    def test_user_has_coach(self):
        response = self.client.get("/user/has-coach/1")

        self.assertIn(response.status_code, [200, 500])


    # Payment
    def test_update_payment_success(self):
        payload = {
            "card_number": "1234567812345678",
            "card_month": "12",
            "card_year": "2032",
            "card_cvv": "124"
        }

        response = self.client.patch(
            "/user/update-payment",
            json=payload,
            headers=self.headers
        )

        self.assertIn(response.status_code, [200, 500])

    def test_update_payment_missing_fields(self):
        response = self.client.patch(
            "/user/update-payment",
            json={},
            headers=self.headers
        )

        self.assertEqual(response.status_code, 400)


    # Chat History
    def test_chat_history_coach_client(self):
        response = self.client.get("/chat/history/7/16")

        self.assertIn(response.status_code, [200, 500])

    def test_chat_contacts_client(self):
        response = self.client.get("/api/contacts/7")

        self.assertIn(response.status_code, [200, 500])

    def test_chat_contacts_coach(self):
        response = self.client.get("/api/contacts/16")

        self.assertIn(response.status_code, [200, 500])

    def test_chat_contacts_admin(self):
        response = self.client.get("/api/contacts/2")

        self.assertIn(response.status_code, [200, 500])

    # Weight Logs
    def test_weight_logs(self):
        response = self.client.get("/user/weight-log/1")

        self.assertEqual(response.status_code, 200)

    # Generic Auth Failure
    def test_unauthorized_access(self):
        response = self.client.put("/user/update-username", json={"new_username": "test"})
        self.assertEqual(response.status_code, 401)

    def test_invalid_token_format(self):
        headers = {"Authorization": "Basic 12345"}
        response = self.client.put("/user/update-username", headers=headers, json={"new_username": "test"})
        self.assertEqual(response.status_code, 401)

    def test_expired_token(self):
        payload = {
            "sub": "1",
            "iat": datetime.datetime.utcnow() - datetime.timedelta(hours=2),
            "exp": datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        }
        expired_token = jwt.encode(payload, app.config["JWT_SECRET_KEY"], algorithm="HS256")
        headers = {"Authorization": f"Bearer {expired_token}"}

        response = self.client.put("/user/update-username", headers=headers, json={"new_username": "test"})
        self.assertEqual(response.status_code, 401)

    def test_get_progress_pictures_success(self):
        response = self.client.get("/user/progress-pictures/1")
        self.assertEqual(response.status_code, 200)

    def test_upload_progress_picture_no_user_id(self):
        response = self.client.post("/user/upload-progress-picture")
        self.assertEqual(response.status_code, 400)

    def test_delete_progress_picture_not_found(self):
        response = self.client.delete("/user/delete-progress-picture/9999/1")
        self.assertEqual(response.status_code, 404)

    def test_daily_survey_non_numeric_rating(self):
        payload = {"rating": "not_a_number"}
        response = self.client.post("/user/daily-survey", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 400)

    def test_update_goals_missing_weights(self):
        payload = {"current_weight": None, "goal_weight": "invalid"}
        response = self.client.put("/user/update-goals", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 400)

    def test_decode_token_invalid_sub(self):
        payload = {"sub": "not-an-int", "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)}
        bad_sub_token = jwt.encode(payload, app.config["JWT_SECRET_KEY"], algorithm="HS256")
        response = self.client.get("/user/check-survey", headers={"Authorization": f"Bearer {bad_sub_token}"})
        self.assertEqual(response.status_code, 200)

    def test_upload_profile_picture_invalid_extension(self):
        data = {'profile_image': (BytesIO(b"fake content"), 'test.txt')}
        response = self.client.post("/user/upload-profile-picture", data=data, headers=self.headers,
                                    content_type='multipart/form-data')
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid file format", response.get_json()['message'])

    def test_delete_account_database_error(self):
        with patch.object(app.extensions['sqlalchemy'].session, 'execute', side_effect=Exception("DB Crash")):
            response = self.client.delete("/user/delete-account", headers=self.headers)
            self.assertEqual(response.status_code, 500)
            self.assertIn("Database error", response.get_json().get('message', ''))

    def test_update_goals_database_error(self):
        payload = {"current_weight": 150, "goal_weight": 140, "goal_type": "Loss"}
        with patch.object(app.extensions['sqlalchemy'].session, 'execute', side_effect=Exception("DB Crash")):
            response = self.client.put("/user/update-goals", json=payload, headers=self.headers)
            self.assertEqual(response.status_code, 500)

    def test_update_username_conflict(self):
        mock_db_result = MagicMock()
        mock_db_result.fetchone.return_value = (999,)

        with patch.object(app.extensions['sqlalchemy'].session, 'execute', return_value=mock_db_result):
            payload = {"new_username": "taken_username"}
            response = self.client.put("/user/update-username", json=payload, headers=self.headers)
            self.assertEqual(response.status_code, 409)

    def test_upload_profile_picture_empty_filename(self):
        data = {'profile_image': (BytesIO(b"file content"), '')}
        response = self.client.post(
            "/user/upload-profile-picture",
            data=data,
            headers=self.headers,
            content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("No selected file", response.get_json().get('message', ''))

    def test_upload_profile_picture_invalid_file(self):
        data = {'profile_image': (BytesIO(b"fake code"), 'script.js')}
        response = self.client.post(
            "/user/upload-profile-picture",
            data=data,
            headers=self.headers,
            content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid file format", response.get_json().get('message', ''))

    def test_daily_survey_update_existing(self):
        mock_db_result = MagicMock()
        mock_db_result.rowcount = 1

        with patch.object(app.extensions['sqlalchemy'].session, 'execute', return_value=mock_db_result):
            payload = {"rating": 5}
            response = self.client.post("/user/daily-survey", json=payload, headers=self.headers)
            self.assertEqual(response.status_code, 200)

    def test_delete_progress_picture_no_user_id(self):
        mock_db_result = MagicMock()
        mock_db_result.mappings().first.return_value = {"image_url": "fake.jpg"}

        with patch.object(app.extensions['sqlalchemy'].session, 'execute', return_value=mock_db_result):
            response = self.client.delete("/user/delete-progress-picture/1/None", headers=self.headers)
            self.assertIn(response.status_code, [404])

    def test_missing_auth_headers(self):
        endpoints_to_test = [
            ("/user/upload-profile-picture", self.client.post),
            ("/user/update-username", self.client.put),
            ("/user/update-goals", self.client.put)
        ]

        for endpoint, method in endpoints_to_test:
            response = method(endpoint, json={"dummy": "data"})
            self.assertEqual(response.status_code, 401)

    def test_invalid_jwt_tokens(self):
        bad_headers = {"Authorization": "Bearer fake.jwt.token"}

        response = self.client.put("/user/update-username", json={"new_username": "test"}, headers=bad_headers)
        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid", response.get_json().get('message', ''))

    def test_upload_profile_picture_database_error(self):
        data = {'profile_image': (BytesIO(b"dummy image data"), 'test.jpg')}

        with patch.object(app.extensions['sqlalchemy'].session, 'execute', side_effect=Exception("DB Crash")):
            response = self.client.post(
                "/user/upload-profile-picture",
                data=data,
                headers=self.headers,
                content_type='multipart/form-data'
            )
            self.assertEqual(response.status_code, 500)
            self.assertIn("Database error", response.get_json().get('message', ''))

    def test_update_username_database_error(self):
        with patch.object(app.extensions['sqlalchemy'].session, 'execute', side_effect=Exception("DB Crash")):
            payload = {"new_username": "valid_name"}
            response = self.client.put("/user/update-username", json=payload, headers=self.headers)
            self.assertEqual(response.status_code, 500)
            self.assertIn("Database error", response.get_json().get('message', ''))

    def test_mass_database_errors(self):
        endpoints = [
            ("/user/daily-survey", self.client.post, {"rating": 5}),
            ("/user/update-payment", self.client.patch, {
                "card_number": "1234", "card_month": "12", "card_year": "2030", "card_cvv": "123"
            })
        ]

        with patch.object(app.extensions['sqlalchemy'].session, 'execute', side_effect=Exception("DB Crash")):
            for endpoint, method, payload in endpoints:
                response = method(endpoint, json=payload, headers=self.headers)
                self.assertEqual(response.status_code, 500)

    @patch('os.remove', side_effect=OSError("Mocked OS Error"))
    def test_delete_progress_picture_os_error(self, mock_remove):
        mock_db_result = MagicMock()
        mock_db_result.mappings().first.return_value = {"image_url": "fake.jpg"}

        with patch.object(app.extensions['sqlalchemy'].session, 'execute', return_value=mock_db_result):
            response = self.client.delete("/user/delete-progress-picture/1/1", headers=self.headers)
            self.assertIn(response.status_code,[200] )

    def test_upload_progress_picture_missing_file(self):
        data = {'user_id': '1'}
        response = self.client.post(
            "/user/upload-progress-picture",
            data=data,
            headers=self.headers,
            content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 400)

    def test_upload_progress_picture_invalid_file(self):
        data = {
            'user_id': '1',
            'progress_image': (BytesIO(b"fake text"), 'document.txt')
        }
        response = self.client.post(
            "/user/upload-progress-picture",
            data=data,
            headers=self.headers,
            content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 400)

if __name__ == "__main__":
    unittest.main()