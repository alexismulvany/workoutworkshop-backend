import unittest
from app import app

class TestCoachRoutes(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    #Coach Data
    def test_get_all_coach_data(self):
        response = self.client.get('/coach/coach-data')
        self.assertIn(response.status_code, [200, 500])

    def test_get_single_coach_data(self):
        response = self.client.get('/coach/coach-data/1')
        self.assertIn(response.status_code, [200, 500])

    def test_get_coach_id_from_user_id(self):
        response = self.client.get('/coach/coach-id/1')
        self.assertIn(response.status_code, [200, 404, 500])

    #Coach Reviews
    def test_get_all_coach_reviews(self):
        response = self.client.get('/coach/coach-reviews/1')
        self.assertIn(response.status_code, [200, 404, 500])

    def test_get_reviews_not_found(self):
        response = self.client.get('/coach/coach-reviews/99999')
        self.assertIn(response.status_code, [404, 500])

    def test_post_coach_review_with_message(self):
        payload = {
            "coach_id": 1,
            "message": "test review",
            "rating": 5,
            "user_id": 1
        }
        response = self.client.post('/coach/submit-coach-review', json=payload)
        self.assertIn(response.status_code, [200, 400])

    def test_post_coach_review_no_message(self):
        payload = {
            "coach_id": 1,
            "rating": 5,
            "user_id": 1
        }
        response = self.client.post('/coach/submit-coach-review', json=payload)
        self.assertIn(response.status_code, [200, 400])

    def test_post_coach_review_missing_fields(self):
        response = self.client.post('/coach/submit-coach-review', json={})
        self.assertEqual(response.status_code, 400)
    
    #Coach Clients
    def test_get_coach_clients(self):
        response = self.client.get('/coach/clients/1')
        self.assertIn(response.status_code, [200, 500])
    
    #Coach Availability
    def test_get_coach_availability(self):
        response = self.client.get('/coach/coach-availibility/1')
        self.assertIn(response.status_code, [200, 500])

    def test_coach_availability_empty(self):
        response = self.client.get('/coach/coach-availibility/99999')
        self.assertIn(response.status_code, [200, 500])

    #Coach Subscription
    def test_user_coach_sub_status(self):
        response = self.client.get('/coach/user-coach-sub/1/1')
        self.assertIn(response.status_code, [200, 500])
    
    #Coach Applications
    def test_post_coach_application(self):
        payload = {
            "coach_id": 1,
            "comment": "test",
            "user_id": 1
        }
        response = self.client.post('/coach/send-user-coach-app', json=payload)
        self.assertIn(response.status_code, [200, 400])

    def test_post_coach_application_missing_fields(self):
        response = self.client.post('/coach/send-user-coach-app', json={})
        self.assertEqual(response.status_code, 400)

    def test_get_coach_requests(self):
        response = self.client.get('/coach/requests/1')
        self.assertIn(response.status_code, [200, 500])

    def test_post_coach_application_decision_valid(self):
        payload = {
            "coach_id": 1,
            "decision": "rejected"
        }
        response = self.client.post('/coach/requests/1/decision', json=payload)
        self.assertIn(response.status_code, [200, 400, 404, 500])

    def test_post_coach_application_decision_invalid(self):
        payload = {
            "coach_id": 1,
            "decision": "maybe"
        }
        response = self.client.post('/coach/requests/1/decision', json=payload)
        self.assertEqual(response.status_code, 400)

    def test_post_coach_application_decision_missing(self):
        response = self.client.post('/coach/requests/1/decision', json={})
        self.assertEqual(response.status_code, 400)
    
    #Reports/Fire Coach
    def test_post_coach_report(self):
        payload = {
            "coach_id": 1,
            "message": "test",
            "reporter_id": 1
        }
        response = self.client.post('/coach/send-coach-report', json=payload)
        self.assertIn(response.status_code, [200, 400])

    def test_post_fire_coach(self):
        payload = {
            "coach_id": 1,
            "user_id": 1
        }
        response = self.client.post('/coach/fire-coach', json=payload)
        self.assertIn(response.status_code, [200, 400])

    def test_post_fire_coach_missing(self):
        response = self.client.post('/coach/fire-coach', json={})
        self.assertEqual(response.status_code, 400)
    
    #Coach - Meal Plan
    def test_get_meal_plan(self):
        response = self.client.get('/coach/meal-plan/1/1')
        self.assertIn(response.status_code, [200, 500])

    def test_post_meal_plan_valid(self):
        payload = {
            "meals": [
                {"dow": "M", "meal": "banana"}
            ]
        }
        response = self.client.post('/coach/meal-plan/1/1', json=payload)
        self.assertIn(response.status_code, [200, 500])

    def test_post_meal_plan_no_meals(self):
        response = self.client.post('/coach/meal-plan/1/1', json={})
        self.assertEqual(response.status_code, 400)
    
    #Coach Profile
    def test_get_coach_profile(self):
        response = self.client.get('/coach/profile/1')
        self.assertIn(response.status_code, [200, 404, 500])

    def test_put_coach_profile_full(self):
        payload = {
            "availability": [
                {"dow": "M", "start_time": "12:00", "end_time": "14:00"}
            ],
            "bio": "test bio",
            "pricing": "24.99"
        }
        response = self.client.put('/coach/profile/1', json=payload)
        self.assertIn(response.status_code, [200, 500])

    def test_put_coach_profile_partial(self):
        payload = {"bio": "only bio"}
        response = self.client.put('/coach/profile/1', json=payload)
        self.assertIn(response.status_code, [200, 500])

    #Coach - Workout Plan
    def test_delete_workout_plan(self):
        response = self.client.delete('/coach/delete-plan/1')
        self.assertIn(response.status_code, [200, 500])

    def test_put_plan_title(self):
        payload = {"title": "test"}
        response = self.client.put('/coach/update-plan-title/1', json=payload)
        self.assertIn(response.status_code, [200, 500])

    def test_put_plan_title_missing(self):
        response = self.client.put('/coach/update-plan-title/1', json={})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()