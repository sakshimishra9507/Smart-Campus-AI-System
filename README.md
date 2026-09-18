# SmartCampus AI

SmartCampus AI is a Django-based smart campus management platform designed to centralize academic information and provide AI-assisted support for students and faculty.

The project aims to bring college operations—including academic information, schedules, notices, attendance, examinations, assignments, reporting, and student assistance—into one web application.

## Features and planned modules

- User authentication and role-based access
- Student and faculty management
- Academic information and timetable access
- Attendance and examination management
- Assignment and notice management
- Reports and academic analytics
- AI/ML-based academic prediction
- Academic assistant support

See [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) for the project objectives, module outline, and future scope.

## Technology stack

- **Backend:** Python, Django 5.2+
- **Database:** MySQL
- **Data and machine learning:** Pandas, NumPy, scikit-learn, joblib
- **Frontend:** HTML and CSS
- **Other:** Pillow, python-dotenv

## Project structure

```text
.
├── home.html                   # Home page template
├── login.html                  # Login page template
├── style.css                   # Frontend styles
├── urls.py                     # URL routing
├── settings.py                 # Django project settings
├── manage.py                   # Django management utility
├── requirements.txt            # Python dependencies
├── AI_ML.md                    # AI/ML documentation
├── API.md                      # API documentation
├── ARCHITECTURE.md             # Architecture documentation
├── DATABASE.md                 # Database documentation
├── DEPLOYMENT.md               # Deployment documentation
└── PROJECT_DOCUMENTATION.md    # Project overview and scope
```

## Getting started

### Prerequisites

- Python 3.10 or newer
- MySQL server
- MySQL development libraries required by `mysqlclient`

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/sakshimishra9507/Smart-Campus-AI-System.git
   cd Smart-Campus-AI-System
   ```

2. Create and activate a virtual environment:

   **Windows:**

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

   **macOS/Linux:**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Configure the Django settings and MySQL database connection. Keep secrets such as database credentials and Django's `SECRET_KEY` out of source control. The project includes `python-dotenv` for environment-based configuration.

5. Apply database migrations:

   ```bash
   python manage.py migrate
   ```

6. Optionally create an administrator account:

   ```bash
   python manage.py createsuperuser
   ```

7. Start the development server:

   ```bash
   python manage.py runserver
   ```

8. Open <http://127.0.0.1:8000/> in your browser. The Django admin is available at <http://127.0.0.1:8000/admin/>.

## Documentation

- [Architecture](ARCHITECTURE.md)
- [AI/ML](AI_ML.md)
- [API](API.md)
- [Database](DATABASE.md)
- [Deployment](DEPLOYMENT.md)
- [Contributing](CONTRIBUTING.md)
- [Project documentation](PROJECT_DOCUMENTATION.md)
- [Roadmap](ROADMAP.md)

## Testing

Run the Django test suite with:

```bash
python manage.py test
```

Recommended coverage areas include authentication, role permissions, attendance calculations, timetable conflicts, notice visibility, marks calculations, prediction services, and chatbot retrieval.

## Future scope

Planned extensions include a mobile application, parent portal, placement management, library integration, hostel and transport management, and advanced analytics. Any face-based attendance feature should be implemented only with appropriate consent, privacy protections, and safeguards.

## License

This project is licensed under the terms described in [LICENSE](LICENSE).
