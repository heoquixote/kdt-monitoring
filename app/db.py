import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = os.environ.get("KDT_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "kdt.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS courses (
  course_id TEXT NOT NULL, round TEXT NOT NULL,
  program TEXT, title TEXT, org_name TEXT, inst_id TEXT, ncs_cd TEXT,
  region TEXT, address TEXT, mode TEXT,
  start_date TEXT, end_date TEXT, hours INTEGER,
  cost INTEGER, real_cost INTEGER, capacity INTEGER, registered INTEGER,
  empl_rate3 REAL, empl_rate6 REAL, empl_source TEXT, satisfaction REAL, grade TEXT,
  tags TEXT, link TEXT, status TEXT, is_sample INTEGER DEFAULT 0,
  first_seen_at TEXT, last_seen_at TEXT,
  PRIMARY KEY (course_id, round)
);
CREATE INDEX IF NOT EXISTS idx_courses_start ON courses(start_date);
CREATE TABLE IF NOT EXISTS course_snapshots (
  course_id TEXT, round TEXT, collected_at TEXT,
  registered INTEGER, capacity INTEGER, status TEXT,
  PRIMARY KEY (course_id, round, collected_at)
);
CREATE TABLE IF NOT EXISTS course_history (   -- 훈련과정 일정 API(310L03) 응답 캐시. 과정 ID 단위
  course_id TEXT PRIMARY KEY, fetched_at TEXT, body TEXT
);
CREATE TABLE IF NOT EXISTS profiles (
  profile_id TEXT PRIMARY KEY, data TEXT NOT NULL, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS feedback (
  profile_id TEXT, course_id TEXT, round TEXT, action TEXT, created_at TEXT,
  PRIMARY KEY (profile_id, course_id, round, action)
);
"""

COURSE_COLS = ["course_id", "round", "program", "title", "org_name", "inst_id", "ncs_cd", "region", "address",
               "mode", "start_date", "end_date", "hours", "cost", "real_cost", "capacity", "registered",
               "empl_rate3", "empl_rate6", "empl_source", "satisfaction", "grade", "tags", "link", "status", "is_sample"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect(path: str | None = None):
    path = path or DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    if "empl_source" not in {r[1] for r in con.execute("PRAGMA table_info(courses)")}:  # 이전 스키마 DB 마이그레이션
        con.execute("ALTER TABLE courses ADD COLUMN empl_source TEXT")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def upsert_courses(con, courses: list[dict]) -> dict:
    """현재 상태는 upsert, 같은 날 이력은 snapshot에 1건씩 append."""
    ts = now()
    day = ts[:10]
    new = 0
    for c in courses:
        row = {k: c.get(k) for k in COURSE_COLS}
        row["tags"] = json.dumps(row["tags"] or [], ensure_ascii=False)
        exists = con.execute("SELECT 1 FROM courses WHERE course_id=? AND round=?",
                             (row["course_id"], row["round"])).fetchone()
        new += exists is None
        cols = ",".join(COURSE_COLS)
        qs = ",".join("?" * len(COURSE_COLS))
        updates = ",".join(f"{k}=excluded.{k}" for k in COURSE_COLS[2:])
        con.execute(
            f"INSERT INTO courses ({cols},first_seen_at,last_seen_at) VALUES ({qs},?,?) "
            f"ON CONFLICT(course_id,round) DO UPDATE SET {updates}, last_seen_at=excluded.last_seen_at",
            [row[k] for k in COURSE_COLS] + [ts, ts])
        con.execute("INSERT OR REPLACE INTO course_snapshots VALUES (?,?,?,?,?,?)",
                    (row["course_id"], row["round"], day, row["registered"], row["capacity"], row["status"]))
    return {"total": len(courses), "new": new}


def load_courses(con, open_only: bool = True) -> list[dict]:
    q = "SELECT * FROM courses"
    if open_only:
        # 마지막 수집에서 목록에 나온 과정 중 아직 개강 전인 것만. 개강·마감으로 목록에서 빠진 과정은
        # courses에 행이 남아 있으므로(이력용) 여기서 걸러야 화면에 지난 과정이 섞이지 않는다.
        q += (" WHERE start_date >= date('now')"
              " AND substr(last_seen_at, 1, 10) = (SELECT max(substr(last_seen_at, 1, 10)) FROM courses)")
    rows = [dict(r) for r in con.execute(q + " ORDER BY start_date")]
    for r in rows:
        r["tags"] = json.loads(r["tags"] or "[]")
    return rows
