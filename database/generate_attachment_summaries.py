"""
첨부 문서 요약 생성 스크립트 (DB 기반)

DB의 agendas 테이블에서 attachments를 읽어서 PDF 요약을 생성하고,
다시 DB에 업데이트합니다.

사용법:
    python database/generate_attachment_summaries.py

특징:
    - DB 기반: agendas 테이블에서 직접 읽고 쓰기
    - 재실행 가능: 이미 요약된 건 건너뜀
    - 범용 프롬프트: 조례안, 보고서, 검토의견서 등 모두 처리
"""

import json
import sqlite3
import requests
import tempfile
import os
import asyncio
import threading
import sys
from pathlib import Path
from typing import List, Dict, Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv

# 프로젝트 루트를 Python path에 추가
sys.path.append(str(Path(__file__).parent.parent))

from utils.cost_tracker import CostTracker

load_dotenv()

# Gemini API 설정
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    print("❌ GOOGLE_API_KEY가 설정되지 않았습니다.")
    exit(1)

client = genai.Client(api_key=GOOGLE_API_KEY)

# 전역 카운터 (스레드 안전)
lock = threading.Lock()
success_count = 0
fail_count = 0


def download_file(url: str, save_path: str) -> bool:
    """
    URL에서 파일 다운로드

    Args:
        url: 다운로드 URL
        save_path: 저장 경로

    Returns:
        성공 여부
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=300)

        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
        else:
            print(f"  ❌ 다운로드 실패: HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"  ❌ 다운로드 오류: {str(e)}")
        return False


async def summarize_pdf_with_gemini(file_path: str, title: str, cost_tracker: CostTracker = None) -> str:
    """
    Gemini File API로 PDF 요약 생성 (범용 프롬프트, 비동기)

    Args:
        file_path: PDF 파일 경로
        title: 문서 제목
        cost_tracker: 비용 추적 객체

    Returns:
        요약 텍스트 (2-4줄)
    """
    try:
        # 파일 읽기
        print(f"    📤 파일 읽기 중...")

        with open(file_path, 'rb') as f:
            file_content = f.read()

        print(f"    ✅ 파일 읽기 완료")

        # 범용 프롬프트 (조례안, 보고서, 검토의견서 등 모두 처리)
        prompt = f"""당신은 서울시의회 회의록 첨부 문서 요약 전문가입니다.

다음 문서를 분석하고, 일반 시민이 이해하기 쉽도록 2-4줄로 요약해주세요.

문서 제목: {title}

요약 규칙:
1. 문서 유형에 맞게 요약
   - 조례안: 목적, 주요 내용, 기대 효과
   - 보고서: 핵심 현황, 주요 발견, 결론
   - 검토의견서: 안건 평가, 주요 쟁점, 검토 의견
   - 기타: 문서의 핵심 메시지

2. 작성 스타일
   - 2-4줄로 간결하게
   - 팩트 중심 (추측 금지)
   - 불확실할 때는 "추정됨", "검토 중" 등 명시
   - 전문 용어는 쉬운 말로 풀어서 설명
   - 모바일 화면에서 읽기 편하게

3. 포함 필수 요소
   - 문서의 목적 또는 배경
   - 핵심 내용 1-2가지
   - 기대 효과 또는 결론 (있는 경우)

4. 제외 사항
   - 발언자 이름 나열
   - 회의 절차 설명
   - 법조문 원문
   - 지나치게 기술적인 세부사항

출력:
- 요약문만 반환 (설명 불필요)
- 2-4줄로 작성
- 문장 종결 확인
"""

        # Gemini 2.5 Flash로 요약 생성 (비동기)
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(
                    data=file_content,
                    mime_type='application/pdf'
                ),
                prompt
            ]
        )

        summary = response.text.strip()

        # 비용 추적
        if cost_tracker and hasattr(response, 'usage_metadata'):
            input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
            output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)
            cost_tracker.add_gemini_cost(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model="gemini-2.5-flash"
            )

        # 비동기 대기 (Rate Limit 대응)
        await asyncio.sleep(2)

        print(f"    ✅ 요약 생성 완료")
        return summary

    except Exception as e:
        print(f"    ❌ Gemini 요약 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        await asyncio.sleep(2)
        return "첨부 문서 요약을 생성할 수 없습니다."


async def process_agenda_attachments(agenda_id: str, agenda_title: str, attachments_json: str, conn: sqlite3.Connection, idx: int, total: int, cost_tracker: CostTracker = None) -> Optional[tuple]:
    """
    안건의 첨부 문서를 처리하여 요약 생성 (비동기)

    Args:
        agenda_id: 안건 ID
        agenda_title: 안건 제목
        attachments_json: attachments JSON 문자열
        conn: SQLite 연결
        idx: 현재 인덱스
        total: 전체 개수
        cost_tracker: 비용 추적 객체

    Returns:
        (agenda_id, updated_json, status) 튜플 또는 None
    """
    global success_count, fail_count

    try:
        # JSON 파싱
        if not attachments_json:
            return None

        attachments = json.loads(attachments_json)
        if not attachments or len(attachments) == 0:
            return None

        print(f"\n[{idx}/{total}] {agenda_title[:60]}...")
        print(f"  📎 첨부 문서 {len(attachments)}개 발견")

        updated = False

        # 각 첨부 문서 처리 (순차)
        for att_idx, attachment in enumerate(attachments, 1):
            title = attachment.get('title', '제목 없음')
            download_url = attachment.get('download_url', '')

            # 이미 요약이 있으면 건너뜀 (단, 다운로드 실패는 재시도)
            if attachment.get('summary') and '다운로드 실패' not in attachment.get('summary'):
                print(f"  ⏭️  [{att_idx}/{len(attachments)}] 이미 요약 존재: {title[:50]}...")
                continue

            print(f"\n  [{att_idx}/{len(attachments)}] {title[:50]}...")

            # 임시 파일로 다운로드
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp_path = tmp.name

            # 다운로드
            if not download_file(download_url, tmp_path):
                attachment['summary'] = "첨부 문서 다운로드 실패"
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                updated = True
                continue

            # 파일 크기 확인
            file_size = os.path.getsize(tmp_path)
            print(f"    📄 파일 크기: {file_size / 1024:.1f} KB")

            # Gemini로 요약 생성 (비동기)
            summary = await summarize_pdf_with_gemini(tmp_path, title, cost_tracker)
            print(f"    ✅ 요약: {summary[:80]}...")

            # summary 추가
            attachment['summary'] = summary
            updated = True

            # 임시 파일 삭제
            os.unlink(tmp_path)

        # 결과 반환
        if updated:
            updated_json = json.dumps(attachments, ensure_ascii=False)
            with lock:
                success_count += 1
            return (agenda_id, updated_json, 'success')
        else:
            return (agenda_id, attachments_json, 'skipped')

    except Exception as e:
        print(f"  ❌ 처리 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        with lock:
            fail_count += 1
        return None


async def main_async():
    """메인 함수 (비동기)

    Returns:
        CostTracker: 비용 추적 객체
    """
    global success_count, fail_count

    print("=" * 80)
    print("📎 첨부 문서 요약 생성 시작 (비동기 병렬 처리)")
    print("=" * 80)
    print()

    # SQLite 연결
    db_path = 'data/sqlite_DB/agendas.db'
    if not os.path.exists(db_path):
        print(f"❌ DB 파일이 없습니다: {db_path}")
        print("먼저 'python database/create_agenda_database.py'를 실행하세요.")
        return None

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # attachments가 있는 안건 조회
    cursor.execute('''
        SELECT agenda_id, agenda_title, attachments
        FROM agendas
        WHERE attachments IS NOT NULL AND attachments != ''
    ''')

    rows = cursor.fetchall()

    if len(rows) == 0:
        print("⚠️  첨부 문서가 있는 안건이 없습니다.")
        print("먼저 크롤링 및 파싱을 완료하세요.")
        conn.close()
        return None

    print(f"📋 첨부 문서가 있는 안건: {len(rows)}개")
    print(f"⚡ 병렬 처리: 10개씩 동시 처리\n")

    # 초기화
    success_count = 0
    fail_count = 0
    skip_count = 0
    cost_tracker = CostTracker()

    # 10개씩 병렬 처리
    semaphore = asyncio.Semaphore(10)

    async def process_with_semaphore(agenda_id, agenda_title, attachments_json, idx):
        async with semaphore:
            return await process_agenda_attachments(
                agenda_id, agenda_title, attachments_json, conn, idx, len(rows), cost_tracker
            )

    tasks = [
        process_with_semaphore(agenda_id, agenda_title, attachments_json, idx)
        for idx, (agenda_id, agenda_title, attachments_json) in enumerate(rows, 1)
    ]
    results = await asyncio.gather(*tasks)

    # DB 업데이트
    print("\n💾 DB 업데이트 중...")
    for result in results:
        if result:
            agenda_id, updated_json, status = result
            if status == 'success':
                cursor.execute('''
                    UPDATE agendas
                    SET attachments = ?
                    WHERE agenda_id = ?
                ''', (updated_json, agenda_id))
            elif status == 'skipped':
                skip_count += 1

    conn.commit()
    conn.close()

    print("\n" + "=" * 80)
    print("✅ 첨부 문서 요약 생성 완료!")
    print("=" * 80)
    print(f"\n📊 결과:")
    print(f"  - 처리된 안건: {len(rows)}개")
    print(f"  - 새로 요약 생성: {success_count}개")
    print(f"  - 이미 요약 있음: {skip_count}개")
    print(f"  - 실패: {fail_count}개")
    print()

    # 비용 요약 출력
    print("=" * 80)
    print("💰 Step 5 비용 요약 (Gemini 2.5 Flash)")
    print("=" * 80)
    cost_tracker.print_summary()
    print()

    return cost_tracker


def main():
    """동기 래퍼 함수

    Returns:
        CostTracker: 비용 추적 객체
    """
    return asyncio.run(main_async())


if __name__ == "__main__":
    main()
