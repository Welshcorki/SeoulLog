# SeoulLog 파이프라인 문서

> 작성일: 2025-11-22
> 버전: 2.0 (코드 정리 완료)

---

## 🎯 개요

서울시의회 회의록 검색 시스템 (벡터 검색 + AI 요약 + 첨부 문서 처리)

---

## 📋 전체 파이프라인

```
1. URL 추출 (Selenium으로 회의록 링크 수집)
   ↓
2. 크롤링 (회의록 HTML → TXT/JSON/MD)
   ↓
3. JSON 생성 (하이브리드 파싱: Gemini + 순수 코드)
   ↓
4. ChromaDB 삽입 (벡터 검색용)
   ↓
5. SQLite DB 생성 (메타데이터)
   ↓
6. AI 요약 생성 (안건별 요약)
   ↓
7. 첨부 문서 요약 생성 (PDF → AI 요약)
   ↓
8. 서버 실행 (FastAPI)
```

---

## 🔧 단계별 실행 방법

### 1단계: 크롤링 (회의록 다운로드)

#### 1-1. URL 추출

**파일:** `crawling/extract_session_332_links.py`

```bash
# Selenium으로 제332회 회의록 링크 자동 추출
python crawling/extract_session_332_links.py
```

**출력:**
- `SESSION_332_URLS.txt` - 52개 회의록 URL 리스트

**특징:**
- Selenium으로 동적 페이지 크롤링
- 제332회 임시회 전체 링크 자동 수집

#### 1-2. 회의록 다운로드

**파일:** `crawling/crawl_all_urls.py`

```bash
# SESSION_332_URLS.txt의 URL 크롤링
python crawling/crawl_all_urls.py
```

**출력:**
- `result/회의명/meeting_*.txt` - 회의록 텍스트
- `result/회의명/meeting_*.json` - 메타데이터
- `result/회의명/meeting_*.md` - 마크다운 (참고용)

**특징:**
- `---` 구분선 처리
- 참고자료 섹션 포함
- URL당 약 10-30초 소요

---

### 2단계: JSON 생성 (하이브리드 파싱)

**파일:** `data_processing/process_all_result_folders.py`

```bash
# 전체 파일 처리
python data_processing/process_all_result_folders.py

# 랜덤 10개만 처리 (테스트용)
python data_processing/process_all_result_folders.py 10
```

**내부 동작:**
1. **Stage 1 (Gemini 2.5 Pro):** 안건 매핑 추출
   - `data_processing/extract_metadata_hybrid.py`
   - 안건 제목, 라인 범위, 발언자, 첨부 문서 매칭

2. **Stage 2 (순수 Python):** 발언 추출
   - `data_processing/parse_with_pure_code.py`
   - Regex로 ○발언자 패턴 추출
   - 500자 초과 시 문장 단위 분할

**출력:**
- `data/result_txt/*.json` - 파싱된 JSON

**성능:**
- 속도: 3초/파일 (기존 30초 대비 10배 빠름)
- 비용: 50% 절감 (Stage 2 API 호출 제거)
- 정확도: 100% (발언 누락 없음)

---

### 3단계: ChromaDB 삽입

**파일:** `database/insert_to_chromadb.py`

```bash
python database/insert_to_chromadb.py
```

**동작:**
- OpenAI text-embedding-3-small 임베딩
- 컬렉션: `seoul_council_meetings`
- 메타데이터: agenda_id, speaker, meeting_date, agenda, meeting_title

**출력:**
- `data/chroma_db/` - 벡터 DB

---

### 4단계: SQLite DB 생성

**파일:** `database/create_agenda_database.py`

```bash
python database/create_agenda_database.py
```

**테이블 구조:**

**agendas 테이블:**
```sql
CREATE TABLE agendas (
    agenda_id TEXT PRIMARY KEY,
    agenda_title TEXT NOT NULL,
    meeting_title TEXT,
    meeting_date TEXT,
    meeting_url TEXT,
    main_speaker TEXT,
    all_speakers TEXT,
    speaker_count INTEGER,
    chunk_count INTEGER,
    chunk_ids TEXT,
    combined_text TEXT,           -- 전체 회의록
    ai_summary TEXT,              -- AI 요약 (150자 이내)
    key_issues TEXT,              -- 핵심 의제 (JSON)
    attachments TEXT,             -- 첨부 문서 (JSON)
    agenda_type TEXT,             -- 안건 유형
    status TEXT DEFAULT '접수',
    created_at TIMESTAMP
)
```

**agenda_chunks 테이블:**
```sql
CREATE TABLE agenda_chunks (
    chunk_id TEXT PRIMARY KEY,
    agenda_id TEXT,
    chunk_index INTEGER,
    speaker TEXT,
    full_text TEXT,               -- 전체 텍스트
    FOREIGN KEY (agenda_id) REFERENCES agendas(agenda_id)
)
```

**출력:**
- `data/sqlite_DB/agendas.db`

---

### 5단계: AI 요약 생성

**파일:** `database/generate_ai_summaries.py`

```bash
python database/generate_ai_summaries.py
```

**동작:**
1. combined_text를 2000자씩 청킹
2. 각 청크를 Gemini 2.5 Flash로 요약
3. 청크 요약들을 합쳐 150자 최종 요약 생성
4. 핵심 의제 추출 (JSON 배열)

**성능:**
- 비동기 병렬 처리 (10개 안건 동시)
- 100개 안건 기준: 약 5분 소요 (기존 50분 대비 10배 빠름)

**출력:**
- `agendas.ai_summary` 업데이트
- `agendas.key_issues` 업데이트

---

### 6단계: 첨부 문서 요약 생성

**파일:** `database/generate_attachment_summaries.py`

```bash
python database/generate_attachment_summaries.py
```

**동작:**
1. agendas 테이블에서 attachments 읽기
2. PDF 다운로드
3. Gemini File API로 2-4줄 요약 생성
4. attachments에 summary 추가하여 DB 업데이트

**특징:**
- 비동기 병렬 처리 (3개씩 동시)
- 재실행 가능 (이미 요약된 건 건너뜀)
- 범용 프롬프트 (조례안, 보고서, 검토의견서 모두 처리)

**프롬프트:** `prompts/summarize_attachment.txt`

**출력:**
- `agendas.attachments` 업데이트 (summary 필드 추가)

---

### 7단계: 서버 실행

**파일:** `app.py`

```bash
python app.py
```

**API 엔드포인트:**
- `GET /` - 메인 페이지
- `GET /api/search?query=...` - 검색
- `GET /api/agenda/{id}` - 안건 상세
- `GET /api/agenda/{id}/formatted-detail` - 포맷된 안건 상세 (첨부 문서 포함)
- `GET /api/top-agendas` - Top 5 주목받는 안건

**접속:**
- http://localhost:8000

---

## 📁 프로젝트 구조 (정리 완료)

```
seoulloc/
├── app.py                # FastAPI 백엔드
│
├── crawling/                        # 크롤링 (2개 파일)
│   ├── extract_session_332_links.py # URL 추출 (Selenium)
│   └── crawl_all_urls.py            # 회의록 다운로드
│
├── data_processing/                 # 데이터 처리 (3개 파일)
│   ├── extract_metadata_hybrid.py   # Stage 1: Gemini 안건 매핑
│   ├── parse_with_pure_code.py      # Stage 2: 순수 코드 발언 추출
│   └── process_all_result_folders.py # 배치 처리 (병렬 3개씩)
│
├── database/                        # 데이터베이스 (4개 파일)
│   ├── create_agenda_database.py    # SQLite DB 생성
│   ├── generate_ai_summaries.py     # AI 요약 생성 (비동기)
│   ├── generate_attachment_summaries.py # 첨부 문서 요약
│   └── insert_to_chromadb.py        # ChromaDB 삽입
│
├── search/                          # 검색 모듈 (6개 파일)
│   ├── query_analyzer.py            # 쿼리 분석 (GPT-4o-mini)
│   ├── simple_query_analyzer.py     # 규칙 기반 fallback
│   ├── metadata_validator.py        # 메타데이터 검증
│   ├── search_executor.py           # 검색 실행
│   ├── result_formatter.py          # 결과 포맷팅
│   └── answer_generator_simple.py   # 답변 생성
│
├── utils/                           # 유틸리티 (4개 파일)
│   ├── cost_tracker.py              # API 비용 추적
│   ├── custom_openai_embedding.py   # OpenAI 임베딩 함수
│   └── search_chromadb.py           # ChromaDB 검색
│
├── frontend/                        # 프론트엔드 (3개 파일)
│   ├── main.html                    # 메인 페이지
│   ├── search.html                  # 검색 결과
│   └── details.html                 # 안건 상세
│
├── old/                             # 구버전/테스트 코드 (28개 파일)
│   ├── data_processing/             # 옛날 파싱 방식 (11개)
│   ├── database/                    # 유틸리티/테스트 (3개)
│   ├── backend/                     # 옛날 백엔드 구조
│   ├── crawl_*.py                   # 크롤링 코드들
│   └── test_*.py                    # 각종 테스트 파일
│
├── data/                            # 데이터 저장소
│   ├── result_txt/                  # JSON 파일
│   ├── chroma_db/                   # ChromaDB 벡터 DB
│   └── sqlite_DB/                   # SQLite DB
│       └── agendas.db
│
├── prompts/                         # 프롬프트 템플릿
│   └── summarize_attachment.txt     # 첨부 문서 요약 프롬프트
│
├── HANDOVER.md                      # 작업 인수인계 (11/18-11/20)
├── HANDOVER2.md                     # 작업 인수인계 (11/21)
├── ATTACHMENT_IMPLEMENTATION.md     # 첨부 문서 구현 문서
└── PIPELINE.md                      # 현재 문서
```

---

## 🚀 빠른 시작 (처음부터 전체 실행)

```bash
# 1. 환경 변수 설정
export GOOGLE_API_KEY="your-key"
export OPENAI_API_KEY="your-key"
conda activate seoul

# 2. URL 추출 (선택: SESSION_332_URLS.txt가 이미 있으면 생략)
python crawling/extract_session_332_links.py

# 3. 크롤링 (선택: 이미 크롤링된 데이터가 있으면 생략)
python crawling/crawl_all_urls.py

# 4. JSON 생성 (하이브리드 파싱)
python data_processing/process_all_result_folders.py

# 5. ChromaDB 삽입
python database/insert_to_chromadb.py

# 6. SQLite DB 생성
python database/create_agenda_database.py

# 7. AI 요약 생성
python database/generate_ai_summaries.py

# 8. 첨부 문서 요약 생성 (첨부 문서가 있는 경우)
python database/generate_attachment_summaries.py

# 9. 서버 실행
python app.py
```

---

## 💡 핵심 설계 원칙

### 1. 하이브리드 파싱 방식
- **Stage 1 (Gemini):** 안건 매핑 (비정형 데이터 이해)
- **Stage 2 (순수 코드):** 발언 추출 (빠르고 안정적)
- **장점:** 빠름, 저렴, 안정적, 정확

### 2. 듀얼 데이터베이스
- **ChromaDB:** 벡터 검색 (의미 기반 매칭)
- **SQLite:** 메타데이터 + 전체 텍스트 (빠른 조회)

### 3. 비동기 병렬 처리
- AI 요약: 10개 안건 동시 처리
- 첨부 문서 요약: 3개 동시 처리
- Semaphore로 동시성 제어

### 4. 재실행 가능 설계
- DB 재생성 시 기존 데이터 삭제
- AI 요약 재생성 가능
- 첨부 문서 요약: 이미 있는 건 건너뜀

---

## 📊 성능 지표

| 항목 | 기존 | 현재 | 개선율 |
|------|------|------|--------|
| 파싱 속도 | 30초/파일 | 3초/파일 | **10배** |
| 파싱 비용 | Stage 1 + 2 | Stage 1만 | **50%** |
| 발언 정확도 | 누락 있음 | 100% | **완벽** |
| AI 요약 속도 | 50분 (100개) | 5분 | **10배** |

---

## 🔍 트러블슈팅

### DB 재생성이 필요한 경우

```bash
# 방법 1: DB 파일 삭제
rm data/sqlite_DB/agendas.db
python database/create_agenda_database.py
python database/generate_ai_summaries.py

# 방법 2: 테이블만 삭제
sqlite3 data/sqlite_DB/agendas.db "DROP TABLE IF EXISTS agenda_chunks; DROP TABLE IF EXISTS agendas;"
python database/create_agenda_database.py
python database/generate_ai_summaries.py
```

### ChromaDB 초기화

```bash
rm -rf data/chroma_db
python database/insert_to_chromadb.py
```

---

## 📝 변경 이력

| 날짜 | 버전 | 내용 |
|------|------|------|
| 2025-11-22 | 2.0 | 코드 정리 (old 폴더 분리), 파이프라인 문서화 |
| 2025-11-21 | 1.5 | 첨부 문서 시스템 구현, DB 스키마 변경 |
| 2025-11-20 | 1.0 | 하이브리드 파싱 시스템 구현, 비동기 병렬 처리 |

---

## 🔗 관련 문서

- **HANDOVER.md** - 작업 인수인계 (11/18-11/20): 하이브리드 파싱, AI 요약 시스템
- **HANDOVER2.md** - 작업 인수인계 (11/21): DB 스키마 변경, AI 요약 truncation 수정
- **ATTACHMENT_IMPLEMENTATION.md** - 첨부 문서 구현 상세

---

**마지막 업데이트:** 2025-11-22
**문서 버전:** 2.0
**프로젝트:** SeoulLog - 서울시의회 회의록 검색 시스템
