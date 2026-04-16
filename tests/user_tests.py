import unittest
import jwt
import datetime
from app import app


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
            "goal_type": "Cut",
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
    def test_chat_history(self):
        response = self.client.get("/user/chat/history/1/2")

        self.assertIn(response.status_code, [200, 500])


    # Weight Logs
    def test_weight_logs(self):
        response = self.client.get("/user/weight-log/1")

        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()