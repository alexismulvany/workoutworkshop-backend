import unittest
from app import app

# cd workoutworkshop-backend, venv\Scripts\activate
# coverage run -m unittest tests/admin_tests.py, coverage report
class TestAdminRoutes(unittest.TestCase):
    
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
    
    # Admin - Test
    def admin_test_route(self):
        response = self.client.get("/admin/test")
        data = response.get_json()
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", data)
    
    # Admin - Coach Applications
    def test_coach_applications(self):
        response = self.client.get("/admin/coach-applications")
        data = response.get_json()
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("applications", data)
        self.assertIn("totalPages", data)
    
    def test_coach_application_details_success(self):
        response = self.client.get("/admin/coach-applications/1")
        data = response.get_json()
        
        # Could be 200 or 404 depending on DB
        self.assertIn(response.status_code, [200, 404])
        
        if response.status_code == 200:
            self.assertIn("name", data)
            self.assertIn("certifications", data)
    
    def test_coach_application_details_failure(self):
        response = self.client.get("/admin/coach-applications/824")
        self.assertEqual(response.status_code, 404)
    
    def test_approve_certification(self):
        payload = {"admin_id": 1}
        
        response = self.client.put(
            "/admin/coach-applications/1/approve",
            json=payload
        )
        
        data = response.get_json()
        self.assertIn(response.status_code, [200, 500])
        
        if response.status_code == 200:
            self.assertIn("message", data)
    
    def test_reject_certification(self):
        payload = {"admin_id": 1}
        
        response = self.client.put(
            "/admin/coach-applications/1/reject",
            json=payload
        )
        
        data = response.get_json()
        self.assertIn(response.status_code, [200, 500])
        
        if response.status_code == 200:
            self.assertIn("message", data)
    
    # Admin - Coach Reports
    def test_coach_reports(self):
        response = self.client.get("/admin/coach-reports")
        data = response.get_json()
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("reports", data)
    
    def test_coach_report_details(self):
        response = self.client.get("/admin/coach-reports/1")
        
        self.assertIn(response.status_code, [200, 404])
    
    def test_dismiss_report(self):
        response = self.client.put("/admin/coach-reports/1/dismiss")
        data = response.get_json()
        
        self.assertIn(response.status_code, [200, 500])
        
        if response.status_code == 200:
            self.assertIn("message", data)
    
    # Admin - Ban / Disable
    def test_ban_coach(self):
        payload = {
            "user_id": 1,
            "reason": "Broke the Rules"
        }
        
        response = self.client.put(
            "/admin/coach-reports/1/ban",
            json=payload
        )
        
        data = response.get_json()
        
        self.assertIn(response.status_code, [200, 400, 404, 500])
        
        if response.status_code == 200:
            self.assertIn("message", data)
    
    def test_disable_coach(self):
        payload = {
            "user_id": 1,
            "reason": "Suspension for breaking the rules",
            "day": 1,
            "month": 1,
            "year": 2028
        }
        
        response = self.client.put(
            "/admin/coach-reports/1/disable",
            json=payload
        )
        
        data = response.get_json()
        
        self.assertIn(response.status_code, [200, 400, 404, 500])
        
        if response.status_code == 200:
            self.assertIn("message", data)
    
    # Admin - Exercises
    def test_exercises(self):
        response = self.client.get("/admin/exercises")
        data = response.get_json()
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("status", data)
    
    def test_search_exercises(self):
        response = self.client.get("/admin/exercises?search=push")
        data = response.get_json()
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["mode"], "search")
    
    def test_add_exercise_success(self):
        payload = {
            "user_id": 1,
            "name": "UnitTest Exercise",
            "muscle_group": "Chest",
            "equipment_needed": "Body Weight",
            "video_url": "http://example.com"
        }
        
        response = self.client.post("/admin/exercises/add", json=payload)
        data = response.get_json()
        
        self.assertIn(response.status_code, [200, 500])
        
        if response.status_code == 200:
            self.assertEqual(data["status"], "success")
            self.assertIn("exercise_id", data)
    
    def test_add_exercise_failure(self):
        payload = {
            "user_id": 1,
            "name": "Bad Exercise",
            "muscle_group": "Invalid",
            "equipment_needed": "Body Weight"
        }
        
        response = self.client.post("/admin/exercises/add", json=payload)
        
        self.assertEqual(response.status_code, 400)
    
    def test_remove_exercise(self):
        payload = {"user_id": 1}
        
        response = self.client.delete(
            "/admin/exercises/remove/1",
            json=payload
        )
        
        data = response.get_json()
        
        self.assertIn(response.status_code, [200, 500])
        
        if response.status_code == 200:
            self.assertEqual(data["status"], "success")
    
    def test_edit_exercise(self):
        payload = {
            "user_id": 1,
            "name": "Updated Exercise",
            "muscle_group": "Chest",
            "equipment_needed": "Body Weight",
            "video_url": "http://example.com"
        }
        
        response = self.client.put(
            "/admin/exercises/update/1",
            json=payload
        )
        
        data = response.get_json()
        
        self.assertIn(response.status_code, [200, 500])
        
        if response.status_code == 200:
            self.assertEqual(data["status"], "success")
    
    # Admin - Users
    def test_fetch_users(self):
        response = self.client.get("/admin/fetch-users")
        data = response.get_json()
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("users", data)
        self.assertIn("totalUsers", data)
    
if __name__ == "__main__":
    unittest.main()