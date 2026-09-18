# API Plan

The project can initially use Django views/templates. A REST API can be introduced if a separate frontend is needed.

## Proposed Endpoints

```text
POST   /api/auth/login/
POST   /api/auth/logout/

GET    /api/student/profile/
GET    /api/student/timetable/
GET    /api/student/notices/
GET    /api/student/attendance/
GET    /api/student/marks/

GET    /api/faculty/timetable/
POST   /api/faculty/attendance/
POST   /api/faculty/notices/

GET    /api/admin/stats/
POST   /api/admin/timetable/

POST   /api/prediction/performance/
POST   /api/chatbot/message/
```

Authentication and permissions must be applied to every private endpoint.
