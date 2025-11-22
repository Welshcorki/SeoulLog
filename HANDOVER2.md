# 인수인계 문서 2 - AI 요약 truncation 버그 수정 및 DB 스키마 변경

> 작성일: 2025-11-21
> 이전 작업: HANDOVER.md 참고
> 최종 업데이트: 2025-11-21 오후

## 📋 오늘 진행한 작업 요약

### 1. AI 요약 truncation 버그 발견 및 수정

**문제 상황:**
- `제332회 기획경제위원회 제2차(2025.09.02)_agenda_009` 안건의 `ai_summary`가 중간에 잘림
- 실제 데이터: `"...적극적인 정책 추"` (160자에서 문장 중간 절단)
- 원인: `database/generate_ai_summaries.py` Line 111의 `summary[:160]` 하드코딩

**해결 방법:**
- LLM 프롬프트: `100-150자로 요약` → `150자 이내로 요약`
- 후처리: 200자 초과 시에만 간단히 자르기 (`[:200]`)
- 복잡한 문장 종결 로직 대신 LLM에게 맡기는 방식 채택

**수정된 코드:**
```python
# database/generate_ai_summaries.py Line 92-115

prompt = f"""안건 '{agenda_title}'에 대한 요약들입니다:

{combined}

위 내용을 통합하여 150자 이내로 최종 요약하세요.
- 안건의 핵심 목적
- 주요 논의 내용
- 결론 또는 결과

요약문만 반환하세요."""

response = await client.aio.models.generate_content(
    model='gemini-2.5-flash',
    contents=prompt
)
summary = response.text.strip()

await asyncio.sleep(1)

# 200자 넘으면 자르기 (LLM이 150자로 생성하므로 보통 200자 이하)
if len(summary) > 200:
    summary = summary[:200]

return summary
```

**결과:**
- ✅ 성공: 182개 안건 재생성
- ❌ 실패: 0개
- 문장 중간 절단 방지


---

### 2. DB 스키마 변경: `text_preview` → `full_text`

**변경 이유:**
- 챗봇 기능 추가를 위해 전체 텍스트 필요
- 기존 `text_preview`는 앞 200자만 저장 (`[:200]`)
- ChromaDB에는 이미 전체 텍스트가 저장되어 있으므로 SQLite도 통일

**수정된 파일 (3개):**

#### 1) `database/create_agenda_database.py`

**Line 51-59 (테이블 스키마):**
```python
CREATE TABLE IF NOT EXISTS agenda_chunks (
    chunk_id TEXT PRIMARY KEY,
    agenda_id TEXT,
    chunk_index INTEGER,
    speaker TEXT,
    full_text TEXT,  # ← text_preview에서 변경
    FOREIGN KEY (agenda_id) REFERENCES agendas(agenda_id)
)
```

**Line 175-185 (INSERT 쿼리):**
```python
cursor.execute('''
    INSERT INTO agenda_chunks (
        chunk_id, agenda_id, chunk_index, speaker, full_text
    ) VALUES (?, ?, ?, ?, ?)
''', (
    chunk_id,
    agenda_id,
    chunk_idx,
    chunk.get('speaker', ''),
    chunk['text']  # ← 전체 텍스트 저장 ([:200] 제거)
))
```

#### 2) `backend_server.py`

**Line 582-584 (SELECT 쿼리):**
```python
cursor.execute('''
    SELECT chunk_id, speaker, full_text
    FROM agenda_chunks
    WHERE agenda_id = ?
    ORDER BY chunk_index
''', (agenda_id,))
```

**Line 620 (JSON 응답):**
```python
"chunks": [
    {
        "chunk_id": chunk[0],
        "speaker": chunk[1],
        "full_text": chunk[2]  # ← text_preview에서 변경
    }
    for chunk in chunks
]
```

#### 3) `frontend/details.html`

**Line 218 (JavaScript):**
```javascript
// 발언자별로 텍스트 그룹핑
const speakerTexts = {};
data.chunks.forEach(chunk => {
    if (!speakerTexts[chunk.speaker]) {
        speakerTexts[chunk.speaker] = [];
    }
    speakerTexts[chunk.speaker].push(chunk.full_text);  // ← text_preview에서 변경
});
```


---

### 3. 데이터베이스 재생성 필요

**현재 상태:**
- 코드는 `full_text` 사용하도록 수정 완료
- 기존 DB는 `text_preview` 컬럼으로 생성되어 있음
- `CREATE TABLE IF NOT EXISTS` 때문에 기존 테이블 유지됨

**재생성 방법:**

```bash
# 방법 1: DB 파일 삭제 후 재생성 (권장)
rm data/sqlite_DB/agendas.db
python database/create_agenda_database.py
python database/generate_ai_summaries.py

# 방법 2: 테이블만 삭제 후 재생성
sqlite3 data/sqlite_DB/agendas.db "DROP TABLE IF EXISTS agenda_chunks; DROP TABLE IF EXISTS agendas;"
python database/create_agenda_database.py
python database/generate_ai_summaries.py
```

**주의사항:**
- `create_agenda_database.py`는 기존 `ai_summary`, `key_issues` 삭제
- 반드시 `generate_ai_summaries.py` 재실행 필요 (약 5-10분 소요)


---

## 🔍 추가 논의된 내용

### agenda_chunks 테이블의 필요성

**현재 사용처:**
- `/api/agenda/{id}` 엔드포인트에서만 사용
- `details.html`에서 AI `key_issues`가 없을 때 폴백으로 사용
- 발언자별로 텍스트 그룹핑하여 표시

**ChromaDB와의 중복:**
- ChromaDB에 이미 `full_text`, `speaker`, `chunk_index`, `agenda_id` 모두 저장됨
- 챗봇은 ChromaDB에서 직접 가져오는 것이 효율적

**결론:**
- 현재는 유지 (폴백 UI 용도)
- 향후 `key_issues`를 발언자별 요약으로 고도화하면 제거 가능


---

## 📊 메타데이터 사용 구조 정리

### ChromaDB 메타데이터
**용도:** 검색 필터링 및 그룹핑
```python
metadata = {
    "meeting_title": "제332회 교육위원회...",
    "meeting_date": "2025-09-02",
    "speaker": "김의원",
    "agenda": "서울특별시 주차장...",
    "agenda_id": "제332회_교육위원회_agenda_001",
    "chunk_index": 0
}
```

**사용 예시:**
```python
# database/insert_to_chromadb.py
results = collection.query(
    query_texts=[query],
    n_results=30,
    where={"speaker": "김의원"}  # ← 메타데이터 필터
)
```

### SQLite 메타데이터
**용도:** 상세 정보 표시

**agendas 테이블:**
- `ai_summary`: AI 생성 요약 (150자 이내)
- `key_issues`: 핵심 의제 JSON 배열
- `combined_text`: 안건 전체 텍스트 (검색용)
- `main_speaker`, `all_speakers`, `speaker_count`
- `meeting_title`, `meeting_date`, `meeting_url`

**agenda_chunks 테이블:**
- `full_text`: 청크별 전체 텍스트
- `speaker`: 발언자
- `chunk_index`: 순서


---

## 🚀 다음 작업 예정 (챗봇 통합)

### 1. 챗봇 데이터 구조 설계
- RAG 파이프라인 구현 (ChromaDB 기반)
- 검색 결과를 컨텍스트로 LLM에 전달
- 발언자별 요약을 `key_issues`에 포함

### 2. API 엔드포인트 추가
```python
@app.post("/api/chat")
async def chat_endpoint(query: str):
    # 1. ChromaDB에서 관련 청크 검색
    # 2. 컨텍스트 구성
    # 3. LLM에 질문 + 컨텍스트 전달
    # 4. 응답 반환
```

### 3. 프론트엔드 챗봇 UI
- 채팅 인터페이스 추가
- 검색 결과와 함께 챗봇 응답 표시


---

## 📝 변경 이력

| 날짜 | 작업 | 파일 |
|------|------|------|
| 2025-11-21 | AI 요약 truncation 로직 변경 (150자 이내) | `database/generate_ai_summaries.py` |
| 2025-11-21 | `text_preview` → `full_text` 스키마 변경 | `database/create_agenda_database.py` |
| 2025-11-21 | API 응답 키 변경 | `backend_server.py` |
| 2025-11-21 | 프론트엔드 속성명 변경 | `frontend/details.html` |


---

## ⚠️ 주의사항

1. **DB 재생성 필수**
   - 기존 DB는 `text_preview` 컬럼 사용
   - 새 코드는 `full_text` 컬럼 참조
   - 스키마 불일치로 500 에러 발생 중

2. **AI 요약 재생성 시간**
   - 182개 안건 기준 약 5-10분 소요
   - Gemini API 비용 발생 (안건당 약 2-3회 호출)

3. **비동기 클라이언트 세션 경고**
   - `Unclosed client session` 경고는 무시 가능
   - 데이터는 정상 저장됨
   - 프로그램 종료 시 자동 정리됨


---

## 📋 2025-11-21 오후 작업 내용

### ✅ 완료된 작업

#### 1. **Windows 환경에서 DB 재생성** ⭐⭐⭐

**배경**:
- 기존 DB는 WSL 환경에서 생성됨 (`/mnt/c/...`)
- VSCode SQLite Viewer가 경로 인식 못함 (ENOENT 에러)
- Windows 네이티브 환경에서 재생성 필요

**실행 명령**:
```bash
# Windows 명령 프롬프트에서
cd C:\Users\SBA\Project\seoulloc
conda activate seoul
python database/create_agenda_database.py
```

**결과**:
- ✅ DB 위치: `C:\Users\SBA\Project\seoulloc\data\sqlite_DB\agendas.db`
- ✅ 안건 수: 182개
- ✅ 청크 수: 5,984개
- ✅ 스키마: `full_text` 컬럼 적용됨
- ✅ VSCode에서 정상 접근 가능

**처리된 회의록**:
- 제332회 교육위원회 제2차 (4개 안건, 681개 청크)
- 제332회 기획경제위원회 제2차 (15개 안건, 981개 청크)
- 제332회 기획경제위원회 제4차 (27개 안건, 541개 청크)
- 제332회 기획경제위원회 제5차 (14개 안건, 165개 청크)
- 제332회 도시안전건설위원회 제4차 (8개 안건, 421개 청크)
- 제332회 도시안전건설위원회 제5차 (3개 안건, 29개 청크)
- 제332회 문화체육관광위원회 제2차 (10개 안건, 858개 청크)
- 제332회 본회의 제2차 (16개 안건, 1,019개 청크)
- 제332회 본회의 제4차 (73개 안건, 505개 청크)
- 제332회 주택공간위원회 제1차 (12개 안건, 784개 청크)

#### 2. **VSCode SQLite Viewer 이슈 해결**

**문제**:
```
Error: ENOENT: no such file or directory, stat
'c:\Users\SBA\Project\seoulloc\data\sqlite_DB\agendas.db'
```

**원인**:
- VSCode 확장프로그램이 WSL 경로와 Windows 경로 혼동
- 캐시 문제

**해결 방법**:
1. Windows 환경에서 DB 재생성 (완료)
2. VSCode 재시작
3. 또는 DB Browser for SQLite 사용 (대안)

#### 3. **현재 시스템 상태 확인**

**데이터베이스**:
- SQLite: 182개 안건, 5,984개 청크
- 스키마: `full_text` 적용 완료
- ChromaDB: `./data/chroma_db` (기존 데이터 유지)

**파이프라인 상태**:
```
✅ 1. JSON 생성 (하이브리드 파싱) - 10개 파일
✅ 2. ChromaDB 삽입 - 완료
✅ 3. SQLite DB 생성 - 완료 (Windows)
⏳ 4. AI 요약 생성 - 대기 중
⏳ 5. 서버 실행 및 테스트 - 대기 중
```

---

## 🎯 다음 작업 순서

### 1단계: AI 요약 생성 (우선순위: 높음) ⭐

```bash
# Windows 명령 프롬프트에서
python database/generate_ai_summaries.py
```

**예상 소요 시간**: 약 5-10분 (182개 안건, 비동기 병렬 처리)

**작업 내용**:
- 각 안건의 `combined_text`를 Gemini 2.5 Flash로 요약
- `ai_summary` (150자 이내) 생성
- `key_issues` (핵심 의제) 추출
- 182개 안건 모두 처리

**예상 결과**:
```
================================================================================
🤖 AI 요약 생성 시작 (총 182개 안건)
================================================================================

비동기 처리 중... (10개 안건 동시 처리)

✅ 성공: 182개
❌ 실패: 0개

================================================================================
✅ AI 요약 생성 완료!
================================================================================
```

### 2단계: 서버 실행 및 테스트

```bash
python backend_server.py
```

**테스트 항목**:
- [ ] 메인 페이지: Top 5 안건 표시
- [ ] 검색 기능: AI 요약 표시
- [ ] 상세 페이지: AI 요약 + 핵심 의제 + 회의록 전문
- [ ] 반응형 디자인: max-w-lg 적용

---

## 📊 최종 시스템 구조

### 데이터베이스 스키마 (최종)

**agendas 테이블**:
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
    status TEXT DEFAULT '심사중',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**agenda_chunks 테이블**:
```sql
CREATE TABLE agenda_chunks (
    chunk_id TEXT PRIMARY KEY,
    agenda_id TEXT,
    chunk_index INTEGER,
    speaker TEXT,
    full_text TEXT,               -- ⭐ 전체 텍스트 (text_preview에서 변경)
    FOREIGN KEY (agenda_id) REFERENCES agendas(agenda_id)
)
```

### 파일 구조

```
seoulloc/
├── data/
│   ├── result_txt/              # JSON 파일 10개
│   ├── chroma_db/               # 벡터 DB
│   └── sqlite_DB/
│       └── agendas.db           # ✅ 182개 안건, 5,984개 청크
├── database/
│   ├── create_agenda_database.py    # ✅ DB 생성 (Windows)
│   ├── generate_ai_summaries.py     # ⏳ AI 요약 생성 대기
│   └── insert_to_chromadb.py        # ✅ ChromaDB 삽입 완료
├── data_processing/
│   ├── extract_metadata_hybrid.py   # 하이브리드 파싱
│   └── parse_with_pure_code.py      # Stage 2 순수 코드 파싱
├── frontend/
│   ├── main.html                # Top 5 안건
│   ├── search.html              # 검색 결과
│   └── details.html             # 상세 페이지
├── backend_server.py            # FastAPI 서버
├── HANDOVER.md                  # 이전 작업 내역
└── HANDOVER2.md                 # 현재 문서
```

---

## 💡 핵심 변경 사항 요약

### 1. DB 스키마 변경
- `text_preview` (200자) → `full_text` (전체 텍스트)
- 챗봇 기능을 위한 준비

### 2. AI 요약 개선
- 문장 중간 절단 방지
- LLM 프롬프트: "150자 이내로 요약"
- 후처리: 200자 초과 시에만 자르기

### 3. Windows 환경 통일
- WSL 경로 문제 해결
- Windows 네이티브 환경에서 DB 생성
- VSCode 정상 작동

---

## ⚠️ 주의사항

### 1. 환경 통일
- **모든 스크립트는 Windows 명령 프롬프트에서 실행**
- WSL과 혼용 금지 (경로 문제 발생)
- `conda activate seoul` 필수

### 2. DB 재생성 시
- 기존 `ai_summary`, `key_issues` 삭제됨
- 반드시 `generate_ai_summaries.py` 재실행 필요
- 약 5-10분 소요

### 3. ChromaDB 경로
- 모든 코드: `./data/chroma_db` 통일됨
- 백엔드-DB 일치 확인됨

---

## 🔗 관련 파일

- `HANDOVER.md`: 이전 작업 내역 (하이브리드 파싱 시스템)
- `database/create_agenda_database.py`: SQLite DB 생성
- `database/generate_ai_summaries.py`: AI 요약 생성
- `database/insert_to_chromadb.py`: ChromaDB 벡터 저장
- `backend_server.py`: FastAPI 백엔드
- `frontend/details.html`: 안건 상세 페이지

---

## 📝 다음 작업자 체크리스트

```
[ ] 1. AI 요약 생성
      - 명령: python database/generate_ai_summaries.py
      - 확인: 182개 안건 모두 ai_summary, key_issues 생성
      - 예상 시간: 5-10분

[ ] 2. 서버 실행
      - 명령: python backend_server.py
      - 접속: http://localhost:8000

[ ] 3. 기능 테스트
      - 메인 페이지: Top 5 안건 확인
      - 검색: "인공지능" 검색 → AI 요약 표시 확인
      - 상세 페이지: 핵심 의제, 회의록 전문 확인

[ ] 4. (선택) 추가 데이터 확장
      - 더 많은 회의록 크롤링
      - JSON 생성 → DB 재생성 → AI 요약 재생성
```

---

**마지막 업데이트**: 2025-11-21 오후
**현재 상태**: Windows 환경에서 DB 재생성 완료, AI 요약 생성 대기 중
**다음 단계**: AI 요약 생성 → 서버 테스트
