# Database Design

## Core Entities

### User
Authentication and role information.

Suggested fields:
- id
- username/email
- password hash
- role
- is_active
- created_at

### Student
Suggested fields:
- id
- user_id
- student_id
- department_id
- semester
- phone
- admission_year

### Faculty
Suggested fields:
- id
- user_id
- employee_id
- department_id
- designation

### Department
- id
- name
- code

### Subject
- id
- code
- name
- department_id
- semester
- credits

### Timetable
- id
- subject_id
- faculty_id
- classroom_id
- day
- start_time
- end_time

### Attendance
- id
- student_id
- subject_id
- date
- status
- marked_by

### Marks
- id
- student_id
- subject_id
- examination_id
- marks

### Notice
- id
- title
- content
- posted_by
- category
- created_at
- expires_at

### Assignment
- id
- subject_id
- faculty_id
- title
- description
- deadline

## Relationships

```text
Department 1 ──── N Student
Department 1 ──── N Faculty
Department 1 ──── N Subject

Subject 1 ──── N Timetable
Faculty 1 ──── N Timetable
Student 1 ──── N Attendance
Subject 1 ──── N Attendance

Student 1 ──── N Marks
Subject 1 ──── N Marks
```

Use Django migrations as the source of truth for the implementation.
