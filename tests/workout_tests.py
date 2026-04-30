import unittest
from unittest.mock import MagicMock
from app import app


class TestWorkoutRoutes(unittest.TestCase):

    def setUp(self):
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.app = app
        self.app.testing = True
        self.client = self.app.test_client()

        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()
    
    # helper function to mock the database
    def setup_mock_db(self):
        mock_db = MagicMock()
        self.app.extensions['sqlalchemy'] = mock_db
        return mock_db
    
    # Get Exercises
    def test_get_exercises_success(self):
        mock_db = self.setup_mock_db()

        mock_db.session.execute.return_value.mappings.return_value.fetchall.return_value = [
            {"exercise_id": 1, "name": "Bench Press"}
        ]

        response = self.client.get('/api/workouts/exercises')
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['status'], 'success')

    def test_get_exercises_failure(self):
        mock_db = self.setup_mock_db()
        mock_db.session.execute.side_effect = Exception("DB error")

        response = self.client.get('/api/workouts/exercises')
        self.assertEqual(response.status_code, 500)

    # Get Daily Plan
    def test_get_daily_plan_with_data(self):
        mock_db = self.setup_mock_db()
        mock_db.session.execute.return_value.mappings.return_value.fetchall.return_value = [
            {"plan_id": 1}
        ]

        response = self.client.get('/api/workouts/daily-plan/1/MON')
        data = response.get_json()

        self.assertTrue(data['hasPlan'])

    def test_get_daily_plan_empty(self):
        mock_db = self.setup_mock_db()
        mock_db.session.execute.return_value.mappings.return_value.fetchall.return_value = []

        response = self.client.get('/api/workouts/daily-plan/1/MON')
        data = response.get_json()

        self.assertFalse(data['hasPlan'])
    
    def test_get_daily_plan_db_failure(self):
        mock_db = self.setup_mock_db()
        mock_db.session.execute.side_effect = Exception("fail")

        response = self.client.get('/api/workouts/daily-plan/1/MON')
        self.assertEqual(response.status_code, 500)
    
    # Save Workout
    def test_save_workout_success(self):
        mock_db = self.setup_mock_db()

        mock_result = MagicMock()
        mock_result.lastrowid = 1
        mock_db.session.execute.return_value = mock_result

        payload = {
            "user_id": 1,
            "date": "MON",
            "workout_name": "Push",
            "exercises": [{"exercise_id": 1, "sets": 3, "reps": 10}]
        }

        response = self.client.post('/api/workouts/save', json=payload)
        self.assertEqual(response.status_code, 201)

    def test_save_workout_missing_fields(self):
        response = self.client.post('/api/workouts/save', json={})
        self.assertEqual(response.status_code, 400)

    def test_save_workout_db_failure(self):
        mock_db = self.setup_mock_db()
        mock_db.session.execute.side_effect = Exception("fail")

        payload = {
            "user_id": 1,
            "date": "MON",
            "workout_name": "Push",
            "exercises": [{"exercise_id": 1, "sets": 3, "reps": 10}]
        }

        response = self.client.post('/api/workouts/save', json=payload)
        self.assertEqual(response.status_code, 500)

    # Get Workout Log
    def test_get_workout_log(self):
        mock_db = self.setup_mock_db()
        mock_db.session.execute.return_value.mappings.return_value.fetchall.return_value = [
            {"id": 1}
        ]

        response = self.client.get('/api/workouts/log/1')
        self.assertEqual(response.status_code, 200)

    def test_get_workout_log_db_failure(self):
        mock_db = self.setup_mock_db()
        mock_db.session.execute.side_effect = Exception("fail")

        response = self.client.get('/api/workouts/log/1')
        self.assertEqual(response.status_code, 500)

    # Get Plan Details
    def test_get_plan_details(self):
        mock_db = self.setup_mock_db()
        mock_db.session.execute.return_value.mappings.return_value.fetchall.return_value = [
            {"exercise_id": 1}
        ]

        response = self.client.get('/api/workouts/plan/1')
        self.assertEqual(response.status_code, 200)

    def test_get_plan_details_empty(self):
        mock_db = self.setup_mock_db()
        mock_db.session.execute.return_value.mappings.return_value.fetchall.return_value = []

        response = self.client.get('/api/workouts/plan/1')
        data = response.get_json()

        self.assertEqual(data['data'], [])

    def test_get_plan_details_db_failure(self):
        mock_db = self.setup_mock_db()
        mock_db.session.execute.side_effect = Exception("fail")

        response = self.client.get('/api/workouts/plan/1')
        self.assertEqual(response.status_code, 500)

    # Update Workout Plan
    def test_update_workout_plan(self):
        self.setup_mock_db()

        payload = {"exercises": [{"exercise_id": 1}]}

        response = self.client.put('/api/workouts/plan/1', json=payload)
        self.assertEqual(response.status_code, 200)

    def test_update_workout_plan_missing(self):
        self.setup_mock_db()

        response = self.client.put('/api/workouts/plan/1', json={})
        self.assertEqual(response.status_code, 400)

    def test_update_workout_plan_db_failure(self):
        mock_db = self.setup_mock_db()
        mock_db.session.execute.side_effect = Exception("fail")

        payload = {"exercises": [{"exercise_id": 1}]}

        response = self.client.put('/api/workouts/plan/1', json=payload)
        self.assertEqual(response.status_code, 500)

    # Delete Workout
    def test_delete_workout(self):
        self.setup_mock_db()

        response = self.client.delete('/api/workouts/plan/1')
        self.assertEqual(response.status_code, 200)

    def test_delete_workout_db_failure(self):
        mock_db = self.setup_mock_db()
        mock_db.session.execute.side_effect = Exception("fail")

        response = self.client.delete('/api/workouts/plan/1')
        self.assertEqual(response.status_code, 500)

    # Add Workout
    def test_add_workout(self):
        mock_db = self.setup_mock_db()

        mock_insert = MagicMock()
        mock_insert.lastrowid = 1
        mock_db.session.execute.return_value = mock_insert

        payload = {
            "planned_date": "MON",
            "user_id": 1,
            "exercise_id": 2
        }

        response = self.client.post('/api/workouts/add-workout', json=payload)
        self.assertEqual(response.status_code, 200)

    def test_add_workout_missing(self):
        self.setup_mock_db()

        response = self.client.post('/api/workouts/add-workout', json={})
        self.assertEqual(response.status_code, 400)

    # Remove Exercise
    def test_remove_exercise(self):
        self.setup_mock_db()

        payload = {"plan_id": 1, "exercise_id": 2}

        response = self.client.post('/api/workouts/remove', json=payload)
        self.assertEqual(response.status_code, 200)

    def test_remove_exercise_missing(self):
        self.setup_mock_db()

        response = self.client.post('/api/workouts/remove', json={})
        self.assertEqual(response.status_code, 400)

    # Toggle Complete Exercise
    def test_toggle_complete(self):
        self.setup_mock_db()

        payload = {"plan_exercise_id": 1, "complete": True}

        response = self.client.post('/api/workouts/complete-exercise', json=payload)
        self.assertEqual(response.status_code, 200)

    def test_toggle_complete_missing(self):
        self.setup_mock_db()

        response = self.client.post('/api/workouts/complete-exercise', json={})
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()