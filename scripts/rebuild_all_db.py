"""
전체 DB 재구축 파이프라인 (초기화 + 데이터 삽입 + AI 요약 + 첨부 문서 요약)

사용법:
    python rebuild_all_db.py                    # 전체 52개 파일 처리
    python rebuild_all_db.py --skip-json        # JSON 생성 건너뛰기 (이미 있는 경우)
    python rebuild_all_db.py --only-new 10      # 최근 10개만 처리 (테스트용)

파이프라인 단계:
    Step 0: 데이터 초기화 (DB, JSON 삭제)
    Step 1: txt → JSON 변환 (첨부 문서 URL 포함)
    Step 2: JSON → ChromaDB 삽입 (벡터 DB)
    Step 3: JSON → SQLite 삽입 (메타데이터 DB)
    Step 4: AI 요약 생성 (안건별 요약)
    Step 5: 첨부 문서 요약 생성 (PDF/HWP 파일 요약) ⭐ 신규

특징:
    - 비동기 병렬 처리: JSON 생성 10개, ChromaDB 삽입 10개, AI 요약 10개 동시
    - 첨부 문서 자동 다운로드 및 Gemini File API로 요약 생성
    - 기존 대비 약 20-30% 빠른 처리 속도
    - 전체 로그 및 비용 정보 자동 저장

주의사항:
    - 기존 DB를 완전히 초기화하고 재구축합니다
    - 약 30-50분 소요 (52개 파일 기준, 첨부 문서 요약 포함)
    - 인터넷 연결 필수 (OpenAI, Gemini API, 파일 다운로드)
"""

import os
import sys
import shutil
import sqlite3
import argparse
import logging
from pathlib import Path
from datetime import datetime
import time
import copy

# 프로젝트 루트를 Python path에 추가
sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv
from utils.cost_tracker import CostTracker

load_dotenv()


def setup_logging():
    """로그 설정 (파일 + 콘솔)"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"pipeline_{timestamp}.log"

    # 로그 포맷
    log_format = '%(asctime)s [%(levelname)s] %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # 파일 핸들러 (모든 로그)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))

    # 콘솔 핸들러 (INFO 이상)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))

    # 루트 로거 설정
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler]
    )

    # Google genai 라이브러리의 AFC 로그 숨기기
    logging.getLogger('google.genai').setLevel(logging.WARNING)
    logging.getLogger('google.ai.generativelanguage').setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"로그 파일: {log_file}")

    return logger, log_file


def print_step(step_num: int, total_steps: int, title: str):
    """단계 출력"""
    print("\n" + "=" * 100)
    print(f"📍 Step {step_num}/{total_steps}: {title}")
    print("=" * 100)


def check_env_vars():
    """환경 변수 확인"""
    required_vars = ["OPENAI_API_KEY", "GOOGLE_API_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        print(f"❌ 필수 환경 변수가 설정되지 않았습니다: {', '.join(missing)}")
        print("   .env 파일을 확인해주세요.")
        sys.exit(1)

    print("✅ 환경 변수 확인 완료")


def cleanup_old_data(skip_json: bool = False):
    """기존 데이터 초기화"""
    print("\n🗑️  기존 데이터 초기화 중...")

    # 1. SQLite DB 삭제
    sqlite_db = Path("data/sqlite_DB/agendas.db")
    if sqlite_db.exists():
        sqlite_db.unlink()
        print(f"   ✓ SQLite DB 삭제: {sqlite_db}")

    # 2. ChromaDB 삭제
    chroma_dir = Path("data/chroma_db")
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)
        print(f"   ✓ ChromaDB 삭제: {chroma_dir}")

    # 3. JSON 파일 삭제 (skip_json이 False인 경우만)
    if not skip_json:
        result_txt_dir = Path("data/result_txt")
        if result_txt_dir.exists():
            json_files = list(result_txt_dir.glob("*.json"))
            for json_file in json_files:
                json_file.unlink()
            print(f"   ✓ JSON 파일 삭제: {len(json_files)}개")
    else:
        print(f"   ⏭️  JSON 생성 건너뛰기 (--skip-json)")

    print("✅ 초기화 완료\n")


def step1_generate_json(n_files: int = None):
    """Step 1: JSON 생성 (txt → JSON)

    Returns:
        tuple: (성공 여부, CostTracker 객체)
    """
    print("\n🔄 txt 파일 → JSON 변환 시작...")
    print(f"   처리 대상: {'전체 52개' if n_files is None else f'랜덤 {n_files}개'}")

    # process_all_result_folders.py 실행
    from data_processing.process_all_result_folders import process_all_txt_files

    try:
        cost_tracker = process_all_txt_files(n_files=n_files)
        print("\n✅ Step 1 완료: JSON 생성")
        return True, cost_tracker
    except Exception as e:
        print(f"\n❌ Step 1 실패: {e}")
        return False, None


def step2_insert_chromadb():
    """Step 2: ChromaDB 삽입 (JSON → ChromaDB) - 비동기 병렬 처리

    Returns:
        tuple: (성공 여부, CostTracker 객체)
    """
    print("\n🔄 JSON → ChromaDB 삽입 시작 (비동기 병렬 처리)...")

    # insert_to_chromadb_async.py의 비동기 함수 실행
    from database.insert_to_chromadb_async import insert_all_jsons_sync

    try:
        cost_tracker = insert_all_jsons_sync()  # 내부에서 asyncio.run() 호출
        print("\n✅ Step 2 완료: ChromaDB 삽입 (비동기 병렬)")
        return True, cost_tracker
    except Exception as e:
        print(f"\n❌ Step 2 실패: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def step3_create_sqlite():
    """Step 3: SQLite DB 생성 (JSON → SQLite)"""
    print("\n🔄 JSON → SQLite DB 생성 시작...")

    # create_agenda_database.py 실행
    from database.create_agenda_database import main as create_db_main

    try:
        create_db_main()
        print("\n✅ Step 3 완료: SQLite DB 생성")
        return True
    except Exception as e:
        print(f"\n❌ Step 3 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def step4_generate_summaries():
    """Step 4: AI 요약 생성 (Gemini API)

    Returns:
        tuple: (성공 여부, CostTracker 객체)
    """
    print("\n🔄 AI 요약 생성 시작...")

    # generate_ai_summaries.py 실행
    from database.generate_ai_summaries import generate_ai_summaries

    try:
        cost_tracker = generate_ai_summaries()  # 내부에서 asyncio.run() 호출
        print("\n✅ Step 4 완료: AI 요약 생성")
        return True, cost_tracker
    except Exception as e:
        print(f"\n❌ Step 4 실패: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def step5_generate_attachment_summaries():
    """Step 5: 첨부 문서 요약 생성 (Gemini File API)

    Returns:
        tuple: (성공 여부, CostTracker 객체)
    """
    print("\n🔄 첨부 문서 요약 생성 시작...")

    # generate_attachment_summaries.py 실행
    from database.generate_attachment_summaries import main as generate_attachment_main

    try:
        cost_tracker = generate_attachment_main()
        print("\n✅ Step 5 완료: 첨부 문서 요약 생성")
        return True, cost_tracker
    except Exception as e:
        print(f"\n❌ Step 5 실패: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def print_final_stats():
    """최종 통계 출력"""
    print("\n" + "=" * 100)
    print("📊 최종 데이터베이스 통계")
    print("=" * 100)

    # SQLite 통계
    sqlite_db = Path("data/sqlite_DB/agendas.db")
    if sqlite_db.exists():
        conn = sqlite3.connect(sqlite_db)
        cursor = conn.cursor()

        # 안건 수
        cursor.execute("SELECT COUNT(*) FROM agendas")
        agenda_count = cursor.fetchone()[0]

        # 청크 수
        cursor.execute("SELECT COUNT(*) FROM agenda_chunks")
        chunk_count = cursor.fetchone()[0]

        # AI 요약 생성 수
        cursor.execute("SELECT COUNT(*) FROM agendas WHERE ai_summary IS NOT NULL")
        summary_count = cursor.fetchone()[0]

        conn.close()

        print(f"\n✅ SQLite DB ({sqlite_db})")
        print(f"   - 안건 수: {agenda_count}개")
        print(f"   - 청크 수: {chunk_count}개")
        print(f"   - AI 요약: {summary_count}개")

    # ChromaDB 통계
    chroma_dir = Path("data/chroma_db")
    if chroma_dir.exists():
        try:
            import chromadb
            from chromadb.config import Settings

            client = chromadb.PersistentClient(
                path=str(chroma_dir),
                settings=Settings(anonymized_telemetry=False)
            )
            collection = client.get_collection("seoul_council_meetings")
            vector_count = collection.count()

            print(f"\n✅ ChromaDB ({chroma_dir})")
            print(f"   - 벡터 수: {vector_count}개")
        except:
            print(f"\n⚠️  ChromaDB 통계 확인 실패")

    # JSON 파일 통계
    result_txt_dir = Path("data/result_txt")
    if result_txt_dir.exists():
        json_files = list(result_txt_dir.glob("*.json"))
        print(f"\n✅ JSON 파일 ({result_txt_dir})")
        print(f"   - JSON 수: {len(json_files)}개")

    print("\n" + "=" * 100)


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="전체 DB 재구축 파이프라인")
    parser.add_argument("--skip-json", action="store_true", help="JSON 생성 건너뛰기")
    parser.add_argument("--only-new", type=int, metavar="N", help="랜덤 N개만 처리 (테스트용)")
    args = parser.parse_args()

    start_time = time.time()

    # 로깅 설정
    logger, log_file = setup_logging()

    print("=" * 100)
    print("🚀 서울시의회 회의록 DB 재구축 파이프라인")
    print("=" * 100)
    print(f"시작 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"로그 파일: {log_file}")
    print()

    logger.info("=" * 100)
    logger.info("🚀 서울시의회 회의록 DB 재구축 파이프라인")
    logger.info("=" * 100)
    logger.info(f"시작 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.skip_json:
        logger.info("옵션: --skip-json (JSON 생성 건너뛰기)")
    if args.only_new:
        logger.info(f"옵션: --only-new {args.only_new} (테스트 모드)")

    # 환경 변수 확인
    check_env_vars()
    logger.info("환경 변수 확인 완료")

    # 초기화
    print_step(0, 5, "데이터 초기화")
    logger.info("Step 0: 데이터 초기화 시작")
    cleanup_old_data(skip_json=args.skip_json)
    logger.info("Step 0: 데이터 초기화 완료")

    # 전체 비용 추적기 초기화
    total_cost_tracker = CostTracker()

    # Step 1: JSON 생성 (선택적)
    if not args.skip_json:
        print_step(1, 5, "JSON 생성 (md → JSON)")
        logger.info("Step 1: JSON 생성 시작")
        success, step1_cost_tracker = step1_generate_json(n_files=args.only_new)
        if not success:
            logger.error("Step 1: JSON 생성 실패")
            print("\n❌ 파이프라인 중단: JSON 생성 실패")
            sys.exit(1)

        # Step 1 비용 로그 기록
        if step1_cost_tracker:
            step1_cost = step1_cost_tracker.total_cost
            logger.info(f"Step 1 비용: ${step1_cost:.6f} (₩{step1_cost * 1300:.2f})")

            # 전체 비용에 통합 (deep copy하여 참조 문제 방지)
            total_cost_tracker.costs_breakdown = copy.deepcopy(step1_cost_tracker.costs_breakdown)
            total_cost_tracker.total_cost = step1_cost_tracker.total_cost

        logger.info("Step 1: JSON 생성 완료")
    else:
        print_step(1, 5, "JSON 생성 (건너뛰기)")
        logger.info("Step 1: JSON 생성 건너뛰기 (기존 파일 사용)")
        print("⏭️  기존 JSON 파일 사용")

    # Step 2: ChromaDB 삽입
    print_step(2, 5, "ChromaDB 삽입 (JSON → ChromaDB)")
    logger.info("Step 2: ChromaDB 삽입 시작")
    success, step2_cost_tracker = step2_insert_chromadb()
    if not success:
        logger.error("Step 2: ChromaDB 삽입 실패")
        print("\n❌ 파이프라인 중단: ChromaDB 삽입 실패")
        sys.exit(1)

    # Step 2 비용 로그 기록
    if step2_cost_tracker:
        step2_cost = step2_cost_tracker.total_cost
        logger.info(f"Step 2 비용: ${step2_cost:.6f} (₩{step2_cost * 1300:.2f})")

        # 전체 비용에 통합 (OpenAI 부분만 추가)
        if 'openai' in step2_cost_tracker.costs_breakdown:
            if 'openai' not in total_cost_tracker.costs_breakdown:
                total_cost_tracker.costs_breakdown['openai'] = {'models': {}}
            if 'models' not in total_cost_tracker.costs_breakdown['openai']:
                total_cost_tracker.costs_breakdown['openai']['models'] = {}

            # OpenAI 모델별로 통합
            for model, model_costs in step2_cost_tracker.costs_breakdown['openai'].get('models', {}).items():
                if model not in total_cost_tracker.costs_breakdown['openai']['models']:
                    # 딕셔너리 전체 복사하여 추가
                    total_cost_tracker.costs_breakdown['openai']['models'][model] = {
                        'tokens': model_costs.get('tokens', 0),
                        'cost': model_costs.get('cost', 0.0),
                        'calls': model_costs.get('calls', 0)
                    }
                else:
                    # 기존 모델 비용에 더하기
                    existing = total_cost_tracker.costs_breakdown['openai']['models'][model]
                    existing['tokens'] = existing.get('tokens', 0) + model_costs.get('tokens', 0)
                    existing['cost'] = existing.get('cost', 0.0) + model_costs.get('cost', 0.0)
                    existing['calls'] = existing.get('calls', 0) + model_costs.get('calls', 0)
            total_cost_tracker.total_cost += step2_cost

    logger.info("Step 2: ChromaDB 삽입 완료")

    # Step 3: SQLite DB 생성
    print_step(3, 5, "SQLite DB 생성 (JSON → SQLite)")
    logger.info("Step 3: SQLite DB 생성 시작")
    if not step3_create_sqlite():
        logger.error("Step 3: SQLite DB 생성 실패")
        print("\n❌ 파이프라인 중단: SQLite 생성 실패")
        sys.exit(1)
    logger.info("Step 3: SQLite DB 생성 완료")

    # Step 4: AI 요약 생성
    print_step(4, 5, "AI 요약 생성 (Gemini API)")
    logger.info("Step 4: AI 요약 생성 시작")
    success, step4_cost_tracker = step4_generate_summaries()
    if not success:
        logger.warning("Step 4: AI 요약 생성 실패 (DB는 사용 가능)")
        print("\n⚠️  AI 요약 생성 실패 (하지만 DB는 사용 가능)")
    else:
        # Step 4 비용 로그 기록
        if step4_cost_tracker:
            step4_cost = step4_cost_tracker.total_cost
            logger.info(f"Step 4 비용: ${step4_cost:.6f} (₩{step4_cost * 1300:.2f})")

            # 전체 비용에 통합
            if 'gemini' in step4_cost_tracker.costs_breakdown:
                if 'gemini' not in total_cost_tracker.costs_breakdown:
                    total_cost_tracker.costs_breakdown['gemini'] = {'models': {}}
                if 'models' not in total_cost_tracker.costs_breakdown['gemini']:
                    total_cost_tracker.costs_breakdown['gemini']['models'] = {}

                # Gemini 모델별로 통합 (gemini-2.5-flash)
                for model, model_costs in step4_cost_tracker.costs_breakdown['gemini'].get('models', {}).items():
                    if model not in total_cost_tracker.costs_breakdown['gemini']['models']:
                        # 딕셔너리 전체 복사하여 추가
                        total_cost_tracker.costs_breakdown['gemini']['models'][model] = {
                            'input_tokens': model_costs.get('input_tokens', 0),
                            'output_tokens': model_costs.get('output_tokens', 0),
                            'cost': model_costs.get('cost', 0.0),
                            'calls': model_costs.get('calls', 0)
                        }
                    else:
                        # 기존 모델 비용에 더하기
                        existing = total_cost_tracker.costs_breakdown['gemini']['models'][model]
                        existing['input_tokens'] = existing.get('input_tokens', 0) + model_costs.get('input_tokens', 0)
                        existing['output_tokens'] = existing.get('output_tokens', 0) + model_costs.get('output_tokens', 0)
                        existing['cost'] = existing.get('cost', 0.0) + model_costs.get('cost', 0.0)
                        existing['calls'] = existing.get('calls', 0) + model_costs.get('calls', 0)
                total_cost_tracker.total_cost += step4_cost

        logger.info("Step 4: AI 요약 생성 완료")

    # Step 5: 첨부 문서 요약 생성
    print_step(5, 5, "첨부 문서 요약 생성 (Gemini File API)")
    logger.info("Step 5: 첨부 문서 요약 생성 시작")
    success, step5_cost_tracker = step5_generate_attachment_summaries()
    if not success:
        logger.warning("Step 5: 첨부 문서 요약 생성 실패 (DB는 사용 가능)")
        print("\n⚠️  첨부 문서 요약 생성 실패 (하지만 DB는 사용 가능)")
    else:
        # Step 5 비용 로그 기록
        if step5_cost_tracker:
            step5_cost = step5_cost_tracker.total_cost
            logger.info(f"Step 5 비용: ${step5_cost:.6f} (₩{step5_cost * 1300:.2f})")

            # 전체 비용에 통합 (Gemini 2.5 Flash)
            if 'gemini' in step5_cost_tracker.costs_breakdown:
                if 'gemini' not in total_cost_tracker.costs_breakdown:
                    total_cost_tracker.costs_breakdown['gemini'] = {'models': {}}
                if 'models' not in total_cost_tracker.costs_breakdown['gemini']:
                    total_cost_tracker.costs_breakdown['gemini']['models'] = {}

                # Gemini 모델별로 통합
                for model, model_costs in step5_cost_tracker.costs_breakdown['gemini'].get('models', {}).items():
                    if model not in total_cost_tracker.costs_breakdown['gemini']['models']:
                        # 딕셔너리 전체 복사하여 추가
                        total_cost_tracker.costs_breakdown['gemini']['models'][model] = {
                            'input_tokens': model_costs.get('input_tokens', 0),
                            'output_tokens': model_costs.get('output_tokens', 0),
                            'cost': model_costs.get('cost', 0.0),
                            'calls': model_costs.get('calls', 0)
                        }
                    else:
                        # 기존 모델 비용에 더하기
                        existing = total_cost_tracker.costs_breakdown['gemini']['models'][model]
                        existing['input_tokens'] = existing.get('input_tokens', 0) + model_costs.get('input_tokens', 0)
                        existing['output_tokens'] = existing.get('output_tokens', 0) + model_costs.get('output_tokens', 0)
                        existing['cost'] = existing.get('cost', 0.0) + model_costs.get('cost', 0.0)
                        existing['calls'] = existing.get('calls', 0) + model_costs.get('calls', 0)
                total_cost_tracker.total_cost += step5_cost

        logger.info("Step 5: 첨부 문서 요약 생성 완료")

    # 최종 통계
    print_final_stats()

    # 전체 비용 요약
    print("\n" + "=" * 100)
    print("💰 전체 파이프라인 비용 요약")
    print("=" * 100)
    total_cost_tracker.print_summary()
    print()

    # 로그에 비용 기록
    logger.info("=" * 100)
    logger.info("💰 전체 파이프라인 비용 요약")
    logger.info("=" * 100)
    logger.info(f"총 비용: ${total_cost_tracker.total_cost:.6f} (₩{total_cost_tracker.total_cost * 1300:.2f})")

    # 모델별 비용 로그
    if 'gemini' in total_cost_tracker.costs_breakdown:
        for model, stats in total_cost_tracker.costs_breakdown['gemini'].get('models', {}).items():
            total_tokens = stats.get('input_tokens', 0) + stats.get('output_tokens', 0)
            logger.info(f"  {model}: ${stats['cost']:.6f} ({total_tokens:,} tokens, {stats.get('calls', 0)} calls)")

    if 'openai' in total_cost_tracker.costs_breakdown:
        for model, stats in total_cost_tracker.costs_breakdown['openai'].get('models', {}).items():
            logger.info(f"  {model}: ${stats['cost']:.6f} ({stats.get('tokens', 0):,} tokens, {stats.get('calls', 0)} calls)")

    # 소요 시간
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    print(f"\n✅ 전체 파이프라인 완료!")
    print(f"   소요 시간: {minutes}분 {seconds}초")
    print(f"   완료 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n🚀 서버 실행: python app.py")
    print("=" * 100 + "\n")

    logger.info("=" * 100)
    logger.info("✅ 전체 파이프라인 완료!")
    logger.info(f"소요 시간: {minutes}분 {seconds}초")
    logger.info(f"완료 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"로그 저장 위치: {log_file}")
    logger.info("=" * 100)


if __name__ == "__main__":
    main()
