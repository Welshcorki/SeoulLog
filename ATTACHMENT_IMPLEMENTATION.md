# 첨부 문서 구현 완료

## 문제 분석

DB를 재생성해도 `attachments` 컬럼이 NULL로 남는 이유:

1. **`extract_metadata_hybrid.py`**: JSON 출력에 `attachments` 필드가 없음
2. **`create_agenda_database.py`**: INSERT 문에 `attachments` 컬럼이 빠져있음

## 구현 내용

### 1. `extract_metadata_hybrid.py` 수정

#### 추가된 기능:
- `extract_reference_materials()`: (참고) 섹션에서 첨부 문서 링크 추출
- `crawl_url()`: 크롤링 시 첨부 문서 추출 추가
- `extract_agenda_mapping()`: Gemini 프롬프트에 첨부 문서 매칭 로직 추가
- `extract_metadata_from_url()`: URL 직접 크롤링 + 파싱 (첨부 문서 포함)

#### JSON 출력 구조 변경:
```json
{
  "meeting_info": {...},
  "agenda_mapping": [
    {
      "agenda_title": "안건명",
      "line_start": 1,
      "line_end": 50,
      "speakers": ["발언자1", "발언자2"],
      "attachments": [
        {"title": "문서명", "url": "다운로드 URL"}
      ]
    }
  ],
  "chunks": [...],
  "usage": {...}
}
```

#### Gemini 프롬프트 개선:
```
**첨부 문서 매칭:**
- 위에 제공된 "첨부 문서 목록"을 분석하여 각 안건에 해당하는 첨부 문서를 attachments 필드에 배열로 추가
- (참고) 섹션은 바로 직전 안건에 속함
- 안건과 관련 없는 첨부 문서는 포함하지 않음
- 첨부 문서가 없는 안건은 attachments를 빈 배열 []로 설정
```

### 2. `create_agenda_database.py` 수정

#### 변경 사항:
1. `group_chunks_by_agenda()`: `agenda_mapping` 파라미터 추가하여 attachments 매칭
2. `insert_agendas_to_db()`:
   - JSON에서 `agenda_mapping` 읽기
   - INSERT 문에 `attachments` 컬럼 추가

```python
# attachments 추출 (agenda_mapping에서 가져오기)
attachments_json = None
if 'attachments' in agenda_data and agenda_data['attachments']:
    attachments_json = json.dumps(agenda_data['attachments'], ensure_ascii=False)

# INSERT 문에 attachments 추가
cursor.execute('''
    INSERT INTO agendas (
        agenda_id, agenda_title, meeting_title, meeting_date, meeting_url,
        main_speaker, all_speakers, speaker_count, chunk_count,
        chunk_ids, combined_text, attachments, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (..., attachments_json, '심사중'))
```

## 사용 방법

### 기존 txt 파일 기반 (첨부 문서 없음)
```python
from data_processing.extract_metadata_hybrid import extract_metadata_hybrid
result = extract_metadata_hybrid(
    txt_path="result/회의록명/meeting_*.txt",
    api_key=GOOGLE_API_KEY
)
# attachments는 모든 안건에서 빈 배열 []
```

### URL 직접 크롤링 (첨부 문서 포함) ⭐ 새로운 방법
```python
from data_processing.extract_metadata_hybrid import extract_metadata_from_url
result = extract_metadata_from_url(
    url="https://ms.smc.seoul.kr/...",
    api_key=GOOGLE_API_KEY
)
# attachments가 자동으로 추출되어 안건별로 매칭됨
```

### DB 재생성 절차

1. **기존 DB 삭제**:
```bash
rm data/sqlite_DB/agendas.db
```

2. **URL 기반 JSON 생성** (첨부 문서 포함):
```python
# data_processing/extract_metadata_hybrid.py의 main() 수정 필요
# 또는 별도 스크립트 작성:

from data_processing.extract_metadata_hybrid import extract_metadata_from_url
from pathlib import Path
import json
import os

api_key = os.getenv("GOOGLE_API_KEY")

# result 폴더의 JSON에서 URL 추출
result_dirs = Path("result").glob("*/")
for result_dir in result_dirs:
    json_files = list(result_dir.glob("meeting_*.json"))
    if json_files:
        with open(json_files[0], 'r', encoding='utf-8') as f:
            old_data = json.load(f)
            url = old_data.get('url')

        # URL 기반 파싱 (첨부 문서 포함)
        new_data = extract_metadata_from_url(url, api_key)

        # data/result_txt에 저장
        output_path = Path("data/result_txt") / f"{result_dir.name}.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
```

3. **DB 생성**:
```bash
python database/create_agenda_database.py
```

4. **첨부 문서 요약 생성**:
```bash
python database/generate_attachment_summaries.py
```

## 데이터 흐름

```
URL 크롤링
    ↓
첨부 문서 추출 (extract_reference_materials)
    ↓
Gemini 안건 매핑 (첨부 문서 매칭 포함)
    ↓
JSON 저장 (agenda_mapping에 attachments 포함)
    ↓
DB 생성 (attachments 컬럼 채워짐)
    ↓
PDF 다운로드 + Gemini 요약 생성
    ↓
DB 업데이트 (attachments에 summary 추가)
    ↓
프론트엔드 표시
```

## 테스트 방법

### 1. URL 기반 파싱 테스트
```bash
# extract_metadata_hybrid.py에 테스트 URL 추가하고 실행
python data_processing/extract_metadata_hybrid.py
```

### 2. DB 확인
```bash
sqlite3 data/sqlite_DB/agendas.db
SELECT agenda_title, attachments FROM agendas WHERE attachments IS NOT NULL LIMIT 3;
```

### 3. 프론트엔드 확인
```
http://localhost:8000/details.html?id=안건ID
```

## 주의사항

1. **기존 txt 파일 기반 파싱**:
   - `extract_metadata_hybrid(txt_path=...)` 사용 시 attachments는 빈 배열
   - txt 파일에는 링크 정보가 없기 때문

2. **URL 기반 파싱 권장**:
   - `extract_metadata_from_url(url=...)` 사용
   - 크롤링 시점에 링크 정보 추출
   - Gemini가 자동으로 안건별 매칭

3. **Gemini 프롬프트 정확도**:
   - (참고) 섹션이 바로 직전 안건에 속한다는 규칙 활용
   - 첨부 문서 제목으로 안건과의 관련성 판단
   - 불확실한 경우 빈 배열 반환

## 다음 단계

현재 구현된 상태:
- ✅ 첨부 문서 추출 로직
- ✅ Gemini 안건 매칭
- ✅ DB 저장
- ✅ PDF 요약 생성
- ✅ 프론트엔드 표시

아직 필요한 작업:
- ⏸️ 기존 result 폴더의 모든 회의록 재처리 (URL 기반)
- ⏸️ data/result_txt 폴더 JSON 업데이트
- ⏸️ DB 재생성
- ⏸️ 첨부 문서 요약 일괄 생성

재처리 스크립트가 필요하면 말씀해주세요!
