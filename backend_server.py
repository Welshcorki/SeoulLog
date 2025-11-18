"""
FastAPI 백엔드 서버

HTML UI와 검색 파이프라인을 연결합니다.

사용법:
    python backend_server.py

API 엔드포인트:
    GET  /                    - main.html 제공
    GET  /search              - search.html 제공
    POST /api/search          - 검색 쿼리 처리
    GET  /api/hot-issues      - 핫이슈 top 5 조회
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import uvicorn
from pathlib import Path
import sqlite3
import chromadb
import os
from dotenv import load_dotenv
from custom_openai_embedding import CustomOpenAIEmbeddingFunction

# 파이프라인 모듈 import
from query_analyzer import QueryAnalyzer
from simple_query_analyzer import SimpleQueryAnalyzer
from metadata_validator import MetadataValidator
from search_executor import SearchExecutor
from result_formatter import ResultFormatter
from answer_generator_simple import SimpleAnswerGenerator

load_dotenv()


app = FastAPI(title="SeoulLog API")

# HTML 파일 경로
HTML_DIR = Path("html")


class SearchRequest(BaseModel):
    """검색 요청 모델"""
    query: str
    n_results: Optional[int] = 5


class SearchResult(BaseModel):
    """검색 결과 모델 (안건 단위)"""
    agenda_id: str
    title: str
    ai_summary: str
    main_speaker: str
    all_speakers: str
    speaker_count: int
    meeting_date: str
    meeting_title: str
    status: str
    similarity: float
    chunk_count: int
    meeting_url: str


class SearchResponse(BaseModel):
    """검색 응답 모델"""
    query: str
    total_results: int
    results: List[SearchResult]


class HotIssue(BaseModel):
    """핫이슈 모델"""
    rank: int
    title: str
    proposer: str
    status: str


# 파이프라인 컴포넌트 초기화
try:
    analyzer = QueryAnalyzer()
    print("✅ QueryAnalyzer (OpenAI) 초기화 성공")
except Exception as e:
    print(f"⚠️ QueryAnalyzer (OpenAI) 초기화 실패: {e}")
    print("   → SimpleQueryAnalyzer (규칙 기반) 사용")
    analyzer = SimpleQueryAnalyzer()

validator = MetadataValidator()
searcher = SearchExecutor()
formatter = ResultFormatter()
answer_generator = SimpleAnswerGenerator()

# ChromaDB 클라이언트 초기화 (안건 검색용)
chroma_client = chromadb.PersistentClient(path="./chroma_db")
openai_ef = CustomOpenAIEmbeddingFunction(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name="text-embedding-3-small"
)
chroma_collection = chroma_client.get_collection(
    name="seoul_council_meetings",
    embedding_function=openai_ef
)
print("✅ ChromaDB 연결 성공")

# SQLite DB 경로
SQLITE_DB_PATH = "sqlite_DB/agendas.db"


@app.get("/", response_class=HTMLResponse)
async def get_main_page():
    """
    메인 페이지 (main.html) 반환
    """
    main_html_path = HTML_DIR / "main.html"

    if not main_html_path.exists():
        raise HTTPException(status_code=404, detail="main.html not found")

    with open(main_html_path, 'r', encoding='utf-8') as f:
        return f.read()


@app.get("/search", response_class=HTMLResponse)
async def get_search_page():
    """
    검색 결과 페이지 (search.html) 반환
    """
    search_html_path = HTML_DIR / "search.html"

    if not search_html_path.exists():
        raise HTTPException(status_code=404, detail="search.html not found")

    with open(search_html_path, 'r', encoding='utf-8') as f:
        return f.read()


@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    안건 단위 검색 (ChromaDB 청크 검색 → 안건 그룹핑 → SQLite 조회)

    Args:
        request: 검색 요청 (query, n_results)

    Returns:
        안건 단위 검색 결과 리스트
    """
    try:
        user_query = request.query
        n_results = request.n_results or 5

        print(f"🔍 검색 요청: {user_query}")

        # Step 1: ChromaDB 청크 검색 (벡터 유사도)
        chunk_results = chroma_collection.query(
            query_texts=[user_query],
            n_results=min(20, n_results * 4)  # 안건별 그룹핑 고려하여 더 많이 검색
        )

        print(f"   청크 검색 결과: {len(chunk_results['ids'][0])}개")

        # Step 2: 안건별 그룹핑 (agenda_id 기준, 최고 유사도만 선택)
        agenda_scores = {}  # {agenda_id: max_similarity}

        for i, chunk_id in enumerate(chunk_results['ids'][0]):
            metadata = chunk_results['metadatas'][0][i]
            distance = chunk_results['distances'][0][i]

            # 코사인 유사도 계산
            # ChromaDB cosine distance는 0~2 범위 (0=동일, 2=완전반대)
            # 옵션 1: similarity = 1 - distance (표준, 하지만 음수 가능)
            # 옵션 2: similarity = 1 - (distance / 2) (0~1 정규화)
            # 옵션 3: similarity = (2 - distance) / 2 (동일)

            # 여러 공식 테스트
            similarity = 1 - (distance / 2)  # 0~1 범위로 정규화

            agenda_id = metadata.get('agenda_id')

            if not agenda_id:
                continue

            # 디버깅: 첫 3개 결과 출력
            if i < 3:
                print(f"   [DEBUG] chunk #{i}: distance={distance:.4f}, similarity={similarity:.4f}, agenda_id={agenda_id}")

            # 안건별 최고 유사도만 유지
            if agenda_id not in agenda_scores:
                agenda_scores[agenda_id] = similarity
            else:
                agenda_scores[agenda_id] = max(agenda_scores[agenda_id], similarity)

        print(f"   그룹핑된 안건 수: {len(agenda_scores)}개")

        # Step 3: 유사도 순으로 정렬하여 상위 N개 선택
        sorted_agendas = sorted(
            agenda_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:n_results]

        # Step 4: SQLite에서 안건 상세 정보 조회
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        formatted_results = []

        for agenda_id, similarity in sorted_agendas:
            cursor.execute('''
                SELECT agenda_id, agenda_title, meeting_title, meeting_date,
                       meeting_url, main_speaker, all_speakers, speaker_count,
                       chunk_count, combined_text, status
                FROM agendas
                WHERE agenda_id = ?
            ''', (agenda_id,))

            row = cursor.fetchone()

            if not row:
                continue

            # AI 요약 생성 (combined_text의 앞부분 사용)
            combined_text = row[9] or ""
            ai_summary = combined_text[:200].strip()
            if len(combined_text) > 200:
                ai_summary += "..."

            formatted_results.append(SearchResult(
                agenda_id=row[0],
                title=row[1] or "제목 없음",
                ai_summary=ai_summary,
                main_speaker=row[5] or "발언자 없음",
                all_speakers=row[6] or "",
                speaker_count=row[7] or 0,
                meeting_date=row[3] or "날짜 없음",
                meeting_title=row[2] or "",
                status=row[10] or "심사중",
                similarity=round(similarity, 4),
                chunk_count=row[8] or 0,
                meeting_url=row[4] or ""
            ))

        conn.close()

        print(f"   최종 안건 결과: {len(formatted_results)}건")

        return SearchResponse(
            query=user_query,
            total_results=len(formatted_results),
            results=formatted_results
        )

    except Exception as e:
        print(f"❌ 검색 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/hot-issues", response_model=List[HotIssue])
async def get_hot_issues():
    """
    핫이슈 top 5 조회

    ChromaDB에서 최근 가장 많이 검색된 안건을 반환합니다.
    현재는 임시 데이터를 반환합니다.

    Returns:
        핫이슈 리스트
    """
    # TODO: 실제로는 ChromaDB에서 인기 안건을 조회해야 함
    # 현재는 하드코딩된 데이터 반환

    hot_issues = [
        HotIssue(
            rank=1,
            title="청년안심주택 공급 확대 조례안",
            proposer="김서울 의원",
            status="심사 중"
        ),
        HotIssue(
            rank=2,
            title="역세권 청년주택 관련 개정안",
            proposer="박시민 의원",
            status="통과"
        ),
        HotIssue(
            rank=3,
            title="서울시 청년주거 기본 조례 일부개정조례안",
            proposer="이나라 의원",
            status="계류"
        ),
        HotIssue(
            rank=4,
            title="공공자전거 '따릉이' 운영 효율화 방안",
            proposer="최교통 의원",
            status="심사 중"
        ),
        HotIssue(
            rank=5,
            title="반려동물 친화도시 조성을 위한 조례안",
            proposer="김애견 의원",
            status="통과"
        )
    ]

    return hot_issues


@app.get("/details", response_class=HTMLResponse)
async def get_details_page():
    """
    안건 상세 페이지 (details.html) 반환
    """
    details_html_path = HTML_DIR / "details.html"

    if not details_html_path.exists():
        raise HTTPException(status_code=404, detail="details.html not found")

    with open(details_html_path, 'r', encoding='utf-8') as f:
        return f.read()


@app.get("/api/agenda/{agenda_id}")
async def get_agenda_detail(agenda_id: str):
    """
    안건 상세 정보 조회

    Args:
        agenda_id: 안건 ID (예: meeting_20251117_195534_agenda_001)

    Returns:
        안건 상세 정보 (제목, 발언자, 전체 텍스트 등)
    """
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        # 안건 상세 정보 조회
        cursor.execute('''
            SELECT agenda_id, agenda_title, meeting_title, meeting_date,
                   meeting_url, main_speaker, all_speakers, speaker_count,
                   chunk_count, chunk_ids, combined_text, status
            FROM agendas
            WHERE agenda_id = ?
        ''', (agenda_id,))

        row = cursor.fetchone()

        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail=f"안건을 찾을 수 없습니다: {agenda_id}")

        # 청크 상세 정보 조회 (발언자별 입장 분석용)
        cursor.execute('''
            SELECT chunk_id, speaker, text_preview
            FROM agenda_chunks
            WHERE agenda_id = ?
            ORDER BY chunk_index
        ''', (agenda_id,))

        chunks = cursor.fetchall()
        conn.close()

        # 응답 생성
        return {
            "agenda_id": row[0],
            "title": row[1],
            "meeting_title": row[2],
            "meeting_date": row[3],
            "meeting_url": row[4],
            "main_speaker": row[5],
            "all_speakers": row[6],
            "speaker_count": row[7],
            "chunk_count": row[8],
            "combined_text": row[10],
            "status": row[11],
            "chunks": [
                {
                    "chunk_id": chunk[0],
                    "speaker": chunk[1],
                    "text_preview": chunk[2]
                }
                for chunk in chunks
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 안건 상세 조회 중 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """
    헬스 체크 엔드포인트
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    import socket

    # 로컬 IP 주소 가져오기
    def get_local_ip():
        try:
            # 외부 연결을 시도해서 로컬 IP 확인
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "IP를 가져올 수 없음"

    local_ip = get_local_ip()

    print("=" * 80)
    print("SeoulLog 백엔드 서버 시작")
    print("=" * 80)
    print()
    print("🌐 로컬 접속: http://localhost:8000")
    print(f"📱 모바일 접속 (같은 WiFi): http://{local_ip}:8000")
    print()
    print("📄 메인 페이지: /")
    print("🔍 검색 API: /api/search")
    print("🔥 핫이슈 API: /api/hot-issues")
    print()
    print("서버를 종료하려면 Ctrl+C를 누르세요.")
    print("=" * 80)
    print()

    uvicorn.run(app, host="0.0.0.0", port=8000)
