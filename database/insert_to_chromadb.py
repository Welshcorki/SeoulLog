"""
JSON 메타데이터를 ChromaDB에 삽입하는 스크립트

사용법:
    python insert_to_chromadb.py
"""

import json
import chromadb
from chromadb.config import Settings
from pathlib import Path
from typing import List, Dict
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from utils.custom_openai_embedding import CustomOpenAIEmbeddingFunction

load_dotenv()


def load_json_metadata(json_path: str) -> Dict:
    """
    JSON 파일에서 메타데이터 로드

    Args:
        json_path: JSON 파일 경로

    Returns:
        메타데이터 딕셔너리
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def insert_to_chromadb(
    json_path: str,
    collection_name: str = "seoul_council_meetings",
    persist_directory: str = "./data/chroma_db"
):
    """
    JSON 메타데이터를 ChromaDB에 삽입

    Args:
        json_path: JSON 파일 경로
        collection_name: ChromaDB 컬렉션 이름
        persist_directory: ChromaDB 저장 경로
    """

    # 1. JSON 로드
    print(f"📂 JSON 로드 중: {json_path}")
    data = load_json_metadata(json_path)

    meeting_info = data['meeting_info']
    chunks = data['chunks']

    # meeting_id 추출 (파일명에서)
    meeting_id = Path(json_path).stem

    print(f"✓ 회의: {meeting_info['title']}")
    print(f"✓ 총 {len(chunks)}개 chunk\n")

    # 2. ChromaDB 클라이언트 생성
    print(f"🗄️  ChromaDB 연결 중...")
    client = chromadb.PersistentClient(
        path=persist_directory,
        settings=Settings(anonymized_telemetry=False)
    )

    # 2-1. OpenAI Embedding 함수 생성
    openai_ef = CustomOpenAIEmbeddingFunction(
        api_key=os.getenv("OPENAI_API_KEY"),
        model_name="text-embedding-3-small"  # OpenAI Embedding 모델
    )
    print(f"✓ Embedding 모델: text-embedding-3-small")

    # 3. 컬렉션 생성 또는 가져오기
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=openai_ef,  # OpenAI Embedding 사용
        metadata={
            "description": "서울시의회 회의록 청크",
            "hnsw:space": "cosine"  # 코사인 유사도
        }
    )

    print(f"✓ 컬렉션: {collection_name}")
    print(f"✓ 기존 문서 수: {collection.count()}개\n")

    # 4. 안건별 인덱싱 (agenda_id 생성)
    # 같은 agenda를 가진 청크들을 그룹핑하여 agenda_id 부여
    agenda_to_id = {}  # {agenda_name: agenda_id}
    agenda_counter = 0

    for chunk in chunks:
        agenda = chunk['agenda'] if chunk['agenda'] else "기타발언"
        if agenda not in agenda_to_id:
            agenda_to_id[agenda] = f"{meeting_id}_agenda_{agenda_counter:03d}"
            agenda_counter += 1

    print(f"📋 발견된 안건: {len(agenda_to_id)}개")
    for agenda, agenda_id in agenda_to_id.items():
        print(f"   - {agenda_id}: {agenda[:50]}...")
    print()

    # 5. 배치 처리 준비
    documents = []
    metadatas = []
    ids = []

    for idx, chunk in enumerate(chunks):
        # 고유 ID 생성: meeting_id + chunk 번호
        chunk_id = f"{meeting_id}_chunk_{idx:04d}"

        # document: 검색 대상 텍스트
        document = chunk['text']

        # 이 청크가 속한 안건 ID
        agenda = chunk['agenda'] if chunk['agenda'] else "기타발언"
        agenda_id = agenda_to_id[agenda]

        # metadata: 필터링/표시용 메타데이터
        metadata = {
            # 회의 정보
            "meeting_title": meeting_info['title'],
            "meeting_date": meeting_info['date'],
            "meeting_url": meeting_info['url'],

            # 청크 정보
            "speaker": chunk['speaker'],
            "agenda": chunk['agenda'] if chunk['agenda'] else "없음",
            "agenda_id": agenda_id,  # ⭐ 안건 ID 추가
            "chunk_index": idx,

            # 파일 정보
            "source_file": meeting_id
        }

        documents.append(document)
        metadatas.append(metadata)
        ids.append(chunk_id)

    # 5. 배치 삽입
    print(f"💾 ChromaDB에 삽입 중...")
    batch_size = 100  # 한 번에 100개씩 처리

    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i:i+batch_size]
        batch_metas = metadatas[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]

        collection.add(
            documents=batch_docs,
            metadatas=batch_metas,
            ids=batch_ids
        )

        print(f"  ✓ {i+len(batch_docs)}/{len(documents)} 삽입 완료")

    print(f"\n✅ 삽입 완료!")
    print(f"📊 최종 문서 수: {collection.count()}개")

    # 6. 삽입 결과 샘플 확인
    print(f"\n📋 삽입 결과 샘플:")
    results = collection.get(
        ids=[ids[0]],
        include=["documents", "metadatas"]
    )

    print(f"  ID: {ids[0]}")
    print(f"  발언자: {results['metadatas'][0]['speaker']}")
    print(f"  안건: {results['metadatas'][0]['agenda']}")
    print(f"  내용: {results['documents'][0][:100]}...")


def insert_all_jsons(
    json_dir: str = "data/result_txt",
    collection_name: str = "seoul_council_meetings",
    persist_directory: str = "./data/chroma_db"
):
    """
    result_txt 폴더의 모든 JSON 파일을 ChromaDB에 삽입

    Args:
        json_dir: JSON 파일들이 있는 디렉토리
        collection_name: ChromaDB 컬렉션 이름
        persist_directory: ChromaDB 저장 경로
    """
    json_path = Path(json_dir)
    json_files = list(json_path.glob("*.json"))

    print(f"📁 {len(json_files)}개 JSON 파일 발견\n")
    print("="*80)

    for idx, json_file in enumerate(json_files, 1):
        print(f"\n[{idx}/{len(json_files)}] {json_file.name}")
        print("-"*80)

        insert_to_chromadb(
            json_path=str(json_file),
            collection_name=collection_name,
            persist_directory=persist_directory
        )

        print("="*80)

    print(f"\n🎉 전체 삽입 완료!")


if __name__ == "__main__":
    # 단일 파일 테스트
    # insert_to_chromadb("result_txt/meeting_20251117_195512.json")

    # 전체 파일 삽입
    insert_all_jsons()
