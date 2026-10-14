# Task Management API

## Overview

The Task Management API is a RESTful backend application built with FastAPI and PostgreSQL. It provides endpoints for creating, retrieving, updating, and deleting tasks.

The application uses Docker Compose to run the API and PostgreSQL database as containerized services. PostgreSQL stores task records persistently using a named Docker volume.

## Features

- Create new tasks.
- Retrieve all tasks.
- Retrieve an individual task by its ID.
- Update existing tasks.
- Delete tasks.
- Validate task input.
- Return appropriate HTTP status codes.
- Initialize the database table automatically.
- Seed the database with sample tasks when the table is empty.
- Persist database records using a named Docker volume.

## Technology Stack

- Python 3.12
- FastAPI
- Uvicorn
- PostgreSQL
- Psycopg
- Docker
- Docker Compose

## Architecture

The application consists of two primary services:

- **API:** A FastAPI application that exposes the task management endpoints.
- **Database:** A PostgreSQL database that stores task records.

The API communicates with PostgreSQL to execute database operations. Docker Compose manages the services, while a named volume preserves database data when containers are recreated.

## Database Structure

The application uses a table named `tasks`.

| Column | Type | Description |
|---|---|---|
| `id` | SERIAL PRIMARY KEY | Unique task identifier |
| `title` | TEXT NOT NULL | Task title |
| `done` | BOOLEAN NOT NULL DEFAULT FALSE | Task completion status |

The database initializes the table automatically and inserts sample tasks when the table contains no records.

## API Endpoints

The API is available at `http://localhost:8000` when running locally through Docker Compose.

| Method | Endpoint | Description | Success status |
|---|---|---|---|
| GET | `/` | Returns the root response | 200 |
| GET | `/health` | Checks API health | 200 |
| GET | `/tasks` | Retrieves all tasks | 200 |
| GET | `/tasks/{task_id}` | Retrieves a task by ID | 200 |
| POST | `/tasks` | Creates a task | 201 |
| PUT | `/tasks/{task_id}` | Updates an existing task | 200 |
| DELETE | `/tasks/{task_id}` | Deletes a task | 204 |

Requests for nonexistent task IDs return HTTP 404.

## Task Data Format

A task contains a title and completion status.

Example request body:

```json
{
  "title": "Complete project documentation",
  "done": false
}
```

## Configuration

The application uses an environment variable for the PostgreSQL password.

Create a local `.env` file based on `.env.example`:

```dotenv
POSTGRES_PASSWORD=change_me
```

Replace the example value with a suitable local development password.

The `.env` file is excluded from Git. The `.env.example` file documents the required configuration without containing a real password.

## Running the Application

Build and start the services:

```bash
docker compose up -d --build
```

Check the running services:

```bash
docker compose ps
```

Check the API health endpoint:

```bash
curl -i http://localhost:8000/health
```

Retrieve all tasks:

```bash
curl -i http://localhost:8000/tasks
```

Interactive API documentation is available at:

`http://localhost:8000/docs`

## Database Persistence

PostgreSQL data is stored in the named Docker volume `taskdata`.

Stop and remove the containers without deleting the volume:

```bash
docker compose down
```

Start the services again:

```bash
docker compose up -d
```

The previously stored tasks remain available because the named volume preserves the database data.

## Project Structure

```text
assignment_3/
├── docs/
│   └── postgres-tasks.png
├── .env.example
├── .gitignore
├── Dockerfile
├── compose.yaml
├── database.py
├── main.py
├── requirements.txt
└── README.md
```