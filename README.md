# KDT 과정 나침반

모집 중인 K-디지털 트레이닝(KDT)·K-디지털 기초역량훈련 과정을 매일 수집·저장하고, 사용자 취향에 맞춰 추천하는 웹사이트 프로토타입입니다. 기획 내용은 [PLAN.md](PLAN.md)에 있습니다.

## 바로 실행 (샘플 데이터)

```bash
pip install -r requirements.txt
python -m app.collector --sample      # data/kdt.db 에 샘플 48건 적재
uvicorn app.main:app --reload         # http://localhost:8000  (API 문서: /docs)
pytest -q
```

서버 없이 화면만 보려면 `python scripts/build_demo.py` 후 `dist/demo.html`을 브라우저로 엽니다.

## 실데이터 연동

1. 고용24 Open API 인증키 발급 → `.env.example`을 `.env`로 복사해 `WORK24_API_KEY` 입력
2. `python -m app.collector --dump raw/` 로 실수집(원본 응답도 저장). KDT 취업률은 과정 일정 API로 이전 회차 평균을 채우며 과정 ID 단위로 30일 캐시
   - 훈련지역 코드표 갱신: `python -m app.collector --codes` (`WORK24_CODE_KEY`, 결과 `data/codes_area.json`)
   - 실데이터 데모: `python scripts/export_courses.py && python scripts/build_demo.py data/courses_live.json`
3. 매일 자동 수집·배포: `.github/workflows/collect.yml`이 매일 06:00(KST)에 수집 → `data/kdt.db`·`data/courses_live.json` 커밋(일별 이력 누적) → GitHub Pages에 화면 배포. main에 코드가 push되면 커밋된 데이터로 Pages만 다시 배포합니다.
   - Settings → Pages → Build and deployment → Source: **GitHub Actions**
   - Settings → Secrets and variables → Actions에 `WORK24_API_KEY`, `WORK24_CODE_KEY` 등록 (없으면 수집은 건너뛰고 배포만 진행)
   - Actions 탭 → `daily-collect` → Run workflow로 즉시 실행 가능
   - 배포 주소: https://heoquixote.github.io/kdt-monitoring/

## 구조

| 경로 | 역할 |
|---|---|
| `app/collector.py` | 고용24 API 수집 → `courses` upsert + `course_snapshots` 일별 이력 |
| `app/db.py` | SQLite 스키마(과정·스냅샷·프로필·피드백) |
| `app/tagging.py` | 과정명 → 관심 분야 태그 |
| `app/recommender.py` | 설명 가능한 가중합 추천 (프론트 JS와 동일 로직) |
| `app/main.py` | FastAPI: `/api/courses` `/api/recommend` `/api/profile/{id}` `/api/feedback` `/api/stats` |
| `app/static/index.html` | 화면 (추천·전체·찜·모니터링 탭) |
| `scripts/make_sample.py` | 샘플 데이터 생성 (가상 과정·기관) |
