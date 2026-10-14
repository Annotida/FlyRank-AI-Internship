import sqlite3
from contextlib import closing, asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

# Store tasks.db in the same directory as this main.py file.
DATABASE_PATH = Path(__file__).resolve().parent / "tasks.db"


def get_db_connection():
    """
    Open a connection to the SQLite database.

    SQLite automatically creates the database file if it
    does not already exist.
    """
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    """
    Create the tasks table if it does not exist.

    Insert three example tasks only when the table is empty.
    Existing task records are preserved across restarts.
    """

    with closing(get_db_connection()) as connection:

        # Create the tasks table.
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

        # Check how many tasks already exist.
        task_count = connection.execute(
            "SELECT COUNT(*) FROM tasks"
        ).fetchone()[0]

        # Seed the database only if the table is empty.
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
# FASTAPI APPLICATION LIFECYCLE
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize the database when the application starts.
    """

    initialize_database()

    yield


app = FastAPI(
    title="Task API",
    description="A CRUD API using FastAPI and SQLite.",
    version="1.0",
    lifespan=lifespan,
)


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
):
    """
    Return consistent JSON error responses.

    Unknown tasks return:
        {"error": "Task not found"}
    """

    if exc.status_code == 404:
        message = "Task not found"
    else:
        message = str(exc.detail)

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": message},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    """
    Return HTTP 400 for invalid request bodies.

    This includes missing required fields and invalid input.
    """

    return JSONResponse(
        status_code=400,
        content={
            "error": "Invalid request body"
        },
    )


# ============================================================
# PYDANTIC MODELS
# ============================================================

class TaskCreate(BaseModel):
    """
    Fields required when creating a task.
    """

    title: str


class TaskUpdate(BaseModel):
    """
    Fields that may be updated on an existing task.

    At least one field must be provided.
    """

    title: str | None = None
    done: bool | None = None


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/", summary="Get API information")
def root():
    """
    Return basic information about the API.
    """

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
    """
    Check whether the API is running.
    """

    return {"status": "ok"}


# ============================================================
# GET ALL TASKS
# ============================================================

@app.get("/tasks", summary="List all tasks")
def get_tasks():
    """
    Retrieve all tasks from SQLite.
    """

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
    """
    Retrieve one task using its ID.

    Return 404 if the task does not exist.
    """

    with closing(get_db_connection()) as connection:

        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Task not found",
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
    """
    Insert a new task into SQLite.

    The database generates the task ID automatically.
    New tasks start with done = False.
    """

    title = task.title.strip()

    # Validate that the title is not empty.
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

        # Retrieve the newly created task.
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
def update_task(
    task_id: int,
    task_update: TaskUpdate,
):
    """
    Update an existing task in SQLite.

    At least one field must be provided.
    Unknown task IDs return 404.
    Invalid values return 400.
    """

    # Ensure that at least one field was supplied.
    if (
        task_update.title is None
        and task_update.done is None
    ):
        raise HTTPException(
            status_code=400,
            detail="At least one field must be provided",
        )

    with closing(get_db_connection()) as connection:

        # Find the existing task.
        existing_task = connection.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

        if existing_task is None:
            raise HTTPException(
                status_code=404,
                detail="Task not found",
            )

        # Keep existing values unless replacements are supplied.
        title = existing_task["title"]
        done = bool(existing_task["done"])

        # Validate and update the title if provided.
        if task_update.title is not None:

            title = task_update.title.strip()

            if not title:
                raise HTTPException(
                    status_code=400,
                    detail="Title cannot be empty",
                )

        # Update the completion status if provided.
        if task_update.done is not None:
            done = task_update.done

        # Save the updated task.
        connection.execute(
            """
            UPDATE tasks
            SET title = ?, done = ?
            WHERE id = ?
            """,
            (title, int(done), task_id),
        )

        connection.commit()

        # Retrieve the updated record.
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
    """
    Delete an existing task from SQLite.

    Return 204 with an empty response body on success.
    Return 404 if the task does not exist.
    """

    with closing(get_db_connection()) as connection:

        cursor = connection.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,),
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Task not found",
            )

        connection.commit()

    return Response(status_code=204)