import os
import sqlite3
from pathlib import Path

APP_DIR_NAME = "personal_productivity_app"
DB_FILE_NAME = "personal_assistant.db"


def get_storage_path() -> Path:
    base_dir = os.environ.get("FLET_APP_STORAGE_DATA")
    if base_dir:
        path = Path(base_dir)
    else:
        path = Path.home() / f".{APP_DIR_NAME}"
    path.mkdir(parents=True, exist_ok=True)
    return path


DB_NAME = str(get_storage_path() / DB_FILE_NAME)


def connect_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    with connect_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                icon_name TEXT NOT NULL DEFAULT 'category',
                color_code TEXT NOT NULL DEFAULT '#607D8B'
            );

            CREATE TABLE IF NOT EXISTS task_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                frequency_type TEXT NOT NULL
                    CHECK(frequency_type IN ('DAILY','WEEKLY','MONTHLY')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                list_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                resource_url TEXT DEFAULT '',
                frequency_type TEXT NOT NULL
                    CHECK(frequency_type IN ('DAILY','WEEKLY','MONTHLY')),
                target_count INTEGER NOT NULL DEFAULT 1,
                advice_text TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(list_id) REFERENCES task_lists(id) ON DELETE CASCADE,
                FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS task_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                period_identifier TEXT NOT NULL,
                completed_count INTEGER NOT NULL DEFAULT 0,
                is_completed INTEGER NOT NULL DEFAULT 0,
                last_updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(task_id, period_identifier),
                FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_period
                ON tasks(frequency_type);

            CREATE INDEX IF NOT EXISTS idx_tasks_category
                ON tasks(category_id);

            CREATE INDEX IF NOT EXISTS idx_logs_period
                ON task_logs(period_identifier);
            """
        )

        categories = [
            ("مهام روحية", "auto_awesome", "#7E57C2"),
            ("مهام بدنية وصحية", "fitness_center", "#43A047"),
            ("مهام تطويرية", "rocket_launch", "#1E88E5"),
            ("مهام تعليمية", "menu_book", "#FB8C00"),
            ("مهام اجتماعية", "groups", "#00897B"),
            ("مهام اقتصادية", "payments", "#F9A825"),
        ]
        conn.executemany(
            """
            INSERT OR IGNORE INTO categories(name, icon_name, color_code)
            VALUES (?, ?, ?)
            """,
            categories,
        )

        lists = [
            ("المهام اليومية", "DAILY"),
            ("المهام الأسبوعية", "WEEKLY"),
            ("المهام الشهرية", "MONTHLY"),
        ]
        for title, freq in lists:
            conn.execute(
                """
                INSERT INTO task_lists(title, frequency_type)
                SELECT ?, ?
                WHERE NOT EXISTS (
                    SELECT 1 FROM task_lists WHERE frequency_type = ?
                )
                """,
                (title, freq, freq),
            )

        defaults = {
            "points": "0",
            "streak": "0",
            "last_completion_date": "",
            "theme_mode": "light",
            "version": "2",
        }
        for key, value in defaults.items():
            conn.execute(
                "INSERT OR IGNORE INTO app_state(key, value) VALUES (?, ?)",
                (key, value),
            )


def get_state(key: str, default: str = "") -> str:
    with connect_db() as conn:
        row = conn.execute(
            "SELECT value FROM app_state WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default


def set_state(key: str, value) -> None:
    with connect_db() as conn:
        conn.execute(
            """
            INSERT INTO app_state(key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, str(value)),
        )


def get_all_state() -> dict:
    with connect_db() as conn:
        rows = conn.execute("SELECT key, value FROM app_state").fetchall()
        return {row["key"]: row["value"] for row in rows}


def export_database(destination: str) -> None:
    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    source = connect_db()
    try:
        target = sqlite3.connect(str(destination_path))
        with target:
            source.backup(target)
        target.close()
    finally:
        source.close()
