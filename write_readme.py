import os

readme_content = """# ExamSentinel 🛡️

**ExamSentinel** is an advanced, AI-powered online examination platform designed for secure, scalable, and human-verified integrity monitoring. It leverages an intelligent risk engine to monitor candidate sessions in real-time, escalating suspicious activities to a human-in-the-loop review queue.

## 🌟 Key Features

* **Role-Based Access Control**: Tailored dashboards for Candidates, Proctors, Reviewers, and Administrators.
* **AI Risk Engine**: Real-time evaluation of webcam, browser, and network events to calculate a dynamic risk score.
* **Human-in-the-Loop Review**: Suspicious sessions are escalated to the Review Queue for human adjudication.
* **Live Dashboard**: Real-time monitoring of active exam sessions via WebSockets.
* **Secure Architecture**: JWT-based authentication, async PostgreSQL operations, and Dockerized deployments.
* **Dark Mode Support**: Beautiful, responsive UI with full light/dark mode capabilities.

## 🛠️ Tech Stack

**Frontend:**
* [Next.js](https://nextjs.org/) (React)
* Tailwind CSS
* Lucide Icons

**Backend:**
* [FastAPI](https://fastapi.tiangolo.com/) (Python)
* SQLAlchemy 2.0 (Asyncpg) + Alembic
* Pydantic (Data validation)

**Infrastructure:**
* PostgreSQL (Database)
* Redis (WebSocket pub/sub & caching)
* Docker & Docker Compose
* Render (Production Hosting)

## 🚀 Getting Started (Local Development)

### Prerequisites
* Docker Desktop (with WSL2 enabled on Windows)
* Node.js 18+
* Python 3.10+

### Windows Quick Start
We have provided a unified startup script for Windows users that handles launching the databases and the backend automatically.

1. Clone the repository.
2. Double-click or run start.cmd from the root directory.
   * *This will spin up PostgreSQL and Redis in Docker, run Alembic database migrations, seed the database with demo accounts, and launch the FastAPI backend.*
3. In a separate terminal, start the frontend:
   `ash
   cd frontend
   npm install
   npm run dev
   `
4. Access the web interface at http://localhost:3000.

## 🔑 Demo Accounts

The database automatically seeds with the following test accounts on startup. 
**Password for all accounts:** DemoPass123!

| Role | Email |
| :--- | :--- |
| **Admin** | dmin@sentinel.edu |
| **Proctor** | proctor@sentinel.edu |
| **Reviewer** | eviewer@sentinel.edu |
| **Candidate** | candidate@sentinel.edu |

## ☁️ Deployment

ExamSentinel is fully configured for automated deployment on [Render](https://render.com/). 

The included ender.yaml Blueprint automatically provisions:
* A Managed PostgreSQL Database
* A Managed Redis Instance
* The FastAPI Backend (Docker)
* The Next.js Frontend (Docker Standalone)

Simply connect your GitHub repository to Render and deploy using the Blueprint.
"""

with open("README.md", "w", encoding="utf-8") as f:
    f.write(readme_content)
