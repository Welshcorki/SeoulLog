# 서울시의회 회의록 시민 서비스

시민이 쉽게 이해할 수 있는 서울시의회 회의록 서비스 프로토타입

---

## 📋 프로젝트 개요

**목적**: 복잡한 서울시의회 회의록을 2030 세대가 쉽게 이해하고 접근할 수 있도록 개선

**핵심 전략**: 회의록 중심 → **이슈 중심**으로 전환
- 기존: "제332회 운영위원회 회의록"
- 개선: "지하철 요금 150원 인상 확정" 같은 실제 이슈

---

## 🎯 핵심 기능 (2주 MVP)

1. **3줄 요약** - 긴 회의록을 3줄로 요약
2. **쉬운 말 설명** - 어려운 용어를 쉽게 풀어서 설명
3. **RAG 챗봇** - 궁금한 점을 바로 질문 가능
4. **키워드 검색** - 관련도 순으로 정확한 검색
5. **시각적 타임라인** - 안건의 진행 과정 시각화

---

## 🗂️ 프로젝트 구조

```
seoulloc/
├── frontend/                    # Next.js 16 프론트엔드
│   ├── app/
│   │   ├── page.tsx            # 메인 페이지 (이슈 목록)
│   │   ├── issue/[id]/page.tsx # 이슈 상세 페이지
│   │   └── comparison/page.tsx # Before/After 비교 페이지
│   ├── components/
│   │   ├── IssueCard.tsx       # 이슈 카드 컴포넌트
│   │   └── ChatBot.tsx         # 플로팅 챗봇
│   └── data/
│       ├── mockData.ts         # Mock 데이터 (초기 개발용)
│       └── realData.ts         # 실제 크롤링 데이터 ✅
│
├── result/                      # 크롤링된 회의록 저장 폴더
│   ├── 제332회 본회의 제1차/
│   ├── 제332회 운영위원회 제1차/
│   └── ...                     # 총 9개 회의록
│
├── crawl_final.py              # 단일 회의록 크롤링 스크립트
├── crawl_all_urls.py           # 여러 URL 일괄 크롤링
├── parse_real_data.py          # 크롤링 데이터 → UI 데이터 변환 ✅
│
├── extract_session_332_links.py # Selenium으로 링크 추출 (시도)
├── extract_links_browser.js     # 브라우저 콘솔에서 링크 추출 ✅
│
└── URL.md                       # 크롤링할 회의록 URL 목록
```

---

## 🚀 실행 방법

### 1. 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
```

→ http://localhost:3000 에서 확인

### 2. 회의록 크롤링

#### 방법 A: URL.md에 있는 URL들 크롤링
```bash
python crawl_all_urls.py
```

#### 방법 B: 제332회 전체 회의록 링크 추출 (브라우저 콘솔 사용)

1. https://ms.smc.seoul.kr/kr/assembly/session.do 열기
2. **F12** → Console 탭
3. `allow pasting` 입력
4. `extract_links_browser.js` 파일 내용 붙여넣기
5. Enter → 자동으로 URL 추출 및 클립보드 복사
6. `URL.md`에 붙여넣기

### 3. 크롤링 데이터 파싱 (UI용 데이터 생성)

```bash
python parse_real_data.py
```

→ `frontend/data/realData.ts` 파일 생성됨

---

## 📊 현재 상태

### ✅ 완료된 작업

1. **프론트엔드 UI 구현**
   - 이슈 중심 메인 페이지
   - 이슈 상세 페이지 (3줄 요약, 쉬운 설명, 타임라인)
   - Before/After 비교 페이지
   - 플로팅 챗봇 UI (Mock)

2. **데이터 크롤링**
   - 9개 회의록 크롤링 완료
   - JSON, Markdown, TXT 형식으로 저장

3. **데이터 파싱**
   - 636개 안건을 이슈로 변환
   - 프론트엔드에서 실제 데이터 표시 중

### 🔄 진행 중

1. **제332회 전체 회의록 링크 추출**
   - Selenium 방식: 트리 구조 문제로 실패
   - 브라우저 콘솔 방식: 스크립트 작성 완료, 테스트 필요

### 📝 향후 작업

1. **RAG 챗봇 구현**
   - VectorDB (ChromaDB) 설정
   - 임베딩 생성
   - LLM 연동

2. **검색 기능 개선**
   - 시맨틱 서치 구현
   - 관련도 순 정렬

3. **데이터 필터링**
   - 636개 안건 → 시민 관심사 기준으로 선별
   - 지역별 필터링 정확도 향상

4. **요약 및 설명 자동화**
   - 현재: 하드코딩
   - 목표: LLM으로 자동 생성

---

## 🛠️ 기술 스택

### Frontend
- **Framework**: Next.js 16 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Build Tool**: Turbopack

### Backend (예정)
- **Language**: Python
- **Vector DB**: ChromaDB
- **Embedding**: sentence-transformers
- **LLM**: OpenAI API / Claude API

### Crawling
- **Library**: BeautifulSoup4, Requests
- **Automation**: Selenium (부분 사용)

---

## 📂 주요 파일 설명

### 프론트엔드

#### `frontend/app/page.tsx`
- 메인 페이지
- 실제 크롤링된 636개 이슈 중 20개 표시
- 지역 필터링 기능

#### `frontend/app/issue/[id]/page.tsx`
- 이슈 상세 페이지
- 3줄 요약, 쉬운 설명, 타임라인, 첨부자료, 원문 보기

#### `frontend/data/realData.ts`
- `parse_real_data.py`로 자동 생성됨
- 636개 실제 이슈 데이터

### 크롤링 & 파싱

#### `crawl_final.py`
- 단일 회의록 URL 크롤링
- JSON, Markdown, TXT 생성

#### `crawl_all_urls.py`
- `URL.md`의 여러 URL 일괄 크롤링
- 서버 부하 방지 (2초 간격)

#### `parse_real_data.py`
- `result/` 폴더의 JSON 파일들을 읽어서
- 프론트엔드용 데이터로 변환
- **각 안건 = 1개 이슈**로 변환

**파싱 로직:**
1. 회의록에서 "의사일정" 섹션 추출
2. 번호로 구분된 안건들 파싱 (1., 2., 3., ...)
3. 각 안건마다 이슈 객체 생성
4. 메타데이터, 요약, 타임라인 자동 생성 (규칙 기반)

#### `extract_links_browser.js`
- 브라우저 콘솔에서 실행
- 제332회 임시회 전체 회의록 링크 자동 추출
- **3단계 트리 구조** 자동 펼침:
  1. 제11대
  2. 제332회
  3. 본회의, 운영위원회, 각 위원회...
  4. 각 위원회의 회차별 링크

---

## 🎨 UI 디자인 특징

### 메인 페이지
- **이슈 카드 형식**: 이모지 + 제목 + 상태 + 영향
- **지역 필터**: 내 지역 관련 이슈만 보기
- **서비스 소개**: 3줄 요약, 쉬운 말, 챗봇, 타임라인 강조

### 이슈 상세 페이지
- **3줄 요약**: 파란색 박스
- **쉬운 설명**: 노란색 강조 박스
- **타임라인**: 세로선 + 컬러 도트 (제안/심의/통과)
- **첨부 자료**: PDF 다운로드 링크
- **원문 보기**: 접었다 펼 수 있는 details 태그

### 비교 페이지
- **Before/After 비교**: 기존 SMC 사이트 vs 개선안
- **사용자 시나리오**: 직장인, 주부, 청년 관점
- **기대 효과**: 10배 체류시간, 6배 재방문율, 7배 참여율

---

## 🔧 알려진 문제 및 해결 방법

### 1. lightningcss 에러 (Windows)
```bash
rmdir /s /q node_modules
del package-lock.json
npm install
```

### 2. Next.js 개발 서버 충돌
- 에러: "Unable to acquire lock"
- 원인: 다른 개발 서버가 실행 중
- 해결: 기존 프로세스 종료 후 재실행

### 3. Selenium 링크 추출 실패
- 원인: Fancytree의 동적 로딩
- 해결: 브라우저 콘솔 JavaScript 방식 사용

### 4. 이슈가 636개로 너무 많음
- 원인: 모든 안건을 이슈로 변환
- 해결 필요: 중요한 이슈만 필터링 (키워드 기반 또는 LLM 판단)

### 5. 지역 필터가 작동 안 함
- 원인: 대부분 안건이 "전체"로 분류됨
- 해결 필요: 더 정교한 지역 판단 로직

---

## 📝 데이터 흐름

```
서울시의회 사이트
    ↓
[크롤링] crawl_all_urls.py
    ↓
result/*.json (9개 회의록)
    ↓
[파싱] parse_real_data.py
    ↓
frontend/data/realData.ts (636개 이슈)
    ↓
[프론트엔드] Next.js
    ↓
http://localhost:3000 (사용자)
```

---

## 🎯 다음 단계 (우선순위)

### 우선순위 1: 데이터 품질 개선
- [ ] 636개 이슈 → 중요 이슈만 선별
- [ ] LLM으로 3줄 요약 자동 생성
- [ ] 쉬운 설명 자동 생성

### 우선순위 2: RAG 챗봇 구현
- [ ] ChromaDB 설정
- [ ] 회의록 임베딩 생성
- [ ] LLM API 연동
- [ ] 챗봇 UI → 실제 API 연결

### 우선순위 3: 검색 기능
- [ ] 시맨틱 서치 구현
- [ ] 검색 결과 페이지 (`/search`) 생성
- [ ] 관련도 순 정렬

### 우선순위 4: 추가 기능
- [ ] 지역 필터 정확도 개선
- [ ] 카테고리 분류 (예산/조례/인사 등)
- [ ] 북마크 기능
- [ ] 공유 기능

---

## 📌 참고 링크

- **원본 사이트**: https://ms.smc.seoul.kr/kr/assembly/session.do
- **회의록 목록**: https://ms.smc.seoul.kr/kr/assembly/session.do
- **프로젝트 계획**: `project_plan.md` 참고

---

## 💡 핵심 인사이트

### 문제 정의
- 2030 세대는 "제332회 운영위원회"에 관심 없음
- 68페이지 회의록은 읽지 않음
- 검색해도 원하는 정보를 못 찾음

### 해결 방법
- **이슈 중심 접근**: "지하철 요금 인상", "청년 지원금" 같은 구체적 이슈
- **정보 계층화**: 3줄 요약 → 상세 → 전문
- **대화형 인터페이스**: 챗봇으로 질문 가능
- **시각화**: 복잡한 과정을 타임라인으로

### 기대 효과
- 페이지 체류시간: 30초 → 3분 (10배 ↑)
- 재방문율: 5% → 30% (6배 ↑)
- 시민 참여율: 0.3% → 2% (7배 ↑)

---

## 👥 기여 방법

1. 이슈 등록
2. Pull Request
3. 피드백 제공

---

## 📄 라이선스

MIT License

---

**Last Updated**: 2025-11-17
**Status**: 프로토타입 개발 중 (2주차)
