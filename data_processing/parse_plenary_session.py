"""
본회의 회의록 파싱 - 안건 경계 자동 감지

본회의 특징:
1. 안건 목록이 먼저 나열됨 (2. 조례안... 3. 조례안...)
2. "의사일정 제N항" 형태로 안건 시작 표시
3. 일괄 상정 후 개별 표결

전략:
- 안건 목록 추출 (정규식)
- 청크별 소속 안건 판단 (키워드 매칭)
- 중복 저장 (하나의 청크를 여러 안건에 할당)
"""

import re
from typing import List, Dict, Optional


def extract_agenda_list(text: str) -> List[Dict]:
    """
    텍스트에서 안건 목록 추출

    예시:
    "2. 서울특별시 병역명문가 예우에 관한 조례 일부개정조례안..."

    Returns:
        [{"num": 2, "title": "서울특별시 병역명문가 예우에 관한 조례 일부개정조례안"}]
    """
    agendas = []

    # 패턴: "숫자. 조례안/계획안/동의안" (발의자 정보 제외)
    pattern = r'(\d+)\.\s+([^(]+?)(?:\([^)]+\s+(?:발의|제출)\))?(?:\s+\(|$|\n)'

    matches = re.finditer(pattern, text)

    for match in matches:
        num = int(match.group(1))
        title = match.group(2).strip()

        # 조례/계획/동의안만 필터링
        if any(keyword in title for keyword in ['조례', '계획안', '동의안', '예산안']):
            agendas.append({
                "num": num,
                "title": title
            })

    return agendas


def detect_agenda_boundary(chunk_text: str, agendas: List[Dict]) -> List[int]:
    """
    청크가 어느 안건에 속하는지 판단

    규칙:
    1. "의사일정 제N항" 명시 → 해당 안건
    2. "제N항부터 제M항까지" → N~M 안건 모두
    3. "제N항은 가결" → 해당 안건
    4. 안건 제목 포함 → 해당 안건

    Returns:
        안건 번호 리스트 (예: [2, 3, 4])
    """
    agenda_nums = []

    # 패턴 1: "의사일정 제N항"
    match = re.search(r'의사일정\s+제(\d+)항', chunk_text)
    if match:
        num = int(match.group(1))
        agenda_nums.append(num)

    # 패턴 2: "제N항부터 제M항까지"
    match = re.search(r'제(\d+)항부터\s+제(\d+)항까지', chunk_text)
    if match:
        start = int(match.group(1))
        end = int(match.group(2))
        agenda_nums.extend(range(start, end + 1))

    # 패턴 3: "제N항은/을"
    match = re.search(r'제(\d+)항(?:은|을|이)', chunk_text)
    if match:
        num = int(match.group(1))
        if num not in agenda_nums:
            agenda_nums.append(num)

    # 패턴 4: 안건 제목 일부 포함 (유사도 체크)
    if not agenda_nums:
        for agenda in agendas:
            # 안건 제목의 핵심 키워드 추출 (첫 10자)
            title_keywords = agenda['title'][:15]
            if title_keywords in chunk_text:
                agenda_nums.append(agenda['num'])

    return sorted(set(agenda_nums))  # 중복 제거 및 정렬


def assign_chunks_to_agendas(chunks: List[Dict], agendas: List[Dict]) -> List[Dict]:
    """
    각 청크에 소속 안건 할당

    Returns:
        확장된 청크 리스트 (중복 저장)
        [
            {"speaker": "...", "agenda_num": 2, "agenda_title": "...", "text": "..."},
            {"speaker": "...", "agenda_num": 3, "agenda_title": "...", "text": "..."},
        ]
    """
    expanded_chunks = []

    for chunk in chunks:
        text = chunk.get('text', '')

        # 소속 안건 판단
        agenda_nums = detect_agenda_boundary(text, agendas)

        if agenda_nums:
            # 여러 안건에 속하면 중복 저장
            for num in agenda_nums:
                agenda_info = next((a for a in agendas if a['num'] == num), None)
                if agenda_info:
                    expanded_chunks.append({
                        **chunk,
                        'agenda_num': num,
                        'agenda': agenda_info['title']
                    })
        else:
            # 안건 미지정 (개회사, 폐회 등)
            expanded_chunks.append({
                **chunk,
                'agenda_num': None,
                'agenda': None
            })

    return expanded_chunks


def test_parser():
    """테스트"""

    # 샘플 텍스트
    sample_text = """
2. 서울특별시 병역명문가 예우에 관한 조례 일부개정조례안(이숙자 의원 발의)
3. 서울특별시 체불임금 없는 관급공사 운영을 위한 조례 일부개정조례안(강동길 의원 발의)
4. 서울특별시 2025년도 제4차 수시분 공유재산관리계획안(서울특별시장 제출)

○의장 최호정  다음은 의사일정 제2항부터 제4항까지 행정자치위원회에서 심사한 안건 3건을 일괄 상정합니다.
    """

    # 1. 안건 목록 추출
    agendas = extract_agenda_list(sample_text)
    print("📋 추출된 안건:")
    for agenda in agendas:
        print(f"  {agenda['num']}. {agenda['title']}")
    print()

    # 2. 청크 소속 판단
    sample_chunks = [
        {
            "speaker": "의장 최호정",
            "text": "다음은 의사일정 제2항부터 제4항까지 행정자치위원회에서 심사한 안건 3건을 일괄 상정합니다."
        },
        {
            "speaker": "의장 최호정",
            "text": "의사일정 제2항 서울특별시 병역명문가 예우에 관한 조례 일부개정조례안을 표결하겠습니다."
        }
    ]

    expanded = assign_chunks_to_agendas(sample_chunks, agendas)

    print("🔍 청크 소속 안건 판단:")
    for i, chunk in enumerate(expanded):
        print(f"  청크 {i+1}:")
        print(f"    안건 번호: {chunk.get('agenda_num')}")
        print(f"    안건 제목: {chunk.get('agenda', 'None')[:30]}...")
        print(f"    텍스트: {chunk['text'][:50]}...")
        print()


if __name__ == "__main__":
    test_parser()
