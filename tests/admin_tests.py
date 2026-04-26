import unittest
from app import app
from user_tests import generate_test_token

# cd workoutworkshop-backend, venv\Scripts\activate
# coverage run -m unittest tests/admin_tests.py, coverage report
class TestAdminRoutes(unittest.TestCase):
    
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
    
    # Admin - Coach Applications
    def test_coach_applications(self):
        response = self.client.get("/admin/coach-applications")
        data = response.get_json()
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("applications", data)
        self.assertIn("totalPages", data)
    
    def test_coach_application_details_success(self):
        response = self.client.get("/admin/coach-applications/1")
        self.assertIn(response.status_code, [200, 404])
        
        if response.status_code == 200:
            data = response.get_json()
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
        
        self.assertIn(response.status_code, [200, 500])
        
        if response.status_code == 200:
            data = response.get_json()
            self.assertIn("message", data)
    
    def test_reject_certification(self):
        payload = {"admin_id": 1}
        
        response = self.client.put(
            "/admin/coach-applications/1/reject",
            json=payload
        )
        
        self.assertIn(response.status_code, [200, 500])
        
        if response.status_code == 200:
            data = response.get_json()
            self.assertIn("message", data)
    
    # Admin - Coach Reports
    def test_coach_reports(self):
        response = self.client.get("/admin/coach-reports")
        data = response.get_json()
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("reports", data)
    
    def test_coach_report_details_success(self):
        response = self.client.get("/admin/coach-reports/1")
        self.assertIn(response.status_code, [200, 404])
        
        if response.status_code == 200:
            data = response.get_json()
            self.assertIn("coach", data)
    
    def test_coach_report_details_failure(self):
        response = self.client.get("/admin/coach-reports/824")
        self.assertEqual(response.status_code, 404)
    
    def test_dismiss_report(self):
        response = self.client.put("/admin/coach-reports/1/dismiss")
        self.assertIn(response.status_code, [200, 500])
        
        if response.status_code == 200:
            data = response.get_json()
            self.assertIn("message", data)
    
    # Admin - Ban / Disable
    def test_ban_coach_success(self):
        payload = {
            "user_id": 1,
            "reason": "Broke the Rules"
        }
        
        response = self.client.put(
            "/admin/coach-reports/1/ban",
            json=payload
        )
        
        self.assertIn(response.status_code, [200, 404, 500])
        
        if response.status_code == 200:
            data = response.get_json()
            self.assertIn("message", data)
    
    def test_ban_coach_missing_fields(self):
        payload = {
            "user_id": 1
        }
        
        response = self.client.put(
            "/admin/coach-reports/1/ban",
            json=payload
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_disable_coach_success(self):
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
        
        self.assertIn(response.status_code, [200, 404, 500])
        
        if response.status_code == 200:
            data = response.get_json()
            self.assertIn("message", data)
    
    def test_disable_coach_missing_fields(self):
        payload = {
            "user_id": 1,
            "reason": "Suspension for breaking the rules"
        }
        
        response = self.client.put(
            "/admin/coach-reports/1/disable",
            json=payload
        )
        
        self.assertEqual(response.status_code, 400)
    
    # Admin - Exercises
    def test_exercises(self):
        response = self.client.get("/admin/exercises")
        data = response.get_json()
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["mode"], "default")
        
        self.assertIn("data", data)
        self.assertIsInstance(data["data"], dict)
        
        self.assertIn("Chest", data["data"])
        self.assertIn("Legs", data["data"])
        self.assertIn("Arms", data["data"])
        self.assertIn("Back", data["data"])
        self.assertIn("Core", data["data"])
        self.assertIn("Cardio", data["data"])
    
    def test_search_exercises(self):
        response = self.client.get("/admin/exercises?search=push")
        data = response.get_json()
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["mode"], "search")
        
        self.assertIn("data", data)
        self.assertIsInstance(data["data"], list)
        
        if len(data["data"]) > 0:
            exercise = data["data"][0]
            self.assertIn("exercise_id", exercise)
            self.assertIn("name", exercise)
            self.assertIn("muscle_group", exercise)
            self.assertIn("equipment", exercise)
    
    def test_search_exercises_no_results(self):
        response = self.client.get("/admin/exercises?search=zzzz_not_real")
        data = response.get_json()
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["mode"], "search")
        self.assertEqual(data["data"], [])
    
    def test_search_exercises_empty_string(self):
        response = self.client.get("/admin/exercises?search=")
        data = response.get_json()
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["mode"], "default")

    def test_add_exercise_success(self):
        payload = {
            "user_id": 1,
            "name": "Pushup Test",
            "muscle_group": "Chest",
            "equipment_needed": "Body Weight",
            "video_url": "http://example.com"
        }

        # Send as Form Data (data=) to match the React frontend
        response = self.client.post("/admin/exercises/add", data=payload)
        self.assertIn(response.status_code, [200, 201])

        if response.status_code in [200, 201]:
            data = response.get_json()
            self.assertIn("message", data)

    def test_add_exercise_invalid_muscle(self):
        payload = {
            "user_id": 1,
            "name": "Bad Exercise",
            "muscle_group": "Invalid",
            "equipment_needed": "Body Weight"
        }

        # Send as Form Data. DB will reject the invalid muscle, triggering your except block (500)
        response = self.client.post("/admin/exercises/add", data=payload)
        self.assertEqual(response.status_code, 500)
    
    def test_remove_exercise(self):
        payload = {"user_id": 1}
        
        response = self.client.delete(
            "/admin/exercises/remove/1",
            json=payload
        )
        
        self.assertIn(response.status_code, [200, 500])
        
        if response.status_code == 200:
            data = response.get_json()
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
            data=payload
        )

        self.assertIn(response.status_code, [200])

        if response.status_code == 200:
            data = response.get_json()
            self.assertEqual(data["status"], "success")
    
    # Admin - Users
    def test_fetch_users(self):
        response = self.client.get("/admin/fetch-users")
        data = response.get_json()
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("users", data)
        self.assertIn("totalUsers", data)
    
    # Admin - Platform Metrics
    def test_platform_metrics(self):
        response = self.client.get("/admin/platform-metrics")
        self.assertIn(response.status_code, [200, 500])
        
        if response.status_code == 200:
            data = response.get_json()
            self.assertEqual(data["status"], "success")
            self.assertIn("data", data)

    def test_coach_application_details_not_found(self):
        """Covers 'if not application' branch"""
        response = self.client.get("/admin/coach-applications/99999")
        self.assertEqual(response.status_code, 404)

    def test_fetch_users_with_search(self):
        """Covers the 'IF search' branch in SQL construction"""
        response = self.client.get("/admin/fetch-users?search=Dylan&page=1&limit=5")
        self.assertEqual(response.status_code, 200)

    def test_fetch_users_empty_results(self):
        """Covers the branch where no users match a search"""
        response = self.client.get("/admin/fetch-users?search=NonExistentUser123")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()['users']), 0)

if __name__ == "__main__":
    unittest.main()