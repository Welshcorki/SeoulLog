"""
ChromaDB에서 회의록 검색 스크립트

사용법:
    python search_chromadb.py
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
from datetime import datetime
import os
from dotenv import load_dotenv
from utils.custom_openai_embedding import CustomOpenAIEmbeddingFunction

load_dotenv()


class MeetingSearcher:
    """
    회의록 검색 클래스
    """

    def __init__(
        self,
        collection_name: str = "seoul_council_meetings",
        persist_directory: str = "./data/chroma_db"
    ):
        """
        검색기 초기화

        Args:
            collection_name: ChromaDB 컬렉션 이름
            persist_directory: ChromaDB 저장 경로
        """
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

        # OpenAI Embedding 함수 생성 (삽입할 때와 동일한 모델 사용)
        openai_ef = CustomOpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name="text-embedding-3-small"
        )

        self.collection = self.client.get_collection(
            name=collection_name,
            embedding_function=openai_ef  # 동일한 Embedding 함수 사용
        )
        print(f"✓ 컬렉션 로드: {collection_name}")
        print(f"✓ Embedding 모델: text-embedding-3-small")
        print(f"✓ 총 문서 수: {self.collection.count()}개\n")

    def search(
        self,
        query: str,
        n_results: int = 5,
        speaker: Optional[str] = None,
        meeting_date: Optional[str] = None,
        agenda_keyword: Optional[str] = None
    ) -> Dict:
        """
        의미 기반 검색 (Semantic Search)

        Args:
            query: 검색 질문
            n_results: 반환할 결과 개수
            speaker: 발언자 필터 (예: "도시기반시설본부장 안대희")
            meeting_date: 회의 날짜 필터 (예: "2025.09.01")
            agenda_keyword: 안건 키워드 필터 (예: "예산")

        Returns:
            검색 결과 딕셔너리
        """
        # 필터 조건 구성
        where = {}
        if speaker:
            where["speaker"] = speaker
        if meeting_date:
            where["meeting_date"] = meeting_date
        if agenda_keyword:
            where["agenda"] = {"$contains": agenda_keyword}

        # 검색 실행
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where if where else None,
            include=["documents", "metadatas", "distances"]
        )

        return self._format_results(query, results, n_results)

    def search_by_speaker(
        self,
        query: str,
        speaker: str,
        n_results: int = 5
    ) -> Dict:
        """
        특정 발언자의 발언만 검색

        Args:
            query: 검색 질문
            speaker: 발언자 이름
            n_results: 반환할 결과 개수

        Returns:
            검색 결과
        """
        return self.search(query, n_results=n_results, speaker=speaker)

    def search_by_date(
        self,
        query: str,
        meeting_date: str,
        n_results: int = 5
    ) -> Dict:
        """
        특정 날짜 회의에서만 검색

        Args:
            query: 검색 질문
            meeting_date: 회의 날짜 (예: "2025.09.01")
            n_results: 반환할 결과 개수

        Returns:
            검색 결과
        """
        return self.search(query, n_results=n_results, meeting_date=meeting_date)

    def search_by_agenda(
        self,
        query: str,
        agenda_keyword: str,
        n_results: int = 5
    ) -> Dict:
        """
        특정 안건 관련 내용만 검색

        Args:
            query: 검색 질문
            agenda_keyword: 안건 키워드 (예: "예산", "현안업무")
            n_results: 반환할 결과 개수

        Returns:
            검색 결과
        """
        return self.search(query, n_results=n_results, agenda_keyword=agenda_keyword)

    def get_all_speakers(self) -> List[str]:
        """
        모든 발언자 목록 조회

        Returns:
            발언자 이름 리스트
        """
        # ChromaDB에서 모든 문서의 메타데이터 가져오기
        all_data = self.collection.get(include=["metadatas"])
        speakers = set(meta["speaker"] for meta in all_data["metadatas"])
        return sorted(list(speakers))

    def get_all_dates(self) -> List[str]:
        """
        모든 회의 날짜 목록 조회

        Returns:
            회의 날짜 리스트
        """
        all_data = self.collection.get(include=["metadatas"])
        dates = set(meta["meeting_date"] for meta in all_data["metadatas"])
        return sorted(list(dates))

    def get_meeting_info(self, meeting_date: str) -> Dict:
        """
        특정 날짜 회의 정보 조회

        Args:
            meeting_date: 회의 날짜

        Returns:
            회의 정보
        """
        results = self.collection.get(
            where={"meeting_date": meeting_date},
            limit=1,
            include=["metadatas"]
        )

        if results["metadatas"]:
            meta = results["metadatas"][0]
            return {
                "title": meta["meeting_title"],
                "date": meta["meeting_date"],
                "url": meta["meeting_url"]
            }
        return {}

    def _format_results(self, query: str, results: Dict, n_results: int) -> Dict:
        """
        검색 결과 포맷팅

        Args:
            query: 검색 질문
            results: ChromaDB 검색 결과
            n_results: 요청한 결과 개수

        Returns:
            포맷팅된 결과
        """
        formatted = {
            "query": query,
            "total_results": len(results["documents"][0]),
            "results": []
        }

        for i in range(len(results["documents"][0])):
            distance = results["distances"][0][i]

            # Cosine distance (0~2)를 cosine similarity (0~1)로 올바르게 변환
            # distance 0 = similarity 1.0 (완전 일치)
            # distance 1 = similarity 0.5 (직각)
            # distance 2 = similarity 0.0 (정반대)
            cosine_similarity = (2 - distance) / 2
            similarity_score = max(0.0, min(1.0, cosine_similarity))

            result = {
                "rank": i + 1,
                "similarity": similarity_score,  # 수정된 계산
                "speaker": results["metadatas"][0][i].get("speaker", ""),
                "agenda": results["metadatas"][0][i].get("agenda", ""),
                "meeting_title": results["metadatas"][0][i].get("meeting_title", ""),
                "meeting_date": results["metadatas"][0][i].get("meeting_date", ""),
                "text": results["documents"][0][i],
                "meeting_url": results["metadatas"][0][i].get("meeting_url", ""),
                "chunk_index": results["metadatas"][0][i].get("chunk_index", 0)
            }
            formatted["results"].append(result)

        return formatted

    def print_results(self, results: Dict):
        """
        검색 결과 출력

        Args:
            results: 검색 결과
        """
        print(f"🔍 검색어: \"{results['query']}\"")
        print(f"📊 결과: {results['total_results']}건\n")
        print("="*80)

        for result in results["results"]:
            print(f"\n[{result['rank']}] 유사도: {result['similarity']:.3f}")
            print(f"📅 회의: {result['meeting_title']}")
            print(f"🗣️  발언자: {result['speaker']}")
            print(f"📋 안건: {result['agenda']}")
            print(f"💬 내용:")
            print(f"   {result['text'][:200]}...")
            print(f"🔗 URL: {result['meeting_url']}")
            print("-"*80)


def demo_search():
    """
    검색 데모
    """
    # 검색기 초기화
    searcher = MeetingSearcher()

    print("="*80)
    print("검색 예시 1: 기본 의미 검색")
    print("="*80)
    results = searcher.search("동북선 공정률이 어떻게 되나요?", n_results=3)
    searcher.print_results(results)

    print("\n\n")
    print("="*80)
    print("검색 예시 2: 발언자 필터")
    print("="*80)
    results = searcher.search_by_speaker(
        query="안전 관리",
        speaker="도시기반시설본부장 안대희",
        n_results=3
    )
    searcher.print_results(results)

    print("\n\n")
    print("="*80)
    print("검색 예시 3: 안건 필터")
    print("="*80)
    results = searcher.search_by_agenda(
        query="예산",
        agenda_keyword="추가경정예산안",
        n_results=3
    )
    searcher.print_results(results)

    print("\n\n")
    print("="*80)
    print("검색 예시 4: 복합 검색")
    print("="*80)
    results = searcher.search(
        query="싱크홀",
        speaker="윤기섭 위원",
        n_results=3
    )
    searcher.print_results(results)

    print("\n\n")
    print("="*80)
    print("메타데이터 조회")
    print("="*80)
    print(f"\n📝 발언자 목록:")
    for speaker in searcher.get_all_speakers():
        print(f"  - {speaker}")

    print(f"\n📅 회의 날짜:")
    for date in searcher.get_all_dates():
        print(f"  - {date}")
        meeting_info = searcher.get_meeting_info(date)
        print(f"    제목: {meeting_info['title']}")


if __name__ == "__main__":
    demo_search()
