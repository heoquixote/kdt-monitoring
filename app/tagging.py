"""과정명·NCS 코드에서 관심 분야 태그를 파생한다.

규칙 기반으로 시작하는 이유: 과정명이 짧고 정형적이라 키워드 사전만으로도 커버리지가 높고,
추천 이유를 설명하기 쉽다. 상세 텍스트가 확보되면 임베딩으로 대체한다.
"""

TAGS: dict[str, dict] = {
    "data": {"label": "데이터분석", "kw": ["데이터", "분석", "빅데이터", "SQL", "태블로", "Tableau", "BI", "시각화", "통계"]},
    "ai": {"label": "AI·머신러닝", "kw": ["AI", "인공지능", "머신러닝", "딥러닝", "LLM", "생성형", "MLOps", "컴퓨터비전", "자연어"]},
    "web": {"label": "웹개발", "kw": ["웹", "풀스택", "프론트엔드", "백엔드", "React", "Spring", "자바", "Java", "Node", "Django"]},
    "mobile": {"label": "모바일앱", "kw": ["모바일", "앱", "Android", "iOS", "Flutter", "Kotlin", "Swift"]},
    "cloud": {"label": "클라우드·DevOps", "kw": ["클라우드", "AWS", "Azure", "DevOps", "쿠버네티스", "Kubernetes", "인프라", "MSA"]},
    "security": {"label": "정보보안", "kw": ["보안", "해킹", "침해", "시큐어", "화이트해커"]},
    "game": {"label": "게임·XR", "kw": ["게임", "유니티", "Unity", "언리얼", "Unreal", "메타버스", "XR", "VR"]},
    "design": {"label": "UX·디자인", "kw": ["UX", "UI", "디자인", "피그마", "Figma"]},
    "manufacturing": {"label": "제조DX·반도체", "kw": ["반도체", "스마트팩토리", "스마트공장", "제조", "IoT", "임베디드", "PLC", "자율주행", "로봇"]},
    "pm": {"label": "기획·PM", "kw": ["기획", "PM", "PO", "서비스기획", "프로덕트"]},
    "blockchain": {"label": "블록체인·핀테크", "kw": ["블록체인", "핀테크", "Web3"]},
}

# NCS 대분류 20(정보통신) 중분류 → 태그 보조 매핑 (제목 매칭이 비었을 때만 사용)
NCS_HINT = {"200101": "pm", "200102": "web", "200103": "data", "200106": "security", "200105": "cloud"}


def derive_tags(title: str, ncs_cd: str | None = None) -> list[str]:
    t = title.lower()
    tags = [k for k, v in TAGS.items() if any(kw.lower() in t for kw in v["kw"])]
    if not tags and ncs_cd:
        hint = NCS_HINT.get(ncs_cd[:6])
        if hint:
            tags.append(hint)
    return tags
