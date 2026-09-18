# System Architecture

```text
                         SMARTCAMPUS AI
                               |
              +----------------+----------------+
              |                |                |
           Student           Faculty           Admin
              |                |                |
              +----------------+----------------+
                               |
                         Django Backend
                               |
          +--------------------+--------------------+
          |                    |                    |
       MySQL DB           AI/ML Service       Notification
          |                    |                    |
          |              Performance Model       Notices
          |              Academic Assistant
          |
     Students / Faculty /
     Subjects / Timetable /
     Attendance / Marks
```

The architecture can evolve as the project grows. Keep business rules in Django services/models rather than duplicating logic across templates.
