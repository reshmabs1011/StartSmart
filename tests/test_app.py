import os
import tempfile
import unittest

TEST_DB = os.path.join(tempfile.gettempdir(), "startsmart_test.db")
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["DATABASE_URL"] = "sqlite:///" + TEST_DB.replace("\\", "/")
os.environ["FLASK_DEBUG"] = "0"

from app import app, db, recommendation_for, recommendation_items  # noqa: E402


class StartSmartTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + TEST_DB.replace("\\", "/")
        self.client = app.test_client()
        with app.app_context():
            db.drop_all()
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def register(self, email="student@example.com", password="password123"):
        return self.client.post(
            "/register",
            data={"email": email, "password": password},
            follow_redirects=True,
        )

    def test_landing_page_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"You don't need to finish everything", response.data)
        self.assertIn(b"Start My Journey", response.data)
        self.assertIn(b'href="#how-it-works"', response.data)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_recommendation_items_are_iterable_lists(self):
        empty = recommendation_for({})
        self.assertIsInstance(empty["items"], list)
        self.assertEqual(recommendation_items(empty), empty["items"])
        self.assertEqual(recommendation_items({"barrier": "x"}), [])
        self.assertEqual(recommendation_items(None), [])
        scored = recommendation_for({"fear_of_failure": 5, "distraction": 1})
        self.assertEqual(scored["barrier"], "Fear of failure")
        self.assertTrue(scored["items"])

    def test_dashboard_renders_without_typeerror(self):
        self.register()
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Let's make today a little easier.", response.data)
        self.assertIn(b"Getting started", response.data)
        self.assertIn(b"Choose one small task", response.data)
        self.assertNotIn(b"<li><li>", response.data)

    def test_invalid_login_and_short_password(self):
        bad_login = self.client.post("/login", data={"email": "nope@example.com", "password": "wrong"})
        self.assertEqual(bad_login.status_code, 200)
        self.assertIn(b"not recognized", bad_login.data)
        short = self.client.post("/register", data={"email": "a@b.com", "password": "short"})
        self.assertEqual(short.status_code, 200)
        self.assertIn(b"at least 8 characters", short.data)

    def test_task_create_and_dashboard_first_step(self):
        self.register()
        created = self.client.post(
            "/tasks/new",
            data={"title": "Write lab report", "description": "Draft methods", "due_date": "2026-10-20"},
            follow_redirects=True,
        )
        self.assertEqual(created.status_code, 200)
        self.assertIn(b"Write lab report", created.data)
        dashboard = self.client.get("/dashboard")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"Write lab report", dashboard.data)
        self.assertIn(b"FIRST STEP", dashboard.data)
        self.assertIn(b"of 1 tasks complete", dashboard.data)

    def test_assessment_requires_all_answers_then_saves(self):
        self.register()
        incomplete = self.client.post("/assessment", data={"q0": "3"})
        self.assertEqual(incomplete.status_code, 200)
        self.assertIn(b"Please answer every question", incomplete.data)
        payload = {f"q{i}": "4" for i in range(8)}
        complete = self.client.post("/assessment", data=payload, follow_redirects=True)
        self.assertEqual(complete.status_code, 200)
        self.assertIn(b"Assessment saved", complete.data)
        self.assertIn(b"A SUGGESTION FOR YOU", complete.data)

    def test_focus_page_and_log(self):
        self.register()
        page = self.client.get("/focus")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Focus Cocoon", page.data)
        logged = self.client.post("/focus", data={"duration": "15", "task_id": ""}, follow_redirects=True)
        self.assertEqual(logged.status_code, 200)
        self.assertIn(b"15-minute focus session logged", logged.data)

    def test_protected_routes_redirect(self):
        for path in ("/dashboard", "/assessment", "/tasks/new", "/focus", "/progress"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302)
            self.assertIn("/login", response.headers.get("Location", ""))

    def test_task_isolation(self):
        self.register("one@example.com")
        self.client.post("/tasks/new", data={"title": "Private task"})
        with app.app_context():
            from app import Task
            task = Task.query.filter_by(title="Private task").first()
            task_id = task.id
        self.client.get("/logout")
        self.register("two@example.com", "password123")
        blocked = self.client.get(f"/tasks/{task_id}")
        self.assertEqual(blocked.status_code, 404)


if __name__ == "__main__":
    unittest.main()
