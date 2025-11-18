"""
Query Analyzer - 사용자 질문에서 메타데이터 추출

사용자의 자연어 질문을 분석하여:
- speaker (발언자)
- topic (주제/키워드)
- agenda (안건)
- meeting_date (회의 날짜)
- intent (질문 의도)

를 추출합니다.
"""

from typing import TypedDict, Optional
import json
import os
from openai import OpenAI


class QueryMetadata(TypedDict):
    """추출된 메타데이터"""
    speaker: Optional[str]
    topic: str
    agenda: Optional[str]
    meeting_date: Optional[str]
    intent: str


class QueryAnalyzer:
    """
    사용자 질문 분석기
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        초기화

        Args:
            api_key: OpenAI API 키 (None이면 환경변수에서 가져옴)
            model: 사용할 모델
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.client = OpenAI(api_key=self.api_key)

    def analyze(self, user_query: str) -> QueryMetadata:
        """
        사용자 질문 분석

        Args:
            user_query: 사용자 질문

        Returns:
            추출된 메타데이터
        """
        print(f"🔍 질문 분석 중: \"{user_query}\"")

        # LLM에게 메타데이터 추출 요청
        system_prompt = """당신은 서울시의회 회의록 검색 시스템의 Query Analyzer입니다.

사용자의 질문을 분석하여 다음 정보를 JSON 형식으로 추출하세요:

1. speaker: 발언자 이름 (예: "윤기섭 위원", "도시기반시설본부장 안대희")
   - 직책 + 이름 형태로 추출
   - 없으면 null

2. topic: 주제/키워드 (검색어로 사용될 핵심 주제)
   - 질문의 핵심 주제를 추출
   - **중요**: speaker, meeting_date, agenda 중 하나라도 있으면 topic이 없어도 검색 가능 → null로 설정
   - **단일 키워드도 검색 가능**: "강동구", "안전", "예산", "싱크홀", "AI" 등 모든 명사는 그대로 topic으로 설정
   - **애매한 경우**: 구체적인 명사가 없고 지시어/대명사만 있으면("그거", "뭐", "응" 등) → 사용자의 원본 질문을 그대로 넣어서 검색하므로 null로 설정
   - 빈 문자열 절대 금지

3. agenda: 안건 키워드 (예: "추가경정예산안", "현안업무")
   - 특정 안건 언급 시에만 추출
   - 없으면 null

4. meeting_date: 회의 날짜 (YYYY.MM.DD 형식)
   - "2025년 9월 1일" → "2025.09.01"
   - 없으면 null

5. intent: 질문 의도
   - "질의_내용_찾기": 특정 인물의 발언 찾기
   - "주제_검색": 특정 주제 관련 내용 찾기
   - "정보_조회": 사업 진행 상황 등 정보 조회
   - "비교_분석": 여러 의견 비교
   - "시간_추적": 특정 사업의 시간별 변화

예시:
질문: "윤기섭 위원이 싱크홀에 대해 뭐라고 했어?"
답변:
{
  "speaker": "윤기섭 위원",
  "topic": "싱크홀",
  "agenda": null,
  "meeting_date": null,
  "intent": "질의_내용_찾기"
}

질문: "그거 알려줘"
답변:
{
  "speaker": null,
  "topic": null,
  "agenda": null,
  "meeting_date": null,
  "intent": "정보_조회"
}

질문: "윤기섭 위원이 뭐라고 했어?"
답변:
{
  "speaker": "윤기섭 위원",
  "topic": null,
  "agenda": null,
  "meeting_date": null,
  "intent": "질의_내용_찾기"
}

질문: "2025년 9월 1일 회의 내용"
답변:
{
  "speaker": null,
  "topic": null,
  "agenda": null,
  "meeting_date": "2025.09.01",
  "intent": "정보_조회"
}

질문: "AI"
답변:
{
  "speaker": null,
  "topic": "AI",
  "agenda": null,
  "meeting_date": null,
  "intent": "주제_검색"
}

질문: "동북선 공정률 알려줘"
답변:
{
  "speaker": null,
  "topic": "동북선 공정률",
  "agenda": null,
  "meeting_date": null,
  "intent": "정보_조회"
}

질문: "2025년 9월 1일 회의에서 안대희 본부장이 안전에 대해 한 말"
답변:
{
  "speaker": "도시기반시설본부장 안대희",
  "topic": "안전",
  "agenda": null,
  "meeting_date": "2025.09.01",
  "intent": "질의_내용_찾기"
}

질문: "추경예산안 내용 뭐야?"
답변:
{
  "speaker": null,
  "topic": "예산",
  "agenda": "추가경정예산안",
  "meeting_date": null,
  "intent": "주제_검색"
}

반드시 순수 JSON만 출력하세요. 설명은 하지 마세요."""

        user_prompt = f"질문: {user_query}"

        # LLM 호출
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        # 응답 파싱
        response_text = response.choices[0].message.content
        metadata = json.loads(response_text)

        print(f"✅ 분석 완료:")
        print(f"   발언자: {metadata.get('speaker', 'None')}")
        print(f"   주제: {metadata.get('topic', 'None')}")
        print(f"   안건: {metadata.get('agenda', 'None')}")
        print(f"   날짜: {metadata.get('meeting_date', 'None')}")
        print(f"   의도: {metadata.get('intent', 'None')}\n")

        return QueryMetadata(
            speaker=metadata.get('speaker'),
            topic=metadata.get('topic', ''),
            agenda=metadata.get('agenda'),
            meeting_date=metadata.get('meeting_date'),
            intent=metadata.get('intent', '주제_검색')
        )


def test_query_analyzer():
    """
    Query Analyzer 테스트
    """
    print("="*80)
    print("Query Analyzer 테스트")
    print("="*80)
    print()

    # API 키 확인
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("   .env 파일에 OPENAI_API_KEY를 추가하거나")
        print("   직접 api_key 파라미터로 전달하세요.")
        return

    analyzer = QueryAnalyzer()

    # 테스트 케이스
    test_cases = [
        "윤기섭 위원이 싱크홀에 대해 뭐라고 했어?",
        "동북선 공정률 알려줘",
        "안대희 본부장의 안전 관리 계획은?",
        "2025년 9월 1일 회의 내용",
        "위례선 트램은 언제 완공되나요?",
        "추경예산 규모는?",
        "문성호 위원이 다국어 통역에 대해 질문한 내용",
        "싱크홀 관련 모든 발언 찾아줘",
        "김성준 위원과 윤기섭 위원의 안전 관련 의견 비교",
        "9호선 4단계 진행 상황"
    ]

    for i, query in enumerate(test_cases, 1):
        print(f"[테스트 {i}/{len(test_cases)}]")
        print("-"*80)

        metadata = analyzer.analyze(query)

        print()

    print("="*80)
    print("✅ 모든 테스트 완료!")
    print("="*80)


if __name__ == "__main__":
    test_query_analyzer()
