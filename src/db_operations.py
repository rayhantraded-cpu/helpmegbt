import datetime
import json
from pathlib import Path

from database import connect_db, get_all_state, get_state, init_db, set_state


ARABIC_TO_FREQ = {
    "يومية": "DAILY",
    "أسبوعية": "WEEKLY",
    "شهرية": "MONTHLY",
    "DAILY": "DAILY",
    "WEEKLY": "WEEKLY",
    "MONTHLY": "MONTHLY",
}
FREQ_TO_ARABIC = {v: k for k, v in ARABIC_TO_FREQ.items() if v in {"DAILY", "WEEKLY", "MONTHLY"}}

CATEGORY_PREFIXES = {
    "🕊️ ": "مهام روحية",
    "💪 ": "مهام بدنية وصحية",
    "🚀 ": "مهام تطويرية",
    "📚 ": "مهام تعليمية",
    "🤝 ": "مهام اجتماعية",
    "💰 ": "مهام اقتصادية",
}


def normalize_category(value: str) -> str:
    value = (value or "").strip()
    for prefix, clean in CATEGORY_PREFIXES.items():
        if value.startswith(prefix):
            return clean
    return value


def period_identifier(freq_type: str, when: datetime.date | None = None) -> str:
    when = when or datetime.date.today()
    freq = ARABIC_TO_FREQ.get(freq_type, freq_type)
    if freq == "WEEKLY":
        iso = when.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    if freq == "MONTHLY":
        return when.strftime("%Y-%m")
    return when.isoformat()


def _category_id(conn, category_name: str) -> int:
    row = conn.execute(
        "SELECT id FROM categories WHERE name = ?", (normalize_category(category_name),)
    ).fetchone()
    if row:
        return row["id"]
    row = conn.execute(
        "SELECT id FROM categories ORDER BY id LIMIT 1"
    ).fetchone()
    return row["id"]


def _list_id(conn, freq_type: str) -> int:
    freq = ARABIC_TO_FREQ.get(freq_type, "DAILY")
    row = conn.execute(
        "SELECT id FROM task_lists WHERE frequency_type = ?", (freq,)
    ).fetchone()
    if row:
        return row["id"]
    conn.execute(
        "INSERT INTO task_lists(title, frequency_type) VALUES (?, ?)",
        (f"المهام {FREQ_TO_ARABIC[freq]}", freq),
    )
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def get_categories():
    init_db()
    with connect_db() as conn:
        return [dict(row) for row in conn.execute(
            "SELECT id, name, icon_name, color_code FROM categories ORDER BY id"
        ).fetchall()]


def get_all_task_lists():
    init_db()
    with connect_db() as conn:
        return [dict(row) for row in conn.execute(
            "SELECT * FROM task_lists ORDER BY id"
        ).fetchall()]


def get_all_tasks():
    init_db()
    with connect_db() as conn:
        rows = conn.execute(
            """
            SELECT t.*, c.name AS category_name, c.icon_name, c.color_code
            FROM tasks t
            JOIN categories c ON c.id = t.category_id
            ORDER BY t.created_at DESC, t.id DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_tasks_for_period(freq_type: str, category_name: str = "", when=None):
    init_db()
    freq = ARABIC_TO_FREQ.get(freq_type, "DAILY")
    period_id = period_identifier(freq, when)
    params = [freq]
    category_clause = ""
    if category_name:
        category_clause = " AND c.name = ?"
        params.append(normalize_category(category_name))

    with connect_db() as conn:
        rows = conn.execute(
            f"""
            SELECT
                t.id, t.list_id, t.category_id, t.title, t.resource_url,
                t.frequency_type, t.target_count, t.advice_text, t.created_at,
                c.name AS category_name, c.icon_name, c.color_code,
                COALESCE(l.completed_count, 0) AS completed_count,
                COALESCE(l.is_completed, 0) AS is_completed
            FROM tasks t
            JOIN categories c ON c.id = t.category_id
            LEFT JOIN task_logs l
              ON l.task_id = t.id AND l.period_identifier = ?
            WHERE t.frequency_type = ? {category_clause}
            ORDER BY t.created_at DESC, t.id DESC
            """,
            [period_id, *params],
        ).fetchall()
        return [dict(row) for row in rows]


def add_task(
    title: str,
    category_name: str,
    frequency_type: str,
    target_count: int = 1,
    resource_url: str = "",
    advice_text: str = "",
):
    init_db()
    freq = ARABIC_TO_FREQ.get(frequency_type, "DAILY")
    with connect_db() as conn:
        category_id = _category_id(conn, category_name)
        list_id = _list_id(conn, freq)
        cur = conn.execute(
            """
            INSERT INTO tasks(
                list_id, category_id, title, resource_url,
                frequency_type, target_count, advice_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                list_id,
                category_id,
                title.strip(),
                resource_url.strip(),
                freq,
                max(1, int(target_count)),
                advice_text.strip(),
            ),
        )
        task_id = cur.lastrowid
        row = conn.execute(
            """
            SELECT t.*, c.name AS category_name, c.icon_name, c.color_code
            FROM tasks t JOIN categories c ON c.id=t.category_id
            WHERE t.id = ?
            """,
            (task_id,),
        ).fetchone()
        return dict(row)


def delete_task(task_id: int):
    init_db()
    with connect_db() as conn:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))


def set_task_completion(task_id: int, completed: bool, freq_type: str, when=None):
    init_db()
    period_id = period_identifier(freq_type, when)
    with connect_db() as conn:
        if completed:
            conn.execute(
                """
                INSERT INTO task_logs(
                    task_id, period_identifier, completed_count,
                    is_completed, last_updated
                ) VALUES (?, ?, 1, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(task_id, period_identifier)
                DO UPDATE SET
                    completed_count = MAX(task_logs.completed_count, 1),
                    is_completed = 1,
                    last_updated = CURRENT_TIMESTAMP
                """,
                (task_id, period_id),
            )
        else:
            conn.execute(
                """
                INSERT INTO task_logs(
                    task_id, period_identifier, completed_count,
                    is_completed, last_updated
                ) VALUES (?, ?, 0, 0, CURRENT_TIMESTAMP)
                ON CONFLICT(task_id, period_identifier)
                DO UPDATE SET
                    completed_count = 0,
                    is_completed = 0,
                    last_updated = CURRENT_TIMESTAMP
                """,
                (task_id, period_id),
            )


def get_completion(task_id: int, freq_type: str, when=None) -> bool:
    init_db()
    period_id = period_identifier(freq_type, when)
    with connect_db() as conn:
        row = conn.execute(
            """
            SELECT is_completed FROM task_logs
            WHERE task_id = ? AND period_identifier = ?
            """,
            (task_id, period_id),
        ).fetchone()
        return bool(row["is_completed"]) if row else False


def update_stats_after_completion(completed: bool):
    init_db()
    points = int(get_state("points", "0"))
    streak = int(get_state("streak", "0"))
    last_date = get_state("last_completion_date", "")
    today = datetime.date.today()

    if completed:
        points += 10
        if last_date != today.isoformat():
            if last_date:
                try:
                    previous = datetime.date.fromisoformat(last_date)
                    if (today - previous).days == 1:
                        streak = max(1, streak) + 1
                    elif (today - previous).days > 1:
                        streak = 1
                except ValueError:
                    streak = 1
            else:
                streak = max(1, streak)
            set_state("last_completion_date", today.isoformat())
    else:
        points = max(0, points - 10)

    set_state("points", points)
    set_state("streak", streak)
    return {"points": points, "streak": streak}


def get_stats():
    state = get_all_state()
    return {
        "points": int(state.get("points", "0")),
        "streak": int(state.get("streak", "0")),
    }


def count_period_tasks(freq_type: str, when=None):
    tasks = get_tasks_for_period(freq_type, when=when)
    total = len(tasks)
    completed = sum(1 for task in tasks if task["is_completed"])
    return total, completed


def import_legacy_json(json_path: str | Path) -> int:
    """
    Import the old tasks_data.json format once.
    The import is intentionally conservative and does not delete the legacy file.
    """
    path = Path(json_path)
    if not path.exists():
        return 0

    init_db()
    with connect_db() as conn:
        marker = conn.execute(
            "SELECT value FROM app_state WHERE key = 'legacy_json_imported'"
        ).fetchone()
        if marker and marker["value"] == "1":
            return 0

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return 0

    tasks = payload.get("tasks", []) if isinstance(payload, dict) else []
    imported = 0
    for task in tasks:
        try:
            created = add_task(
                title=task.get("title", "مهمة بدون عنوان"),
                category_name=task.get("category", "مهام تطويرية"),
                frequency_type=task.get("period", "يومية"),
                target_count=task.get("count", 1),
                resource_url=task.get("link", ""),
                advice_text="",
            )
            if task.get("completed"):
                set_task_completion(
                    created["id"], True, created["frequency_type"]
                )
            imported += 1
        except Exception:
            continue

    if isinstance(payload, dict):
        if "points" in payload:
            set_state("points", payload.get("points", 0))
        if "streak" in payload:
            set_state("streak", payload.get("streak", 0))
        if "last_completion_date" in payload:
            set_state(
                "last_completion_date",
                payload.get("last_completion_date") or "",
            )

    set_state("legacy_json_imported", "1")
    return imported
