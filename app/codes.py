"""고용24 훈련 공통코드(319L01). 훈련지역 코드(trngAreaCd, 5자리) → '시도 시군구'.

목록 응답의 address는 훈련기관 주소라 실제 훈련장소와 다를 수 있다(2026-10-08 기준 610건 중 약 60건).
region은 훈련장소 코드인 trngAreaCd로 채운다. 코드표는 `python -m app.collector --codes`로 갱신한다.
"""
import json
import os
import re

CODE_URL = "https://www.work24.go.kr/cm/openApi/call/hr/callOpenApiSvcInfo319L01.do"
AREA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "codes_area.json")
# 대분류 코드 → 표준 시도 약칭. 12(전남광주)는 코드표 이름이 '주 동구'처럼 잘려 있어 시군구로 나눈다.
SIDO = {"11": "서울", "26": "부산", "27": "대구", "28": "인천", "29": "광주", "30": "대전", "31": "울산",
        "36": "세종", "41": "경기", "42": "강원", "51": "강원", "43": "충북", "44": "충남", "45": "전북",
        "52": "전북", "46": "전남", "47": "경북", "48": "경남", "49": "제주", "50": "제주"}
GWANGJU_GU = {"동구", "서구", "남구", "북구", "광산구"}


def parse_code_xml(xml: str) -> dict[str, str]:
    return {c: n.strip() for c, n in re.findall(r"<rsltCode>([^<]*)</rsltCode>\s*<rsltName>([^<]*)</rsltName>", xml)}


def fetch_area_codes(client, key: str) -> dict[str, str]:
    """srchType=01(훈련지역 중분류) 1회 호출."""
    r = client.get(CODE_URL, params={"authKey": key, "returnType": "XML", "outType": "1", "srchType": "01"},
                   timeout=30)
    r.raise_for_status()
    return parse_code_xml(r.text)


def save_area_codes(codes: dict[str, str]):
    with open(AREA_PATH, "w", encoding="utf-8") as f:
        json.dump(codes, f, ensure_ascii=False, indent=0, sort_keys=True)


_area = None


def region_name(code: str | None) -> str | None:
    global _area
    if _area is None:
        _area = json.load(open(AREA_PATH, encoding="utf-8")) if os.path.exists(AREA_PATH) else {}
    code = (code or "").strip()
    sigungu = _area.get(code)
    if not sigungu:
        return None
    if code[:2] == "12":
        sigungu = re.sub(r"^주 ", "", sigungu)
        return f"{'광주' if sigungu in GWANGJU_GU else '전남'} {sigungu}"
    sido = SIDO.get(code[:2])
    return f"{sido} {sigungu}" if sido and sido != sigungu else sigungu
