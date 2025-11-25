# 첨부 문서 요약 생성 가이드

Step 5: 첨부 문서 요약 생성 (Gemini File API)

## 📋 개요

서울시의회 회의록의 첨부 문서 (PDF, HWP 등)를 자동으로 다운로드하여 Gemini File API로 요약을 생성하고, SQLite DB의 `attachments` 필드를 업데이트합니다.

## 🎯 목적

**원래 파이프라인:**
```
JSON 파일의 attachments:
{
  "title": "도시공간본부 업무보고서",
  "url": "https://ms.smc.seoul.kr/record/appendixDownload.do?key=..."
}

↓ (Step 5 실행)

DB의 attachments:
{
  "title": "도시공간본부 업무보고서",
  "url": "https://...",
  "summary": "도시공간본부는 ICAO 김포공항 고도제한..." ← 추가됨!
}
```

## 🚀 사용법

### Option 1: 독립 실행 (Step 5만)

```bash
# 조건: SQLite DB가 이미 생성되어 있어야 함
python database/generate_attachment_summaries.py
```

### Option 2: 전체 파이프라인 실행

```bash
# Step 1~5 모두 실행
python rebuild_all_db.py
```

## ⚙️ 동작 방식

1. **DB 조회**: SQLite DB에서 `attachments` 필드가 있는 안건 조회
2. **파일 다운로드**: 첨부 문서 URL에서 PDF/HWP 파일 다운로드
3. **Gemini Upload**: Gemini File API로 파일 업로드
4. **요약 생성**: Gemini 2.5 Flash로 요약 생성 (2-4줄)
5. **DB 업데이트**: `attachments` 필드에 summary 추가
6. **재실행 안전**: 이미 요약이 있으면 건너뜀

## 📊 처리 흐름

```
안건 조회 (SQLite)
  ↓
첨부 문서 발견: attachments != null
  ↓
각 첨부 문서:
  1. URL에서 파일 다운로드
  2. Gemini File API 업로드
  3. 요약 생성 (2-4줄)
  4. 로컬 파일 삭제
  ↓
DB 업데이트: attachments += summary
  ↓
완료!
```

## 🔧 기술 스택

- **파일 다운로드**: requests (동기)
- **AI 요약**: Gemini 2.5 Flash (비동기)
- **DB**: SQLite
- **병렬 처리**: asyncio (3개씩 동시)

## 📝 요약 프롬프트

```
문서 유형별 자동 인식:
- 조례안: 목적, 주요 내용, 기대 효과
- 보고서: 핵심 현황, 주요 발견, 결론
- 검토의견서: 안건 평가, 주요 쟁점, 검토 의견

출력 형식:
- 2-4줄로 간결하게
- 시민이 이해하기 쉬운 언어
- 전문 용어는 쉽게 설명
```

## 📋 예시

**입력 (DB):**
```json
{
  "title": "도시공간본부 업무보고서",
  "url": "https://ms.smc.seoul.kr/record/appendixDownload.do?key=abc123"
}
```

**처리:**
1. 파일 다운로드: `도시공간본부 업무보고서.pdf`
2. Gemini 업로드 및 요약 생성
3. 요약: "도시공간본부는 ICAO 김포공항 고도제한 기준 개정(2030년 시행)에 대한 규제 강화 우려를 보고했다. 서울시는 안전을 전제로 현행보다 규제가 심화되지 않도록 관계기관과 협력, 2026년 세부기준 확정 시 주민 불이익을 막고 합리적 완화안을 마련해 적극 대응할 계획이다."

**출력 (DB):**
```json
{
  "title": "도시공간본부 업무보고서",
  "url": "https://ms.smc.seoul.kr/record/appendixDownload.do?key=abc123",
  "summary": "도시공간본부는 ICAO 김포공항 고도제한..."
}
```

## 💰 비용

- **Gemini 2.5 Flash**: 무료 (2025년 1월 기준)
- **다운로드**: 무료
- **예상 시간**: 안건당 30초 (파일 크기에 따라 다름)

## ⚠️ 주의사항

1. **SQLite DB 필수**: 먼저 `create_agenda_database.py` 실행 필요
2. **인터넷 연결 필수**: 파일 다운로드, Gemini API
3. **재실행 안전**: 이미 요약이 있으면 자동으로 건너뜀
4. **다운로드 실패**: 네트워크 오류 시 "첨부 문서 다운로드 실패" 표시

## 🔍 디버깅

### 특정 안건만 확인
```python
import sqlite3
import json

conn = sqlite3.connect('data/sqlite_DB/agendas.db')
cursor = conn.cursor()

cursor.execute('''
    SELECT agenda_title, attachments
    FROM agendas
    WHERE agenda_id = '제332회 규제개혁특별위원회 제3차(2025.09.05)_agenda_001'
''')

result = cursor.fetchone()
attachments = json.loads(result[1])
print(json.dumps(attachments, ensure_ascii=False, indent=2))
```

### 요약 통계 확인
```sql
SELECT
  COUNT(*) as total_agendas,
  SUM(CASE WHEN attachments IS NOT NULL THEN 1 ELSE 0 END) as with_attachments
FROM agendas;
```

## 🚀 향후 개선 방향

- [ ] HWP → PDF 변환 지원
- [ ] 요약 품질 평가 (길이, 명확성)
- [ ] 다운로드 실패 시 재시도 로직
- [ ] 병렬 처리 개수 조정 (5개 → 10개)
