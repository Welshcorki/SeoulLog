"""
Answer Generator (간단 버전)

Query Analyzer에서 "답변생성불가"가 나오면 바로 안내 메시지 반환
"""

from typing import Dict, List


class SimpleAnswerGenerator:
    """
    간단한 답변 생성기
    """

    def generate_answer(
        self,
        metadata: Dict,
        search_results: List[Dict] = None
    ) -> str:
        """
        답변 생성

        Args:
            metadata: Query Analyzer 결과
            search_results: 검색 결과 (optional)

        Returns:
            최종 답변
        """
        # 1. topic이 "답변생성불가"인 경우
        if metadata.get('topic') == '답변생성불가':
            return self._generate_clarification_message(metadata)

        # 2. 검색 결과가 없는 경우
        if not search_results or len(search_results) == 0:
            return self._generate_no_results_message(metadata)

        # 3. 정상 답변 생성
        return self._generate_normal_answer(metadata, search_results)

    def _generate_clarification_message(self, metadata: Dict) -> str:
        """
        질문이 명확하지 않을 때 안내 메시지
        """
        message = "❓ **질문이 명확하지 않습니다.**\n\n"
        message += "다음과 같이 구체적으로 질문해 주세요:\n\n"
        message += "**예시:**\n"
        message += "- \"동북선 공정률 알려줘\"\n"
        message += "- \"윤기섭 위원이 싱크홀에 대해 뭐라고 했어?\"\n"
        message += "- \"2025년 9월 1일 회의 내용\"\n"
        message += "- \"안전 관리 계획은?\"\n\n"
        message += "**도움말:**\n"
        message += "- 📍 주제를 명확히 해주세요 (예: 동북선, 싱크홀, 안전)\n"
        message += "- 👤 특정 발언자를 찾으시면 이름을 포함해주세요\n"
        message += "- 📅 특정 날짜 회의를 찾으시면 날짜를 알려주세요\n"

        return message

    def _generate_no_results_message(self, metadata: Dict) -> str:
        """
        검색 결과가 없을 때 안내 메시지
        """
        message = "🔍 **검색 결과가 없습니다.**\n\n"
        message += f"**검색 조건:**\n"

        if metadata.get('topic'):
            message += f"- 주제: {metadata['topic']}\n"
        if metadata.get('speaker'):
            message += f"- 발언자: {metadata['speaker']}\n"
        if metadata.get('meeting_date'):
            message += f"- 날짜: {metadata['meeting_date']}\n"
        if metadata.get('agenda'):
            message += f"- 안건: {metadata['agenda']}\n"

        message += "\n**제안:**\n"
        message += "- 다른 키워드로 검색해보세요\n"
        message += "- 발언자 이름을 확인해보세요\n"
        message += "- 날짜를 다시 확인해보세요\n"

        return message

    def _generate_normal_answer(
        self,
        metadata: Dict,
        search_results: List[Dict]
    ) -> str:
        """
        정상 답변 생성 (간단 버전)
        """
        message = f"📊 **검색 결과 ({len(search_results)}건)**\n\n"

        for i, result in enumerate(search_results[:3], 1):  # 상위 3개만
            message += f"### [{i}] {result['speaker']}\n"
            message += f"📅 {result['meeting_date']} | 🏛️ {result['meeting_title']}\n"
            message += f"📋 {result['agenda']}\n\n"
            message += f"> {result['text'][:200]}...\n\n"
            message += f"[🔗 회의록 보기]({result['meeting_url']})\n\n"
            message += "---\n\n"

        return message


def test_simple_answer_generator():
    """
    SimpleAnswerGenerator 테스트
    """
    print("="*80)
    print("Simple Answer Generator 테스트")
    print("="*80)
    print()

    generator = SimpleAnswerGenerator()

    # 테스트 1: 답변생성불가
    print("[테스트 1] 질문이 명확하지 않은 경우")
    print("-"*80)
    metadata1 = {
        "topic": "답변생성불가",
        "speaker": None,
        "intent": "정보_조회"
    }
    answer1 = generator.generate_answer(metadata1)
    print(answer1)
    print()

    # 테스트 2: 검색 결과 없음
    print("[테스트 2] 검색 결과가 없는 경우")
    print("-"*80)
    metadata2 = {
        "topic": "마약",
        "speaker": None,
        "meeting_date": "2025.09.01",
        "intent": "주제_검색"
    }
    answer2 = generator.generate_answer(metadata2, search_results=[])
    print(answer2)
    print()

    # 테스트 3: 정상 답변
    print("[테스트 3] 정상 검색 결과")
    print("-"*80)
    metadata3 = {
        "topic": "싱크홀",
        "speaker": "윤기섭 위원",
        "intent": "질의_내용_찾기"
    }
    search_results3 = [
        {
            "speaker": "윤기섭 위원",
            "meeting_date": "2025.09.01",
            "meeting_title": "제332회 교통위원회 제1차",
            "agenda": "현안업무 보고",
            "text": "싱크홀 사고가 2022년도에 16건, 2023년도에 22건, 2024년도에 16건 이렇게 있었는데 이게 올 2025년 상반기에만 75건으로 갑자기 늘었어요.",
            "meeting_url": "https://ms.smc.seoul.kr/..."
        },
        {
            "speaker": "윤기섭 위원",
            "meeting_date": "2025.09.01",
            "meeting_title": "제332회 교통위원회 제1차",
            "agenda": "현안업무 보고",
            "text": "업무보고 20페이지 보면 대형 굴착공사장 23개 현장에 GPR 탐사하고 CCTV 모니터링을 하고 있다고 했는데요 그렇게 모니터링해서 실적이 있었나요?",
            "meeting_url": "https://ms.smc.seoul.kr/..."
        }
    ]
    answer3 = generator.generate_answer(metadata3, search_results3)
    print(answer3)
    print()


if __name__ == "__main__":
    test_simple_answer_generator()
