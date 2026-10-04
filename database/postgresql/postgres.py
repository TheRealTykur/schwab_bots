import os

import psycopg2
from psycopg2.extensions import connection


def get_connection() -> connection:
    """
    Create and return a PostgreSQL database connection.

    Database credentials are read from environment variables:
        DB_NAME
        DB_USER
        DB_PASSWORD

    Optional:
        DB_HOST (default: localhost)
        DB_PORT (default: 5432)
    """
    return psycopg2.connect(
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
    )
