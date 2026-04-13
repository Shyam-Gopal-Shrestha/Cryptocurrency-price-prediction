# Ansush Crypto Starter

A starter project for React + FastAPI + MySQL authentication with three roles: user, admin, researcher.

## Backend
1. Create the MySQL database with `backend/schema.sql`
2. Open a terminal in `backend/`
3. Install packages:
   - `pip install -r requirements.txt`
4. Start server:
   - `uvicorn main:app --reload`

## Frontend
1. Open a terminal in `frontend/`
2. Install packages:
   - `npm install`
3. Start app:
   - `npm run dev`

## Notes
- Update `DATABASE_URL` in `backend/database.py` if your MySQL username or password differs.
- Frontend expects the API at `http://127.0.0.1:8000/api`
