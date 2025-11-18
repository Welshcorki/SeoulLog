"""
제332회 임시회 회의록 파싱 스크립트
- result 폴더의 53개 JSON 파일을 읽어서 안건 단위로 분리
- 메타데이터 추출 및 구조화
- ChromaDB용 데이터 및 프론트엔드용 데이터 생성
"""

import json
import os
import re
from datetime import datetime
from typing import List, Dict, Any

def extract_text_from_content(content: List[Dict]) -> str:
    """JSON content에서 텍스트만 추출"""
    text = ""
    for item in content:
        if item["type"] == "text":
            text += item["content"]
        elif item["type"] == "link":
            text += item.get("text", "")
    return text

def parse_meeting_title(title: str) -> Dict[str, str]:
    """
    회의록 제목에서 메타데이터 추출
    예: "제332회 교육위원회 제1차(2025.09.01)"
    """
    # 패턴: 제XXX회 [위원회명] 제X차(YYYY.MM.DD)
    pattern = r'제(\d+)회\s+(.+?)\s+제(\d+)차\((\d{4}\.\d{2}\.\d{2})\)'
    match = re.search(pattern, title)

    if match:
        session_number = match.group(1)
        committee = match.group(2)
        meeting_number = match.group(3)
        date = match.group(4)

        return {
            "session_number": session_number,
            "committee": committee,
            "meeting_number": meeting_number,
            "date": date,
            "full_title": title
        }

    return {
        "session_number": "",
        "committee": title,
        "meeting_number": "",
        "date": "",
        "full_title": title
    }

def extract_agenda_items(text: str, meeting_info: Dict) -> List[Dict]:
    """
    회의록 텍스트에서 안건 추출
    의사일정 섹션을 찾아서 번호로 구분된 안건들을 파싱
    """
    agenda_items = []

    # 의사일정 섹션 찾기
    agenda_section_start = text.find('의사일정')

    if agenda_section_start == -1:
        # 의사일정이 없으면 전체를 하나의 안건으로 처리
        unique_id = f"{meeting_info['committee']}_{meeting_info['date']}_meeting{meeting_info['meeting_number']}_전체"
        return [{
            "id": unique_id,
            "item_number": 0,
            "title": meeting_info['full_title'],
            "content": text[:3000],  # 처음 3000자
            "decision": "정보없음",
            "metadata": meeting_info
        }]

    # 의사일정 이후 텍스트
    agenda_section = text[agenda_section_start:]

    # 심사된안건 또는 의사내용 섹션 찾기
    content_start = max(
        agenda_section.find('심사된안건'),
        agenda_section.find('의사내용'),
        0
    )

    if content_start > 0:
        full_content = agenda_section[content_start:]
    else:
        full_content = agenda_section

    # 번호로 구분된 안건 찾기 (1., 2., 3., ...)
    # 패턴: 숫자. 으로 시작하는 라인
    item_pattern = r'(?:^|\n)(\d+)\.\s*([^\n]+)'
    items = re.findall(item_pattern, agenda_section[:500], re.MULTILINE)  # 의사일정 섹션만

    if not items:
        # 안건을 찾지 못하면 전체를 하나로
        unique_id = f"{meeting_info['committee']}_{meeting_info['date']}_meeting{meeting_info['meeting_number']}_전체"
        return [{
            "id": unique_id,
            "item_number": 0,
            "title": meeting_info['full_title'],
            "content": text[:3000],
            "decision": "정보없음",
            "metadata": meeting_info
        }]

    for item_num, item_title in items:
        item_title = item_title.strip()

        # 안건 본문 찾기
        # 1) 제목으로 본문 검색
        title_pos = full_content.find(item_title)

        if title_pos != -1:
            # 다음 안건 시작 위치 찾기
            next_item_pattern = rf'\n{int(item_num)+1}\.\s+'
            next_match = re.search(next_item_pattern, full_content[title_pos:])

            if next_match:
                end_pos = title_pos + next_match.start()
                content = full_content[title_pos:end_pos].strip()
            else:
                # 마지막 안건이면 끝까지
                content = full_content[title_pos:title_pos+3000].strip()
        else:
            # 본문을 찾지 못하면 제목만
            content = item_title

        # 결론 추출 (원안가결, 부결, 계류 등)
        decision = "정보없음"
        decision_keywords = ["원안가결", "수정가결", "부결", "계류", "보류", "철회", "가결"]
        for keyword in decision_keywords:
            if keyword in content:
                decision = keyword
                break

        # 고유 ID 생성 (위원회_날짜_회차_안건번호)
        unique_id = f"{meeting_info['committee']}_{meeting_info['date']}_meeting{meeting_info['meeting_number']}_item_{item_num}"

        agenda_items.append({
            "id": unique_id,
            "item_number": int(item_num),
            "title": item_title,
            "content": content[:3000],  # 3000자 제한
            "decision": decision,
            "metadata": meeting_info
        })

    return agenda_items

def process_all_meetings(result_dir: str = "result") -> List[Dict]:
    """
    result 폴더의 모든 회의록 JSON 파일 처리
    """
    all_agenda_items = []
    meeting_count = 0
    global_item_index = 0  # 전역 인덱스로 완전히 고유한 ID 생성

    print("=" * 80)
    print("제332회 임시회 회의록 파싱 시작")
    print("=" * 80 + "\n")

    # result 폴더의 모든 하위 폴더 탐색
    for folder_name in os.listdir(result_dir):
        folder_path = os.path.join(result_dir, folder_name)

        if not os.path.isdir(folder_path):
            continue

        # JSON 파일 찾기
        json_files = [f for f in os.listdir(folder_path) if f.endswith('.json')]

        if not json_files:
            continue

        json_path = os.path.join(folder_path, json_files[0])

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            meeting_count += 1
            print(f"[{meeting_count}] 처리 중: {data['title']}")

            # 메타데이터 추출
            meeting_info = parse_meeting_title(data['title'])
            meeting_info['url'] = data['url']
            meeting_info['timestamp'] = data['timestamp']

            # 텍스트 추출
            full_text = extract_text_from_content(data['content'])

            # 안건 추출
            agenda_items = extract_agenda_items(full_text, meeting_info)

            # 각 안건에 전역 고유 인덱스 추가
            for item in agenda_items:
                global_item_index += 1
                # 기존 ID에 전역 인덱스 추가해서 완전히 고유하게
                item['id'] = f"{item['id']}_idx{global_item_index}"

            print(f"   → {len(agenda_items)}개 안건 추출")

            all_agenda_items.extend(agenda_items)

        except Exception as e:
            print(f"   ⚠ 오류 발생: {str(e)}")
            continue

    print("\n" + "=" * 80)
    print(f"총 {meeting_count}개 회의록 처리 완료")
    print(f"총 {len(all_agenda_items)}개 안건 추출")
    print("=" * 80 + "\n")

    return all_agenda_items

def save_to_json(agenda_items: List[Dict], output_file: str):
    """안건 데이터를 JSON 파일로 저장"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(agenda_items, f, ensure_ascii=False, indent=2)
    print(f"✓ {output_file}에 저장 완료 ({len(agenda_items)}개 안건)")

def generate_frontend_data(agenda_items: List[Dict], output_file: str):
    """
    프론트엔드용 TypeScript 데이터 파일 생성
    """

    # TypeScript 인터페이스에 맞는 형식으로 변환
    issues = []

    for idx, item in enumerate(agenda_items):
        issue = {
            "id": idx + 1,
            "title": item['title'],
            "category": item['metadata']['committee'],
            "status": "통과" if "가결" in item['decision'] else "심의중",
            "date": item['metadata']['date'],
            "impact": "전체",  # 나중에 개선
            "summary": item['content'][:200] + "...",  # 요약
            "committee": item['metadata']['committee'],
            "decision": item['decision'],
            "url": item['metadata']['url']
        }
        issues.append(issue)

    # TypeScript 파일 생성
    ts_content = f'''// 자동 생성된 파일 - 수정하지 마세요
// 생성 시각: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
// 총 안건 수: {len(issues)}

export interface Issue {{
  id: number;
  title: string;
  category: string;
  status: string;
  date: string;
  impact: string;
  summary: string;
  committee: string;
  decision: string;
  url: string;
}}

export const issues: Issue[] = {json.dumps(issues, ensure_ascii=False, indent=2)};

export default issues;
'''

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(ts_content)

    print(f"✓ {output_file}에 저장 완료 (프론트엔드용)")

if __name__ == "__main__":
    # 1. 모든 회의록 처리
    agenda_items = process_all_meetings("result")

    # 2. JSON 저장 (ChromaDB용)
    save_to_json(agenda_items, "parsed_agenda_items.json")

    # 3. 프론트엔드 데이터 생성
    generate_frontend_data(agenda_items, "frontend/data/realData.ts")

    print("\n✅ 모든 파싱 작업 완료!")
