"""
ChromaDB 컬렉션 삭제 스크립트
"""

import chromadb
from chromadb.config import Settings

def delete_collection(
    collection_name: str = "seoul_council_meetings",
    persist_directory: str = "./data/chroma_db"
):
    """
    ChromaDB 컬렉션 삭제
    """
    try:
        print(f"🗑️  ChromaDB 컬렉션 삭제 중...")
        print(f"   컬렉션: {collection_name}")
        print(f"   경로: {persist_directory}\n")

        client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

        # 기존 컬렉션 목록 확인
        collections = client.list_collections()
        print(f"📋 현재 컬렉션 목록:")
        for col in collections:
            print(f"   - {col.name}")
        print()

        # 컬렉션 삭제
        try:
            client.delete_collection(name=collection_name)
            print(f"✅ 컬렉션 '{collection_name}' 삭제 완료!")
        except Exception as e:
            print(f"⚠️  컬렉션 삭제 중 오류: {e}")
            print(f"   (컬렉션이 없거나 이미 삭제되었을 수 있습니다)")

        # 삭제 후 확인
        collections_after = client.list_collections()
        print(f"\n📋 삭제 후 컬렉션 목록:")
        if collections_after:
            for col in collections_after:
                print(f"   - {col.name}")
        else:
            print(f"   (없음)")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")


if __name__ == "__main__":
    delete_collection()
