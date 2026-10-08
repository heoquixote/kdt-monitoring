"""과정 데이터를 내장한 단일 HTML 데모(dist/demo.html)를 만든다. 서버 없이 열어 볼 수 있다.

  python scripts/build_demo.py                          # 샘플 데이터
  python scripts/build_demo.py data/courses_live.json   # 실데이터 (scripts/export_courses.py로 생성)
"""
import os
import sys

root = os.path.join(os.path.dirname(__file__), "..")
src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "data", "sample_courses.json")
html = open(os.path.join(root, "app", "static", "index.html"), encoding="utf-8").read()
data = open(src, encoding="utf-8").read().replace("</", "<\\/")
os.makedirs(os.path.join(root, "dist"), exist_ok=True)
out = os.path.join(root, "dist", "demo.html")
# index.html은 본문 조각이라 app/main.py와 같은 문서 골격을 씌운다(charset 없으면 파일로 열 때 한글이 깨짐).
page = ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        f'</head><body>{html.replace("__SAMPLE_DATA__", data)}</body></html>')
open(out, "w", encoding="utf-8").write(page)
print("wrote", out, "from", os.path.relpath(src, root))
