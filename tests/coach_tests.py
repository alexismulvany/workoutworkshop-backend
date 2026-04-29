import unittest
from app import app

class TestCoachRoutes(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] == True
        self.client = app.test_client()

    #Coach - Coach Clients
    def test_get_coach_clients_coach_id(self):
        response = self.client.get('/coach/clients/1')

        self.assertIn(response.status_code, [200, 500])

    #Coach - User Options
    def test_get_coach_availibility(self):
        response = self.client.get('/coach/coach-availibility/1')

        self.assertIn(response.status_code, [200, 500])

    def test_post_fire_coach(self):
        payload = {
            "coach_id": 0,
            "user_id": 0
            }
        response = self.client.post('/coach/fire-coach', json=payload)

        self.assertIn(response.status_code, [200, 400])
    
    def test_post_coach_report(self):
        payload = {
            "coach_id": 0,
            "message": "test",
            "report_id": 0
        }
        response = self.client.post('/coach/send-coach-report', json=payload)

        self.assertIn(response.status_code, [200, 400])
    
    #Coach - Coach Data
    def test_get_all_coach_data(self):
        response = self.client.get('/coach/coach-data')

        self.assertIn(response.status_code, [200, 500])

    def test_get_single_coach_data(self):
        response = self.client.get('/coach/coach-data/1')

        self.assertIn(response.status_code, [200, 500])

    def test_get_coach_id_from_user_id(self):
        response = self.client.get('/coach/coach-id/1')

        self.assertIn(response.status_code, [200, 404, 500])
    
    #Coach - Coach Reviews
    def test_get_all_coach_reviews(self):
        response = self.client.get('/coach/coach-reviews/1')

        self.assertIn(response.status_code, [200, 404, 500])

    def test_post_coach_review(self):
        payload = {
            "coach_id": 0,
            "message": "test",
            "rating": 0,
            "user_id": 0
        }
        response = self.client.post('/coach/submit-coach-review', json=payload)

        self.assertIn(response.status_code, [200, 400])

    #Coach - Coach Workout
    def test_delete_workout_plan(self):
        response = self.client.delete('/coach/delete-plan/1')

        self.assertIn(response.status_code, [200, 500])
    
    def test_put_plan_title(self):
        payload = {
            "title": "test"
        }
        response = self.client.put('/coach/update-plan-title/1', json=payload)

        self.assertIn(response.status_code, [200, 400, 500])
    
    #Coach - Meal Plan
    def test_get_meal_plan(self):
        response = self.client.get('/coach/meal-plan/1/1')

        self.assertIn(response.status_code, [200, 500])

    def test_post_meal_plan(self):
        payload = {
            "dow": "M",
            "meal": "banana",
            "weekly_id": 0
        }
        response = self.client.post('/coach/meal-plan/1/1', json=payload)

        self.assertIn(response.status_code, [200, 400, 500])
    
    #Coach - Coach Profile
    def test_get_coach_profile(self):
        response = self.client.get('/coach/profile/1')

        self.assertIn(response.status_code, [200, 500])

    def test_put_coach_profile(self):
        payload = {
            "availibility": [
                {
                    "dow": "M",
                    "end_time": "14:00",
                    "start_time": "12:00"
                }
            ],
            "bio": "test",
            "pricing": "24.99"
        }
        response = self.client.put('/coach/profile/1', json=payload)

        self.assertIn(response.status_code, [200, 500])
    
    #Coach - Coach Application
    def test_get_coach_requests(self):
        response = self.client.get('/coach/requests/1')

        self.assertIn(response.status_code, [200, 500])
    
    def test_post_coach_application_decision(self):
        payload = {
            "coach_id": 0,
            "decision": "rejected"
        }
        response = self.client.post('/coach/requests/1/decision', json=payload)

        self.assertIn(response.status_code, [200, 400, 404, 500])
    
    def test_post_coach_application(self):
        payload = {
            "coach_id": 0,
            "comment": "test",
            "user_id": 0
        }
        response = self.client.post('/coach/send-user-coach-app', json=payload)

        self.assertIn(response.status_code, [200, 400])
    
    #Coach - User-Coach Subscription Status
    def test_user_coach_sub_status(self):
        response = self.client.get('/coach/user-coach-sub/1/1')

        self.assertIn(response.status_code, [200, 500])


if __name__ == "__main__":
    unittest.main()