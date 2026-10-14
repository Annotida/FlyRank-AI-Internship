import os
import time

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:dev@localhost:5432/tasks",
)


def get_db_connection():
    """Connect to PostgreSQL and return rows as dictionaries."""
    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
        connect_timeout=5,
    )


def initialize_database():
    """Create the tasks table and seed it only when empty."""

    # Wait for PostgreSQL to become available.
    for attempt in range(10):
        try:
            with get_db_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS tasks (
                            id SERIAL PRIMARY KEY,
                            title TEXT NOT NULL,
                            done BOOLEAN NOT NULL DEFAULT FALSE
                        )
                        """
                    )

                    cursor.execute("SELECT COUNT(*) FROM tasks")
                    task_count = cursor.fetchone()["count"]

                    if task_count == 0:
                        cursor.executemany(
                            """
                            INSERT INTO tasks (title, done)
                            VALUES (%s, %s)
                            """,
                            [
                                ("Learn FastAPI", False),
                                ("Build CRUD API", False),
                                ("Test with Swagger", True),
                            ],
                        )

            return

        except psycopg.OperationalError:
            if attempt == 9:
                raise

            time.sleep(2)