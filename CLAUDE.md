# GridPulse Project Instructions

GridPulse is an F1 Race Intelligence Platform.

Current phase: Phase 1 only.

Phase 1 scope:
- FastAPI backend
- PostgreSQL connection
- SQLAlchemy models
- seeded local F1 data
- basic endpoints:
  - GET /
  - GET /health
  - GET /drivers
  - GET /drivers/{id}
  - GET /teams
  - GET /calendar
  - GET /standings/drivers

Do not add yet:
- frontend
- authentication
- Google sign-in
- notifications
- email notifications
- AI
- Redis
- WebSockets
- Docker
- live F1 data
- track map
- ML

Development style:
- Build step by step
- Explain changes clearly
- Keep code beginner-friendly
- Do not overbuild
- After changes, explain how to test manually