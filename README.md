# ExamSentinel - Official University Platform

ExamSentinel is a scalable, cloud-native examination and proctoring platform designed for university environments.

## Features
- **High-Security Proctoring Engine**: Tracks facial recognition, background noise, tab-switching, and unauthorized devices.
- **SQL & Code Sandbox**: Fully isolated Docker-based environment for executing student code and SQL queries safely.
- **Automated AI Pre-Grading**: Powered by Gemini 2.0 to instantly pre-grade code and essays against Professor rubrics.
- **University Plagiarism Checker**: Advanced sequence-matcher to catch code similarities across student submissions.
- **Bulk Import**: Easily import student rosters and question banks via CSV.
- **AWS Native**: Pre-configured for deployment to AWS EC2, ECS, RDS, and ElastiCache.

## Architecture

- **Frontend**: Next.js (React), TailwindCSS, Monaco Editor (Standalone Production Build)
- **Backend**: FastAPI (Python), SQLAlchemy, asyncpg
- **Database**: PostgreSQL
- **Cache / WebSocket**: Redis
- **Security Sandboxing**: Docker out-of-Docker (DooD) execution

## AWS Deployment Guide for IT Staff

### 1. Requirements
- An AWS EC2 Instance (e.g. `t3.large`) running Amazon Linux 2023 or Ubuntu 22.04.
- Docker and Docker Compose installed.

### 2. Environment Configuration
1. Clone this repository to the EC2 instance.
2. Run `cp .env.example .env`.
3. Generate a strong, random 64-character secret key and set it as `SECRET_KEY` in `.env`.
4. (Optional) Point `DATABASE_URL` and `REDIS_URL` to your AWS RDS and ElastiCache instances. By default, the `docker-compose.prod.yml` will spin up local Postgres and Redis containers for you.
5. Set `CORS_ORIGINS` to the exact subdomain the frontend will be hosted on (e.g., `https://exams.university.edu`).

### 3. Running the Stack
Run the following command from the root of the project:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 4. Sandbox Security Notes
The `docker-compose.prod.yml` explicitly mounts `/var/run/docker.sock` to the backend container. This is required because the backend dynamically spins up temporary, heavily-restricted sandbox containers to evaluate student code submissions. The sandboxes are automatically killed and destroyed after execution.

## Local Development (For Developers)
1. Navigate to `/backend`.
2. `pip install -r requirements.txt`.
3. `uvicorn app.main:app --reload`.
4. Navigate to `/frontend`.
5. `npm install` && `npm run dev`.
