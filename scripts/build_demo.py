"""과정 데이터를 내장한 단일 HTML 데모(dist/demo.html)를 만든다. 서버 없이 열어 볼 수 있다.

  python scripts/build_demo.py                          # 샘플 데이터
  python scripts/build_demo.py data/courses_live.json   # 실데이터 (scripts/export_courses.py로 생성)
"""
import os
import sqlite3
import sys

root = os.path.join(os.path.dirname(__file__), "..")
src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "data", "sample_courses.json")
html = open(os.path.join(root, "app", "static", "index.html"), encoding="utf-8").read()
data = open(src, encoding="utf-8").read().replace("</", "<\\/")
# 정적 배포에서도 "언제 수집한 데이터인지" 보이도록 DB의 마지막 수집 시각을 넣는다(샘플 빌드면 비워 둠)
as_of = ""
db_path = os.path.join(root, "data", "kdt.db")
if "sample" not in os.path.basename(src) and os.path.exists(db_path):
    with sqlite3.connect(db_path) as con:
        as_of = con.execute("SELECT max(last_seen_at) FROM courses WHERE is_sample = 0").fetchone()[0] or ""
os.makedirs(os.path.join(root, "dist"), exist_ok=True)
out = os.path.join(root, "dist", "demo.html")
# index.html은 본문 조각이라 app/main.py와 같은 문서 골격을 씌운다(charset 없으면 파일로 열 때 한글이 깨짐).
page = ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        f'</head><body>{html.replace("__SAMPLE_DATA__", data).replace("__DATA_AS_OF__", as_of)}</body></html>')
open(out, "w", encoding="utf-8").write(page)
print("wrote", out, "from", os.path.relpath(src, root))
