# SeoulLog 리팩토링 계획 (Refactoring Plan)

> 작성일: 2025-11-22
> 버전: 1.0
> 목적: Service + Repository 패턴 적용으로 클린 아키텍처 구현

---

## 📋 목차

1. [현재 구조의 문제점](#현재-구조의-문제점)
2. [목표 아키텍처](#목표-아키텍처)
3. [리팩토링 후 파일 구조](#리팩토링-후-파일-구조)
4. [계층별 역할](#계층별-역할)
5. [데이터 흐름](#데이터-흐름)
6. [상세 설계](#상세-설계)
7. [리팩토링 단계](#리팩토링-단계)
8. [주요 변경사항](#주요-변경사항)
9. [테스트 계획](#테스트-계획)

---

## 🔴 현재 구조의 문제점

### 1. app.py (759줄)

#### 문제점:
```python
# app.py 현재 구조

@app.post("/api/search")
async def search(request: SearchRequest):
    # 1. 쿼리 분석 (QueryAnalyzer 사용)
    analyzed_metadata = analyzer.analyze(user_query)

    # 2. 메타데이터 검증 (MetadataValidator 사용)
    validation_result = validator.validate(analyzed_metadata)

    # 3. ChromaDB 직접 쿼리 ❌
    chunk_results = chroma_collection.query(...)

    # 4. 안건별 그룹핑 (비즈니스 로직) ❌
    agenda_scores = {}
    for i, chunk_id in enumerate(chunk_results['ids'][0]):
        agenda_id = metadata.get('agenda_id')
        similarity = 1 - (distance / 2)
        agenda_scores[agenda_id] = max(...)

    # 5. SQLite 직접 쿼리 ❌
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor.execute('''SELECT ... FROM agendas WHERE agenda_id = ?''')

    # 6. 결과 포맷팅 (비즈니스 로직) ❌
    formatted_results.append(SearchResult(...))

    return SearchResponse(...)
```

**위반 사항:**
- ❌ **라우터에 비즈니스 로직** (안건 그룹핑, 결과 포맷팅)
- ❌ **라우터에서 DB 직접 접근** (ChromaDB, SQLite)
- ❌ **단일 책임 원칙 위반** (SRP - Single Responsibility Principle)
- ❌ **테스트 불가능** (DB와 강하게 결합)
- ❌ **코드 중복** (connection 관리, 에러 핸들링)

### 2. 다른 엔드포인트들도 동일한 문제

```python
@app.get("/api/top-agendas")   # SQLite 직접 쿼리 ❌

@app.get("/api/agenda/{id}")   # SQLite 직접 쿼리 ❌

@app.get("/api/agenda/{id}/formatted-detail")  # SQLite 직접 쿼리 ❌
```

---

## 🎯 목표 아키텍처

### Clean Architecture (3-Layer Pattern)

```
┌─────────────────────────────────────────────────────────┐
│  Presentation Layer (프레젠테이션 계층)                   │
│  - app.py (FastAPI 라우터)                   │
│  - 요청/응답 처리                                         │
│  - Service 계층 호출만                                    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Business Layer (비즈니스 계층)                           │
│  - services/                                            │
│  - 비즈니스 로직                                          │
│  - 검색 파이프라인                                         │
│  - 데이터 변환                                            │
│  - Repository 계층 호출                                   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Data Access Layer (데이터 접근 계층)                     │
│  - repositories/                                        │
│  - DB 접근 (ChromaDB, SQLite)                           │
│  - 순수 CRUD 작업만                                       │
│  - 비즈니스 로직 없음                                      │
└─────────────────────────────────────────────────────────┘
```

### 설계 원칙

1. **단일 책임 원칙 (SRP)**
   - 각 계층은 하나의 책임만
   - Presentation: 요청/응답 처리
   - Business: 비즈니스 로직
   - Data Access: DB 접근

2. **의존성 역전 원칙 (DIP)**
   - 상위 계층은 하위 계층에 의존
   - 하위 계층은 상위 계층을 몰라야 함

3. **개방-폐쇄 원칙 (OCP)**
   - 확장에는 열려있고 수정에는 닫혀있음
   - 새 기능 추가 시 기존 코드 수정 최소화

4. **테스트 용이성**
   - 각 계층 독립적으로 테스트 가능
   - Mock 객체로 의존성 주입

---

## 📁 리팩토링 후 파일 구조

```
seoulloc/
├── app.py                   # 📄 라우터만 (250-300줄)
│
├── services/                           # 📁 비즈니스 로직
│   ├── __init__.py
│   ├── agenda_service.py               # 안건 CRUD 서비스
│   └── agenda_search_service.py        # 검색 서비스
│
├── repositories/                       # 📁 데이터 접근
│   ├── __init__.py
│   ├── agenda_repository.py            # 안건 Repository
│   └── chroma_repository.py            # ChromaDB Repository
│
├── models/                             # 📁 데이터 모델 (옵션)
│   ├── __init__.py
│   ├── requests.py                     # Request 모델
│   ├── responses.py                    # Response 모델
│   └── domain.py                       # Domain 모델
│
├── search/                             # 📁 검색 파이프라인 (기존)
│   ├── query_analyzer.py
│   ├── simple_query_analyzer.py
│   ├── metadata_validator.py
│   ├── search_executor.py
│   ├── result_formatter.py
│   └── answer_generator_simple.py
│
├── utils/                              # 📁 유틸리티 (기존)
│   ├── custom_openai_embedding.py
│   ├── search_chromadb.py
│   └── cost_tracker.py
│
├── database/                           # 📁 DB 스크립트 (기존)
├── data_processing/                    # 📁 데이터 처리 (기존)
├── crawling/                           # 📁 크롤링 (기존)
└── frontend/                           # 📁 프론트엔드 (기존)
```

---

## 🏛️ 계층별 역할

### 1. Presentation Layer (app.py)

**역할:**
- FastAPI 라우트 정의
- 요청 데이터 검증 (Pydantic)
- Service 계층 호출
- 응답 데이터 반환
- 에러 핸들링 (HTTP 에러)

**금지 사항:**
- ❌ 비즈니스 로직
- ❌ DB 직접 접근
- ❌ 데이터 변환 로직

**예시:**
```python
# app.py

@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """검색 API - Service 계층에 위임"""
    try:
        # Service 호출만
        results = await search_service.search(
            query=request.query,
            n_results=request.n_results or 5
        )

        return SearchResponse(
            query=request.query,
            total_results=len(results),
            results=results
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

### 2. Business Layer (services/)

**역할:**
- 비즈니스 로직 구현
- 데이터 변환 및 포맷팅
- Repository 호출 및 조합
- 트랜잭션 관리 (필요시)
- 비즈니스 규칙 검증

**금지 사항:**
- ❌ HTTP 요청/응답 직접 처리
- ❌ SQL 쿼리 직접 작성
- ❌ DB 연결 직접 관리

#### 2.1. AgendaSearchService

**책임:**
- 검색 파이프라인 전체 조율
- 쿼리 분석 → ChromaDB 검색 → 그룹핑 → SQLite 조회 → 결과 포맷팅
- agenda_type 필터링 (procedural, discussion, other 제외)

**메소드:**
```python
class AgendaSearchService:
    def __init__(
        self,
        chroma_repo: ChromaRepository,
        agenda_repo: AgendaRepository,
        analyzer: QueryAnalyzer,
        validator: MetadataValidator
    ):
        self.chroma_repo = chroma_repo
        self.agenda_repo = agenda_repo
        self.analyzer = analyzer
        self.validator = validator

    async def search(
        self,
        query: str,
        n_results: int = 5
    ) -> List[SearchResult]:
        """검색 파이프라인 실행"""
        # 1. 쿼리 분석
        # 2. 메타데이터 검증
        # 3. ChromaDB 검색 (Repository 호출)
        # 4. 안건별 그룹핑
        # 5. agenda_type 필터링
        # 6. SQLite 조회 (Repository 호출)
        # 7. 결과 포맷팅
```

#### 2.2. AgendaService

**책임:**
- 안건 CRUD 비즈니스 로직
- 안건 상세 조회
- Top 안건 조회
- 포맷된 상세 정보 생성

**메소드:**
```python
class AgendaService:
    def __init__(self, agenda_repo: AgendaRepository):
        self.agenda_repo = agenda_repo

    async def get_agenda_detail(self, agenda_id: str) -> Dict:
        """안건 상세 조회"""
        # Repository 호출 + 비즈니스 로직

    async def get_formatted_detail(self, agenda_id: str) -> Dict:
        """포맷된 안건 상세 (첨부 문서 포함)"""
        # Repository 호출 + 데이터 변환

    async def get_top_agendas(self, limit: int = 5) -> List[TopAgenda]:
        """Top 안건 조회"""
        # Repository 호출 + 필터링 + 정렬
```

---

### 3. Data Access Layer (repositories/)

**역할:**
- DB 연결 관리
- CRUD 작업
- 순수 SQL 쿼리
- 데이터 객체 매핑

**금지 사항:**
- ❌ 비즈니스 로직
- ❌ 데이터 변환 (Domain 객체로만 변환)
- ❌ 여러 Repository 조합

#### 3.1. AgendaRepository

**책임:**
- SQLite DB 접근
- 안건 테이블 CRUD
- 청크 테이블 조회

**메소드:**
```python
class AgendaRepository:
    def __init__(self, db_path: str = "data/sqlite_DB/agendas.db"):
        self.db_path = db_path

    def find_by_id(self, agenda_id: str) -> Optional[Dict]:
        """안건 ID로 조회"""

    def find_all(self, limit: int = None) -> List[Dict]:
        """전체 안건 조회"""

    def find_top_agendas(
        self,
        limit: int = 5,
        exclude_agenda_types: List[str] = None
    ) -> List[Dict]:
        """Top 안건 조회 (개의/산회 제외)"""

    def find_chunks_by_agenda_id(self, agenda_id: str) -> List[Dict]:
        """안건 ID로 청크 조회"""

    def find_by_agenda_ids(
        self,
        agenda_ids: List[str],
        exclude_agenda_types: List[str] = None
    ) -> List[Dict]:
        """여러 안건 ID로 조회 + agenda_type 필터링"""
```

#### 3.2. ChromaRepository

**책임:**
- ChromaDB 접근
- 벡터 검색
- 메타데이터 조회

**메소드:**
```python
class ChromaRepository:
    def __init__(
        self,
        collection_name: str = "seoul_council_meetings",
        persist_directory: str = "./data/chroma_db"
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self._init_client()

    def search(
        self,
        query: str,
        n_results: int = 20,
        where_filter: Dict = None
    ) -> Dict:
        """벡터 검색"""

    def get_all_speakers(self) -> List[str]:
        """모든 발언자 조회"""

    def get_all_dates(self) -> List[str]:
        """모든 회의 날짜 조회"""
```

---

## 🔄 데이터 흐름

### 검색 API 흐름

```
User Request
    ↓
┌───────────────────────────────────────────────────────┐
│ app.py                                     │
│ POST /api/search                                      │
│                                                       │
│ - 요청 데이터 검증 (Pydantic)                          │
│ - search_service.search() 호출                        │
└───────────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────────┐
│ AgendaSearchService                                   │
│                                                       │
│ 1. analyzer.analyze(query)                            │
│    → QueryMetadata 추출                               │
│                                                       │
│ 2. validator.validate(metadata)                       │
│    → ValidationResult 검증                            │
│                                                       │
│ 3. chroma_repo.search(query, where_filter)            │
│    → 청크 결과 (20개)                                  │
│                                                       │
│ 4. _group_by_agenda(chunk_results)                    │
│    → {agenda_id: max_similarity}                      │
│                                                       │
│ 5. _filter_by_agenda_type(agenda_ids)                 │
│    → procedural, discussion, other 제외               │
│                                                       │
│ 6. agenda_repo.find_by_agenda_ids(agenda_ids)         │
│    → 안건 상세 정보 (5개)                              │
│                                                       │
│ 7. _format_results(agendas, scores)                   │
│    → List[SearchResult]                               │
└───────────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────────┐
│ ChromaRepository                  AgendaRepository    │
│                                                       │
│ chroma_collection.query()         cursor.execute()   │
│ → ChromaDB 결과                   → SQLite 결과        │
└───────────────────────────────────────────────────────┘
    ↓
SearchResponse
    ↓
User
```

### 안건 상세 API 흐름

```
User Request
    ↓
┌───────────────────────────────────────────────────────┐
│ app.py                                     │
│ GET /api/agenda/{agenda_id}                           │
│                                                       │
│ - agenda_service.get_agenda_detail(agenda_id) 호출     │
└───────────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────────┐
│ AgendaService                                         │
│                                                       │
│ 1. agenda_repo.find_by_id(agenda_id)                  │
│    → 안건 기본 정보                                     │
│                                                       │
│ 2. agenda_repo.find_chunks_by_agenda_id(agenda_id)    │
│    → 청크 목록                                         │
│                                                       │
│ 3. _parse_json_fields(agenda)                         │
│    → key_issues, attachments JSON 파싱                │
│                                                       │
│ 4. return 안건 상세 딕셔너리                            │
└───────────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────────┐
│ AgendaRepository                                      │
│                                                       │
│ cursor.execute(SELECT ... FROM agendas)               │
│ cursor.execute(SELECT ... FROM agenda_chunks)         │
└───────────────────────────────────────────────────────┘
    ↓
Agenda Detail Response
    ↓
User
```

---

## 🔧 상세 설계

### 1. repositories/agenda_repository.py

```python
"""
안건 Repository - SQLite DB 접근
"""

import sqlite3
from typing import List, Dict, Optional
from contextlib import contextmanager


class AgendaRepository:
    """
    안건 데이터 접근 계층

    책임:
    - SQLite DB 연결 관리
    - 안건 테이블 CRUD
    - 청크 테이블 조회
    """

    def __init__(self, db_path: str = "data/sqlite_DB/agendas.db"):
        """
        초기화

        Args:
            db_path: SQLite DB 경로
        """
        self.db_path = db_path

    @contextmanager
    def get_connection(self):
        """DB 연결 컨텍스트 매니저"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Dict-like access
        try:
            yield conn
        finally:
            conn.close()

    def find_by_id(self, agenda_id: str) -> Optional[Dict]:
        """
        안건 ID로 조회

        Args:
            agenda_id: 안건 ID

        Returns:
            안건 딕셔너리 또는 None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT agenda_id, agenda_title, meeting_title, meeting_date,
                       meeting_url, main_speaker, all_speakers, speaker_count,
                       chunk_count, chunk_ids, combined_text, ai_summary,
                       key_issues, attachments, agenda_type, status, created_at
                FROM agendas
                WHERE agenda_id = ?
            ''', (agenda_id,))

            row = cursor.fetchone()
            return dict(row) if row else None

    def find_by_agenda_ids(
        self,
        agenda_ids: List[str],
        exclude_agenda_types: List[str] = None
    ) -> List[Dict]:
        """
        여러 안건 ID로 조회 + agenda_type 필터링

        Args:
            agenda_ids: 안건 ID 리스트
            exclude_agenda_types: 제외할 agenda_type 리스트

        Returns:
            안건 리스트
        """
        if not agenda_ids:
            return []

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # WHERE 조건 구성
            placeholders = ','.join('?' * len(agenda_ids))
            params = list(agenda_ids)

            where_clause = f'agenda_id IN ({placeholders})'

            # agenda_type 필터링
            if exclude_agenda_types:
                type_placeholders = ','.join('?' * len(exclude_agenda_types))
                where_clause += f' AND agenda_type NOT IN ({type_placeholders})'
                params.extend(exclude_agenda_types)

            query = f'''
                SELECT agenda_id, agenda_title, meeting_title, meeting_date,
                       meeting_url, main_speaker, all_speakers, speaker_count,
                       chunk_count, ai_summary, key_issues, status, agenda_type
                FROM agendas
                WHERE {where_clause}
            '''

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def find_top_agendas(
        self,
        limit: int = 5,
        exclude_titles_like: List[str] = None
    ) -> List[Dict]:
        """
        Top 안건 조회 (최신 + 활발한 논의)

        Args:
            limit: 조회 개수
            exclude_titles_like: 제외할 제목 패턴 리스트 (예: ['%개의%', '%산회%'])

        Returns:
            Top 안건 리스트
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # WHERE 조건 구성
            where_conditions = []
            if exclude_titles_like:
                for pattern in exclude_titles_like:
                    where_conditions.append(f"agenda_title NOT LIKE '{pattern}'")

            where_conditions.append("chunk_count > 10")

            where_clause = ' AND '.join(where_conditions)

            query = f'''
                SELECT agenda_id, agenda_title, meeting_title, meeting_date,
                       ai_summary, chunk_count, main_speaker, status
                FROM agendas
                WHERE {where_clause}
                ORDER BY meeting_date DESC, chunk_count DESC
                LIMIT ?
            '''

            cursor.execute(query, (limit,))
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def find_chunks_by_agenda_id(self, agenda_id: str) -> List[Dict]:
        """
        안건 ID로 청크 조회

        Args:
            agenda_id: 안건 ID

        Returns:
            청크 리스트
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT chunk_id, speaker, full_text, chunk_index
                FROM agenda_chunks
                WHERE agenda_id = ?
                ORDER BY chunk_index
            ''', (agenda_id,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]
```

### 2. repositories/chroma_repository.py

```python
"""
ChromaDB Repository - 벡터 DB 접근
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import os
from utils.custom_openai_embedding import CustomOpenAIEmbeddingFunction


class ChromaRepository:
    """
    ChromaDB 데이터 접근 계층

    책임:
    - ChromaDB 연결 관리
    - 벡터 검색
    - 메타데이터 조회
    """

    def __init__(
        self,
        collection_name: str = "seoul_council_meetings",
        persist_directory: str = "./data/chroma_db"
    ):
        """
        초기화

        Args:
            collection_name: 컬렉션 이름
            persist_directory: ChromaDB 저장 경로
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self._init_client()

    def _init_client(self):
        """ChromaDB 클라이언트 초기화"""
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

        openai_ef = CustomOpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name="text-embedding-3-small"
        )

        self.collection = self.client.get_collection(
            name=self.collection_name,
            embedding_function=openai_ef
        )

    def search(
        self,
        query: str,
        n_results: int = 20,
        where_filter: Optional[Dict] = None
    ) -> Dict:
        """
        벡터 검색

        Args:
            query: 검색 쿼리
            n_results: 결과 개수
            where_filter: 메타데이터 필터 (ChromaDB where 조건)

        Returns:
            ChromaDB 검색 결과
        """
        return self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter if where_filter else None
        )

    def get_all_speakers(self) -> List[str]:
        """
        모든 발언자 조회

        Returns:
            발언자 이름 리스트
        """
        all_data = self.collection.get(include=["metadatas"])
        speakers = set(meta["speaker"] for meta in all_data["metadatas"])
        return sorted(list(speakers))

    def get_all_dates(self) -> List[str]:
        """
        모든 회의 날짜 조회

        Returns:
            회의 날짜 리스트
        """
        all_data = self.collection.get(include=["metadatas"])
        dates = set(meta["meeting_date"] for meta in all_data["metadatas"])
        return sorted(list(dates))
```

### 3. services/agenda_search_service.py

```python
"""
안건 검색 서비스 - 검색 파이프라인 비즈니스 로직
"""

from typing import List, Dict, Optional
from repositories.agenda_repository import AgendaRepository
from repositories.chroma_repository import ChromaRepository
from search.query_analyzer import QueryAnalyzer
from search.metadata_validator import MetadataValidator
from utils.cost_tracker import CostTracker
import json


class AgendaSearchService:
    """
    안건 검색 서비스

    책임:
    - 검색 파이프라인 전체 조율
    - 쿼리 분석 → ChromaDB 검색 → 그룹핑 → 필터링 → SQLite 조회 → 포맷팅
    """

    # agenda_type 필터링 (실제 안건만 표시)
    EXCLUDED_AGENDA_TYPES = ["procedural", "discussion", "other"]

    def __init__(
        self,
        chroma_repo: ChromaRepository,
        agenda_repo: AgendaRepository,
        analyzer: QueryAnalyzer,
        validator: Optional[MetadataValidator] = None
    ):
        """
        초기화

        Args:
            chroma_repo: ChromaDB Repository
            agenda_repo: 안건 Repository
            analyzer: 쿼리 분석기
            validator: 메타데이터 검증기 (optional)
        """
        self.chroma_repo = chroma_repo
        self.agenda_repo = agenda_repo
        self.analyzer = analyzer
        self.validator = validator

    async def search(
        self,
        query: str,
        n_results: int = 5
    ) -> List[Dict]:
        """
        검색 파이프라인 실행

        Args:
            query: 사용자 쿼리
            n_results: 반환할 안건 개수

        Returns:
            검색 결과 리스트 (SearchResult 형태 Dict)
        """
        print(f"🔍 검색 요청: {query}")

        # 비용 추적
        cost_tracker = CostTracker()

        # Step 1: 쿼리 분석
        analyzed_metadata = self._analyze_query(query, cost_tracker)

        # Step 2: 메타데이터 검증
        where_filter = None
        if self.validator:
            is_valid, where_filter = self._validate_metadata(
                analyzed_metadata
            )
            if not is_valid:
                return []

        # Step 3: ChromaDB 검색
        chunk_results = self._search_chunks(
            query, n_results, where_filter, cost_tracker
        )

        # Step 4: 안건별 그룹핑
        agenda_scores = self._group_by_agenda(chunk_results)

        # Step 5: 유사도 순 정렬 + 상위 N개 선택
        sorted_agendas = sorted(
            agenda_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:n_results]

        agenda_ids = [agenda_id for agenda_id, _ in sorted_agendas]

        # Step 6: SQLite 조회 (agenda_type 필터링 적용)
        agendas = self.agenda_repo.find_by_agenda_ids(
            agenda_ids=agenda_ids,
            exclude_agenda_types=self.EXCLUDED_AGENDA_TYPES
        )

        # Step 7: 결과 포맷팅
        results = self._format_results(agendas, agenda_scores)

        # 비용 출력
        self._print_cost_summary(cost_tracker)

        return results

    def _analyze_query(
        self,
        query: str,
        cost_tracker: CostTracker
    ) -> Dict:
        """쿼리 분석"""
        analyzed_metadata = self.analyzer.analyze(query)

        # 비용 추적
        query_tokens = cost_tracker.count_tokens(query)
        cost_tracker.add_chat_cost(
            input_tokens=500 + query_tokens,
            output_tokens=100,
            model="gpt-4o-mini"
        )

        return analyzed_metadata

    def _validate_metadata(
        self,
        metadata: Dict
    ) -> tuple[bool, Optional[Dict]]:
        """메타데이터 검증"""
        if not self.validator:
            return True, None

        validation_result = self.validator.validate(metadata)

        if not validation_result.is_valid:
            print(f"   ⚠️ 검증 실패: {validation_result.message}")
            return False, None

        # where 필터 구성
        where_filter = self._build_where_filter(
            validation_result.corrected_metadata or metadata
        )

        return True, where_filter

    def _build_where_filter(self, metadata: Dict) -> Optional[Dict]:
        """ChromaDB where 필터 구성"""
        where_conditions = []

        if metadata.get('speaker'):
            where_conditions.append({'speaker': metadata['speaker']})
        if metadata.get('meeting_date'):
            where_conditions.append({'meeting_date': metadata['meeting_date']})

        if len(where_conditions) == 1:
            return where_conditions[0]
        elif len(where_conditions) > 1:
            return {'$and': where_conditions}

        return None

    def _search_chunks(
        self,
        query: str,
        n_results: int,
        where_filter: Optional[Dict],
        cost_tracker: CostTracker
    ) -> Dict:
        """ChromaDB 청크 검색"""
        # Embedding 비용 추적
        cost_tracker.add_embedding_cost(
            text=query,
            model="text-embedding-3-small"
        )

        # ChromaDB 검색
        chunk_results = self.chroma_repo.search(
            query=query,
            n_results=min(20, n_results * 4),
            where_filter=where_filter
        )

        print(f"   청크 검색 결과: {len(chunk_results['ids'][0])}개")

        return chunk_results

    def _group_by_agenda(self, chunk_results: Dict) -> Dict[str, float]:
        """
        안건별 그룹핑 (최고 유사도만 선택)

        Returns:
            {agenda_id: max_similarity}
        """
        agenda_scores = {}

        for i, chunk_id in enumerate(chunk_results['ids'][0]):
            metadata = chunk_results['metadatas'][0][i]
            distance = chunk_results['distances'][0][i]

            # Cosine similarity 계산
            similarity = 1 - (distance / 2)

            agenda_id = metadata.get('agenda_id')
            if not agenda_id:
                continue

            # 디버깅
            if i < 3:
                print(f"   [DEBUG] chunk #{i}: distance={distance:.4f}, "
                      f"similarity={similarity:.4f}, agenda_id={agenda_id}")

            # 최고 유사도만 유지
            if agenda_id not in agenda_scores:
                agenda_scores[agenda_id] = similarity
            else:
                agenda_scores[agenda_id] = max(agenda_scores[agenda_id], similarity)

        print(f"   그룹핑된 안건 수: {len(agenda_scores)}개")

        return agenda_scores

    def _format_results(
        self,
        agendas: List[Dict],
        agenda_scores: Dict[str, float]
    ) -> List[Dict]:
        """결과 포맷팅"""
        results = []

        for agenda in agendas:
            agenda_id = agenda['agenda_id']
            similarity = agenda_scores.get(agenda_id, 0.0)

            # AI 요약
            ai_summary = agenda.get('ai_summary') or ""
            if not ai_summary:
                combined_text = agenda.get('combined_text', '')
                ai_summary = combined_text[:200].strip()
                if len(combined_text) > 200:
                    ai_summary += "..."

            # 핵심 의제 파싱
            key_issues = None
            if agenda.get('key_issues'):
                try:
                    key_issues = json.loads(agenda['key_issues'])
                except:
                    pass

            results.append({
                "agenda_id": agenda_id,
                "title": agenda.get('agenda_title', '제목 없음'),
                "ai_summary": ai_summary,
                "key_issues": key_issues,
                "main_speaker": agenda.get('main_speaker', '발언자 없음'),
                "all_speakers": agenda.get('all_speakers', ''),
                "speaker_count": agenda.get('speaker_count', 0),
                "meeting_date": agenda.get('meeting_date', '날짜 없음'),
                "meeting_title": agenda.get('meeting_title', ''),
                "status": agenda.get('status', '심사중'),
                "similarity": round(similarity, 4),
                "chunk_count": agenda.get('chunk_count', 0),
                "meeting_url": agenda.get('meeting_url', '')
            })

        print(f"   최종 안건 결과: {len(results)}건")

        return results

    def _print_cost_summary(self, cost_tracker: CostTracker):
        """비용 요약 출력"""
        cost_summary = cost_tracker.get_summary()
        print(f"\n💰 검색 비용:")
        print(f"   Embedding: {cost_summary['breakdown'].get('embedding', {}).get('cost', 0)*1300:.4f}원")
        if 'chat' in cost_summary['breakdown']:
            print(f"   QueryAnalyzer: {cost_summary['breakdown']['chat']['cost']*1300:.4f}원")
        print(f"   총 비용: {cost_summary['total_cost_krw']}")
```

### 4. services/agenda_service.py

```python
"""
안건 서비스 - 안건 CRUD 비즈니스 로직
"""

from typing import List, Dict, Optional
from repositories.agenda_repository import AgendaRepository
import json


class AgendaService:
    """
    안건 서비스

    책임:
    - 안건 CRUD 비즈니스 로직
    - 안건 상세 조회
    - Top 안건 조회
    """

    def __init__(self, agenda_repo: AgendaRepository):
        """
        초기화

        Args:
            agenda_repo: 안건 Repository
        """
        self.agenda_repo = agenda_repo

    async def get_agenda_detail(self, agenda_id: str) -> Dict:
        """
        안건 상세 조회

        Args:
            agenda_id: 안건 ID

        Returns:
            안건 상세 딕셔너리

        Raises:
            ValueError: 안건을 찾을 수 없는 경우
        """
        # Repository 호출
        agenda = self.agenda_repo.find_by_id(agenda_id)

        if not agenda:
            raise ValueError(f"안건을 찾을 수 없습니다: {agenda_id}")

        # 청크 조회
        chunks = self.agenda_repo.find_chunks_by_agenda_id(agenda_id)

        # JSON 필드 파싱
        key_issues = self._parse_json_field(agenda.get('key_issues'))

        # 결과 구성
        return {
            "agenda_id": agenda['agenda_id'],
            "title": agenda['agenda_title'],
            "meeting_title": agenda['meeting_title'],
            "meeting_date": agenda['meeting_date'],
            "meeting_url": agenda['meeting_url'],
            "main_speaker": agenda['main_speaker'],
            "all_speakers": agenda['all_speakers'],
            "speaker_count": agenda['speaker_count'],
            "chunk_count": agenda['chunk_count'],
            "combined_text": agenda['combined_text'],
            "ai_summary": agenda['ai_summary'],
            "key_issues": key_issues,
            "status": agenda['status'],
            "chunks": [
                {
                    "chunk_id": chunk['chunk_id'],
                    "speaker": chunk['speaker'],
                    "full_text": chunk['full_text']
                }
                for chunk in chunks
            ]
        }

    async def get_formatted_detail(self, agenda_id: str) -> Dict:
        """
        포맷된 안건 상세 조회 (첨부 문서 포함)

        Args:
            agenda_id: 안건 ID

        Returns:
            포맷된 안건 상세

        Raises:
            ValueError: 안건을 찾을 수 없는 경우
        """
        agenda = self.agenda_repo.find_by_id(agenda_id)

        if not agenda:
            raise ValueError(f"안건을 찾을 수 없습니다: {agenda_id}")

        # 첨부 문서 파싱
        attachments = self._parse_json_field(agenda.get('attachments'))

        return {
            "agenda_title": agenda['agenda_title'],
            "summary": agenda.get('ai_summary') or "요약 생성 중...",
            "attachments": attachments or [],
            "combined_text": agenda['combined_text']
        }

    async def get_top_agendas(self, limit: int = 5) -> List[Dict]:
        """
        Top 안건 조회

        Args:
            limit: 조회 개수

        Returns:
            Top 안건 리스트
        """
        agendas = self.agenda_repo.find_top_agendas(
            limit=limit,
            exclude_titles_like=['%개의%', '%산회%']
        )

        return agendas

    def _parse_json_field(self, json_str: Optional[str]) -> Optional[any]:
        """JSON 문자열 파싱"""
        if not json_str:
            return None

        try:
            return json.loads(json_str)
        except:
            return None
```

### 5. app.py (리팩토링 후)

```python
"""
FastAPI 백엔드 서버 (리팩토링 후)

라우팅과 요청/응답 처리만 담당
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from pathlib import Path

# Repository
from repositories.agenda_repository import AgendaRepository
from repositories.chroma_repository import ChromaRepository

# Service
from services.agenda_service import AgendaService
from services.agenda_search_service import AgendaSearchService

# Search Pipeline
from search.query_analyzer import QueryAnalyzer
from search.simple_query_analyzer import SimpleQueryAnalyzer
from search.metadata_validator import MetadataValidator

# Pydantic Models
class SearchRequest(BaseModel):
    query: str
    n_results: Optional[int] = 5

class SearchResult(BaseModel):
    agenda_id: str
    title: str
    ai_summary: str
    key_issues: Optional[List[str]] = None
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
    query: str
    total_results: int
    results: List[SearchResult]

# ... (다른 Pydantic 모델들)

# FastAPI App
app = FastAPI(title="SeoulLog API")

# HTML 경로
HTML_DIR = Path("frontend")

# Repository 초기화
chroma_repo = ChromaRepository()
agenda_repo = AgendaRepository()

# 쿼리 분석기 초기화
try:
    analyzer = QueryAnalyzer()
    print("✅ QueryAnalyzer (OpenAI) 초기화 성공")
except Exception as e:
    print(f"⚠️ QueryAnalyzer 초기화 실패: {e}")
    analyzer = SimpleQueryAnalyzer()

# 메타데이터 검증기 초기화
try:
    validator = MetadataValidator(
        collection_name="seoul_council_meetings",
        persist_directory="./data/chroma_db"
    )
    print("✅ MetadataValidator 초기화 성공")
except Exception as e:
    print(f"⚠️ MetadataValidator 초기화 실패: {e}")
    validator = None

# Service 초기화
search_service = AgendaSearchService(
    chroma_repo=chroma_repo,
    agenda_repo=agenda_repo,
    analyzer=analyzer,
    validator=validator
)
agenda_service = AgendaService(agenda_repo=agenda_repo)

# ============================================================
# 라우트 정의
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def get_main_page():
    """메인 페이지"""
    main_html_path = HTML_DIR / "main.html"
    if not main_html_path.exists():
        raise HTTPException(status_code=404, detail="main.html not found")
    with open(main_html_path, 'r', encoding='utf-8') as f:
        return f.read()

@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    검색 API

    Service 계층에 완전히 위임
    """
    try:
        results = await search_service.search(
            query=request.query,
            n_results=request.n_results or 5
        )

        return SearchResponse(
            query=request.query,
            total_results=len(results),
            results=results
        )

    except Exception as e:
        print(f"❌ 검색 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agenda/{agenda_id}")
async def get_agenda_detail(agenda_id: str):
    """안건 상세 조회"""
    try:
        detail = await agenda_service.get_agenda_detail(agenda_id)
        return detail
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"❌ 안건 상세 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agenda/{agenda_id}/formatted-detail")
async def get_formatted_agenda_detail(agenda_id: str):
    """포맷된 안건 상세"""
    try:
        detail = await agenda_service.get_formatted_detail(agenda_id)
        return detail
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"❌ 포맷된 안건 상세 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/top-agendas")
async def get_top_agendas():
    """Top 안건 조회"""
    try:
        agendas = await agenda_service.get_top_agendas(limit=5)
        return agendas
    except Exception as e:
        print(f"❌ Top 안건 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ... (다른 라우트들)

if __name__ == "__main__":
    print("=" * 80)
    print("SeoulLog 백엔드 서버 시작")
    print("=" * 80)
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## 📝 리팩토링 단계

### Phase 1: Repository 계층 구현

1. **폴더 생성**
   ```bash
   mkdir repositories
   touch repositories/__init__.py
   ```

2. **AgendaRepository 작성**
   - `repositories/agenda_repository.py`
   - SQLite 접근 로직 이동
   - 메소드: `find_by_id`, `find_by_agenda_ids`, `find_top_agendas`, `find_chunks_by_agenda_id`

3. **ChromaRepository 작성**
   - `repositories/chroma_repository.py`
   - ChromaDB 접근 로직 이동
   - 메소드: `search`, `get_all_speakers`, `get_all_dates`

### Phase 2: Service 계층 구현

1. **폴더 생성**
   ```bash
   mkdir services
   touch services/__init__.py
   ```

2. **AgendaSearchService 작성**
   - `services/agenda_search_service.py`
   - 검색 파이프라인 로직 이동
   - 메소드: `search`

3. **AgendaService 작성**
   - `services/agenda_service.py`
   - 안건 CRUD 로직 이동
   - 메소드: `get_agenda_detail`, `get_formatted_detail`, `get_top_agendas`

### Phase 3: app.py 리팩토링

1. **Repository 및 Service 초기화**
   - Repository 인스턴스 생성
   - Service 인스턴스 생성 (의존성 주입)

2. **라우트 간소화**
   - POST /api/search → search_service.search() 호출
   - GET /api/agenda/{id} → agenda_service.get_agenda_detail() 호출
   - GET /api/agenda/{id}/formatted-detail → agenda_service.get_formatted_detail() 호출
   - GET /api/top-agendas → agenda_service.get_top_agendas() 호출

3. **불필요한 코드 제거**
   - ChromaDB 직접 접근 코드 제거
   - SQLite 직접 접근 코드 제거
   - 비즈니스 로직 제거

### Phase 4: 테스트 및 검증

1. **서버 실행**
   ```bash
   python app.py
   ```

2. **API 테스트**
   - POST /api/search 테스트
   - GET /api/agenda/{id} 테스트
   - GET /api/top-agendas 테스트

3. **동작 확인**
   - 검색 결과 확인
   - 안건 상세 확인
   - agenda_type 필터링 확인

### Phase 5: Git Commit

1. **커밋 메시지**
   ```bash
   refactor: Service + Repository 패턴 적용으로 Clean Architecture 구현

   - Repository 계층 추가 (AgendaRepository, ChromaRepository)
   - Service 계층 추가 (AgendaService, AgendaSearchService)
   - app.py 간소화 (759줄 → 300줄)
   - agenda_type 필터링 추가 (procedural, discussion, other 제외)
   - 단일 책임 원칙(SRP) 적용
   - 테스트 용이성 개선
   ```

---

## 📊 주요 변경사항

### 코드 라인 수 변화

| 파일 | 현재 | 리팩토링 후 | 변화 |
|------|------|-------------|------|
| app.py | 759줄 | ~300줄 | **-60%** |
| POST /api/search | 237줄 | ~20줄 | **-92%** |
| **새 파일** | | | |
| repositories/agenda_repository.py | - | ~200줄 | 신규 |
| repositories/chroma_repository.py | - | ~100줄 | 신규 |
| services/agenda_search_service.py | - | ~250줄 | 신규 |
| services/agenda_service.py | - | ~100줄 | 신규 |

### 기능 추가

- ✅ agenda_type 필터링 (procedural, discussion, other 제외)
- ✅ Service + Repository 패턴
- ✅ 의존성 주입 (Dependency Injection)
- ✅ 계층 분리로 테스트 용이성 향상

---

## 🧪 테스트 계획

### 1. Repository 테스트 (수동)

```python
# repositories/agenda_repository.py 테스트

repo = AgendaRepository()

# 1. find_by_id 테스트
agenda = repo.find_by_id("meeting_20251119_113802_agenda_001")
assert agenda is not None
assert agenda['agenda_title'] == "개의"

# 2. find_by_agenda_ids 테스트
agendas = repo.find_by_agenda_ids(
    agenda_ids=["meeting_20251119_113802_agenda_001"],
    exclude_agenda_types=["procedural"]
)
assert len(agendas) == 0  # 개의는 procedural

# 3. find_top_agendas 테스트
top_agendas = repo.find_top_agendas(limit=5)
assert len(top_agendas) <= 5
```

### 2. Service 테스트 (수동)

```python
# services/agenda_search_service.py 테스트

import asyncio

search_service = AgendaSearchService(...)

# 검색 테스트
results = asyncio.run(search_service.search("AI 인재 양성", n_results=5))
assert len(results) <= 5
assert all(r['agenda_type'] not in ['procedural', 'discussion', 'other'] for r in results)
```

### 3. API 테스트 (curl)

```bash
# 검색 API
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "AI 인재 양성", "n_results": 5}'

# 안건 상세 API
curl http://localhost:8000/api/agenda/meeting_20251119_113802_agenda_001

# Top 안건 API
curl http://localhost:8000/api/top-agendas
```

---

## 🎯 성공 기준

### 1. 코드 품질
- [ ] app.py 300줄 이하
- [ ] 각 계층이 단일 책임 원칙 준수
- [ ] 의존성 주입 패턴 적용
- [ ] Private 메소드 적절히 사용 (`_` 접두사)

### 2. 기능
- [ ] 모든 API 정상 동작
- [ ] agenda_type 필터링 정상 작동 (procedural, discussion, other 제외)
- [ ] 검색 결과 정확도 유지
- [ ] 에러 핸들링 정상

### 3. 성능
- [ ] 검색 속도 유지 (기존과 동일)
- [ ] DB 연결 관리 효율적

### 4. 문서화
- [ ] NAMING_CONVENTION.md 준수
- [ ] 각 클래스/메소드에 Docstring 작성
- [ ] 타입 힌팅 적용

---

**마지막 업데이트:** 2025-11-22
**문서 버전:** 1.0
**프로젝트:** SeoulLog - 서울시의회 회의록 검색 시스템
