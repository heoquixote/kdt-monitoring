from app.codes import region_name
from app.collector import normalize, summarize_history


def test_summarize_history_weights_by_completers_and_skips_codes():
    rounds = [
        {"trprDegr": 1, "finiCnt": 20, "eiEmplRate3": "20.0", "eiEmplRate6": "50.0"},
        {"trprDegr": 2, "finiCnt": 10, "eiEmplRate3": "50.0", "eiEmplRate6": "B"},  # 6개월 미집계
        {"trprDegr": 3, "finiCnt": 0, "eiEmplRate3": "B", "eiEmplRate6": "B"},      # 진행 중
    ]
    s = summarize_history(rounds)
    assert s["3"] == (30.0, 2, 30)
    assert s["6"] == (50.0, 1, 20)
    assert summarize_history([{"finiCnt": 0, "eiEmplRate3": "D"}]) == {}


def test_region_from_training_area_code():
    assert region_name("11110") == "서울 종로구"
    assert region_name("12210") == "광주 동구"      # 전남광주 코드표 이름 '주 동구' 보정
    assert region_name("12110") == "전남 목포시"
    assert region_name("36110") == "세종"
    assert region_name("00000") is None


def test_normalize_prefers_area_code_over_institution_address():
    item = {"trprId": "X", "trprDegr": "1", "title": "t", "address": "서울 중구", "trngAreaCd": "47111",
            "stdgScor": "0", "eiEmplRate3": ""}
    c = normalize(item, "C0104", "집체")
    assert c["region"] == "경북 포항시 남구"
    assert c["satisfaction"] is None and c["empl_rate3"] is None
    assert normalize(item, "C0105", "원격")["region"] == "원격"


def test_load_courses_excludes_stale(tmp_path):
    from datetime import date, timedelta

    from app import db

    future = (date.today() + timedelta(days=10)).isoformat()
    past = (date.today() - timedelta(days=1)).isoformat()
    base = {k: None for k in db.COURSE_COLS} | {"round": "1", "title": "t", "tags": [], "is_sample": 0}
    with db.connect(str(tmp_path / "t.db")) as con:
        db.upsert_courses(con, [base | {"course_id": "OLD", "start_date": future}])
        con.execute("UPDATE courses SET last_seen_at = '2000-01-01T00:00:00+00:00'")
        db.upsert_courses(con, [base | {"course_id": "NEW", "start_date": future},
                                base | {"course_id": "STARTED", "start_date": past}])
        ids = {r["course_id"] for r in db.load_courses(con)}
    assert ids == {"NEW"}
