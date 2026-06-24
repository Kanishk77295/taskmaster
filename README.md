# TaskMaster 🗂️

A full-stack task management web app with user authentication, EDF scheduling algorithm, and a REST API — built with Python, Flask, and SQLite.


## Features

- **User authentication** — register, login, logout with hashed passwords (Werkzeug PBKDF2)
- **EDF scheduling algorithm** — tasks auto-sorted by Earliest Deadline First with priority weighting
- **CRUD operations** — create, read, update, delete tasks with title, description, priority, deadline
- **Live dashboard** — task completion percentage, overdue count, due-today count
- **REST API** — `GET /api/tasks` returns JSON sorted by urgency score
- **Async toggle** — mark tasks done/pending without page reload (fetch API)
- **Responsive design** — works on mobile and desktop

---

## Tech Stack

| Layer      | Technology                          |
|------------|-------------------------------------|
| Backend    | Python 3.11, Flask 3.0              |
| Database   | SQLite (dev), PostgreSQL (prod-ready)|
| ORM        | Flask-SQLAlchemy                    |
| Auth       | Werkzeug password hashing, Flask sessions |
| Frontend   | HTML5, CSS3, Vanilla JavaScript     |
| Deployment | Render (free tier), Gunicorn        |
| Version control | Git, GitHub                   |

---

## The EDF Algorithm

Tasks are ranked by a **urgency score**:

```
urgency_score = days_until_deadline × priority_weight

priority_weight:  High = 1  |  Medium = 2  |  Low = 3
```

Lower score = shown first. A high-priority task due tomorrow scores `1 × 1 = 1` and beats a low-priority task due today scoring `0 × 3 = 0`... wait, same deadline = deadline wins. This mirrors real-time OS scheduling used in embedded systems.

---

## Project Structure

```
taskmaster/
├── app.py                  # Flask app, routes, models, EDF logic
├── requirements.txt        # Python dependencies
├── render.yaml             # Render deployment config
├── static/
│   ├── css/
│   │   └── style.css       # All styles (dark theme, responsive)
│   └── js/
│       └── main.js         # Async toggle, flash auto-dismiss
└── templates/
    ├── base.html           # Navbar, flash messages, layout
    ├── index.html          # Landing page
    ├── login.html          # Login form
    ├── register.html       # Registration form
    ├── dashboard.html      # Main task view
    └── task_form.html      # Create / edit task
```

---


The SQLite database (`taskmaster.db`) is created automatically on first run.

---
---

## API Reference

### `GET /api/tasks`
Returns all tasks for the logged-in user, sorted by EDF urgency score.

**Response:**
```json
[
  {
    "id": 3,
    "title": "Submit internship application",
    "description": "Apply to DE Shaw before deadline",
    "priority": "high",
    "status": "pending",
    "deadline": "2025-07-01",
    "is_overdue": false,
    "days_left": 5,
    "urgency_score": 5
  }
]
```

---

## Database Schema

```
User
  id        INTEGER PRIMARY KEY
  username  TEXT UNIQUE NOT NULL
  email     TEXT UNIQUE NOT NULL
  password  TEXT NOT NULL          ← PBKDF2 hashed, never stored plain
  created   DATETIME

Task
  id          INTEGER PRIMARY KEY
  title       TEXT NOT NULL
  description TEXT
  priority    TEXT (high/medium/low)
  status      TEXT (pending/done)
  deadline    DATE
  created     DATETIME
  user_id     INTEGER FK → User.id
```

---
