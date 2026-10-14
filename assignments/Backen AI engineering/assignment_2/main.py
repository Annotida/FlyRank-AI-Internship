import sqlite3

from contextlib import closing
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DATABASE_PATH = Path(__file__).resolve().parent / "tasks.db"


def get_db_connection():
    """
    Open a connection to the SQLite database.

    The database file is created automatically if it does not exist.
    """
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    """
    Create the tasks table and insert three example tasks
    only when the table is empty.
    """

    with closing(get_db_connection()) as connection:

        # Create the tasks table if it does not exist.
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0
                    CHECK (done IN (0, 1))
            )
            """
        )

        # Check whether the table already contains tasks.
        task_count = connection.execute(
            "SELECT COUNT(*) FROM tasks"
        ).fetchone()[0]

        # Insert the example tasks only on the first run
        # or when the table is empty.
        if task_count == 0:

            example_tasks = [
                ("Learn FastAPI", 0),
                ("Build CRUD API", 0),
                ("Test with Swagger", 1),
            ]

            connection.executemany(
                """
                INSERT INTO tasks (title, done)
                VALUES (?, ?)
                """,
                example_tasks,
            )

        connection.commit()


# ============================================================
# DATABASE HELPER FUNCTIONS
# ============================================================

def convert_task(row):
    """
    Convert a SQLite row into a Python dictionary.

    SQLite stores Boolean values as integers:
    0 = False
    1 = True
    """

    if row is None:
        return None

    return {
        "id": row["id"],
        "title": row["title"],
        "done": bool(row["done"]),
    }


# ============================================================
# FASTAPI APPLICATION
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialise the database when the application starts.
    """

    initialize_database()

    yield


app = FastAPI(lifespan=lifespan)


# ============================================================
# PYDANTIC MODELS
# ============================================================

class TaskCreate(BaseModel):
    title: str


class TaskUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/", summary="Get API information")
def root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": [
            "/tasks",
            "/tasks/{task_id}",
        ],
    }


# ============================================================
# HEALTH ENDPOINT
# ============================================================

@app.get("/health", summary="Check API health")
def health():
    return {"status": "ok"}


# ============================================================
# GET ALL TASKS
# ============================================================

@app.get("/tasks", summary="List all tasks")
def get_tasks():

    with closing(get_db_connection()) as connection:

        rows = connection.execute(
            "SELECT * FROM tasks ORDER BY id"
        ).fetchall()

        return [
            convert_task(row)
            for row in rows
        ]


# ============================================================
# GET A TASK BY ID
# ============================================================

@app.get("/tasks/{task_id}", summary="Get a task by ID")
def get_task(task_id: int):

    with closing(get_db_connection()) as connection:

        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found",
            )

        return convert_task(row)


# ============================================================
# CREATE A TASK
# ============================================================

@app.post(
    "/tasks",
    status_code=201,
    summary="Create a new task",
)
def create_task(task: TaskCreate):

    title = task.title.strip()

    # Validate the task title.
    if not title:
        raise HTTPException(
            status_code=400,
            detail="Title is required and cannot be empty",
        )

    with closing(get_db_connection()) as connection:

        cursor = connection.execute(
            """
            INSERT INTO tasks (title, done)
            VALUES (?, ?)
            """,
            (title, 0),
        )

        new_id = cursor.lastrowid

        connection.commit()

        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (new_id,),
        ).fetchone()

        return convert_task(row)


# ============================================================
# UPDATE A TASK
# ============================================================

@app.put(
    "/tasks/{task_id}",
    summary="Update a task",
)
def update_task(task_id: int, task_update: TaskUpdate):

    # Preserve the original validation rule.
    if task_update.title is None and task_update.done is None:
        raise HTTPException(
            status_code=400,
            detail="At least one field must be provided",
        )

    with closing(get_db_connection()) as connection:

        # Check whether the task exists.
        existing_task = connection.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

        if existing_task is None:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found",
            )

        # Keep the existing values unless new values are supplied.
        title = existing_task["title"]
        done = bool(existing_task["done"])

        # Validate and update the title when supplied.
        if task_update.title is not None:

            title = task_update.title.strip()

            if not title:
                raise HTTPException(
                    status_code=400,
                    detail="Title cannot be empty",
                )

        # Update the completion status when supplied.
        if task_update.done is not None:
            done = task_update.done

        # Save the changes to SQLite.
        connection.execute(
            """
            UPDATE tasks
            SET title = ?, done = ?
            WHERE id = ?
            """,
            (title, int(done), task_id),
        )

        connection.commit()

        # Return the updated task.
        updated_task = connection.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

        return convert_task(updated_task)


# ============================================================
# DELETE A TASK
# ============================================================

@app.delete(
    "/tasks/{task_id}",
    status_code=204,
    summary="Delete a task",
)
def delete_task(task_id: int):

    with closing(get_db_connection()) as connection:

        # Delete only if the task exists.
        cursor = connection.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,),
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found",
            )

        connection.commit()

    # FastAPI returns an empty response with status 204.
    return None