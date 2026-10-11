import json
import os
from datetime import date

from app.recommender import recommend
from app.tagging import derive_tags

SAMPLE = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data", "sample_courses.json"), encoding="utf-8"))
TODAY = date(2026, 10, 8)


def test_derive_tags():
    assert set(derive_tags("[KDT] SQL·Tableau 기반 BI 데이터 분석 실무")) == {"data"}
    assert "ai" in derive_tags("LLM 서비스 개발자 과정")


def test_derive_tags_fallback_and_new_keywords():
    assert derive_tags("[두산로보틱스] 지능형 로보틱스 엔지니어") == ["manufacturing"]
    assert derive_tags("에코업 탄소중립 실무 프로젝트 전문가 양성과정") == ["etc"]


def test_untagged_course_matches_etc_interest():
    c = {**SAMPLE[0], "tags": []}
    assert recommend([c], {"interests": ["etc"]}, k=1, today=TODAY)[0]["score_parts"]["interest"] == 1.0


def test_interest_drives_ranking():
    recs = recommend(SAMPLE, {"interests": ["security"]}, k=2, today=TODAY)
    assert all("security" in r["tags"] for r in recs)


def test_dismissed_excluded():
    top = recommend(SAMPLE, {"interests": ["data"]}, k=1, today=TODAY)[0]
    again = recommend(SAMPLE, {"interests": ["data"]}, {(top["course_id"], top["round"])}, k=50, today=TODAY)
    assert (top["course_id"], top["round"]) not in {(r["course_id"], r["round"]) for r in again}


def test_region_mismatch_ranks_lower():
    p = {"interests": ["data"], "regions": ["부산"], "modes": ["집체"]}
    recs = recommend(SAMPLE, p, k=len(SAMPLE), today=TODAY)
    busan = [i for i, r in enumerate(recs) if r["region"].startswith("부산") and "data" in r["tags"]]
    seoul = [i for i, r in enumerate(recs) if r["region"].startswith("서울") and "data" in r["tags"]]
    if busan and seoul:
        assert min(busan) < min(seoul)
