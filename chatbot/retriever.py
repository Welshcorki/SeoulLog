import sys
from pathlib import Path
from collections import defaultdict
from typing import List, Dict

# 프로젝트 루트를 Python path에 추가
sys.path.append(str(Path(__file__).parent.parent))

from utils.search_chromadb import MeetingSearcher
from search.bm25_retriever import BM25Retriever

class Retriever:
    """
    BM25 (키워드)와 Chroma (의미) 검색을 '청크' 단위로 결합하는 앙상블 리트리버
    """
    def __init__(self):
        """
        앙상블 리트리버를 초기화하고, 각 리트리버를 로드합니다.
        """
        print("앙상블 리트리버(청크 단위) 초기화 중...")
        try:
            self.chroma_searcher = MeetingSearcher()
            self.bm25_retriever = BM25Retriever() # 청크 단위 리트리버
            print("앙상블 리트리버(청크 단위) 초기화 완료.")
        except Exception as e:
            print(f"앙상블 리트리버 초기화 실패: {e}")
            self.chroma_searcher = None
            self.bm25_retriever = None

    def retrieve_documents(self, query: str, n_results: int = 5, k: int = 60) -> List[Dict]:
        """
        주어진 쿼리로 청크를 검색하고, RRF를 사용하여 결과를 융합합니다.

        Args:
            query: 검색할 쿼리 (재작성된 질문)
            n_results: 반환할 최종 결과 수
            k: RRF 랭킹 상수 (일반적으로 60 사용)

        Returns:
            융합되고 재정렬된 청크 딕셔너리 리스트
        """
        if not self.chroma_searcher or not self.bm25_retriever:
            print("오류: 리트리버가 제대로 초기화되지 않았습니다.")
            return []

        print(f"🔍 앙상블 검색(청크 단위) 중... (query: {query})")
        
        # 1. 각 리트리버에서 후보 청크군 검색
        candidate_count = n_results * 5
        bm25_chunks = self.bm25_retriever.search(query, n_results=candidate_count)
        
        chroma_search_results = self.chroma_searcher.search(query, n_results=candidate_count)
        chroma_chunks = chroma_search_results.get('results', [])

        # 2. RRF (Reciprocal Rank Fusion) 계산
        rrf_scores = defaultdict(float)
        # 청크의 고유 ID (meeting_title, chunk_index)를 기준으로 청크 정보 저장
        chunk_store = {}

        # BM25 결과 처리
        for rank, chunk in enumerate(bm25_chunks):
            if 'meeting_title' not in chunk or 'chunk_index' not in chunk:
                continue
            chunk_id = (chunk['meeting_title'], chunk['chunk_index'])
            rrf_scores[chunk_id] += 1 / (k + rank + 1)
            if chunk_id not in chunk_store:
                chunk['similarity'] = chunk['score'] # BM25 점수를 유사도로 활용
                chunk_store[chunk_id] = chunk

        # Chroma 결과 처리
        for rank, chunk in enumerate(chroma_chunks):
            if 'meeting_title' not in chunk or 'chunk_index' not in chunk:
                continue
            chunk_id = (chunk['meeting_title'], chunk['chunk_index'])
            rrf_scores[chunk_id] += 1 / (k + rank + 1)
            if chunk_id not in chunk_store:
                chunk_store[chunk_id] = chunk
        
        # 3. RRF 점수에 따라 청크 ID 정렬
        sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        
        # 4. 최종 결과 포맷팅
        final_results = []
        for chunk_id in sorted_chunk_ids[:n_results]:
            chunk_info = chunk_store[chunk_id]
            final_results.append({
                "text": chunk_info.get("text", ""),
                "similarity": rrf_scores[chunk_id], # RRF 점수를 최종 유사도로 사용
                "source": chunk_info.get("meeting_title", "N/A") 
            })

        print(f"   -> {len(final_results)}개 청크 최종 선택 (RRF)")
        return final_results

if __name__ == '__main__':
    # 테스트용 코드
    try:
        ensemble_retriever = Retriever()
        
        test_query = "서울시 인공지능 정책"
        print(f"\n--- 앙상블 리트리버(청크) 테스트 (query: '{test_query}') ---")
        
        retrieved_docs = ensemble_retriever.retrieve_documents(test_query, n_results=3)

        if retrieved_docs:
            for i, doc in enumerate(retrieved_docs):
                print(f"\n[최종 결과 {i+1}]")
                print(f"  - 출처(회의 제목): {doc['source']}")
                print(f"  - RRF 점수: {doc['similarity']:.4f}")
                print(f"  - 내용: {doc['text'][:200]}...")
        else:
            print("검색된 문서가 없습니다.")
            
    except Exception as e:
        print(f"테스트 중 오류 발생: {e}")