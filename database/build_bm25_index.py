import os
import json
import pickle
import glob
from kiwipiepy import Kiwi
from rank_bm25 import BM25Okapi
import time

def build_bm25_index():
    """
    회의록 JSON 파일로부터 '청크' 단위의 BM25 인덱스를 생성하고 저장합니다.
    """
    print("청크 단위 BM25 인덱스 생성을 시작합니다...")

    # 1. 경로 설정
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source_files_path = os.path.join(base_dir, 'data', 'result_txt', '*.json')
    output_dir = os.path.join(base_dir, 'data', 'bm25_index_chunk') # 새로운 폴더에 저장
    
    os.makedirs(output_dir, exist_ok=True)
    
    bm25_index_path = os.path.join(output_dir, 'bm25_index.pkl')
    chunk_corpus_path = os.path.join(output_dir, 'bm25_chunk_corpus.pkl')

    # 2. 데이터 로드 및 청크 단위 분리
    print(f"'{source_files_path}'에서 JSON 파일을 로드하여 청크 단위로 분리합니다.")
    file_paths = glob.glob(source_files_path)
    
    if not file_paths:
        print(f"오류: 소스 JSON 파일을 찾을 수 없습니다. 경로: {source_files_path}")
        return

    chunk_corpus = [] # 각 청크의 정보를 담을 리스트
    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                meeting_title = data.get('meeting_info', {}).get('title')
                
                for idx, chunk_data in enumerate(data.get('chunks', [])):
                    if 'text' in chunk_data and meeting_title:
                        chunk_corpus.append({
                            "text": chunk_data['text'],
                            "meeting_title": meeting_title,
                            "chunk_index": idx,
                            "doc_path": os.path.basename(file_path)
                        })
        except Exception as e:
            print(f"경고: 파일 처리 중 오류 발생. 파일을 건너뜁니다: {file_path}, 오류: {e}")

    print(f"총 {len(chunk_corpus)}개의 청크를 로드했습니다.")
    if not chunk_corpus:
        print("오류: 처리할 청크가 없습니다.")
        return

    # 3. 한국어 토큰화 (청크 텍스트 기준)
    print("Kiwi 형태소 분석기를 사용하여 청크를 토큰화합니다...")
    start_time = time.time()
    
    kiwi = Kiwi()
    tokenized_corpus = [
        [token.form for token in kiwi.tokenize(chunk['text'])] 
        for chunk in chunk_corpus
    ]
    
    end_time = time.time()
    print(f"토큰화 완료. (소요 시간: {end_time - start_time:.2f}초)")

    # 4. BM25 인덱스 생성
    print("BM25 인덱스를 생성합니다...")
    start_time = time.time()
    
    bm25 = BM25Okapi(tokenized_corpus)
    
    end_time = time.time()
    print(f"인덱스 생성 완료. (소요 시간: {end_time - start_time:.2f}초)")

    # 5. 인덱스 및 청크 데이터 저장
    print(f"생성된 인덱스와 데이터를 '{output_dir}'에 저장합니다.")
    with open(bm25_index_path, 'wb') as f:
        pickle.dump(bm25, f)
    # 전체 청크 정보를 담은 리스트를 저장
    with open(chunk_corpus_path, 'wb') as f:
        pickle.dump(chunk_corpus, f)
        
    print("청크 단위 BM25 인덱스 생성이 성공적으로 완료되었습니다.")

if __name__ == '__main__':
    build_bm25_index()