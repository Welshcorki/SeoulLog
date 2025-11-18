"""
result 폴더의 모든 txt 파일을 JSON으로 변환하여 result_txt에 저장 (비동기 병렬 처리 - Gemini 버전)

사용법:
    python process_all_txt_to_json_async_gemini.py

특징:
    - Gemini 2.5 Flash 사용 (더 빠르고 저렴)
    - 비동기 병렬 처리로 속도 향상
    - 동시 처리 개수 제한 (기본 10개, 조절 가능)
    - 진행률 표시
    - max_tokens: 65536 (Gemini 2.5 Flash 최대 출력)
"""

import os
import asyncio
from pathlib import Path
from extract_metadata_from_txt_gemini import extract_metadata_with_llm
from dotenv import load_dotenv
from datetime import datetime
import time

load_dotenv()


async def process_single_file(
    txt_file: Path,
    api_key: str,
    model: str,
    max_tokens: int,
    idx: int,
    total: int
) -> tuple[bool, str]:
    """
    단일 txt 파일을 JSON으로 변환 (비동기)

    Args:
        txt_file: txt 파일 경로
        api_key: Google API 키
        model: 사용할 Gemini 모델
        max_tokens: 최대 출력 토큰
        idx: 현재 파일 인덱스
        total: 전체 파일 개수

    Returns:
        (성공 여부, 메시지)
    """
    try:
        print(f"[{idx}/{total}] 처리 시작: {txt_file.name}")

        # asyncio.to_thread를 사용하여 동기 함수를 비동기로 실행
        result = await asyncio.to_thread(
            extract_metadata_with_llm,
            txt_path=str(txt_file),
            api_key=api_key,
            model=model,
            max_tokens=max_tokens
        )

        if result:
            msg = f"✅ [{idx}/{total}] 성공: {txt_file.name} → result_txt/{txt_file.stem}.json"
            print(msg)
            return (True, msg)
        else:
            msg = f"❌ [{idx}/{total}] 실패: {txt_file.name}"
            print(msg)
            return (False, msg)

    except Exception as e:
        msg = f"❌ [{idx}/{total}] 오류: {txt_file.name} - {str(e)}"
        print(msg)
        return (False, msg)


async def process_all_txt_files_async(
    result_dir: str = "result",
    api_key: str = None,
    model: str = "gemini-2.5-flash",
    max_tokens: int = 65536,  # Gemini 2.5 Flash 최대 출력 토큰
    max_concurrent: int = 10  # Gemini는 OpenAI보다 rate limit 여유로움
):
    """
    result 폴더의 모든 txt 파일을 JSON으로 변환 (비동기 병렬 처리 - Gemini)

    Args:
        result_dir: result 폴더 경로
        api_key: Google API 키 (None이면 환경변수에서 가져옴)
        model: 사용할 Gemini 모델
        max_tokens: 최대 출력 토큰 (Gemini 2.5 Flash는 65536까지 가능)
        max_concurrent: 동시 처리 개수 (기본 10개)
    """
    # API 키 확인
    if not api_key:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("❌ GOOGLE_API_KEY가 설정되지 않았습니다.")
            print("   .env 파일을 확인하세요.")
            return

    print("=" * 80)
    print("result 폴더 txt 파일 → JSON 변환 시작 (비동기 병렬 처리 - Gemini)")
    print("=" * 80)
    print(f"🤖 모델: {model}")
    print(f"📊 최대 출력 토큰: {max_tokens}")
    print(f"⚙️  동시 처리 개수: {max_concurrent}개")
    print()

    # result 폴더의 모든 하위 폴더 탐색
    result_path = Path(result_dir)
    txt_files = []

    for folder in result_path.iterdir():
        if folder.is_dir():
            # 각 폴더의 txt 파일 찾기
            for file in folder.glob("*.txt"):
                txt_files.append(file)

    if not txt_files:
        print(f"❌ {result_dir} 폴더에 txt 파일이 없습니다.")
        return

    print(f"📂 총 {len(txt_files)}개 txt 파일 발견")
    print()

    # 시작 시간
    start_time = time.time()

    # Semaphore로 동시 처리 개수 제한
    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_with_semaphore(txt_file, idx):
        async with semaphore:
            return await process_single_file(
                txt_file=txt_file,
                api_key=api_key,
                model=model,
                max_tokens=max_tokens,
                idx=idx,
                total=len(txt_files)
            )

    # 모든 파일을 비동기로 처리
    tasks = [
        process_with_semaphore(txt_file, idx)
        for idx, txt_file in enumerate(txt_files, 1)
    ]

    # 모든 작업 완료 대기
    results = await asyncio.gather(*tasks)

    # 결과 집계
    success_count = sum(1 for success, _ in results if success)
    fail_count = len(results) - success_count

    # 종료 시간
    end_time = time.time()
    elapsed_time = end_time - start_time

    # 최종 결과
    print()
    print("=" * 80)
    print("변환 완료!")
    print("=" * 80)
    print(f"✅ 성공: {success_count}개")
    print(f"❌ 실패: {fail_count}개")
    print(f"📁 저장 위치: result_txt/")
    print(f"⏱️  소요 시간: {elapsed_time:.2f}초 ({elapsed_time/60:.2f}분)")
    print(f"⚡ 평균 처리 시간: {elapsed_time/len(txt_files):.2f}초/파일")
    print()

    # 토큰 사용량 집계 (result_txt의 JSON 파일에서 읽기)
    total_input_tokens = 0
    total_output_tokens = 0

    result_txt_path = Path("result_txt")
    if result_txt_path.exists():
        import json
        for json_file in result_txt_path.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    usage = data.get('usage', {})
                    total_input_tokens += usage.get('input_tokens', 0)
                    total_output_tokens += usage.get('output_tokens', 0)
            except:
                pass

    if total_input_tokens > 0 or total_output_tokens > 0:
        print("📊 총 토큰 사용량:")
        print(f"   입력: {total_input_tokens:,} tokens")
        print(f"   출력: {total_output_tokens:,} tokens")
        print(f"   합계: {total_input_tokens + total_output_tokens:,} tokens")
        print()


def main():
    """
    메인 함수 - asyncio 실행
    """
    # 동시 처리 개수 설정 (필요 시 조정)
    # Gemini는 rate limit이 OpenAI보다 여유로워서 더 많이 병렬 처리 가능
    # - 10개: 권장 기본값 (빠르고 안정적)
    # - 15개: 매우 빠름 (rate limit 주의)
    # - 5개: 안전하게 처리
    max_concurrent = 10

    # 최대 출력 토큰 설정
    # - 65536: Gemini 2.5 Flash 최대값 (긴 회의록도 처리 가능)
    # - 32768: 중간값 (대부분의 회의록 처리 가능)
    # - 16384: 작은 값 (짧은 회의록용)
    max_tokens = 65536

    asyncio.run(process_all_txt_files_async(
        max_concurrent=max_concurrent,
        max_tokens=max_tokens
    ))


if __name__ == "__main__":
    main()
