"""
result 폴더의 모든 md 파일을 JSON으로 변환 (하이브리드 방식 + 병렬 처리)

사용법:
    python process_all_result_folders.py           # 전체 파일 처리
    python process_all_result_folders.py 10        # 랜덤 10개만 처리
    python process_all_result_folders.py 5         # 랜덤 5개만 처리

방식:
    - 1단계: Gemini 2.5 Flash (개선된 프롬프트)로 안건 매핑 추출 (md 파일 → 첨부 문서 URL 포함)
    - 2단계: 순수 Python 코드로 발언 추출 (빠르고 안정적)
    - 병렬 처리: 10개 파일씩 동시 처리

개선 사항:
    - Flash 전용 강화 프롬프트 적용 (의사일정 안건만 추출, 분할 방지, 정확한 line_start 등)
    - 개회식/폐회식 특수 처리, 시정질문 통합, 절차 안건 제외

결과:
    - data/result_txt/ 폴더에 JSON 저장
"""

import os
import json
import sys
import random
from pathlib import Path
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 프로젝트 루트를 Python path에 추가 (Windows 환경 호환)
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(current_dir))

# 하이브리드 파싱 함수 임포트
from data_processing.extract_metadata_hybrid import extract_metadata_hybrid, extract_metadata_hybrid_flash
from utils.cost_tracker import CostTracker

load_dotenv()

# 전역 카운터 및 비용 추적 (스레드 안전)
lock = threading.Lock()
success_count = 0
fail_count = 0
failed_files = []
cost_tracker = None


def process_single_file(txt_file: Path, api_key: str, total: int, idx: int, use_pro: bool = False) -> dict:
    """단일 md 파일 처리 (파라미터명은 txt_file이지만 실제로는 md 파일을 처리)

    Args:
        txt_file: md 파일 경로 (extract_metadata_hybrid 함수 호환성을 위해 파라미터명 유지)
        api_key: Google API 키
        total: 전체 파일 수
        idx: 현재 인덱스

    Note:
        md 파일에 포함된 마크다운 링크에서 Gemini가 첨부 문서 URL을 자동 추출
    """
    global success_count, fail_count, failed_files, cost_tracker

    folder_name = txt_file.parent.name

    try:
        # 하이브리드 파싱 실행
        if use_pro:
            # Pro 모델 사용
            result = extract_metadata_hybrid(
                txt_path=str(txt_file),
                api_key=api_key,
                stage1_model="gemini-2.5-pro",
                verbose=False
            )
        else:
            # Flash 모델 사용 (개선된 프롬프트)
            result = extract_metadata_hybrid_flash(
                txt_path=str(txt_file),
                api_key=api_key,
                verbose=False
            )

        # 제목을 파일명으로 사용 (특수문자 제거)
        title = result['meeting_info']['title']
        safe_title = title.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')

        # data/result_txt/ 경로에만 저장
        result_txt_dir = Path("data/result_txt")
        result_txt_dir.mkdir(parents=True, exist_ok=True)
        json_output_path = result_txt_dir / f"{safe_title}.json"

        # JSON 저장
        with open(json_output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # 비용 추적 (토큰 정보 추출)
        usage = result.get('usage', {})
        stage1_tokens = usage.get('stage1_tokens', {})
        input_tokens = stage1_tokens.get('input', 0)
        output_tokens = stage1_tokens.get('output', 0)

        # 사용된 모델 확인
        model_used = usage.get('stage1_model', 'gemini-2.5-flash')

        with lock:
            success_count += 1
            current_success = success_count
            current_fail = fail_count

            # CostTracker에 비용 추가
            if cost_tracker and input_tokens > 0:
                cost_tracker.add_gemini_cost(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    model=model_used
                )

        print(f"✅ [{idx}/{total}] {folder_name[:60]}")
        print(f"   💾 {json_output_path.name}")
        print(f"   📊 {len(result['chunks'])}개 발언 | 진행: {current_success}개 성공, {current_fail}개 실패")
        print()

        return {'status': 'success', 'file': folder_name}

    except Exception as e:
        with lock:
            fail_count += 1
            failed_files.append((folder_name, str(e)))
            current_success = success_count
            current_fail = fail_count

        print(f"❌ [{idx}/{total}] {folder_name[:60]}")
        print(f"   오류: {str(e)}")
        print(f"   진행: {current_success}개 성공, {current_fail}개 실패")

        # 상세 traceback 출력
        import traceback
        print("   상세 에러:")
        traceback.print_exc()
        print()

        return {'status': 'failed', 'file': folder_name, 'error': str(e)}


def process_all_txt_files(n_files: int = None, use_pro: bool = False):
    """result 폴더의 모든 md 파일 처리 (10개씩 병렬)

    Args:
        n_files: 처리할 파일 개수 (None이면 전체, 숫자면 랜덤 선택)
        use_pro: True이면 gemini-2.5-pro 사용, False이면 gemini-2.5-flash 사용

    Returns:
        CostTracker: 비용 추적 객체

    Note:
        - md 파일을 사용하면 Gemini가 마크다운 링크에서 첨부 문서 URL을 자동으로 추출합니다.
        - Flash: 개선된 프롬프트 적용 (의사일정 안건만, 분할 방지, 정확한 line_start)
        - Pro: 기존 프롬프트 사용
    """
    global success_count, fail_count, failed_files, cost_tracker

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY가 설정되지 않았습니다.")
        return

    # result 폴더의 모든 md 파일 찾기 (마크다운 링크에서 첨부 문서 URL 추출 가능)
    result_dir = Path("result")
    all_md_files = sorted(result_dir.glob("*/meeting_*.md"))

    # 랜덤 선택 (n_files가 지정된 경우)
    if n_files is not None:
        if n_files > len(all_md_files):
            print(f"⚠️  요청한 파일 수({n_files}개)가 전체 파일 수({len(all_md_files)}개)보다 많습니다.")
            print(f"   전체 {len(all_md_files)}개 파일을 처리합니다.")
            md_files = all_md_files
        else:
            random.seed()
            md_files = random.sample(all_md_files, n_files)
            print(f"🎲 전체 {len(all_md_files)}개 중 랜덤 {n_files}개 선택")
    else:
        md_files = all_md_files

    print("=" * 100)
    print("📂 result 폴더 JSON 변환 (하이브리드 방식 + 병렬 처리)")
    print("=" * 100)
    print(f"처리할 파일 수: {len(md_files)}개")
    print(f"방식: 1단계 Gemini Flash (개선된 프롬프트) + 2단계 순수 코드")
    print(f"병렬 처리: 10개 파일씩 동시 처리")
    print(f"개선 사항: 의사일정 안건만 추출, 분할 방지, 정확한 line_start")
    print()

    # 카운터 및 비용 추적 초기화
    success_count = 0
    fail_count = 0
    failed_files = []
    cost_tracker = CostTracker()

    # ThreadPoolExecutor로 10개씩 병렬 처리
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(process_single_file, md_file, api_key, len(md_files), idx, use_pro): (idx, md_file)
            for idx, md_file in enumerate(md_files, 1)
        }

        # 완료되는 대로 결과 수집
        for future in as_completed(futures):
            idx, md_file = futures[future]
            try:
                result = future.result()
            except Exception as e:
                print(f"⚠️  예상치 못한 오류 발생: {md_file.parent.name}")
                print(f"   오류: {e}")
                import traceback
                print("   상세 traceback:")
                traceback.print_exc()
                print()

    # 최종 결과
    print("=" * 100)
    print("📊 최종 결과")
    print("=" * 100)
    print(f"총 파일: {len(md_files)}개")
    print(f"✅ 성공: {success_count}개")
    print(f"❌ 실패: {fail_count}개")
    print()

    if failed_files:
        print("실패한 파일 목록:")
        for folder, error in failed_files:
            print(f"  - {folder}: {error}")
        print()

    # 비용 요약 출력
    print("=" * 100)
    print("💰 Step 1 비용 요약 (Gemini 2.5 Flash - 개선된 프롬프트)")
    print("=" * 100)
    cost_tracker.print_summary()
    print()

    return cost_tracker


def main():
    """메인 함수"""
    # 커맨드 라인 인자 파싱
    n_files = None
    use_pro = False

    if len(sys.argv) > 1:
        try:
            n_files = int(sys.argv[1])
            if n_files <= 0:
                print("❌ 파일 개수는 1 이상이어야 합니다.")
                print("\n사용법:")
                print("  python process_all_result_folders.py           # 전체 파일 처리 (Flash)")
                print("  python process_all_result_folders.py 10        # 랜덤 10개만 처리 (Flash)")
                print("  python process_all_result_folders.py 3 pro     # 랜덤 3개 Pro로 처리")
                return
        except ValueError:
            print(f"❌ 잘못된 인자: '{sys.argv[1]}'")
            print("   숫자를 입력해주세요.")
            print("\n사용법:")
            print("  python process_all_result_folders.py           # 전체 파일 처리 (Flash)")
            print("  python process_all_result_folders.py 10        # 랜덤 10개만 처리 (Flash)")
            print("  python process_all_result_folders.py 3 pro     # 랜덤 3개 Pro로 처리")
            return

    # 두 번째 인자로 "pro" 체크
    if len(sys.argv) > 2 and sys.argv[2].lower() == 'pro':
        use_pro = True

    process_all_txt_files(n_files=n_files, use_pro=use_pro)


if __name__ == "__main__":
    main()
