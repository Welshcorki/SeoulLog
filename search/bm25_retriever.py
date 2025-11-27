import os
import pickle
from kiwipiepy import Kiwi
from rank_bm25 import BM25Okapi
from typing import List, Dict

class BM25Retriever:
    """
    미리 빌드된 '청크 단위' BM25 인덱스를 사용하여 청크를 검색하는 클래스
    """
    def __init__(self, index_dir: str = None):
        """
        BM25Retriever를 초기화하고 청크 단위 인덱스 파일을 로드합니다.

        Args:
            index_dir: 청크 단위 BM25 인덱스 파일이 저장된 디렉토리.
                       None이면 기본 경로 'data/bm25_index_chunk'를 사용합니다.
        """
        if index_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            index_dir = os.path.join(base_dir, 'data', 'bm25_index_chunk')

        bm25_index_path = os.path.join(index_dir, 'bm25_index.pkl')
        chunk_corpus_path = os.path.join(index_dir, 'bm25_chunk_corpus.pkl')

        print("BM25 리트리버(청크 단위) 초기화 중...")
        try:
            with open(bm25_index_path, 'rb') as f:
                self.bm25 = pickle.load(f)
            with open(chunk_corpus_path, 'rb') as f:
                self.chunk_corpus = pickle.load(f)
            
            self.kiwi = Kiwi()
            print(f"BM25 인덱스(청크 단위) 로드 완료. ({len(self.chunk_corpus)}개 청크)")
        except FileNotFoundError as e:
            print(f"오류: BM25 청크 인덱스 파일을 찾을 수 없습니다. '{index_dir}' 경로를 확인하거나,")
            print("   `database/build_bm25_index.py`를 실행하여 인덱스를 생성해주세요.")
            raise e

    def search(self, query: str, n_results: int = 10) -> List[Dict]:
        """
        주어진 쿼리로 청크를 검색합니다.

        Args:
            query: 검색할 쿼리 문자열
            n_results: 반환할 결과의 수

        Returns:
            검색된 청크 정보를 담은 딕셔너리 리스트.
        """
        if not hasattr(self, 'bm25'):
            print("오류: BM25 리트리버가 제대로 초기화되지 않았습니다.")
            return []

        # 1. 쿼리 토큰화
        tokenized_query = [token.form for token in self.kiwi.tokenize(query)]

        # 2. BM25 점수 계산 및 상위 N개 인덱스 추출
        doc_scores = self.bm25.get_scores(tokenized_query)
        top_n_indices = sorted(range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True)[:n_results]

        # 3. 결과 포맷팅
        results = []
        for i in top_n_indices:
            score = doc_scores[i]
            if score <= 0:
                continue
            
            # chunk_corpus에서 해당 인덱스의 청크 정보를 가져옴
            chunk_info = self.chunk_corpus[i].copy()
            chunk_info['score'] = score # BM25 점수 추가
            results.append(chunk_info)
            
        return results

if __name__ == '__main__':
    # 테스트용 코드
    print("--- BM25Retriever(Chunk) 테스트 ---")
    try:
        retriever = BM25Retriever()
        test_query = "서울시 청년 주거 지원 정책"
        search_results = retriever.search(test_query, n_results=3)

        print(f"\n[쿼리] '{test_query}'")
        if search_results:
            for i, result in enumerate(search_results):
                print(f"\n[결과 {i+1}]")
                print(f"  - 문서: {result.get('doc_path')}")
                print(f"  - 제목: {result.get('meeting_title')}")
                print(f"  - 청크 인덱스: {result.get('chunk_index')}")
                print(f"  - 점수: {result.get('score', 0.0):.4f}")
                print(f"  - 내용: {result.get('text', '')[:150]}...")
        else:
            print("검색 결과가 없습니다.")
            
    except Exception as e:
        print(f"테스트 중 예기치 않은 오류 발생: {e}")
