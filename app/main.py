"""FastAPI 백엔드. 실행: uvicorn app.main:app --reload  →  http://localhost:8000"""
import json
import os
from collections import Counter
from datetime import date, timedelta

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import db
from .recommender import recommend
from .tagging import TAGS

app = FastAPI(title="KDT 과정 추천 API")
STATIC = os.path.join(os.path.dirname(__file__), "static")


class Profile(BaseModel):
    interests: list[str] = []
    keywords: list[str] = []
    regions: list[str] = []
    modes: list[str] = []
    start_after: str | None = None
    max_weeks: int | None = None


class Feedback(BaseModel):
    profile_id: str
    course_id: str
    round: str
    action: str  # save | dismiss | click | unsave


@app.get("/api/meta")
def meta():
    return {"tags": {k: v["label"] for k, v in TAGS.items()}}


@app.get("/api/courses")
def courses(tag: str | None = None, region: str | None = None, program: str | None = None, q: str | None = None):
    with db.connect() as con:
        rows = db.load_courses(con)
    if tag:
        rows = [r for r in rows if tag in r["tags"]]
    if region:
        rows = [r for r in rows if (r["region"] or "").startswith(region)]
    if program:
        rows = [r for r in rows if r["program"] == program]
    if q:
        rows = [r for r in rows if q.lower() in (r["title"] + r["org_name"]).lower()]
    return rows


@app.put("/api/profile/{profile_id}")
def save_profile(profile_id: str, p: Profile):
    with db.connect() as con:
        con.execute("INSERT OR REPLACE INTO profiles VALUES (?,?,?)",
                    (profile_id, p.model_dump_json(), db.now()))
    return {"ok": True}


@app.get("/api/profile/{profile_id}")
def get_profile(profile_id: str):
    with db.connect() as con:
        r = con.execute("SELECT data FROM profiles WHERE profile_id=?", (profile_id,)).fetchone()
        fb = con.execute("SELECT course_id, round, action FROM feedback WHERE profile_id=?", (profile_id,)).fetchall()
    return {"profile": json.loads(r["data"]) if r else None, "feedback": [dict(x) for x in fb]}


@app.post("/api/feedback")
def feedback(f: Feedback):
    with db.connect() as con:
        if f.action == "unsave":
            con.execute("DELETE FROM feedback WHERE profile_id=? AND course_id=? AND round=? AND action='save'",
                        (f.profile_id, f.course_id, f.round))
        else:
            con.execute("INSERT OR REPLACE INTO feedback VALUES (?,?,?,?,?)",
                        (f.profile_id, f.course_id, f.round, f.action, db.now()))
    return {"ok": True}


@app.post("/api/recommend")
def recommend_api(p: Profile, profile_id: str | None = None, k: int = 10):
    with db.connect() as con:
        rows = db.load_courses(con)
        dismissed = set()
        if profile_id:
            dismissed = {(r["course_id"], r["round"]) for r in con.execute(
                "SELECT course_id, round FROM feedback WHERE profile_id=? AND action='dismiss'", (profile_id,))}
    return recommend(rows, p.model_dump(), dismissed, k)


@app.get("/api/stats")
def stats():
    """모니터링 지표: 사업·분야별 모집 과정 수, 최근 7일 신규, 마감 임박."""
    with db.connect() as con:
        rows = db.load_courses(con)
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    tag_cnt = Counter(t for r in rows for t in r["tags"])
    near_full = sorted((r for r in rows if r["capacity"]), key=lambda r: -(r["registered"] or 0) / r["capacity"])[:5]
    return {
        "open_total": len(rows),
        "by_program": Counter(r["program"] for r in rows),
        "by_tag": {TAGS[k]["label"]: v for k, v in tag_cnt.most_common()},
        "new_7d": sum(1 for r in rows if (r["first_seen_at"] or "") >= week_ago),
        "near_full": [{"title": r["title"], "fill": round((r["registered"] or 0) / r["capacity"], 2)} for r in near_full],
    }


@app.get("/", response_class=HTMLResponse)
def index():
    # index.html은 아티팩트 데모와 공유하는 본문 조각이라 문서 골격을 여기서 씌운다.
    body = open(os.path.join(STATIC, "index.html"), encoding="utf-8").read()
    return ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            f'</head><body>{body}</body></html>')


app.mount("/static", StaticFiles(directory=STATIC), name="static")
