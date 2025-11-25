# 파이프라인 검증 체크리스트

## 실행 명령어
```bash
python rebuild_all_db.py --only-new 3
```

## ✅ 1. 로그 파일 확인

### 기본 정보
- [ ] 로그 파일 생성됨: `logs/pipeline_YYYYMMDD_HHMMSS.log`
- [ ] 에러 없이 완료 메시지 표시: "✅ 전체 파이프라인 완료!"

### Step별 성공 여부
- [ ] Step 0: 데이터 초기화 완료
- [ ] Step 1: JSON 생성 완료 (3개)
- [ ] Step 2: ChromaDB 삽입 완료
- [ ] Step 3: SQLite DB 생성 완료
- [ ] Step 4: AI 요약 생성 완료
- [ ] Step 5: 첨부 문서 요약 생성 완료

### 비용 추적
- [ ] Step 1 비용 기록됨 (Gemini 2.5 Pro)
- [ ] Step 2 비용 기록됨 (OpenAI Embedding) - $0.00이 아님
- [ ] Step 4 비용 기록됨 (Gemini 2.5 Flash)
- [ ] Step 5 비용 기록됨 (Gemini 2.5 Flash)
- [ ] 전체 비용 요약 출력됨
- [ ] 모델별 토큰 사용량 표시됨

**확인 명령어:**
```bash
# 로그에서 비용 정보 추출
grep "비용\|총 비용" logs/pipeline_*.log | tail -10

# Step별 완료 확인
grep "Step [0-5].*완료" logs/pipeline_*.log
```

---

## ✅ 2. JSON 파일 검증

### 파일 생성 확인
- [ ] `data/result_txt/` 폴더에 3개 JSON 파일 생성됨
- [ ] 각 JSON 파일 크기가 0보다 큼

### JSON 내용 검증
```bash
# JSON 파일 개수 확인
ls data/result_txt/*.json | wc -l

# JSON 구조 확인 (첫 번째 파일)
python3 -c "
import json
from pathlib import Path

json_files = list(Path('data/result_txt').glob('*.json'))
if json_files:
    with open(json_files[0], 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f'✅ meeting_info 존재: {\"meeting_info\" in data}')
    print(f'✅ agenda_mapping 존재: {\"agenda_mapping\" in data}')
    print(f'✅ 안건 수: {len(data.get(\"agenda_mapping\", []))}개')

    # 첨부 문서 URL 확인
    attachments_with_url = 0
    for agenda in data.get('agenda_mapping', []):
        for att in agenda.get('attachments', []):
            if att.get('download_url'):
                attachments_with_url += 1

    print(f'✅ download_url 있는 첨부 문서: {attachments_with_url}개')
"
```

**예상 결과:**
- ✅ meeting_info 존재: True
- ✅ agenda_mapping 존재: True
- ✅ 안건 수: 10~15개
- ✅ download_url 있는 첨부 문서: 5~20개

---

## ✅ 3. ChromaDB 검증

### 데이터 존재 확인
```bash
# ChromaDB 파일 크기 확인
du -sh data/chroma_db/

# ChromaDB 컬렉션 확인
python3 -c "
import chromadb
from chromadb.config import Settings

client = chromadb.PersistentClient(
    path='data/chroma_db',
    settings=Settings(anonymized_telemetry=False)
)

try:
    collection = client.get_collection('seoul_council_meetings')
    count = collection.count()
    print(f'✅ ChromaDB 청크 수: {count}개')

    # 예상: 3개 파일 × 평균 450개 청크 = 약 1,350개
    if count > 100:
        print('✅ 정상: 충분한 데이터 저장됨')
    else:
        print('⚠️  경고: 데이터가 너무 적음')
except Exception as e:
    print(f'❌ ChromaDB 오류: {e}')
"
```

**예상 결과:**
- ✅ ChromaDB 청크 수: 1,000~2,000개
- ✅ 정상: 충분한 데이터 저장됨

---

## ✅ 4. SQLite DB 검증

### 안건 데이터 확인
```bash
python3 -c "
import sqlite3
import json

conn = sqlite3.connect('data/sqlite_DB/agendas.db')
cursor = conn.cursor()

# 전체 안건 수
cursor.execute('SELECT COUNT(*) FROM agendas')
total = cursor.fetchone()[0]
print(f'✅ 전체 안건 수: {total}개')

# AI 요약이 있는 안건 수
cursor.execute('SELECT COUNT(*) FROM agendas WHERE ai_summary IS NOT NULL AND ai_summary != \"\"')
with_summary = cursor.fetchone()[0]
print(f'✅ AI 요약 있는 안건: {with_summary}개')

# 첨부 문서 요약 확인
cursor.execute('SELECT attachments FROM agendas WHERE attachments IS NOT NULL AND attachments != \"\" LIMIT 1')
row = cursor.fetchone()
if row:
    attachments = json.loads(row[0])
    has_summary = any(att.get('summary') for att in attachments)
    has_url = any(att.get('download_url') for att in attachments)
    print(f'✅ 첨부 문서 URL: {\"있음\" if has_url else \"없음\"}')
    print(f'✅ 첨부 문서 요약: {\"있음\" if has_summary else \"없음\"}')

conn.close()
"
```

**예상 결과:**
- ✅ 전체 안건 수: 30~45개 (3개 파일 기준)
- ✅ AI 요약 있는 안건: 30~45개
- ✅ 첨부 문서 URL: 있음
- ✅ 첨부 문서 요약: 있음

---

## ✅ 5. 백엔드 API 테스트

### 서버 실행
```bash
python app.py
```

### API 테스트
```bash
# 1. 안건 검색 테스트
curl "http://localhost:8000/api/search?query=예산&limit=5"

# 2. Top 안건 조회
curl "http://localhost:8000/api/agendas/top?limit=5"

# 3. 특정 안건 상세 조회 (agenda_id는 실제 값으로 변경)
curl "http://localhost:8000/api/agendas/{agenda_id}"
```

**예상 결과:**
- [ ] 검색 결과에 안건 리스트 반환
- [ ] Top 안건에 `agenda_title`, `ai_summary`, `attachments` 포함
- [ ] 상세 조회 시 `combined_text`, `key_issues` 포함
- [ ] 첨부 문서에 `summary` 필드 존재 ("undefined undefined" 없음)

---

## ✅ 6. 프론트엔드 확인

### 브라우저 테스트
1. http://localhost:8000 접속
2. 검색창에 "예산" 입력
3. 검색 결과 클릭
4. 상세 페이지 확인

**확인 항목:**
- [ ] 검색 결과가 표시됨
- [ ] 안건 제목, 요약이 정상 표시
- [ ] 첨부 문서 섹션에서 "undefined undefined" 없음
- [ ] 첨부 문서 요약 정상 표시
- [ ] 핵심 의제(key_issues) 표시됨

---

## 📊 비용 예상

### 3개 파일 기준
- Step 1: ₩165 × 3 = **₩495**
- Step 2: ₩1 × 3 = **₩3**
- Step 4: ₩12 × 3 = **₩36**
- Step 5: ₩13 × 3 = **₩39**
- **합계: 약 ₩573**

### 52개 파일 전체 (검증 성공 후)
- Step 1: ₩165 × 52 = **₩8,580**
- Step 2: ₩1 × 52 = **₩52**
- Step 4: ₩12 × 52 = **₩624**
- Step 5: ₩13 × 52 = **₩676**
- **합계: 약 ₩9,932**

---

## 🚨 문제 발생 시 대처

### 일반적인 오류
1. **KeyError**: 위에서 수정했으므로 발생하지 않아야 함
2. **Step 2 비용 $0.00**: OpenAI Embedding 토큰 추출 문제
3. **aiohttp Unclosed session**: 무시 가능 (기능에 영향 없음)
4. **첨부 문서 다운로드 실패**: 네트워크 문제 또는 URL 만료

### 중단된 경우
```bash
# 로그 확인
tail -100 logs/pipeline_*.log

# 특정 Step부터 재실행 (예: Step 4부터)
# rebuild_all_db.py에 --start-from 옵션 추가 필요
```

---

## ✅ 최종 점검

모든 체크리스트 항목이 ✅ 이면 **52개 파일 전체 실행 가능**!

```bash
# 전체 파이프라인 실행
python rebuild_all_db.py
```
