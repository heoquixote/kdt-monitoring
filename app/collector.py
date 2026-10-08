"""고용24 Open API(국민내일배움카드 훈련과정 목록)에서 KDT 과정을 수집해 DB에 저장한다.

사용:
  python -m app.collector                # .env의 WORK24_API_KEY로 실수집
  python -m app.collector --sample       # 샘플 데이터 적재 (키 발급 전)
  python -m app.collector --dump raw/    # 원본 응답도 저장 (필드 검증용)
  python -m app.collector --codes        # 훈련지역 코드표(data/codes_area.json) 갱신, WORK24_CODE_KEY 사용

응답 필드명은 2026-10-08 실호출(returnType=JSON)로 검증함. 목록 키 srchList, 총건수 scn_cnt.
stdgScor "0"·eiEmplRate* ""는 값 없음(신규·미집계)으로 보고 None 처리.

KDT(C0104)는 목록 응답에 취업률이 비어 있다. 과정 일정 API(310L03)를 srchTrprId만으로 부르면 과거 회차별
취업률(eiEmplRate3/6, 수료인원 finiCnt)이 오므로, 집계가 끝난 회차를 수료인원 가중평균해 채우고 empl_source에
출처를 남긴다. 응답은 course_history에 과정 ID 단위로 캐시해 HISTORY_TTL_DAYS 안에는 다시 부르지 않는다.
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import date, timedelta

import httpx

from . import codes, db
from .tagging import derive_tags

BASE = "https://www.work24.go.kr/cm/openApi/call/hr/callOpenApiSvcInfo310L01.do"
PROGRAMS = {"C0104": "K-디지털 트레이닝", "C0105": "K-디지털 기초역량훈련"}
# 훈련방법(공통코드 319L01 srchType=10). 목록 응답에 방법 필드가 없어 srchTraGbn으로 나눠 조회한다.
# 2026-10-08 기준 C0104는 전부 M1001, C0105는 전부 M1005였다. 나머지는 혹시 생길 경우 대비(빈 조회 1회씩).
METHODS = {"M1001": "집체", "M1005": "원격", "M1010": "혼합", "M1015": "비대면실시간"}
PAGE_SIZE = 100
HISTORY_URL = "https://www.work24.go.kr/cm/openApi/call/hr/callOpenApiSvcInfo310L03.do"
HISTORY_TTL_DAYS = 30      # 새 회차 취업률이 쌓이는 속도를 고려한 재조회 주기
MAX_HISTORY_CALLS = 300    # 1회 실행당 일정 API 호출 상한 (일 1,000회 한도 보호)
SAMPLE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sample_courses.json")


def load_env():
    path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            m = re.match(r"^([A-Z0-9_]+)=(.*)$", line.strip())
            if m:
                os.environ.setdefault(m[1], m[2])


def _num(v, cast=int):
    try:
        return cast(str(v).replace(",", "")) if v not in (None, "", "-") else None
    except ValueError:
        return None


def _date(v):
    v = str(v or "").replace("-", "")
    return f"{v[:4]}-{v[4:6]}-{v[6:8]}" if len(v) >= 8 else None


def normalize(item: dict, program: str, mode: str | None = None) -> dict:
    """API 1건 → courses 스키마. mode는 srchTraGbn 조회 결과, 없으면 과정명으로 추정."""
    title = (item.get("title") or "").strip()
    address = (item.get("address") or "").strip()
    mode = mode or ("원격" if "원격" in title or "온라인" in title or "원격" in address else "집체")
    remote = mode in ("원격", "비대면실시간")
    return {
        "course_id": item.get("trprId"),
        "round": str(item.get("trprDegr") or "1"),
        "program": program,
        "title": title,
        "org_name": (item.get("subTitle") or "").strip(),
        "inst_id": item.get("trainstCstId") or item.get("instCd"),
        "ncs_cd": item.get("ncsCd"),
        # address는 기관 주소라 훈련장소와 다를 수 있어 훈련지역 코드를 우선한다
        "region": "원격" if remote else codes.region_name(item.get("trngAreaCd")) or " ".join(address.split()[:2]),
        "address": address,
        "mode": mode,
        "start_date": _date(item.get("traStartDate")),
        "end_date": _date(item.get("traEndDate")),
        "hours": None,
        "cost": _num(item.get("courseMan")),
        "real_cost": _num(item.get("realMan")),
        "capacity": _num(item.get("yardMan")),
        "registered": _num(item.get("regCourseMan")),
        "empl_rate3": _num(item.get("eiEmplRate3"), float),
        "empl_rate6": _num(item.get("eiEmplRate6"), float),
        "satisfaction": _num(item.get("stdgScor"), float) or None,  # "0" = 미집계
        "grade": item.get("grade"),
        "tags": derive_tags(title, item.get("ncsCd")),
        "link": item.get("titleLink"),
        "status": "모집중",
        "is_sample": 0,
    }


def fetch_program(client: httpx.Client, key: str, program: str, method: str, dump_dir: str | None) -> list[dict]:
    today = date.today()
    out, page = [], 1
    while True:
        params = {
            "authKey": key, "returnType": "JSON", "outType": "1",
            "pageNum": page, "pageSize": PAGE_SIZE,
            "srchTraStDt": today.strftime("%Y%m%d"),
            "srchTraEndDt": (today + timedelta(days=180)).strftime("%Y%m%d"),
            "sort": "ASC", "sortCol": "2", "crseTracseSe": program, "srchTraGbn": method,
        }
        r = client.get(BASE, params=params, timeout=30)
        r.raise_for_status()
        body = r.json()
        if dump_dir:
            os.makedirs(dump_dir, exist_ok=True)
            with open(os.path.join(dump_dir, f"{program}_{method}_p{page}.json"), "w", encoding="utf-8") as f:
                json.dump(body, f, ensure_ascii=False, indent=1)
        items = body.get("srchList") or []
        if isinstance(items, dict):  # 1건일 때 객체로 오는 경우 방어
            items = [items]
        # crseTracseSe=C0104 조회에 국가기간전략산업직종(C0054)·과정평가형(C0055C) 등이 섞여 오므로 실제 유형으로 거른다
        out += [normalize(i, program, METHODS[method]) for i in items if i.get("trainTargetCd", program) == program]
        total = _num(body.get("scn_cnt")) or 0
        if page * PAGE_SIZE >= total or not items:
            return out
        page += 1
        time.sleep(0.5)  # 일 1,000회 한도·서버 부하 고려


def summarize_history(rounds: list[dict]) -> dict:
    """310L03 회차 목록 → 수료인원 가중평균 취업률. 'A'·'B'·'D' 같은 문자값(미집계 등)은 제외."""
    out = {}
    for k in ("3", "6"):
        vals = [(_num(r.get(f"eiEmplRate{k}"), float), _num(r.get("finiCnt")) or 0) for r in rounds]
        vals = [(x, n) for x, n in vals if x is not None and n > 0]
        if vals:
            n = sum(n for _, n in vals)
            out[k] = (round(sum(x * n for x, n in vals) / n, 1), len(vals), n)
    return out


def enrich_with_history(con, client: httpx.Client, key: str, courses: list[dict]) -> int:
    """취업률이 빈 과정에 과거 회차 취업률을 채운다. 반환값: 이번에 호출한 횟수."""
    fresh_after = (date.today() - timedelta(days=HISTORY_TTL_DAYS)).isoformat()
    cache, calls = {}, 0
    for c in courses:
        if c["empl_rate3"] is not None or c["empl_rate6"] is not None:
            continue
        cid = c["course_id"]
        if cid not in cache:
            row = con.execute("SELECT fetched_at, body FROM course_history WHERE course_id=?", (cid,)).fetchone()
            if row and row["fetched_at"] >= fresh_after:
                cache[cid] = json.loads(row["body"])
            elif calls < MAX_HISTORY_CALLS:
                r = client.get(HISTORY_URL, params={"authKey": key, "returnType": "JSON", "outType": "2",
                                                    "srchTrprId": cid}, timeout=30)
                r.raise_for_status()
                calls += 1
                cache[cid] = r.json().get("scn_list") or []
                con.execute("INSERT OR REPLACE INTO course_history VALUES (?,?,?)",
                            (cid, db.now(), json.dumps(cache[cid], ensure_ascii=False)))
                time.sleep(0.3)
            else:
                cache[cid] = json.loads(row["body"]) if row else []  # 상한 도달: 오래된 캐시라도 사용
        s = summarize_history(cache[cid])
        if s:
            c["empl_rate3"] = s["3"][0] if "3" in s else None
            c["empl_rate6"] = s["6"][0] if "6" in s else None
            rounds, n = max((v[1], v[2]) for v in s.values())
            c["empl_source"] = f"이전 {rounds}개 회차 평균(수료 {n}명)"
    return calls


def update_area_codes() -> int:
    load_env()
    key = os.environ.get("WORK24_CODE_KEY")
    if not key:
        sys.exit("WORK24_CODE_KEY가 없습니다.")
    with httpx.Client() as client:
        area = codes.fetch_area_codes(client, key)
    codes.save_area_codes(area)
    return len(area)


def collect(dump_dir: str | None = None) -> dict:
    load_env()
    key = os.environ.get("WORK24_API_KEY")
    if not key:
        sys.exit("WORK24_API_KEY가 없습니다. .env.example을 .env로 복사해 키를 넣거나 --sample로 실행하세요.")
    courses = {}
    with httpx.Client() as client:
        for program in PROGRAMS:
            for method in METHODS:
                for c in fetch_program(client, key, program, method, dump_dir):
                    courses.setdefault((c["course_id"], c["round"]), c)
    courses = list(courses.values())
    with db.connect() as con, httpx.Client() as client:
        calls = enrich_with_history(con, client, key, courses)
        return {**db.upsert_courses(con, courses), "history_calls": calls}


def load_sample() -> dict:
    courses = json.load(open(SAMPLE_PATH, encoding="utf-8"))
    with db.connect() as con:
        return db.upsert_courses(con, courses)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true")
    ap.add_argument("--dump")
    ap.add_argument("--codes", action="store_true")
    a = ap.parse_args()
    print(load_sample() if a.sample else update_area_codes() if a.codes else collect(a.dump))
