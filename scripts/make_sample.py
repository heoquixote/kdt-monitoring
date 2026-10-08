"""키 발급 전 프로토타입용 샘플 데이터 생성 (가상의 과정·기관). 실데이터 아님."""
import json
import os
import random
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.tagging import derive_tags  # noqa: E402

random.seed(42)
TODAY = date(2026, 10, 8)
TITLES = [
    ("[KDT] 생성형 AI 활용 데이터 분석가 양성과정", 24), ("[KDT] SQL·Tableau 기반 BI 데이터 분석 실무", 16),
    ("[KDT] 파이썬 머신러닝·딥러닝 AI 엔지니어 부트캠프", 26), ("[KDT] LLM 서비스 개발자 과정 (RAG·에이전트)", 24),
    ("[KDT] 클라우드 네이티브 MSA 백엔드 개발자 (Spring·AWS)", 26), ("[KDT] React·Node 풀스택 웹 개발자 양성", 24),
    ("[KDT] AWS·쿠버네티스 DevOps 엔지니어", 20), ("[KDT] 화이트해커 정보보안 전문가 과정", 24),
    ("[KDT] 유니티 메타버스 게임 개발자", 24), ("[KDT] UX/UI 서비스 디자인 & 피그마 실무", 16),
    ("[KDT] 반도체 공정 데이터 분석 & 스마트팩토리", 20), ("[KDT] 자율주행 임베디드 SW 개발자", 26),
    ("[KDT] 서비스기획·PM 실무 과정 (데이터 기반 의사결정)", 14), ("[KDT] Flutter 크로스플랫폼 모바일 앱 개발", 20),
    ("[KDT] MLOps 엔지니어 실무 (클라우드 AI 파이프라인)", 22), ("[KDT] 빅데이터 엔지니어 (Spark·Kafka)", 24),
    ("[KDT] 블록체인·핀테크 백엔드 개발자", 22), ("[KDT] AI 컴퓨터비전 제조 품질검사 과정", 20),
    ("[KDT] 자바 웹 개발자 취업 과정", 24), ("[KDT] 데이터 시각화 & 대시보드 디자인", 12),
    ("[K-디지털 기초역량] 비전공자를 위한 파이썬 데이터 분석 입문 (원격)", 6),
    ("[K-디지털 기초역량] 생성형 AI 업무 자동화 첫걸음 (원격)", 4),
    ("[K-디지털 기초역량] 웹 프론트엔드 기초 HTML·CSS·JS (원격)", 6),
    ("[K-디지털 기초역량] SQL 데이터 활용 기초 (온라인)", 5),
]
ORGS = ["가온디지털캠퍼스(샘플)", "누리IT아카데미(샘플)", "다솜코딩스쿨(샘플)", "라온데이터랩(샘플)",
        "미르AI교육원(샘플)", "바름소프트아카데미(샘플)", "새봄테크스쿨(샘플)"]
REGIONS = ["서울 강남구", "서울 마포구", "서울 금천구", "서울 종로구", "경기 성남시", "경기 수원시",
           "인천 남동구", "부산 해운대구", "대구 동구", "광주 북구", "대전 유성구"]

courses = []
for i in range(48):
    title, weeks = TITLES[i % len(TITLES)]
    kdt = title.startswith("[KDT]")
    remote = "원격" in title or "온라인" in title
    start = TODAY + timedelta(days=random.randint(3, 75))
    cap = random.choice([20, 25, 30, 30, 40]) if kdt else random.choice([60, 100, 200])
    has_hist = random.random() < 0.7
    region = "원격" if remote else random.choice(REGIONS)
    courses.append({
        "course_id": f"SAMPLE{2026000 + i:07d}", "round": str(random.randint(1, 12)),
        "program": "C0104" if kdt else "C0105", "title": title, "org_name": random.choice(ORGS),
        "inst_id": None, "ncs_cd": None, "region": region, "address": region, "mode": "원격" if remote else "집체",
        "start_date": start.isoformat(), "end_date": (start + timedelta(weeks=weeks)).isoformat(),
        "hours": weeks * 40 if kdt else weeks * 10,
        "cost": random.choice([6_500_000, 8_200_000, 9_800_000, 11_400_000]) if kdt else random.choice([300_000, 450_000]),
        "real_cost": 0, "capacity": cap, "registered": int(cap * random.uniform(0.1, 1.05)),
        "empl_rate3": round(random.uniform(35, 85), 1) if kdt and has_hist else None,
        "empl_rate6": None, "satisfaction": round(random.uniform(78, 96), 1) if has_hist else None,
        "grade": None, "tags": derive_tags(title), "link": "https://www.work24.go.kr",
        "status": "모집중", "is_sample": 1,
    })
json.dump(courses, open(os.path.join(os.path.dirname(__file__), "..", "data", "sample_courses.json"), "w",
                         encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(courses), "sample courses")
