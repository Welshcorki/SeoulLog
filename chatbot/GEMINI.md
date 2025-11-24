# Gemini 작업 기록

---
### 2025년 11월 21일: RAG 챗봇 구현 (1-2단계)

1.  **챗봇 모듈화 구조 생성 (1단계)**
    *   `chatbot` 디렉터리를 생성하여 챗봇 관련 코드를 분리했습니다.
    *   `chatbot/router.py`: FastAPI의 `APIRouter`를 사용하여 `/api/chat` 엔드포인트를 모듈식으로 정의했습니다.
    *   `chatbot/__init__.py`: `chatbot` 디렉터리를 파이썬 패키지로 만들기 위해 생성했습니다.
    *   `backend_server.py`에 라우터를 통합하는 작업은 구현 우선순위에 따라 잠시 보류했습니다.

2.  **쿼리 재구성 기능 구현 (2단계)**
    *   `chatbot/query_rewriter.py`: 대화 기록을 바탕으로 사용자의 후속 질문을 명확하고 독립적인 질문으로 재작성하는 `rewrite_query` 함수를 구현했습니다.
        *   OpenAI `gpt-4o-mini` 모델을 사용하여 재작성을 수행합니다.
    *   `chatbot/router.py`를 수정하여, 임시 대화 기록과 함께 `rewrite_query` 함수를 호출하고 그 결과를 반환하도록 업데이트했습니다. 이를 통해 2단계 기능의 독립적인 테스트 환경을 마련했습니다.

---
### 2025년 11월 21일: RAG 챗봇 구현 (3-4단계 및 UI 연동)

3.  **문서 검색(Retrieval) 기능 구현 (3단계)**
    *   `search/search_executor.py`를 분석하고, RAG 파이프라인에 더 적합하도록 `utils.search_chromadb.MeetingSearcher`를 직접 사용하는 `chatbot/retriever.py` 모듈을 구현했습니다.
    *   `chatbot/router.py`를 수정하여 쿼리 재구성 후 문서 검색을 수행하고, 검색된 문서를 반환하도록 파이프라인을 확장했습니다.

4.  **답변 생성(Generation) 기능 구현 (4단계)**
    *   `chatbot/generator.py`: 검색된 문서(Context)와 재구성된 질문을 바탕으로 LLM(gpt-4o-mini)이 최종 답변을 생성하는 `generate_answer` 함수를 구현했습니다.
    *   `chatbot/router.py`를 수정하여 RAG의 전체 파이프라인(재구성 → 검색 → 생성)을 완성했습니다.

5.  **챗봇 UI 연동 (6단계)**
    *   사용자가 제공한 `chatbot/chatbot.html` 정적 UI 파일을 분석했습니다.
    *   `chatbot.html` 파일 내에 동적 기능을 위한 JavaScript 코드를 삽입하여, UI 제어 및 `/api/chat` 엔드포인트와 통신하는 로직을 구현했습니다.
