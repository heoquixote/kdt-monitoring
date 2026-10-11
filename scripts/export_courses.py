"""data/kdt.db의 모집 중 실데이터 과정을 데모용 JSON으로 내보낸다.

  python scripts/export_courses.py                      # → data/courses_live.json
  python scripts/build_demo.py data/courses_live.json   # 실데이터 데모 생성
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import db  # noqa: E402
from app.collector import load_env  # noqa: E402

root = os.path.join(os.path.dirname(__file__), "..")
load_env()
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "data", "courses_live.json")
with db.connect() as con:
    rows = [r for r in db.load_courses(con) if not r["is_sample"]]
cols = db.COURSE_COLS + ["first_seen_at", "last_seen_at"]
courses = [{k: r[k] for k in cols} for r in rows]
text = json.dumps(courses, ensure_ascii=False, indent=1)
keys = [os.environ[k] for k in ("WORK24_API_KEY", "WORK24_CODE_KEY") if os.environ.get(k)]
if "authKey" in text or any(k in text for k in keys):  # 키가 섞여 나가지 않도록 확인
    sys.exit("내보낼 데이터에 인증키가 포함돼 있습니다.")
open(out, "w", encoding="utf-8").write(text)
print(f"wrote {out} ({len(courses)} courses)")
