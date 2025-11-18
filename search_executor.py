"""
Search Executor - 검증된 메타데이터로 실제 검색 수행

Metadata Validator를 통과한 메타데이터를 사용하여
ChromaDB에서 실제 검색을 수행합니다.
"""

from typing import Dict, List, Optional
from search_chromadb import MeetingSearcher


class SearchExecutor:
    """
    검색 실행기
    """

    def __init__(
        self,
        collection_name: str = "seoul_council_meetings",
        persist_directory: str = "./chroma_db"
    ):
        """
        초기화

        Args:
            collection_name: ChromaDB 컬렉션 이름
            persist_directory: ChromaDB 저장 경로
        """
        self.searcher = MeetingSearcher(
            collection_name=collection_name,
            persist_directory=persist_directory
        )
        print(f"✅ Search Executor 초기화 완료\n")

    def execute(
        self,
        metadata: Dict,
        n_results: int = 10,
        original_query: str = None
    ) -> List[Dict]:
        """
        검증된 메타데이터로 검색 수행

        Args:
            metadata: 검증된 메타데이터 (Query Analyzer → Metadata Validator 통과)
            n_results: 반환할 결과 수
            original_query: 원본 사용자 쿼리 (우선 사용)

        Returns:
            검색 결과 리스트
        """
        print(f"🔍 검색 실행 중...")
        print(f"   원본 쿼리: {original_query}")
        print(f"   topic: {metadata.get('topic')}")
        print(f"   speaker: {metadata.get('speaker')}")
        print(f"   meeting_date: {metadata.get('meeting_date')}")
        print(f"   agenda: {metadata.get('agenda')}\n")

        # 원본 쿼리를 우선 사용, 없으면 topic 사용
        # 이렇게 하면 사용자가 입력한 그대로 벡터 검색
        query = original_query or metadata.get('topic') or ""

        # 검색 수행
        search_results = self.searcher.search(
            query=query,
            speaker=metadata.get('speaker'),
            meeting_date=metadata.get('meeting_date'),
            agenda_keyword=metadata.get('agenda'),
            n_results=n_results
        )

        # 결과 포맷팅
        results = []
        if search_results and 'results' in search_results:
            for i, result in enumerate(search_results['results'], 1):
                results.append({
                    'rank': i,
                    'speaker': result.get('speaker', ''),
                    'meeting_date': result.get('meeting_date', ''),
                    'meeting_title': result.get('meeting_title', ''),
                    'agenda': result.get('agenda', ''),
                    'text': result.get('text', ''),
                    'meeting_url': result.get('meeting_url', ''),
                    'similarity': result.get('similarity', 0.0),  # distance → similarity로 수정
                    'chunk_index': result.get('chunk_index', 0)
                })

        print(f"✅ 검색 완료: {len(results)}건 발견\n")
        return results


def test_search_executor():
    """
    Search Executor 테스트
    """
    print("="*80)
    print("Search Executor 테스트")
    print("="*80)
    print()

    executor = SearchExecutor()

    # 테스트 케이스
    test_cases = [
        {
            "name": "발언자 + 주제 검색",
            "metadata": {
                "speaker": "윤기섭 위원",
                "topic": "싱크홀",
                "agenda": None,
                "meeting_date": None,
                "intent": "질의_내용_찾기"
            }
        },
        {
            "name": "주제만 검색",
            "metadata": {
                "speaker": None,
                "topic": "안전",
                "agenda": None,
                "meeting_date": None,
                "intent": "주제_검색"
            }
        },
        {
            "name": "발언자만 검색 (topic=None)",
            "metadata": {
                "speaker": "도시기반시설본부장 안대희",
                "topic": None,
                "agenda": None,
                "meeting_date": None,
                "intent": "질의_내용_찾기"
            }
        },
        {
            "name": "날짜로 검색",
            "metadata": {
                "speaker": None,
                "topic": None,
                "agenda": None,
                "meeting_date": "2025.09.01",
                "intent": "정보_조회"
            }
        }
    ]

    for i, tc in enumerate(test_cases, 1):
        print(f"[테스트 {i}/{len(test_cases)}] {tc['name']}")
        print("="*80)

        results = executor.execute(tc['metadata'], n_results=3)

        if results:
            print(f"📊 검색 결과 ({len(results)}건):\n")
            for result in results:
                print(f"  [{result['rank']}] {result['speaker']}")
                print(f"      📅 {result['meeting_date']} | 🏛️ {result['meeting_title']}")
                print(f"      📋 {result['agenda']}")
                print(f"      💬 {result['text'][:100]}...")
                print(f"      🔗 {result['meeting_url']}")
                print(f"      📊 거리: {result['distance']:.4f}")
                print()
        else:
            print("❌ 검색 결과 없음\n")

        print()


if __name__ == "__main__":
    test_search_executor()
