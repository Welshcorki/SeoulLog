# SeoulLog - 서울시의회 안건 검색 서비스

<div align="center">
  <img src="image/diff.png" alt="SeoulLog vs 원래 서비스 비교" width="75%">
  <p><i>기존 서울시 홈페이지(좌) vs SeoulLog 개선 서비스(우)</i></p>
</div>

서울시의회 회의록을 시민이 쉽게 검색하고 이해할 수 있는 AI 기반 검색 서비스

---

## 📋 프로젝트 개요

**목적**: 복잡한 서울시의회 회의록을 AI 요약과 시맨틱 검색으로 누구나 쉽게 접근 가능하도록 개선

**핵심 전략**:
- **안건 단위 검색**: 같은 안건의 여러 발언을 하나로 그룹핑하여 중복 제거
- **하이브리드 검색**: ChromaDB(벡터 검색) + SQLite(메타데이터) 조합
- **AI 요약**: LLM을 활용한 자동 요약 및 핵심 의제 추출

---

## 🎯 핵심 기능

### ✅ 구현 완료
1. **안건 단위 검색** - 벡터 유사도 기반 시맨틱 검색
2. **안건 상세 페이지** - 발언자별 입장, 전체 텍스트 제공
3. **반응형 UI** - 모바일/데스크톱 대응 (Tailwind CSS)

### 🔄 구현 예정
1. **AI 요약** - LLM으로 안건 자동 요약
2. **핵심 의제 추출** - 찬반 입장 자동 분석
3. **쉬운 용어 설명** - 어려운 법률 용어 자동 해설
4. **관련 안건 추천** - 유사한 안건 자동 추천
5. **RAG 챗봇** - 안건 관련 질의응답

---

## 🗂️ 프로젝트 구조

```
seoulloc/
├── html/                           # 프론트엔드 (반응형 HTML)
│   ├── main.html                  # 메인 검색 페이지
│   ├── search.html                # 검색 결과 페이지
│   └── details.html               # 안건 상세 페이지
│
├── backend_server.py              # FastAPI 메인 서버
│
├── 검색 파이프라인/
│   ├── query_analyzer.py          # LLM 기반 쿼리 분석
│   ├── simple_query_analyzer.py   # 규칙 기반 쿼리 분석
│   ├── metadata_validator.py      # 발언자명 보정
│   ├── search_executor.py         # ChromaDB 검색 실행
│   ├── result_formatter.py        # 결과 포맷팅
│   └── answer_generator_simple.py # 간단 답변 생성
│
├── 데이터베이스 구축/
│   ├── insert_to_chromadb.py      # 청크별 벡터 DB 생성
│   ├── create_agenda_database.py  # 안건별 SQLite DB 생성
│   ├── custom_openai_embedding.py # OpenAI 임베딩 함수
│   └── delete_chromadb_collection.py # ChromaDB 초기화
│
├── 데이터 처리/
│   ├── process_all_txt_to_json_async_gemini.py # 회의록 JSON 변환
│   ├── parse_session_332.py       # 332회 회의록 파싱
│   └── result_txt/                # 처리된 JSON 데이터
│
├── 데이터베이스/
│   ├── chroma_db/                 # ChromaDB 벡터 저장소
│   └── sqlite_DB/
│       └── agendas.db            # 안건 메타데이터 SQLite DB
│
├── HANDOVER.md                    # 작업 인수인계 문서
├── proposal.md                    # 해커톤 제안서
└── requirements_backend.txt       # Python 패키지 목록
```

---

## 🚀 실행 방법

### 1. 환경 설정

```bash
# Python 가상환경 생성 (conda 권장)
conda create -n seoul python=3.10
conda activate seoul

# 패키지 설치
pip install -r requirements_backend.txt
```

### 2. 환경 변수 설정

`.env` 파일 생성:
```
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. 데이터베이스 구축

```bash
# Step 1: ChromaDB 청크 컬렉션 생성 (벡터 검색용)
python insert_to_chromadb.py

# Step 2: SQLite 안건 DB 생성 (메타데이터용)
python create_agenda_database.py
```

### 4. 서버 실행

```bash
python backend_server.py
```

→ http://localhost:8000 에서 확인

**모바일 접속**: 같은 WiFi에서 `http://{your-ip}:8000`

---

## 🏗️ 시스템 아키텍처

### 검색 흐름
```
사용자 쿼리 입력
    ↓
ChromaDB 청크 검색 (벡터 유사도)
    ↓
안건별 그룹핑 (agenda_id 기준, 최고 유사도만 선택)
    ↓
SQLite에서 안건 상세 정보 조회
    ↓
안건 단위로 검색 결과 반환
```

### 데이터 구조

**ChromaDB**: `seoul_council_meetings` 컬렉션
- 청크별로 저장 (세밀한 벡터 검색)
- 메타데이터: `agenda_id`, `speaker`, `meeting_title` 등

**SQLite**: `agendas.db`
- 안건별로 저장 (빠른 메타데이터 조회)
- 테이블:
  - `agendas`: 안건 상세 정보 (제목, 발언자, 전체 텍스트, 상태)
  - `agenda_chunks`: 안건-청크 매핑

---

## 📊 API 엔드포인트

### 검색 API
```http
POST /api/search
Content-Type: application/json

{
  "query": "AI 정책",
  "n_results": 5
}
```

**응답**:
```json
{
  "query": "AI 정책",
  "total_results": 3,
  "results": [
    {
      "agenda_id": "meeting_20251117_195534_agenda_001",
      "title": "서울특별시 인공지능산업 육성 및 지원 조례안",
      "ai_summary": "...",
      "main_speaker": "경제실장 주용태",
      "similarity": 0.85,
      ...
    }
  ]
}
```

### 안건 상세 API
```http
GET /api/agenda/{agenda_id}
```

### 핫이슈 API
```http
GET /api/hot-issues
```

---

## 🛠️ 기술 스택

### Backend
- **Framework**: FastAPI
- **Vector DB**: ChromaDB (코사인 유사도)
- **Relational DB**: SQLite
- **Embedding**: OpenAI `text-embedding-3-small`
- **LLM**: OpenAI GPT-4o-mini (쿼리 분석용)

### Frontend
- **Framework**: Vanilla HTML/CSS/JavaScript
- **Styling**: Tailwind CSS (CDN)
- **Icons**: Material Symbols

### Data Processing
- **LLM**: Google Gemini (회의록 JSON 변환)
- **Parsing**: Python (BeautifulSoup4, json)

---

## 📂 주요 파일 설명

### Backend

#### `backend_server.py`
- FastAPI 메인 서버
- `/api/search`: 안건 검색 (ChromaDB → 그룹핑 → SQLite)
- `/api/agenda/{agenda_id}`: 안건 상세 조회
- 현재는 파이프라인 모듈을 우회하고 직접 ChromaDB/SQLite 호출

#### `insert_to_chromadb.py`
- JSON 회의록을 ChromaDB에 청크별로 삽입
- 각 청크에 `agenda_id` 메타데이터 추가
- OpenAI 임베딩 사용

#### `create_agenda_database.py`
- JSON 회의록을 안건별로 그룹핑하여 SQLite에 저장
- `agendas` 테이블: 안건 상세 정보
- `agenda_chunks` 테이블: 안건-청크 매핑

### Frontend

#### `html/main.html`
- 메인 페이지
- 검색 입력창, 태그 검색, 핫이슈 top 5

#### `html/search.html`
- 검색 결과 페이지
- 안건 카드 (제목, AI 요약, 발언자, 유사도, 진행 상태)

#### `html/details.html`
- 안건 상세 페이지
- 핵심 의제, 쉬운 용어 설명, 관련 의안 (현재 하드코딩)

---

## 📊 현재 데이터

- **회의록 수**: 2개 JSON 파일
- **총 청크**: 169개
- **안건 수**: 약 10개
- **회의**: 제332회 AI경쟁력강화특별위원회

---

## 🚨 알려진 이슈 & 향후 작업

### 구현 필요 (하드코딩 → 자동화)

1. **AI 요약** (우선순위: 높음)
   - 현재: 텍스트 앞 200자만 자르기
   - 목표: LLM으로 실제 요약 생성

2. **핵심 의제 추출** (우선순위: 높음)
   - 현재: 발언자별로 텍스트만 나열
   - 목표: LLM으로 쟁점 추출 및 찬반 입장 분석

3. **쉬운 용어 설명** (우선순위: 중간)
   - 현재: 하드코딩된 정적 텍스트
   - 목표: LLM으로 어려운 용어 자동 추출 및 설명

4. **관련 의안 추천** (우선순위: 중간)
   - 현재: 하드코딩된 정적 HTML
   - 목표: ChromaDB 유사도 검색으로 자동 추천

5. **핫이슈 top 5** (우선순위: 낮음)
   - 현재: 하드코딩된 데이터
   - 목표: SQLite에서 실제 안건 조회 또는 랜덤 표시

6. **의안 진행과정** (우선순위: 낮음)
   - 현재: 진행 상태가 "심사중"만 있음
   - 목표: 실제 단계별 진행 데이터 (발의 → 위원회 → 본회의 → 공포)

### 사용되지 않는 모듈

현재 초기화만 되고 실제 사용되지 않는 파이프라인:
- `QueryAnalyzer` (LLM 쿼리 분석)
- `MetadataValidator` (발언자명 보정)
- `SearchExecutor` (ChromaDB 검색)
- `ResultFormatter` (결과 포맷팅)

→ 향후 RAG 챗봇 구현 시 활용 가능

---

## 🔧 개발 팁

### ChromaDB 재구축
```bash
# 1. 기존 ChromaDB 삭제
rm -rf chroma_db/

# 2. 재구축
python insert_to_chromadb.py
```

### SQLite DB 확인
```bash
# DB 상태 확인 스크립트
python check_db.py
```

### 유사도 공식
현재 사용: `similarity = 1 - (distance / 2)`
- ChromaDB 코사인 거리: 0~2 범위
- 유사도: 0~1 범위 (1에 가까울수록 유사)

---

## 📝 데이터 흐름

```
서울시의회 회의록 (텍스트)
    ↓
[Gemini 처리] process_all_txt_to_json_async_gemini.py
    ↓
result_txt/*.json (구조화된 회의록)
    ↓
[ChromaDB 구축] insert_to_chromadb.py
    ↓
chroma_db/ (벡터 검색용)
    ↓
[SQLite 구축] create_agenda_database.py
    ↓
sqlite_DB/agendas.db (메타데이터용)
    ↓
[FastAPI 서버] backend_server.py
    ↓
HTML 프론트엔드 → 사용자
```

---

## 🎯 다음 단계 (우선순위)

### Phase 1: AI 기능 구현 (1-2일)
- [ ] AI 요약 생성 (LLM)
- [ ] 핵심 의제 추출 (LLM)
- [ ] 쉬운 용어 설명 (LLM)

### Phase 2: 추천 시스템 (1일)
- [ ] 관련 의안 추천 (ChromaDB 유사도 검색)
- [ ] 핫이슈 실제 데이터 연결

### Phase 3: RAG 챗봇 (2-3일)
- [ ] Langgraph 워크플로 구현
- [ ] 대화 히스토리 관리
- [ ] 챗봇 UI 연결

### Phase 4: 데이터 확장
- [ ] 더 많은 회의록 수집
- [ ] 의안 진행 상태 데이터 확보
- [ ] 카테고리 분류 (예산/조례/인사)

---

## 📌 참고 문서

- **작업 인수인계**: `HANDOVER.md`
- **해커톤 제안서**: `proposal.md`
- **원본 사이트**: https://ms.smc.seoul.kr

---

## 💡 핵심 인사이트

### 설계 철학
1. **검색 정확도**: 청크 단위 벡터 검색 (세밀한 매칭)
2. **UI 표시**: 안건 단위로 그룹핑 (중복 제거, 깔끔한 UX)
3. **하이브리드 구조**: ChromaDB(검색) + SQLite(메타데이터)

### 기술적 선택
- **Langgraph 미사용**: 현재 기능들은 단순 LLM 호출로 충분
- **파이프라인 우회**: 초기 구상과 달리 직접 DB 호출로 단순화
- **비동기 처리**: asyncio로 병렬 LLM 호출 가능

---

## 👥 기여 방법

1. Issue 등록
2. Pull Request
3. 피드백 제공

---

## 📄 라이선스

MIT License

---

**Last Updated**: 2025-11-18
**Status**: 안건 검색 기능 구현 완료, AI 요약 기능 구현 예정
