"""
파이프라인 실행 결과 자동 검증 스크립트

사용법:
    python validate_pipeline.py
"""

import json
import sqlite3
from pathlib import Path
import chromadb
from chromadb.config import Settings


def print_header(title):
    """섹션 헤더 출력"""
    print("\n" + "=" * 80)
    print(f"✅ {title}")
    print("=" * 80)


def check_logs():
    """로그 파일 검증"""
    print_header("1. 로그 파일 검증")

    log_dir = Path("logs")
    log_files = sorted(log_dir.glob("pipeline_*.log"), key=lambda x: x.stat().st_mtime, reverse=True)

    if not log_files:
        print("❌ 로그 파일이 없습니다.")
        return False

    latest_log = log_files[0]
    print(f"📄 최신 로그: {latest_log.name}")

    with open(latest_log, 'r', encoding='utf-8') as f:
        log_content = f.read()

    # Step별 완료 확인
    steps = {
        "Step 0": "데이터 초기화 완료",
        "Step 1": "JSON 생성 완료",
        "Step 2": "ChromaDB 삽입 완료",
        "Step 3": "SQLite DB 생성 완료",
        "Step 4": "AI 요약 생성 완료",
        "Step 5": "첨부 문서 요약 생성 완료"
    }

    all_passed = True
    for step, message in steps.items():
        if message in log_content:
            print(f"  ✅ {step}: {message}")
        else:
            print(f"  ❌ {step}: 완료되지 않음")
            all_passed = False

    # 비용 확인
    print("\n💰 비용 정보:")
    for line in log_content.split('\n'):
        if '비용:' in line and 'Step' in line:
            print(f"  {line.split('[INFO]')[1].strip()}")

    # 전체 완료 확인
    if "✅ 전체 파이프라인 완료!" in log_content:
        print("\n✅ 파이프라인 정상 완료")
    else:
        print("\n⚠️  파이프라인이 완료되지 않았거나 오류 발생")
        all_passed = False

    return all_passed


def check_json_files():
    """JSON 파일 검증"""
    print_header("2. JSON 파일 검증")

    result_dir = Path("data/result_txt")
    json_files = list(result_dir.glob("*.json"))

    print(f"📁 JSON 파일 수: {len(json_files)}개")

    if len(json_files) == 0:
        print("❌ JSON 파일이 없습니다.")
        return False

    # 첫 번째 파일 상세 검증
    sample_file = json_files[0]
    print(f"\n📄 샘플 파일: {sample_file.name}")

    with open(sample_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    checks = {
        "meeting_info 존재": "meeting_info" in data,
        "agenda_mapping 존재": "agenda_mapping" in data,
        "안건 수 > 0": len(data.get("agenda_mapping", [])) > 0,
    }

    for check, result in checks.items():
        status = "✅" if result else "❌"
        print(f"  {status} {check}")

    # 첨부 문서 URL 확인
    attachments_with_url = 0
    total_attachments = 0
    for agenda in data.get('agenda_mapping', []):
        for att in agenda.get('attachments', []):
            total_attachments += 1
            if att.get('download_url'):
                attachments_with_url += 1

    if total_attachments > 0:
        print(f"  ✅ download_url 있는 첨부 문서: {attachments_with_url}/{total_attachments}개")
    else:
        print(f"  ℹ️  첨부 문서 없음")

    return all(checks.values())


def check_chromadb():
    """ChromaDB 검증"""
    print_header("3. ChromaDB 검증")

    try:
        client = chromadb.PersistentClient(
            path='data/chroma_db',
            settings=Settings(anonymized_telemetry=False)
        )

        collection = client.get_collection('seoul_council_meetings')
        count = collection.count()

        print(f"📊 ChromaDB 청크 수: {count:,}개")

        if count > 100:
            print("✅ 정상: 충분한 데이터 저장됨")
            return True
        else:
            print("⚠️  경고: 데이터가 너무 적음")
            return False

    except Exception as e:
        print(f"❌ ChromaDB 오류: {e}")
        return False


def check_sqlite():
    """SQLite DB 검증"""
    print_header("4. SQLite DB 검증")

    db_path = 'data/sqlite_DB/agendas.db'
    if not Path(db_path).exists():
        print(f"❌ DB 파일이 없습니다: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 전체 안건 수
    cursor.execute('SELECT COUNT(*) FROM agendas')
    total = cursor.fetchone()[0]
    print(f"📊 전체 안건 수: {total}개")

    if total == 0:
        print("❌ 안건이 없습니다.")
        conn.close()
        return False

    # AI 요약 확인
    cursor.execute('SELECT COUNT(*) FROM agendas WHERE ai_summary IS NOT NULL AND ai_summary != ""')
    with_summary = cursor.fetchone()[0]
    print(f"✅ AI 요약 있는 안건: {with_summary}개 ({with_summary/total*100:.1f}%)")

    # 핵심 의제 확인
    cursor.execute('SELECT COUNT(*) FROM agendas WHERE key_issues IS NOT NULL AND key_issues != ""')
    with_issues = cursor.fetchone()[0]
    print(f"✅ 핵심 의제 있는 안건: {with_issues}개 ({with_issues/total*100:.1f}%)")

    # 첨부 문서 확인
    cursor.execute('SELECT COUNT(*) FROM agendas WHERE attachments IS NOT NULL AND attachments != ""')
    with_attachments = cursor.fetchone()[0]
    print(f"📎 첨부 문서 있는 안건: {with_attachments}개")

    # 첨부 문서 요약 확인
    cursor.execute('''
        SELECT attachments FROM agendas
        WHERE attachments IS NOT NULL AND attachments != ""
        LIMIT 5
    ''')

    attachment_summary_count = 0
    attachment_url_count = 0
    total_checked = 0

    for row in cursor.fetchall():
        attachments = json.loads(row[0])
        for att in attachments:
            total_checked += 1
            if att.get('download_url'):
                attachment_url_count += 1
            if att.get('summary'):
                attachment_summary_count += 1

    if total_checked > 0:
        print(f"✅ 첨부 문서 URL: {attachment_url_count}/{total_checked}개 ({attachment_url_count/total_checked*100:.1f}%)")
        print(f"✅ 첨부 문서 요약: {attachment_summary_count}/{total_checked}개 ({attachment_summary_count/total_checked*100:.1f}%)")

    conn.close()
    return True


def main():
    """메인 함수"""
    print("=" * 80)
    print("🔍 파이프라인 검증 시작")
    print("=" * 80)

    results = {
        "로그 파일": check_logs(),
        "JSON 파일": check_json_files(),
        "ChromaDB": check_chromadb(),
        "SQLite DB": check_sqlite(),
    }

    # 최종 결과
    print("\n" + "=" * 80)
    print("📊 검증 결과 요약")
    print("=" * 80)

    for category, result in results.items():
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{status} - {category}")

    all_passed = all(results.values())

    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 모든 검증 통과! 전체 파이프라인 실행 가능합니다.")
        print("\n다음 명령어로 전체 52개 파일 처리:")
        print("  python rebuild_all_db.py")
    else:
        print("⚠️  일부 검증 실패. 로그를 확인하고 문제를 해결하세요.")
    print("=" * 80)


if __name__ == "__main__":
    main()
