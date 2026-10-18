from datetime import date, datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-development-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///procrastination.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    scores_json = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    due_date = db.Column(db.Date, nullable=True)
    planned_start = db.Column(db.DateTime, nullable=True)
    actual_start = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default="pending", nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    subtasks = db.relationship("Subtask", backref="task", cascade="all, delete-orphan", lazy=True)


class Subtask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    mini_deadline = db.Column(db.Date, nullable=True)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)


class FocusSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=True)
    started_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    ended_at = db.Column(db.DateTime, nullable=True)
    duration_minutes = db.Column(db.Integer, default=0, nullable=False)


class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=True)
    event_type = db.Column(db.String(80), nullable=False)
    occurred_at = db.Column(db.DateTime, default=utcnow, nullable=False)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def log_event(user_id, event_type, task_id=None):
    db.session.add(ActivityLog(user_id=user_id, event_type=event_type, task_id=task_id))


SUPPORTIVE_NOTES = (
    "A tiny start still counts.",
    "You can make progress without feeling completely ready.",
    "One small step is enough for now.",
    "Done is not the only kind of progress. Starting matters too.",
)


def recommendation_for(scores):
    if not scores:
        return {
            "barrier": "Getting started",
            "items": ["Choose one small task and work on it for five minutes.",
                      "Write down the very next action you can take."]
        }
    barrier = max(scores, key=scores.get)
    strategies = {
        "fear_of_failure": ("Fear of failure", [
            "Create a rough first draft; improve it later.",
            "Define success as making progress, not being perfect.",
            "Choose one small step that feels safe to begin."
        ]),
        "task_overwhelm": ("Task overwhelm / planning", [
            "Break the assignment into three to five small steps.",
            "Choose a first step that takes ten minutes or less.",
            "Set a realistic mini-deadline for the next step."
        ]),
        "low_confidence": ("Low confidence", [
            "Start with the easiest subtask to build momentum.",
            "Record completed steps so you can see your progress.",
            "Choose a small, achievable goal for this session."
        ]),
        "distraction": ("Distraction", [
            "Try a 15-minute focus session.",
            "Put your phone out of reach or silence optional notifications.",
            "Keep a distraction note and return to the task."
        ]),
        "task_anxiety": ("Task-related anxiety", [
            "Take a slow, comfortable breathing break if useful.",
            "Make the first action small and specific.",
            "Ask for support if the task or distress feels unmanageable."
        ])
    }
    label, items = strategies.get(barrier, strategies["task_overwhelm"])
    return {"barrier": label, "items": list(items)}


def recommendation_items(recommendation):
    if not isinstance(recommendation, dict):
        return []
    items = recommendation.get("items")
    if isinstance(items, list):
        return [item for item in items if item]
    return []


def choose_first_step(pending_tasks):
    if not pending_tasks:
        return None
    return sorted(
        pending_tasks,
        key=lambda task: (
            task.due_date is None,
            task.due_date or date.max,
            task.created_at or datetime.min,
        ),
    )[0]


def supportive_note(total, completed):
    if total == 0:
        return SUPPORTIVE_NOTES[0]
    if completed == 0:
        return SUPPORTIVE_NOTES[1]
    if completed >= total:
        return SUPPORTIVE_NOTES[3]
    return SUPPORTIVE_NOTES[2]


@app.route("/")
def index():
    return render_template("little_by_little.html")

@app.route("/little-by-little")
def little_by_little():
    return render_template("little_by_little.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not email or len(password) < 8:
            flash("Enter a valid email and a password with at least 8 characters.", "error")
            return render_template("register.html")
        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
            return render_template("register.html")
        user = User(email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        session["user_id"] = user.id
        flash("Account created. Start with your assessment or add a task.", "success")
        return redirect(url_for("dashboard"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash("Email or password was not recognized.", "error")
            return render_template("login.html")
        session["user_id"] = user.id
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    uid = session["user_id"]
    tasks = Task.query.filter_by(user_id=uid).order_by(Task.created_at.desc()).all()
    total = len(tasks)
    completed = sum(t.status == "completed" for t in tasks)
    pending = [t for t in tasks if t.status != "completed"]
    focus_count = FocusSession.query.filter_by(user_id=uid).count()
    assessment = Assessment.query.filter_by(user_id=uid).order_by(Assessment.created_at.desc()).first()
    scores = assessment.scores_json if assessment else {}
    recommendation = recommendation_for(scores)
    items = recommendation_items(recommendation)
    percent = int(round((completed / total) * 100)) if total else 0
    garden_slots = 8
    garden_grown = int(round((percent / 100) * garden_slots)) if total else 0
    first_step = choose_first_step(pending)
    next_action = None
    if first_step:
        next_action = next((subtask for subtask in first_step.subtasks if not subtask.completed), None)
    return render_template(
        "dashboard.html",
        tasks=tasks,
        total=total,
        completed=completed,
        pending_count=len(pending),
        pending_tasks=pending,
        focus_count=focus_count,
        recommendation=recommendation,
        recommendation_items=items,
        has_assessment=bool(assessment),
        completion_percent=percent,
        garden_slots=garden_slots,
        garden_grown=garden_grown,
        first_step=first_step,
        next_action=next_action,
        supportive_note=supportive_note(total, completed),
        today=date.today(),
    )


@app.route("/assessment", methods=["GET", "POST"])
@login_required
def assessment():
    questions = [
        ("fear_of_failure", "I delay work because I worry about making mistakes."),
        ("task_overwhelm", "I feel overwhelmed when an assignment has many steps."),
        ("low_confidence", "I doubt I can complete academic work successfully."),
        ("distraction", "I get distracted by unrelated activities when studying."),
        ("task_anxiety", "I put off work because thinking about it makes me anxious."),
        ("task_overwhelm", "I find it difficult to plan when and how to begin tasks."),
        ("fear_of_failure", "I wait until I feel that my work will be perfect before starting."),
        ("distraction", "I find it hard to stay focused on one task for a short period.")
    ]
    if request.method == "POST":
        totals, counts = {}, {}
        for i, (category, _) in enumerate(questions):
            try:
                value = int(request.form.get(f"q{i}", ""))
                if value < 1 or value > 5:
                    raise ValueError()
            except ValueError:
                flash("Please answer every question using the 1–5 scale.", "error")
                return render_template("assessment.html", questions=questions)
            totals[category] = totals.get(category, 0) + value
            counts[category] = counts.get(category, 0) + 1
        scores = {k: round(totals[k] / counts[k], 2) for k in totals}
        db.session.add(Assessment(user_id=session["user_id"], scores_json=scores))
        log_event(session["user_id"], "assessment_completed")
        db.session.commit()
        flash("Assessment saved. These results are reflective prompts, not a diagnosis.", "success")
        return redirect(url_for("dashboard"))
    return render_template("assessment.html", questions=questions)

@app.route("/tasks")
@login_required
def tasks_page():
    uid = session["user_id"]
    tasks = Task.query.filter_by(user_id=uid).order_by(Task.created_at.desc()).all()
    return render_template("tasks.html", tasks=tasks)
    
@app.route("/tasks/new", methods=["GET", "POST"])
@login_required
def new_task():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        due_raw = request.form.get("due_date", "")
        planned_raw = request.form.get("planned_start", "")
        if not title:
            flash("Task title is required.", "error")
            return render_template("task_new.html")
        due_date = datetime.strptime(due_raw, "%Y-%m-%d").date() if due_raw else None
        planned_start = datetime.fromisoformat(planned_raw) if planned_raw else None
        task = Task(user_id=session["user_id"], title=title, description=description,
                    due_date=due_date, planned_start=planned_start)
        db.session.add(task)
        db.session.flush()
        # Starter task template. Students can edit or remove these later.
        for sub_title in ["Gather materials / research", "Create an outline", "Complete a first draft", "Review and submit"]:
            db.session.add(Subtask(task_id=task.id, title=sub_title))
        log_event(session["user_id"], "task_created", task.id)
        db.session.commit()
        flash("Task created with editable starter subtasks.", "success")
        return redirect(url_for("task_detail", task_id=task.id))
    return render_template("task_new.html")


@app.route("/tasks/<int:task_id>")
@login_required
def task_detail(task_id):
    task = Task.query.filter_by(id=task_id, user_id=session["user_id"]).first_or_404()
    return render_template("task_detail.html", task=task)


@app.route("/tasks/<int:task_id>/start", methods=["POST"])
@login_required
def start_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=session["user_id"]).first_or_404()
    if not task.actual_start:
        task.actual_start = utcnow()
        log_event(session["user_id"], "task_start_recorded", task.id)
        db.session.commit()
    flash("Task start recorded. Nice work taking the first step.", "success")
    return redirect(url_for("task_detail", task_id=task.id))


@app.route("/subtasks/<int:subtask_id>/toggle", methods=["POST"])
@login_required
def toggle_subtask(subtask_id):
    subtask = Subtask.query.join(Task).filter(
        Subtask.id == subtask_id, Task.user_id == session["user_id"]
    ).first_or_404()
    subtask.completed = not subtask.completed
    subtask.completed_at = utcnow() if subtask.completed else None
    log_event(session["user_id"], "subtask_completed" if subtask.completed else "subtask_reopened", subtask.task_id)
    all_done = all(s.completed for s in subtask.task.subtasks)
    if all_done:
        subtask.task.status = "completed"
        log_event(session["user_id"], "task_completed", subtask.task_id)
    else:
        subtask.task.status = "pending"
    db.session.commit()
    return redirect(url_for("task_detail", task_id=subtask.task_id))


@app.route("/tasks/<int:task_id>/complete", methods=["POST"])
@login_required
def complete_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=session["user_id"]).first_or_404()
    now = utcnow()
    for subtask in task.subtasks:
        if not subtask.completed:
            subtask.completed = True
            subtask.completed_at = now
    task.status = "completed"
    if not task.actual_start:
        task.actual_start = now
    log_event(session["user_id"], "task_completed", task.id)
    db.session.commit()
    flash("Nice work. That task is marked complete.", "success")
    return redirect(url_for("dashboard"))


@app.route("/subtasks/<int:subtask_id>/deadline", methods=["POST"])
@login_required
def update_subtask_deadline(subtask_id):
    subtask = Subtask.query.join(Task).filter(
        Subtask.id == subtask_id, Task.user_id == session["user_id"]
    ).first_or_404()
    raw = request.form.get("mini_deadline", "").strip()
    if raw:
        try:
            subtask.mini_deadline = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            flash("Enter a valid mini-deadline date.", "error")
            return redirect(url_for("task_detail", task_id=subtask.task_id))
    else:
        subtask.mini_deadline = None
    db.session.commit()
    flash("Mini-deadline saved.", "success")
    return redirect(url_for("task_detail", task_id=subtask.task_id))


@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=session["user_id"]).first_or_404()
    db.session.delete(task)
    db.session.commit()
    flash("Task deleted.", "success")
    return redirect(url_for("dashboard"))


@app.route("/focus", methods=["GET", "POST"])
@login_required
def focus():
    if request.method == "POST":
        try:
            duration = max(1, min(180, int(request.form.get("duration", "15"))))
        except ValueError:
            duration = 15
        task_id_raw = request.form.get("task_id", "")
        task_id = None
        if task_id_raw:
            task = Task.query.filter_by(id=int(task_id_raw), user_id=session["user_id"]).first()
            task_id = task.id if task else None
        focus_session = FocusSession(user_id=session["user_id"], task_id=task_id,
                                     started_at=utcnow(), duration_minutes=duration)
        db.session.add(focus_session)
        log_event(session["user_id"], "focus_session_logged", task_id)
        db.session.commit()
        flash(f"{duration}-minute focus session logged. This records participation, not proof of uninterrupted work.", "success")
        return redirect(url_for("focus"))
    tasks = Task.query.filter_by(user_id=session["user_id"], status="pending").all()
    recent = FocusSession.query.filter_by(user_id=session["user_id"]).order_by(FocusSession.started_at.desc()).limit(5).all()
    return render_template("focus.html", tasks=tasks, recent=recent)


@app.route("/progress")
@login_required
def progress():
    uid = session["user_id"]
    tasks = Task.query.filter_by(user_id=uid).all()
    total_subtasks = sum(len(t.subtasks) for t in tasks)
    done_subtasks = sum(s.completed for t in tasks for s in t.subtasks)
    completed_tasks = sum(t.status == "completed" for t in tasks)
    sessions = FocusSession.query.filter_by(user_id=uid).all()
    total_focus = sum(s.duration_minutes for s in sessions)
    events = ActivityLog.query.filter_by(user_id=uid).order_by(ActivityLog.occurred_at.desc()).limit(15).all()
    starts = [t for t in tasks if t.planned_start and t.actual_start]
    avg_latency = None
    if starts:
        avg_latency = round(sum((t.actual_start - t.planned_start).total_seconds() / 60 for t in starts) / len(starts), 1)
    return render_template("progress.html", tasks=tasks, total_subtasks=total_subtasks,
                           done_subtasks=done_subtasks, completed_tasks=completed_tasks,
                           total_focus=total_focus, events=events, avg_latency=avg_latency)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "1") == "1")
