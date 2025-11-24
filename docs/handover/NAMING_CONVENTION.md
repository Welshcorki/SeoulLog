# SeoulLog 네이밍 규칙 (Naming Convention)

> 작성일: 2025-11-22
> 버전: 1.0
> 목적: 코드베이스 전체의 일관성 있는 네이밍 규칙 정립

---

## 📋 목차

1. [기본 원칙](#기본-원칙)
2. [파일명 (File Names)](#파일명-file-names)
3. [폴더명 (Folder Names)](#폴더명-folder-names)
4. [클래스명 (Class Names)](#클래스명-class-names)
5. [메소드명 (Method Names)](#메소드명-method-names)
6. [변수명 (Variable Names)](#변수명-variable-names)
7. [상수 (Constants)](#상수-constants)
8. [TypedDict & Pydantic 모델](#typeddict--pydantic-모델)
9. [데이터베이스 관련](#데이터베이스-관련)
10. [일관성 체크리스트](#일관성-체크리스트)

---

## 🎯 기본 원칙

### 1. 명확성 (Clarity)
- **의미를 즉시 이해할 수 있어야 함**
- 약어 사용 최소화 (단, 관습적인 약어는 허용)
- 주석 없이도 코드 의도가 명확해야 함

### 2. 일관성 (Consistency)
- **같은 개념은 같은 이름으로**
- 같은 패턴을 반복적으로 사용
- 예외 최소화

### 3. 간결성 (Conciseness)
- 불필요하게 길지 않게
- 하지만 명확성을 희생하지 않는 선에서

### 4. 영어 사용
- 모든 이름은 영어로 작성
- 한국어는 주석과 문서에서만 사용

---

## 📄 파일명 (File Names)

### 규칙
- **snake_case** 사용
- 소문자만 사용
- 단어 구분은 언더스코어(`_`)
- 명확한 역할 표현

### 패턴

#### 생성/삽입 작업
```
create_*.py      # DB/테이블/구조 생성
generate_*.py    # AI를 사용한 콘텐츠 생성
insert_*.py      # 데이터 삽입
```

**예시:**
- `create_agenda_database.py` ✅
- `generate_ai_summaries.py` ✅
- `generate_attachment_summaries.py` ✅
- `insert_to_chromadb.py` ✅

#### 추출/처리 작업
```
extract_*.py     # 데이터 추출
parse_*.py       # 파싱
process_*.py     # 배치 처리
```

**예시:**
- `extract_metadata_hybrid.py` ✅
- `parse_with_pure_code.py` ✅
- `process_all_result_folders.py` ✅

#### 검색/분석 작업
```
search_*.py      # 검색 기능
*_analyzer.py    # 분석 도구
*_validator.py   # 검증 도구
*_executor.py    # 실행 도구
```

**예시:**
- `search_chromadb.py` ✅
- `query_analyzer.py` ✅
- `simple_query_analyzer.py` ✅
- `metadata_validator.py` ✅
- `search_executor.py` ✅

#### 유틸리티
```
*_tracker.py     # 추적 도구
*_formatter.py   # 포맷팅 도구
custom_*.py      # 커스텀 구현
```

**예시:**
- `cost_tracker.py` ✅
- `result_formatter.py` ✅
- `custom_openai_embedding.py` ✅

#### 서버/애플리케이션
```
*_server.py      # 서버 파일
app.py           # 메인 애플리케이션 (간단한 경우)
```

**예시:**
- `app.py` ✅

### 안티패턴 ❌

```python
# 너무 모호함
utils.py
helpers.py
main.py  # 역할이 불명확

# 약어 남용
qry_anlzr.py
mtdt_vldtr.py

# 카멜케이스 사용
QueryAnalyzer.py
searchExecutor.py
```

---

## 📁 폴더명 (Folder Names)

### 규칙
- **snake_case** 사용
- 소문자만 사용
- **복수형 사용** (모듈 그룹인 경우)
- 역할을 명확히 표현

### 구조

```
seoulloc/
├── app.py           # 단일 서버 파일
│
├── crawling/                   # 크롤링 모듈 (복수형)
├── data_processing/            # 데이터 처리 모듈 (복수형)
├── database/                   # 데이터베이스 관련 (복수형)
├── search/                     # 검색 모듈 (복수형)
├── services/                   # 비즈니스 로직 (복수형) ⭐ 새로 추가
├── repositories/               # 데이터 접근 계층 (복수형) ⭐ 새로 추가
├── utils/                      # 유틸리티 (복수형)
│
├── frontend/                   # 프론트엔드 (복수형)
├── data/                       # 데이터 저장소 (복수형)
├── old/                        # 구버전 코드 (복수형)
├── prompts/                    # 프롬프트 템플릿 (복수형)
└── logs/                       # 로그 파일 (복수형)
```

### 권장 네이밍

| 폴더 역할 | 폴더명 | 설명 |
|----------|--------|------|
| 크롤링 | `crawling/` | 웹 크롤링 스크립트 |
| 데이터 처리 | `data_processing/` | 파싱, 변환 |
| 데이터베이스 | `database/` | DB 생성, 마이그레이션 |
| 검색 | `search/` | 검색 파이프라인 |
| 비즈니스 로직 | `services/` | 서비스 계층 |
| 데이터 접근 | `repositories/` | Repository 패턴 |
| 유틸리티 | `utils/` | 공통 유틸리티 |
| 모델 | `models/` | 데이터 모델 (필요시) |
| 프론트엔드 | `frontend/` | HTML/CSS/JS |
| 데이터 | `data/` | 실제 데이터 저장 |

### 안티패턴 ❌

```
# 단수형 사용 (틀림)
service/
repository/
util/

# 카멜케이스 사용
dataProcessing/
searchExecutor/
```

---

## 🏛️ 클래스명 (Class Names)

### 규칙
- **PascalCase** 사용
- 명사형
- 역할을 명확히 표현
- 접미사로 역할 구분

### 패턴

#### 분석/처리 클래스
```python
*Analyzer        # 분석 클래스
*Validator       # 검증 클래스
*Executor        # 실행 클래스
*Processor       # 처리 클래스
*Parser          # 파싱 클래스
```

**예시:**
```python
class QueryAnalyzer:           ✅
class SimpleQueryAnalyzer:     ✅
class MetadataValidator:       ✅
class SearchExecutor:          ✅
```

#### 검색/조회 클래스
```python
*Searcher        # 검색 클래스
*Finder          # 찾기 클래스
*Retriever       # 조회 클래스
```

**예시:**
```python
class MeetingSearcher:         ✅
class AgendaFinder:            ✅
```

#### 포맷팅/변환 클래스
```python
*Formatter       # 포맷팅 클래스
*Converter       # 변환 클래스
*Transformer     # 변환 클래스
```

**예시:**
```python
class ResultFormatter:         ✅
class DataConverter:           ✅
```

#### 추적/관리 클래스
```python
*Tracker         # 추적 클래스
*Manager         # 관리 클래스
*Handler         # 핸들러 클래스
```

**예시:**
```python
class CostTracker:             ✅
class DatabaseManager:         ✅
```

#### 함수형 클래스
```python
*Function        # 함수형 클래스 (callable)
```

**예시:**
```python
class CustomOpenAIEmbeddingFunction:  ✅
```

#### 서비스 계층 ⭐ 새로 추가
```python
*Service         # 비즈니스 로직 서비스
```

**예시:**
```python
class AgendaService:           ✅
class AgendaSearchService:     ✅
```

#### Repository 계층 ⭐ 새로 추가
```python
*Repository      # 데이터 접근 계층
```

**예시:**
```python
class AgendaRepository:        ✅
class ChunkRepository:         ✅
```

### 안티패턴 ❌

```python
# snake_case 사용 (틀림)
class query_analyzer:          ❌
class metadata_validator:      ❌

# 동사형 (틀림)
class AnalyzeQuery:            ❌
class ValidateMetadata:        ❌

# 모호한 이름
class Helper:                  ❌
class Util:                    ❌
class Manager:                 ❌ (단독 사용 금지, 역할 명시 필요)
```

---

## 🔧 메소드명 (Method Names)

### 규칙
- **snake_case** 사용
- 동사로 시작
- 동작을 명확히 표현
- Private 메소드는 언더스코어(`_`) 접두사

### 패턴

#### 조회 (Read)
```python
get_*()          # 단일 항목 조회 (없으면 에러)
find_*()         # 단일 항목 조회 (없으면 None)
get_all_*()      # 전체 조회
list_*()         # 리스트 조회
```

**예시:**
```python
def get_agenda_detail(agenda_id: str):     ✅
def find_agenda_by_id(agenda_id: str):     ✅
def get_all_speakers():                    ✅
def list_agendas():                        ✅
```

#### 검색
```python
search_*()       # 일반 검색
search_by_*()    # 특정 조건 검색
```

**예시:**
```python
def search(query: str):                    ✅
def search_by_speaker(speaker: str):       ✅
def search_by_date(date: str):             ✅
def search_by_agenda(agenda: str):         ✅
```

#### 생성/추가 (Create)
```python
create_*()       # 생성
add_*()          # 추가
insert_*()       # 삽입
generate_*()     # 생성 (AI 사용)
```

**예시:**
```python
def create_database():                     ✅
def add_embedding_cost():                  ✅
def insert_chunk():                        ✅
def generate_summary():                    ✅
```

#### 수정/삭제 (Update/Delete)
```python
update_*()       # 수정
delete_*()       # 삭제
remove_*()       # 제거
```

**예시:**
```python
def update_agenda(agenda_id: str):         ✅
def delete_chunk(chunk_id: str):           ✅
```

#### 검증/분석 (Validation/Analysis)
```python
validate_*()     # 검증
analyze_*()      # 분석
check_*()        # 체크
verify_*()       # 확인
```

**예시:**
```python
def validate(metadata: Dict):              ✅
def analyze(user_query: str):              ✅
def check_existence():                     ✅
```

#### 실행/처리 (Execute/Process)
```python
execute_*()      # 실행
process_*()      # 처리
run_*()          # 실행
perform_*()      # 수행
```

**예시:**
```python
def execute(metadata: Dict):               ✅
def process_all_files():                   ✅
```

#### 포맷팅/변환 (Format/Convert)
```python
format_*()       # 포맷팅
convert_*()      # 변환
transform_*()    # 변환
parse_*()        # 파싱
```

**예시:**
```python
def format_results(results: List):         ✅
def convert_to_json():                     ✅
def parse_html(html: str):                 ✅
```

#### 출력/표시 (Output)
```python
print_*()        # 콘솔 출력
display_*()      # 화면 표시
render_*()       # 렌더링
```

**예시:**
```python
def print_summary():                       ✅
def print_results():                       ✅
```

#### 유틸리티
```python
count_*()        # 카운트
calculate_*()    # 계산
build_*()        # 빌드
extract_*()      # 추출
```

**예시:**
```python
def count_tokens(text: str):               ✅
def calculate_cost():                      ✅
def extract_metadata():                    ✅
```

#### Private 메소드
```python
_*()             # Private 메소드 (내부 사용)
```

**예시:**
```python
def _validate_speaker(speaker: str):       ✅
def _validate_date(date: str):             ✅
def _format_results(results: Dict):        ✅
def _find_similar_speakers():              ✅
def _build_where_filter():                 ✅
```

### 안티패턴 ❌

```python
# 명사형 (틀림)
def speaker():                             ❌
def metadata():                            ❌

# 모호한 이름
def do_something():                        ❌
def handle():                              ❌
def execute():  # 무엇을 실행하는지 불명확 ❌

# 불필요한 접두사
def getSpeaker():  # PascalCase            ❌
def GetSpeaker():  # PascalCase            ❌
```

---

## 📊 변수명 (Variable Names)

### 규칙
- **snake_case** 사용
- 명사형
- 의미를 명확히 표현
- 약어 최소화

### 패턴

#### 일반 변수
```python
user_query       # 사용자 쿼리
n_results        # 결과 개수
meeting_date     # 회의 날짜
agenda_id        # 안건 ID
chunk_id         # 청크 ID
speaker          # 발언자
```

#### 컬렉션 (리스트/딕셔너리)
```python
*_list           # 리스트
*_dict           # 딕셔너리
*_results        # 검색 결과
*_items          # 항목들
*_groups         # 그룹들
```

**예시:**
```python
agenda_list = []               ✅
speaker_dict = {}              ✅
search_results = []            ✅
chunk_items = []               ✅
agenda_groups = {}             ✅
```

#### 설정/옵션
```python
api_key          # API 키
model_name       # 모델 이름
collection_name  # 컬렉션 이름
persist_directory # 저장 경로
db_path          # DB 경로
```

#### 임시 변수
```python
i, j, k          # 루프 인덱스 (짧은 루프만)
idx              # 인덱스
temp             # 임시 변수 (짧은 스코프만)
result           # 결과
data             # 데이터 (구체적 이름 우선)
```

#### Boolean 변수
```python
is_*             # 상태 확인
has_*            # 소유 확인
can_*            # 가능 여부
should_*         # 권장 여부
```

**예시:**
```python
is_valid = True                ✅
has_attachments = False        ✅
can_execute = True             ✅
should_retry = False           ✅
```

#### 메타데이터 관련
```python
analyzed_metadata     # 분석된 메타데이터
validation_result     # 검증 결과
formatted_results     # 포맷팅된 결과
```

#### ChromaDB/DB 관련
```python
chroma_client         # ChromaDB 클라이언트
chroma_collection     # ChromaDB 컬렉션
chunk_results         # 청크 검색 결과
agenda_scores         # 안건 점수
sorted_agendas        # 정렬된 안건
```

### 안티패턴 ❌

```python
# 너무 짧음
q = "질문"                     ❌
r = results                   ❌
d = data                      ❌

# 너무 모호함
temp = get_data()             ❌
data = process()              ❌
result = do_something()       ❌

# 약어 남용
usr_qry = "질문"               ❌
mtdt = metadata               ❌
spkr = speaker                ❌
```

---

## 📐 상수 (Constants)

### 규칙
- **UPPER_CASE** 사용
- 언더스코어(`_`)로 단어 구분
- 명사형
- 모듈 상단에 정의

### 패턴

```python
# 설정값
DEFAULT_N_RESULTS = 5
MAX_RETRIES = 3
TIMEOUT_SECONDS = 30

# 경로
SQLITE_DB_PATH = "data/sqlite_DB/agendas.db"
HTML_DIR = Path("frontend")
LOG_DIR = Path("logs")

# API 관련
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# 가격표
PRICING = {
    "text-embedding-3-small": {
        "input": 0.020 / 1_000_000
    }
}

# 모델명
DEFAULT_MODEL = "gpt-4o-mini"
EMBEDDING_MODEL = "text-embedding-3-small"
```

### 안티패턴 ❌

```python
# snake_case 사용 (틀림)
default_n_results = 5          ❌
max_retries = 3                ❌

# PascalCase 사용 (틀림)
DefaultNResults = 5            ❌
MaxRetries = 3                 ❌
```

---

## 📦 TypedDict & Pydantic 모델

### 규칙
- **PascalCase** 사용
- 명사형
- 데이터를 표현하는 이름
- 접미사로 역할 구분

### 패턴

#### 요청/응답 (FastAPI)
```python
*Request         # 요청 데이터
*Response        # 응답 데이터
```

**예시:**
```python
class SearchRequest(BaseModel):          ✅
    query: str
    n_results: Optional[int] = 5

class SearchResponse(BaseModel):         ✅
    query: str
    total_results: int
    results: List[SearchResult]
```

#### 결과/데이터
```python
*Result          # 결과 데이터
*Metadata        # 메타데이터
*Info            # 정보
*Data            # 데이터
```

**예시:**
```python
class SearchResult(BaseModel):           ✅
class ValidationResult:                  ✅
class QueryMetadata(TypedDict):          ✅
class AgendaInfo(BaseModel):             ✅
```

#### 엔티티 (DB 모델)
```python
# 도메인 객체 이름 그대로
Agenda           # 안건
Chunk            # 청크
Meeting          # 회의
Speaker          # 발언자
```

**예시:**
```python
class Agenda(BaseModel):                 ✅
    agenda_id: str
    title: str

class TopAgenda(BaseModel):              ✅
class HotIssue(BaseModel):               ✅
```

### 일관성 규칙 ⭐ 중요

#### ❌ 문제: 같은 이름, 다른 구조

```python
# query_analyzer.py
class QueryMetadata(TypedDict):
    speaker: Optional[str]
    topic: str
    meeting_date: Optional[str]

# simple_query_analyzer.py
class QueryMetadata(TypedDict):          ❌ 이름 충돌!
    speaker: Optional[str]
    topic: str
    agenda: Optional[str]
    meeting_date: Optional[str]
    intent: str
```

#### ✅ 해결: 역할에 맞는 이름 사용

```python
# query_analyzer.py
class QueryMetadata(TypedDict):          ✅
    speaker: Optional[str]
    topic: str
    meeting_date: Optional[str]

# simple_query_analyzer.py
class SimpleQueryMetadata(TypedDict):    ✅ 구분됨
    speaker: Optional[str]
    topic: str
    agenda: Optional[str]
    meeting_date: Optional[str]
    intent: str
```

---

## 🗄️ 데이터베이스 관련

### 테이블명
- **snake_case** 사용
- **복수형** 사용
- 명사형

**예시:**
```sql
agendas          ✅
agenda_chunks    ✅
meetings         ✅
speakers         ✅
```

### 컬럼명
- **snake_case** 사용
- 명사형
- 접미사로 타입 힌트

**패턴:**
```sql
*_id             # ID (PRIMARY KEY, FOREIGN KEY)
*_date           # 날짜
*_url            # URL
*_count          # 개수
*_text           # 텍스트
*_title          # 제목
*_at             # 타임스탬프 (created_at, updated_at)
```

**예시:**
```sql
agenda_id        ✅
meeting_date     ✅
meeting_url      ✅
speaker_count    ✅
combined_text    ✅
agenda_title     ✅
created_at       ✅
```

### ChromaDB 관련

#### 컬렉션명
- **snake_case** 사용
- **복수형** 사용

**예시:**
```python
collection_name = "seoul_council_meetings"     ✅
```

#### 메타데이터 필드
- **snake_case** 사용
- DB 컬럼명과 동일하게

**예시:**
```python
metadata = {
    "agenda_id": "...",      ✅
    "speaker": "...",        ✅
    "meeting_date": "...",   ✅
    "meeting_title": "...",  ✅
    "agenda": "...",         ✅
    "meeting_url": "...",    ✅
    "chunk_index": 0         ✅
}
```

---

## ✅ 일관성 체크리스트

### 파일 생성 시

- [ ] snake_case 사용
- [ ] 역할에 맞는 접두사/접미사 사용
- [ ] 모호한 이름 지양 (utils.py, helpers.py 금지)

### 클래스 생성 시

- [ ] PascalCase 사용
- [ ] 명사형
- [ ] 역할에 맞는 접미사 사용 (*Service, *Repository, *Analyzer, 등)

### 메소드 생성 시

- [ ] snake_case 사용
- [ ] 동사로 시작
- [ ] Private 메소드는 `_` 접두사

### 변수 생성 시

- [ ] snake_case 사용
- [ ] 명사형
- [ ] 의미를 명확히 표현
- [ ] Boolean은 `is_*`, `has_*`, `can_*` 패턴

### 상수 생성 시

- [ ] UPPER_CASE 사용
- [ ] 모듈 상단에 정의

### Pydantic 모델 생성 시

- [ ] PascalCase 사용
- [ ] 역할에 맞는 접미사 (*Request, *Response, *Result, *Metadata)
- [ ] 같은 이름 중복 금지

### DB 관련

- [ ] 테이블명: snake_case, 복수형
- [ ] 컬럼명: snake_case, 접미사로 타입 힌트
- [ ] ChromaDB 메타데이터: DB 컬럼명과 동일

---

## 📝 예시: 새로운 기능 추가 시

### 시나리오: "안건 댓글 기능" 추가

#### ✅ 올바른 네이밍

```
파일 구조:
services/
  agenda_comment_service.py      # 비즈니스 로직

repositories/
  agenda_comment_repository.py   # DB 접근

models/
  comment.py                      # Pydantic 모델

database/
  create_comment_table.py         # DB 마이그레이션
```

```python
# models/comment.py
class CommentCreateRequest(BaseModel):       ✅
    agenda_id: str
    user_id: str
    content: str

class CommentResponse(BaseModel):            ✅
    comment_id: str
    agenda_id: str
    user_id: str
    content: str
    created_at: datetime

# repositories/agenda_comment_repository.py
class AgendaCommentRepository:               ✅
    def create_comment(self, comment_data: Dict):  ✅
        ...

    def get_comments_by_agenda_id(self, agenda_id: str):  ✅
        ...

    def delete_comment(self, comment_id: str):  ✅
        ...

# services/agenda_comment_service.py
class AgendaCommentService:                  ✅
    def add_comment(self, request: CommentCreateRequest):  ✅
        ...

    def list_comments(self, agenda_id: str):  ✅
        ...
```

#### ❌ 잘못된 네이밍

```python
# 파일명 - PascalCase 사용 (틀림)
AgendaCommentService.py          ❌

# 클래스명 - snake_case 사용 (틀림)
class agenda_comment_service:    ❌

# 메소드명 - 명사형 (틀림)
def comment(self):               ❌

# 메소드명 - PascalCase (틀림)
def AddComment(self):            ❌

# 변수명 - 약어 남용
cmt_id = "123"                   ❌
usr_id = "456"                   ❌
```

---

## 🔍 리뷰 체크리스트

코드 리뷰 시 다음을 확인:

### 1. 파일/폴더명
- [ ] snake_case 사용
- [ ] 역할이 명확한가?
- [ ] 패턴에 맞는가? (create_*, generate_*, *_analyzer, 등)

### 2. 클래스명
- [ ] PascalCase 사용
- [ ] 명사형
- [ ] 접미사가 역할을 표현하는가?

### 3. 메소드명
- [ ] snake_case 사용
- [ ] 동사로 시작
- [ ] 동작이 명확한가?
- [ ] Private 메소드는 `_` 접두사

### 4. 변수명
- [ ] snake_case 사용
- [ ] 의미가 명확한가?
- [ ] 너무 짧거나 모호하지 않은가?

### 5. 일관성
- [ ] 같은 개념은 같은 이름으로 표현
- [ ] 프로젝트 전체와 일관성 유지

---

## 📚 참고 자료

- [PEP 8 - Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices)

---

**마지막 업데이트:** 2025-11-22
**문서 버전:** 1.0
**프로젝트:** SeoulLog - 서울시의회 회의록 검색 시스템
