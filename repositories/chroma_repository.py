"""
ChromaDB Repository - 벡터 DB 접근

책임:
- ChromaDB 연결 관리
- 벡터 검색
- 메타데이터 조회
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import os
from utils.custom_openai_embedding import CustomOpenAIEmbeddingFunction


class ChromaRepository:
    """
    ChromaDB 데이터 접근 계층

    순수 벡터 검색 작업만 수행하며, 비즈니스 로직은 포함하지 않습니다.
    """

    def __init__(
        self,
        collection_name: str = "seoul_council_meetings",
        persist_directory: str = "./data/chroma_db"
    ):
        """
        초기화

        Args:
            collection_name: 컬렉션 이름
            persist_directory: ChromaDB 저장 경로
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self._init_client()

    def _init_client(self):
        """ChromaDB 클라이언트 및 컬렉션 초기화"""
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

        openai_ef = CustomOpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name="text-embedding-3-small"
        )

        self.collection = self.client.get_collection(
            name=self.collection_name,
            embedding_function=openai_ef
        )

    def search(
        self,
        query: str,
        n_results: int = 20,
        where_filter: Optional[Dict] = None
    ) -> Dict:
        """
        벡터 검색

        Args:
            query: 검색 쿼리
            n_results: 결과 개수
            where_filter: 메타데이터 필터 (ChromaDB where 조건)

        Returns:
            ChromaDB 검색 결과
            {
                'ids': [[chunk_id, ...]],
                'distances': [[distance, ...]],
                'metadatas': [[{metadata}, ...]],
                'documents': [[text, ...]]
            }
        """
        return self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter if where_filter else None
        )

    def get_all_speakers(self) -> List[str]:
        """
        모든 발언자 조회

        Returns:
            발언자 이름 리스트 (정렬됨)
        """
        all_data = self.collection.get(include=["metadatas"])
        speakers = set(meta["speaker"] for meta in all_data["metadatas"])
        return sorted(list(speakers))

    def get_all_dates(self) -> List[str]:
        """
        모든 회의 날짜 조회

        Returns:
            회의 날짜 리스트 (정렬됨)
        """
        all_data = self.collection.get(include=["metadatas"])
        dates = set(meta["meeting_date"] for meta in all_data["metadatas"])
        return sorted(list(dates))

    def get_collection_count(self) -> int:
        """
        컬렉션의 총 문서 개수 조회

        Returns:
            문서 개수
        """
        return self.collection.count()
