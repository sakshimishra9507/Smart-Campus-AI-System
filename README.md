# SmartCampus AI 🎓

**AI-Based College Management & Student Academic Assistance System**

SmartCampus AI is a final-year project designed to provide a centralized college management portal for students, faculty, and administrators. It combines everyday academic-management features with AI/ML capabilities such as student performance prediction and an academic assistant.

> **Project status:** Roadmap / starter repository. Core implementation is intentionally organized into phases so features can be developed and tested incrementally.

## Core Features

- Role-based authentication: Student, Faculty, Admin
- Student and faculty profiles
- Departments and subjects
- Class timetable / daily schedule
- Daily notices and announcements
- Attendance management
- Marks and examination management
- Assignments
- Notifications
- AI-based student performance prediction
- Academic AI assistant / chatbot
- Reports and analytics

## Suggested Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python + Django |
| Database | MySQL (PostgreSQL is also suitable) |
| Frontend | HTML, CSS, JavaScript, Bootstrap |
| ML | Pandas, NumPy, Scikit-learn |
| Version Control | Git + GitHub |

## Repository Structure

```text
SmartCampusAI/
├── README.md
├── ROADMAP.md
├── CONTRIBUTING.md
├── LICENSE
├── .gitignore
├── requirements.txt
├── .env.example
├── manage.py
├── config/
├── apps/
│   ├── accounts/
│   ├── students/
│   ├── faculty/
│   ├── academics/
│   ├── attendance/
│   ├── examinations/
│   ├── notices/
│   ├── chatbot/
│   └── prediction/
├── templates/
├── static/
├── ml_models/
├── ml_data/
├── docs/
│   ├── DATABASE.md
│   ├── API.md
│   ├── AI_ML.md
│   └── DEPLOYMENT.md
└── tests/
```

## Quick Start

### 1. Clone

```bash
git clone https://github.com/YOUR_USERNAME/SmartCampusAI.git
cd SmartCampusAI
```

### 2. Create a virtual environment

macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env` and update the database credentials.

```bash
cp .env.example .env
```

Never commit `.env`.

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Create an admin user

```bash
python manage.py createsuperuser
```

### 7. Start the server

```bash
python manage.py runserver
```

Open:

`http://127.0.0.1:8000/`

## Development Roadmap

See [ROADMAP.md](ROADMAP.md) for the complete phase-by-phase plan.

## AI/ML Overview

The proposed prediction module can use academic features such as attendance, internal marks, assignment scores, quiz scores, and previous academic performance.

Example pipeline:

```text
Raw Academic Data
       ↓
Data Cleaning
       ↓
Feature Engineering
       ↓
Train/Test Split
       ↓
Model Training
       ↓
Evaluation
       ↓
Saved Model
       ↓
Django Prediction API
       ↓
Student/F faculty Dashboard
```

Do not use AI predictions as the sole basis for disciplinary, grading, admission, scholarship, or other high-impact decisions. Treat predictions as academic-support signals and document model limitations.

## Security

- Keep secrets in `.env`
- Hash passwords using Django authentication
- Use role-based permissions
- Validate uploaded files
- Protect forms with CSRF
- Do not commit personal student data
- Do not commit real passwords, API keys, or production database dumps

## License

This repository uses the MIT License. See [LICENSE](LICENSE).

## Contributors

Add your project team here.

- Your Name — Developer
- Team Member 2 — Developer
- Team Member 3 — Developer
