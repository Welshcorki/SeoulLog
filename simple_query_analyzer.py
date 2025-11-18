"""
Simple Query Analyzer - OpenAI API 없이 간단한 규칙 기반 분석

OpenAI API가 실패하거나 사용할 수 없을 때 사용하는 fallback
"""

from typing import TypedDict, Optional
import re


class QueryMetadata(TypedDict):
    """추출된 메타데이터"""
    speaker: Optional[str]
    topic: str
    agenda: Optional[str]
    meeting_date: Optional[str]
    intent: str


class SimpleQueryAnalyzer:
    """
    규칙 기반 간단한 쿼리 분석기
    """

    def analyze(self, user_query: str) -> QueryMetadata:
        """
        간단한 규칙으로 쿼리 분석

        Args:
            user_query: 사용자 질문

        Returns:
            추출된 메타데이터
        """
        print(f"🔍 [Simple] 질문 분석 중: \"{user_query}\"")

        metadata: QueryMetadata = {
            'speaker': None,
            'topic': user_query,  # 기본적으로 전체 쿼리를 topic으로
            'agenda': None,
            'meeting_date': None,
            'intent': '주제_검색'
        }

        # 발언자 패턴 찾기
        speaker_patterns = [
            r'([\w가-힣]+\s*위원(?:장)?)',  # "김철수 위원", "위원장"
            r'([\w가-힣]+\s*(?:본부장|과장|실장|국장))',  # "경제실장", "본부장"
        ]

        for pattern in speaker_patterns:
            match = re.search(pattern, user_query)
            if match:
                metadata['speaker'] = match.group(1)
                # speaker를 찾으면 topic에서 제거
                metadata['topic'] = user_query.replace(match.group(1), '').strip()
                metadata['intent'] = '질의_내용_찾기'
                break

        # 날짜 패턴 찾기
        date_patterns = [
            (r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', lambda m: f"{m.group(1)}.{int(m.group(2)):02d}.{int(m.group(3)):02d}"),
            (r'(\d{4})\.(\d{1,2})\.(\d{1,2})', lambda m: f"{m.group(1)}.{int(m.group(2)):02d}.{int(m.group(3)):02d}"),
        ]

        for pattern, formatter in date_patterns:
            match = re.search(pattern, user_query)
            if match:
                metadata['meeting_date'] = formatter(match)
                # 날짜를 topic에서 제거
                metadata['topic'] = re.sub(pattern, '', metadata['topic']).strip()
                break

        # 조례/안건 키워드 찾기
        agenda_keywords = ['조례', '예산', '안건', '보고']
        for keyword in agenda_keywords:
            if keyword in user_query:
                metadata['agenda'] = keyword
                break

        # topic 정제
        # 질문 패턴 제거
        question_patterns = [
            r'[이가]?\s*뭐라고\s*했어\??',
            r'에\s*대해',
            r'에\s*관해',
            r'을\s*알려줘',
            r'를\s*알려줘',
            r'이\s*뭐야\??',
            r'가\s*뭐야\??',
        ]

        topic = metadata['topic']
        for pattern in question_patterns:
            topic = re.sub(pattern, '', topic, flags=re.IGNORECASE)

        # 공백 정리
        topic = ' '.join(topic.split()).strip()

        # 너무 짧거나 의미 없는 경우
        if len(topic) < 2 or topic in ['', '그거', '뭐', '응']:
            topic = user_query  # 원본 그대로 사용

        metadata['topic'] = topic

        print(f"✅ [Simple] 분석 완료:")
        print(f"   발언자: {metadata['speaker']}")
        print(f"   주제: {metadata['topic']}")
        print(f"   안건: {metadata['agenda']}")
        print(f"   날짜: {metadata['meeting_date']}")
        print(f"   의도: {metadata['intent']}\n")

        return metadata


def test_simple_analyzer():
    """
    Simple Query Analyzer 테스트
    """
    print("=" * 80)
    print("Simple Query Analyzer 테스트")
    print("=" * 80)
    print()

    analyzer = SimpleQueryAnalyzer()

    test_queries = [
        "AI 경쟁력",
        "청년취업사관학교",
        "이용균 위원이 뭐라고 했어?",
        "경제실장의 AI 인재 양성 발언",
        "인공지능 산업 조례",
    ]

    for query in test_queries:
        result = analyzer.analyze(query)
        print()


if __name__ == "__main__":
    test_simple_analyzer()
