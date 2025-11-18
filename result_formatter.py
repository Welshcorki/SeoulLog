"""
Result Formatter - 검색 결과를 사용자 친화적 형태로 포맷팅

Search Executor의 검색 결과를 받아서:
- Markdown 형식으로 변환
- 중요 정보 강조
- 읽기 쉬운 형태로 출력
"""

from typing import List, Dict, Optional


class ResultFormatter:
    """
    검색 결과 포맷터
    """

    def __init__(self):
        """
        초기화
        """
        print(f"✅ Result Formatter 초기화 완료\n")

    def format(
        self,
        results: List[Dict],
        user_query: str,
        metadata: Dict,
        show_url: bool = True,
        show_similarity: bool = True,
        max_text_length: int = 300
    ) -> str:
        """
        검색 결과를 Markdown 형식으로 포맷팅

        Args:
            results: Search Executor의 검색 결과
            user_query: 사용자 원본 질문
            metadata: Query Analyzer가 추출한 메타데이터
            show_url: URL 표시 여부
            show_similarity: 유사도 점수 표시 여부
            max_text_length: 발언 내용 최대 길이

        Returns:
            포맷팅된 Markdown 문자열
        """
        print(f"📝 결과 포맷팅 중... ({len(results)}건)")

        if not results:
            return self._format_no_results(user_query, metadata)

        # Markdown 생성
        markdown_lines = []

        # 헤더
        markdown_lines.append(f"# 🔍 검색 결과")
        markdown_lines.append(f"")
        markdown_lines.append(f"**질문**: {user_query}")
        markdown_lines.append(f"")

        # 검색 조건
        search_conditions = []
        if metadata.get('speaker'):
            search_conditions.append(f"👤 발언자: `{metadata['speaker']}`")
        if metadata.get('topic'):
            search_conditions.append(f"🔑 키워드: `{metadata['topic']}`")
        if metadata.get('agenda'):
            search_conditions.append(f"📋 안건: `{metadata['agenda']}`")
        if metadata.get('meeting_date'):
            search_conditions.append(f"📅 날짜: `{metadata['meeting_date']}`")

        if search_conditions:
            markdown_lines.append(f"**검색 조건**:")
            for condition in search_conditions:
                markdown_lines.append(f"- {condition}")
            markdown_lines.append(f"")

        markdown_lines.append(f"**결과 개수**: {len(results)}건")
        markdown_lines.append(f"")
        markdown_lines.append(f"---")
        markdown_lines.append(f"")

        # 각 검색 결과
        for result in results:
            markdown_lines.extend(self._format_single_result(
                result=result,
                show_url=show_url,
                show_similarity=show_similarity,
                max_text_length=max_text_length
            ))

        formatted_text = "\n".join(markdown_lines)
        print(f"✅ 포맷팅 완료!\n")
        return formatted_text

    def _format_single_result(
        self,
        result: Dict,
        show_url: bool,
        show_similarity: bool,
        max_text_length: int
    ) -> List[str]:
        """
        개별 검색 결과 포맷팅

        Args:
            result: 단일 검색 결과
            show_url: URL 표시 여부
            show_similarity: 유사도 표시 여부
            max_text_length: 발언 내용 최대 길이

        Returns:
            포맷팅된 라인 리스트
        """
        lines = []

        # 결과 번호 + 유사도
        header = f"## [{result['rank']}] "
        if show_similarity:
            similarity_percent = result['similarity'] * 100
            header += f"유사도: {similarity_percent:.1f}%"

        lines.append(header)
        lines.append(f"")

        # 메타 정보
        lines.append(f"- 👤 **발언자**: {result['speaker']}")
        lines.append(f"- 📅 **회의 날짜**: {result['meeting_date']}")
        lines.append(f"- 🏛️ **회의명**: {result['meeting_title']}")
        lines.append(f"- 📋 **안건**: {result['agenda']}")
        lines.append(f"")

        # 발언 내용
        text = result['text']
        if len(text) > max_text_length:
            text = text[:max_text_length] + "..."

        lines.append(f"**💬 발언 내용**:")
        lines.append(f"> {text}")
        lines.append(f"")

        # URL
        if show_url and result.get('meeting_url'):
            lines.append(f"🔗 [회의록 원문 보기]({result['meeting_url']})")
            lines.append(f"")

        lines.append(f"---")
        lines.append(f"")

        return lines

    def _format_no_results(self, user_query: str, metadata: Dict) -> str:
        """
        검색 결과 없음 메시지 포맷팅

        Args:
            user_query: 사용자 질문
            metadata: 추출된 메타데이터

        Returns:
            포맷팅된 Markdown 문자열
        """
        lines = []
        lines.append(f"# ❌ 검색 결과 없음")
        lines.append(f"")
        lines.append(f"**질문**: {user_query}")
        lines.append(f"")
        lines.append(f"다음 조건으로 검색했지만 결과를 찾지 못했습니다:")
        lines.append(f"")

        if metadata.get('speaker'):
            lines.append(f"- 👤 발언자: `{metadata['speaker']}`")
        if metadata.get('topic'):
            lines.append(f"- 🔑 키워드: `{metadata['topic']}`")
        if metadata.get('agenda'):
            lines.append(f"- 📋 안건: `{metadata['agenda']}`")
        if metadata.get('meeting_date'):
            lines.append(f"- 📅 날짜: `{metadata['meeting_date']}`")

        lines.append(f"")
        lines.append(f"**제안**:")
        lines.append(f"- 검색어를 다르게 표현해보세요")
        lines.append(f"- 발언자 이름을 정확히 입력했는지 확인하세요")
        lines.append(f"- 날짜 형식을 확인하세요 (예: 2025.09.01)")

        return "\n".join(lines)

    def format_simple(self, results: List[Dict], max_results: int = 3) -> str:
        """
        간단한 포맷 (상위 N개만 표시)

        Args:
            results: 검색 결과
            max_results: 표시할 최대 결과 수

        Returns:
            간단한 포맷의 문자열
        """
        if not results:
            return "❌ 검색 결과가 없습니다."

        lines = [f"📊 검색 결과: {len(results)}건 (상위 {max_results}건 표시)\n"]

        for result in results[:max_results]:
            lines.append(f"[{result['rank']}] {result['speaker']}")
            lines.append(f"    📅 {result['meeting_date']}")
            lines.append(f"    💬 {result['text'][:100]}...")
            lines.append(f"    📊 유사도: {result['similarity']*100:.1f}%")
            lines.append("")

        return "\n".join(lines)


def test_result_formatter():
    """
    Result Formatter 테스트
    """
    print("="*80)
    print("Result Formatter 테스트")
    print("="*80)
    print()

    formatter = ResultFormatter()

    # 테스트 데이터
    user_query = "윤기섭 위원이 싱크홀에 대해 뭐라고 했어?"
    metadata = {
        "speaker": "윤기섭 위원",
        "topic": "싱크홀",
        "agenda": None,
        "meeting_date": None,
        "intent": "질의_내용_찾기"
    }

    mock_results = [
        {
            'rank': 1,
            'speaker': '윤기섭 위원',
            'meeting_date': '2025.09.01',
            'meeting_title': '제332회 서울특별시의회(정례회) 도시안전건설위원회회의록',
            'agenda': '서울특별시 도시기반시설본부 행정사무감사',
            'text': '싱크홀 관련해서 질문드리겠습니다. GPR 탐사를 통해 지하 공동을 사전에 발견하고 있다고 하셨는데, 실제로 얼마나 효과적인지 궁금합니다. 그리고 싱크홀이 발생했을 때의 긴급 대응 체계는 어떻게 되어 있나요?',
            'meeting_url': 'https://example.com/meeting/332',
            'similarity': 0.8234,
            'chunk_index': 15
        },
        {
            'rank': 2,
            'speaker': '도시기반시설본부장 안대희',
            'meeting_date': '2025.09.01',
            'meeting_title': '제332회 서울특별시의회(정례회) 도시안전건설위원회회의록',
            'agenda': '서울특별시 도시기반시설본부 행정사무감사',
            'text': '싱크홀 예방을 위해 서울시는 GPR 탐사를 연간 1,500km 이상 실시하고 있습니다. 지하 공동 발견 시 즉시 보수 조치를 취하고 있으며, 긴급 출동 시스템도 24시간 운영하고 있습니다.',
            'meeting_url': 'https://example.com/meeting/332',
            'similarity': 0.7891,
            'chunk_index': 16
        },
        {
            'rank': 3,
            'speaker': '윤기섭 위원',
            'meeting_date': '2025.09.01',
            'meeting_title': '제332회 서울특별시의회(정례회) 도시안전건설위원회회의록',
            'agenda': '서울특별시 도시기반시설본부 행정사무감사',
            'text': '싱크홀 예방도 중요하지만, 발생 후 신속한 복구가 더 중요합니다. 특히 주요 도로에서 발생할 경우 교통 혼잡이 심각하니, 복구 소요 시간을 단축할 방안도 마련해주시기 바랍니다.',
            'meeting_url': 'https://example.com/meeting/332',
            'similarity': 0.7456,
            'chunk_index': 18
        }
    ]

    print("[테스트 1] 전체 포맷")
    print("="*80)
    markdown = formatter.format(
        results=mock_results,
        user_query=user_query,
        metadata=metadata
    )
    print(markdown)
    print()

    print()
    print("[테스트 2] 간단한 포맷")
    print("="*80)
    simple = formatter.format_simple(mock_results, max_results=2)
    print(simple)
    print()

    print()
    print("[테스트 3] 결과 없음")
    print("="*80)
    no_results = formatter.format(
        results=[],
        user_query="존재하지 않는 내용",
        metadata={"speaker": None, "topic": "존재하지않는주제", "agenda": None, "meeting_date": None, "intent": "주제_검색"}
    )
    print(no_results)
    print()

    print("="*80)
    print("✅ 모든 테스트 완료!")
    print("="*80)


if __name__ == "__main__":
    test_result_formatter()
