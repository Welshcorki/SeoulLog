"""
안건별 SQLite 데이터베이스 생성

JSON 파일에서 안건별로 데이터를 그룹핑하여 SQLite DB에 저장합니다.
ChromaDB는 벡터 검색용, SQLite는 메타데이터 및 전체 텍스트 저장용입니다.
"""

import json
import sqlite3
from pathlib import Path
from collections import Counter
from datetime import datetime


def create_database():
    """SQLite 데이터베이스 및 테이블 생성"""

    # sqlite_DB 폴더 생성 (없으면)
    db_dir = Path('sqlite_DB')
    db_dir.mkdir(exist_ok=True)

    conn = sqlite3.connect('sqlite_DB/agendas.db')
    cursor = conn.cursor()

    # 안건 테이블
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS agendas (
        agenda_id TEXT PRIMARY KEY,
        agenda_title TEXT NOT NULL,
        meeting_title TEXT,
        meeting_date TEXT,
        meeting_url TEXT,
        main_speaker TEXT,
        all_speakers TEXT,
        speaker_count INTEGER,
        chunk_count INTEGER,
        chunk_ids TEXT,
        combined_text TEXT,
        status TEXT DEFAULT '심사중',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 안건-청크 매핑 테이블 (옵션)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS agenda_chunks (
        chunk_id TEXT PRIMARY KEY,
        agenda_id TEXT,
        chunk_index INTEGER,
        speaker TEXT,
        text_preview TEXT,
        FOREIGN KEY (agenda_id) REFERENCES agendas(agenda_id)
    )
    ''')

    conn.commit()
    print("✅ 데이터베이스 테이블 생성 완료")

    return conn


def group_chunks_by_agenda(chunks):
    """청크를 안건별로 그룹핑"""

    agenda_groups = {}

    for idx, chunk in enumerate(chunks):
        agenda = chunk.get('agenda') or "기타발언"

        if agenda not in agenda_groups:
            agenda_groups[agenda] = {
                'texts': [],
                'speakers': [],
                'chunk_indices': []
            }

        agenda_groups[agenda]['texts'].append(chunk['text'])
        agenda_groups[agenda]['speakers'].append(chunk.get('speaker', '발언자 없음'))
        agenda_groups[agenda]['chunk_indices'].append(idx)

    return agenda_groups


def insert_agendas_to_db(conn):
    """JSON 파일에서 안건 정보를 추출하여 DB에 삽입"""

    cursor = conn.cursor()

    # 기존 데이터 삭제 (재실행 시)
    cursor.execute('DELETE FROM agendas')
    cursor.execute('DELETE FROM agenda_chunks')
    conn.commit()

    result_txt_dir = Path("result_txt")
    json_files = list(result_txt_dir.glob("*.json"))

    print(f"\n📁 발견된 JSON 파일: {len(json_files)}개")

    total_agendas = 0

    for json_file in json_files:
        print(f"\n📄 처리 중: {json_file.name}")

        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        meeting_info = data.get('meeting_info', {})
        chunks = data.get('chunks', [])
        meeting_id = json_file.stem

        # 안건별로 그룹핑
        agenda_groups = group_chunks_by_agenda(chunks)

        print(f"   안건 수: {len(agenda_groups)}개")

        # 각 안건을 DB에 삽입
        for agenda_index, (agenda, agenda_data) in enumerate(agenda_groups.items()):
            # 안건 ID 생성
            agenda_id = f"{meeting_id}_agenda_{agenda_index:03d}"

            # 전체 텍스트 병합
            combined_text = "\n\n".join(agenda_data['texts'])

            # 발언자 목록 (중복 제거, 순서 유지)
            unique_speakers = []
            for speaker in agenda_data['speakers']:
                if speaker not in unique_speakers:
                    unique_speakers.append(speaker)

            # 주 발언자 (가장 많이 발언한 사람)
            speaker_counts = Counter(agenda_data['speakers'])
            main_speaker = speaker_counts.most_common(1)[0][0] if speaker_counts else "발언자 없음"

            # chunk_ids 생성
            chunk_ids = ','.join([
                f"{meeting_id}_chunk_{idx:04d}"
                for idx in agenda_data['chunk_indices']
            ])

            # 안건 테이블에 삽입
            cursor.execute('''
                INSERT INTO agendas (
                    agenda_id, agenda_title, meeting_title, meeting_date, meeting_url,
                    main_speaker, all_speakers, speaker_count, chunk_count,
                    chunk_ids, combined_text, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                agenda_id,
                agenda,
                meeting_info.get('title', ''),
                meeting_info.get('date', ''),
                meeting_info.get('url', ''),
                main_speaker,
                ', '.join(unique_speakers),
                len(unique_speakers),
                len(agenda_data['texts']),
                chunk_ids,
                combined_text,
                '심사중'  # 기본 상태
            ))

            # 안건-청크 매핑 테이블에 삽입
            for chunk_idx in agenda_data['chunk_indices']:
                chunk_id = f"{meeting_id}_chunk_{chunk_idx:04d}"
                chunk = chunks[chunk_idx]

                cursor.execute('''
                    INSERT INTO agenda_chunks (
                        chunk_id, agenda_id, chunk_index, speaker, text_preview
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    chunk_id,
                    agenda_id,
                    chunk_idx,
                    chunk.get('speaker', ''),
                    chunk['text'][:200]  # 앞 200자만
                ))

            total_agendas += 1
            print(f"   ✓ [{agenda_index + 1}] {agenda[:50]}... "
                  f"(발언자: {len(unique_speakers)}명, 청크: {len(agenda_data['texts'])}개)")

        conn.commit()

    print("\n" + "=" * 80)
    print(f"✅ 완료! 총 {total_agendas}개 안건이 저장되었습니다.")
    print("=" * 80)

    # 통계 출력
    cursor.execute('SELECT COUNT(*) FROM agendas')
    agenda_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM agenda_chunks')
    chunk_count = cursor.fetchone()[0]

    print(f"\n📊 데이터베이스 통계:")
    print(f"   안건 수: {agenda_count}개")
    print(f"   청크 수: {chunk_count}개")
    print(f"   저장 파일: sqlite_DB/agendas.db")
    print()


def view_sample_data(conn):
    """샘플 데이터 확인"""

    cursor = conn.cursor()

    print("📋 샘플 안건 (최대 3개):")
    print("-" * 80)

    cursor.execute('SELECT * FROM agendas LIMIT 3')
    agendas = cursor.fetchall()

    for agenda in agendas:
        print(f"\nAgenda ID: {agenda[0]}")
        print(f"제목: {agenda[1][:60]}...")
        print(f"회의: {agenda[2]}")
        print(f"날짜: {agenda[3]}")
        print(f"주 발언자: {agenda[5]}")
        print(f"전체 발언자: {agenda[6]}")
        print(f"청크 수: {agenda[8]}개")
        print(f"상태: {agenda[11]}")
        print("-" * 80)


if __name__ == "__main__":
    print("=" * 80)
    print("안건별 SQLite 데이터베이스 생성")
    print("=" * 80)
    print()

    # 1. 데이터베이스 생성
    conn = create_database()

    # 2. 안건 데이터 삽입
    insert_agendas_to_db(conn)

    # 3. 샘플 데이터 확인
    view_sample_data(conn)

    # 4. 연결 종료
    conn.close()

    print("\n✅ 모든 작업 완료!")
