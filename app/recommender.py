"""설명 가능한 콘텐츠 기반 추천 (기획안 5-1).

프론트 데모(app/static/index.html)의 JS 구현과 가중치·로직을 동일하게 유지한다.
"""
from datetime import date
from statistics import mean

from .tagging import TAGS

WEIGHTS = {"interest": 0.40, "region": 0.15, "mode": 0.10, "schedule": 0.10, "quality": 0.15, "urgency": 0.10}
PRIOR_STRENGTH = 20  # 베이지안 보정 사전 강도 m


def _bayes(x, n, mu, m=PRIOR_STRENGTH):
    if x is None:
        return mu
    n = n or 0
    return (n * x + m * mu) / (n + m)


def _quality_stats(courses):
    er = [c["empl_rate3"] for c in courses if c.get("empl_rate3") is not None] or [50.0]
    sat = [c["satisfaction"] for c in courses if c.get("satisfaction") is not None] or [80.0]
    return mean(er), mean(sat)


def score_course(c: dict, p: dict, stats, today: date) -> tuple[float, list[str], dict]:
    er_mu, sat_mu = stats
    interests = set(p.get("interests") or [])
    keywords = [k.strip().lower() for k in (p.get("keywords") or []) if k.strip()]
    parts, reasons = {}, []

    # interest: 태그 일치 비율 + 자유 키워드 부분일치 보너스
    hit = interests & set(c.get("tags") or ["etc"])  # 태그 없는 옛 데이터는 "기타"로 본다
    kw_hit = [k for k in keywords if k in c["title"].lower()]
    parts["interest"] = min(1.0, (len(hit) / len(interests) if interests else 0.3) + 0.3 * len(kw_hit))
    if hit:
        reasons.append(f"관심 분야 {TAGS[sorted(hit)[0]]['label']}")
    if kw_hit:
        reasons.append(f"키워드 '{kw_hit[0]}'")

    regions = p.get("regions") or []
    if c.get("mode") == "원격":
        parts["region"] = 0.8
    elif not regions:
        parts["region"] = 0.5
    else:
        parts["region"] = 1.0 if any((c.get("region") or "").startswith(r) for r in regions) else 0.0
        if parts["region"]:
            reasons.append(f"선호 지역 {c['region']}")

    modes = p.get("modes") or []
    parts["mode"] = 1.0 if not modes or c.get("mode") in modes else 0.0

    start = date.fromisoformat(c["start_date"]) if c.get("start_date") else None
    end = date.fromisoformat(c["end_date"]) if c.get("end_date") else None
    ok = 1.0
    if p.get("start_after") and start and start < date.fromisoformat(p["start_after"]):
        ok -= 0.6
    if p.get("max_weeks") and start and end and (end - start).days / 7 > p["max_weeks"]:
        ok -= 0.6
    parts["schedule"] = max(0.0, ok)

    er = _bayes(c.get("empl_rate3"), c.get("capacity"), er_mu) / 100
    sat = _bayes(c.get("satisfaction"), c.get("capacity"), sat_mu) / 100
    parts["quality"] = 0.6 * er + 0.4 * sat
    if c.get("empl_rate3") is not None and c["empl_rate3"] >= er_mu + 10:
        reasons.append(f"취업률 {c['empl_rate3']:.0f}%")

    days = (start - today).days if start else 60
    fill = (c.get("registered") or 0) / c["capacity"] if c.get("capacity") else 0
    parts["urgency"] = max(0.0, 1 - days / 60) * 0.5 + min(fill, 1) * 0.5
    if 0 <= days <= 14:
        reasons.append(f"개강 D-{days}")

    score = sum(WEIGHTS[k] * v for k, v in parts.items())
    if parts["mode"] == 0 or parts["schedule"] == 0:
        score *= 0.5  # 하드 제약 위반은 크게 감점하되 완전 제외는 하지 않음
    return round(score, 4), reasons[:3], parts


def recommend(courses: list[dict], profile: dict, dismissed: set | None = None, k: int = 10,
              today: date | None = None) -> list[dict]:
    today = today or date.today()
    dismissed = dismissed or set()
    stats = _quality_stats(courses)
    out = []
    for c in courses:
        if (c["course_id"], c["round"]) in dismissed:
            continue
        s, reasons, parts = score_course(c, profile, stats, today)
        out.append({**c, "score": s, "reasons": reasons, "score_parts": parts})
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:k]
