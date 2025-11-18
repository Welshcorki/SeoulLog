"""
안건별 ChromaDB 컬렉션 생성

JSON 파일의 청크들을 안건(agenda) 단위로 그룹핑하여
'seoul_council_agendas' 컬렉션에 저장합니다.

용도: 검색 UI (안건 단위 표시)
"""

import json
import os
from pathlib import Path
from typing import Dict, List
import chromadb
from chromadb.config import Settings
from custom_openai_embedding import CustomOpenAIEmbeddingFunction
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RESULT_TXT_DIR = Path("result_txt")
CHROMA_DB_DIR = "./chroma_db"
COLLECTION_NAME = "seoul_council_agendas"  # 안건별 컬렉션


def group_chunks_by_agenda(chunks: List[Dict]) -> Dict[str, Dict]:
    """
    청크들을 안건별로 그룹핑

    Args:
        chunks: JSON 파일의 chunks 리스트

    Returns:
        안건별로 그룹핑된 딕셔너리
        {
            "안건명": {
                "texts": [...],
                "speakers": [...],
                "chunk_indices": [...]
            }
        }
    """
    agenda_groups = {}

    for idx, chunk in enumerate(chunks):
        # agenda가 없으면 "기타발언"으로 분류
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


def insert_agendas_to_chromadb():
    """
    안건별로 그룹핑된 데이터를 ChromaDB에 저장
    """
    print("=" * 80)
    print("안건별 ChromaDB 컬렉션 생성")
    print("=" * 80)
    print()

    # ChromaDB 클라이언트 생성
    client = chromadb.PersistentClient(
        path=CHROMA_DB_DIR,
        settings=Settings(anonymized_telemetry=False)
    )

    # Embedding 함수
    embedding_function = CustomOpenAIEmbeddingFunction(
        api_key=OPENAI_API_KEY,
        model_name="text-embedding-3-small"
    )

    # 컬렉션 생성 (기존 것이 있으면 삭제 후 재생성)
    try:
        client.delete_collection(name=COLLECTION_NAME)
        print(f"⚠️  기존 컬렉션 '{COLLECTION_NAME}' 삭제")
    except:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function,
        metadata={"description": "서울시의회 안건별 그룹핑 컬렉션"}
    )

    print(f"✅ 컬렉션 '{COLLECTION_NAME}' 생성 완료\n")

    # JSON 파일들 처리
    json_files = list(RESULT_TXT_DIR.glob("*.json"))
    print(f"📁 발견된 JSON 파일: {len(json_files)}개\n")

    total_agendas = 0

    for json_file in json_files:
        print(f"📄 처리 중: {json_file.name}")

        # JSON 파일 읽기
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        meeting_info = data.get('meeting_info', {})
        chunks = data.get('chunks', [])

        # meeting_id 생성 (파일명에서 추출)
        meeting_id = json_file.stem

        # 안건별로 그룹핑
        agenda_groups = group_chunks_by_agenda(chunks)

        print(f"   안건 수: {len(agenda_groups)}개")

        # 각 안건을 ChromaDB에 저장
        for agenda_index, (agenda, data_dict) in enumerate(agenda_groups.items()):
            # 모든 텍스트 병합
            combined_text = "\n\n".join(data_dict['texts'])

            # 토큰 제한 고려: 텍스트가 너무 길면 자르기
            # OpenAI embedding 모델 최대: 8192 토큰 (약 30,000자)
            MAX_CHARS = 30000
            if len(combined_text) > MAX_CHARS:
                combined_text = combined_text[:MAX_CHARS] + "\n\n[...텍스트가 너무 길어 일부만 표시됩니다...]"
                print(f"   ⚠️  안건 텍스트가 너무 길어서 {MAX_CHARS}자로 자름")

            # 발언자 목록 (중복 제거, 순서 유지)
            unique_speakers = []
            for speaker in data_dict['speakers']:
                if speaker not in unique_speakers:
                    unique_speakers.append(speaker)

            # 주 발언자 (가장 많이 발언한 사람)
            from collections import Counter
            speaker_counts = Counter(data_dict['speakers'])
            main_speaker = speaker_counts.most_common(1)[0][0] if speaker_counts else "발언자 없음"

            # 메타데이터 생성
            metadata = {
                "agenda_id": f"{meeting_id}_agenda_{agenda_index:03d}",
                "agenda": agenda,
                "meeting_title": meeting_info.get('title', ''),
                "meeting_date": meeting_info.get('date', ''),
                "meeting_url": meeting_info.get('url', ''),
                "main_speaker": main_speaker,
                "speakers": ", ".join(unique_speakers),
                "speaker_count": len(unique_speakers),
                "chunk_count": len(data_dict['texts']),
                "chunk_indices": ",".join(map(str, data_dict['chunk_indices'])),
                "source_file": meeting_id
            }

            # ChromaDB에 추가
            doc_id = f"{meeting_id}_agenda_{agenda_index:03d}"

            collection.add(
                documents=[combined_text],
                metadatas=[metadata],
                ids=[doc_id]
            )

            total_agendas += 1
            print(f"   ✓ [{agenda_index + 1}] {agenda[:30]}... (발언자: {len(unique_speakers)}명, 청크: {len(data_dict['texts'])}개)")

        print()

    print("=" * 80)
    print(f"✅ 완료! 총 {total_agendas}개 안건이 저장되었습니다.")
    print("=" * 80)
    print()
    print(f"📊 컬렉션 정보:")
    print(f"   이름: {COLLECTION_NAME}")
    print(f"   문서 수: {collection.count()}")
    print(f"   저장 경로: {CHROMA_DB_DIR}")
    print()


if __name__ == "__main__":
    insert_agendas_to_chromadb()
