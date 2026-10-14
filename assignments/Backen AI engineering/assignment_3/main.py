from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from database import get_db_connection, initialize_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Task API",
    description="A CRUD API using FastAPI and PostgreSQL.",
    version="1.0",
    lifespan=lifespan,
)


# Error handlers

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    message = "Task not found" if exc.status_code == 404 else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": message},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": "Invalid request body"},
    )


# Request models

class TaskCreate(BaseModel):
    title: str


class TaskUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None


# Root and health endpoints

@app.get("/")
def root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks", "/tasks/{task_id}"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# GET all tasks

@app.get("/tasks")
def get_tasks():
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM tasks ORDER BY id")
            return cursor.fetchall()


# GET one task

@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM tasks WHERE id = %s",
                (task_id,),
            )
            task = cursor.fetchone()

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


# CREATE a task

@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):
    title = task.title.strip()

    if not title:
        raise HTTPException(
            status_code=400,
            detail="Title is required and cannot be empty",
        )

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tasks (title, done)
                VALUES (%s, %s)
                RETURNING *
                """,
                (title, False),
            )
            return cursor.fetchone()


# UPDATE a task

@app.put("/tasks/{task_id}")
def update_task(task_id: int, task_update: TaskUpdate):
    if task_update.title is None and task_update.done is None:
        raise HTTPException(
            status_code=400,
            detail="At least one field must be provided",
        )

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM tasks WHERE id = %s",
                (task_id,),
            )
            existing_task = cursor.fetchone()

            if existing_task is None:
                raise HTTPException(
                    status_code=404,
                    detail="Task not found",
                )

            title = existing_task["title"]
            done = existing_task["done"]

            if task_update.title is not None:
                title = task_update.title.strip()
                if not title:
                    raise HTTPException(
                        status_code=400,
                        detail="Title cannot be empty",
                    )

            if task_update.done is not None:
                done = task_update.done

            cursor.execute(
                """
                UPDATE tasks
                SET title = %s, done = %s
                WHERE id = %s
                RETURNING *
                """,
                (title, done, task_id),
            )
            return cursor.fetchone()


# DELETE a task

@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM tasks WHERE id = %s",
                (task_id,),
            )

            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=404,
                    detail="Task not found",
                )

    return Response(status_code=204)