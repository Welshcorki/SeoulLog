from fastapi import APIRouter
from pydantic import BaseModel
from chatbot.query_rewriter import rewrite_query
from chatbot.retriever import retrieve_documents
from chatbot.generator import generate_answer

# 요청 본문을 위한 Pydantic 모델
class ChatRequest(BaseModel):
    message: str
    session_id: str
    # 실제 구현에서는 session_id를 기반으로 서버에서 히스토리를 관리해야 함
    history: list[tuple[str, str]] = [] 

# 챗봇 API 라우터 생성
router = APIRouter()

# 임시 대화 기록 (테스트용)
# 실제로는 세션 ID별로 DB나 메모리 캐시에서 관리해야 함
temp_chat_history = {
    "test_session_123": [
        ("서울시 AI 정책에 대해 알려줘.", "서울시는 '서울특별시 인공지능산업 육성 및 지원 조례안'을 통해 AI 산업을 지원하고 있습니다.")
    ]
}

@router.post("/chat")
async def handle_chat(request: ChatRequest):
    """
    RAG 챗봇의 전체 파이프라인을 실행하는 엔드포인트입니다.
    (쿼리 재구성 -> 문서 검색 -> 답변 생성)
    """
    # 1. 세션 ID로 대화 기록 가져오기 (현재는 임시 데이터 사용)
    history = temp_chat_history.get(request.session_id, [])
    
    # 2. 쿼리 재구성
    rewritten_question = rewrite_query(request.message, history)

    # 3. 문서 검색 (재작성된 쿼리 사용)
    retrieved_docs = retrieve_documents(rewritten_question, n_results=3)

    # 4. 답변 생성
    final_answer = generate_answer(rewritten_question, retrieved_docs)

    # TODO: 5단계 - 대화 히스토리 저장
    # temp_chat_history[request.session_id].append((request.message, final_answer))

    # 최종 답변 및 중간 결과 반환 (디버깅용)
    return {
        "response": final_answer,
        "debug_info": {
            "original_question": request.message,
            "rewritten_question": rewritten_question,
            "retrieved_documents": retrieved_docs
        }
    }
