from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from functools import wraps
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///taskmaster.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ─── Models ───────────────────────────────────────────────────────────────────

class User(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email    = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created  = db.Column(db.DateTime, default=datetime.utcnow)
    tasks    = db.relationship('Task', backref='owner', lazy=True, cascade='all, delete-orphan')

class Task(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    priority    = db.Column(db.String(10), default='medium')   # high / medium / low
    status      = db.Column(db.String(10), default='pending')  # pending / done
    deadline    = db.Column(db.Date, nullable=True)
    created     = db.Column(db.DateTime, default=datetime.utcnow)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # ── Earliest-Deadline-First priority score (lower = more urgent) ──────────
    def urgency_score(self):
        """
        EDF scheduling algorithm:
        score = days_until_deadline * priority_weight
        priority_weight: high=1, medium=2, low=3
        Tasks with no deadline get score=9999 (lowest urgency).
        """
        weights = {'high': 1, 'medium': 2, 'low': 3}
        w = weights.get(self.priority, 2)
        if self.deadline is None:
            return 9999
        delta = (self.deadline - date.today()).days
        return delta * w

    @property
    def is_overdue(self):
        return self.deadline and self.deadline < date.today() and self.status == 'pending'

    @property
    def days_left(self):
        if not self.deadline:
            return None
        return (self.deadline - date.today()).days

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'priority': self.priority,
            'status': self.status,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'is_overdue': self.is_overdue,
            'days_left': self.days_left,
            'urgency_score': self.urgency_score()
        }

# ─── Auth helpers ──────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'info')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email    = request.form['email'].strip().lower()
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'error')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return redirect(url_for('register'))

        user = User(
            username=username,
            email=email,
            password=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        flash(f'Welcome, {username}!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form['email'].strip().lower()
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user  = current_user()
    tasks = Task.query.filter_by(user_id=user.id).all()

    # EDF sort: pending tasks sorted by urgency score, done tasks at the bottom
    pending = sorted([t for t in tasks if t.status == 'pending'], key=lambda t: t.urgency_score())
    done    = [t for t in tasks if t.status == 'done']

    total    = len(tasks)
    complete = len(done)
    pct      = round((complete / total * 100) if total else 0)

    overdue   = [t for t in pending if t.is_overdue]
    due_today = [t for t in pending if t.deadline == date.today()]

    return render_template('dashboard.html',
        user=user,
        pending=pending,
        done=done,
        total=total,
        complete=complete,
        pct=pct,
        overdue_count=len(overdue),
        due_today_count=len(due_today),
        today=date.today()
    )

@app.route('/task/new', methods=['GET', 'POST'])
@login_required
def new_task():
    if request.method == 'POST':
        deadline_str = request.form.get('deadline')
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None
        task = Task(
            title       = request.form['title'].strip(),
            description = request.form.get('description', '').strip(),
            priority    = request.form.get('priority', 'medium'),
            deadline    = deadline,
            user_id     = session['user_id']
        )
        db.session.add(task)
        db.session.commit()
        flash('Task added.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('task_form.html', task=None, today=date.today().isoformat())

@app.route('/task/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=session['user_id']).first_or_404()
    if request.method == 'POST':
        deadline_str = request.form.get('deadline')
        task.title       = request.form['title'].strip()
        task.description = request.form.get('description', '').strip()
        task.priority    = request.form.get('priority', 'medium')
        task.deadline    = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None
        db.session.commit()
        flash('Task updated.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('task_form.html', task=task, today=date.today().isoformat())

@app.route('/task/<int:task_id>/toggle', methods=['POST'])
@login_required
def toggle_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=session['user_id']).first_or_404()
    task.status = 'done' if task.status == 'pending' else 'pending'
    db.session.commit()
    return jsonify({'status': task.status, 'pct': _completion_pct()})

@app.route('/task/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=session['user_id']).first_or_404()
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted.', 'info')
    return redirect(url_for('dashboard'))

# ─── API endpoint (shows REST knowledge on resume) ────────────────────────────

@app.route('/api/tasks')
@login_required
def api_tasks():
    """
    REST endpoint: GET /api/tasks
    Returns all tasks for the logged-in user sorted by EDF urgency score.
    """
    tasks = Task.query.filter_by(user_id=session['user_id']).all()
    sorted_tasks = sorted(tasks, key=lambda t: t.urgency_score())
    return jsonify([t.to_dict() for t in sorted_tasks])

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _completion_pct():
    if 'user_id' not in session:
        return 0
    tasks = Task.query.filter_by(user_id=session['user_id']).all()
    if not tasks:
        return 0
    done = sum(1 for t in tasks if t.status == 'done')
    return round(done / len(tasks) * 100)

# ─── Init ─────────────────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
