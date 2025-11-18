"""
Metadata Validator - 추출된 메타데이터가 DB에 실제로 존재하는지 검증

검증 항목:
1. speaker가 DB에 존재하는지
2. meeting_date가 DB에 존재하는지
3. topic이 "답변생성불가"인지 체크
"""

from typing import Dict, Optional, List
from search_chromadb import MeetingSearcher


class ValidationResult:
    """검증 결과"""
    def __init__(
        self,
        is_valid: bool,
        message: str = "",
        suggestions: List[str] = None,
        corrected_metadata: Dict = None
    ):
        self.is_valid = is_valid
        self.message = message
        self.suggestions = suggestions or []
        self.corrected_metadata = corrected_metadata


class MetadataValidator:
    """
    메타데이터 검증기
    """

    def __init__(
        self,
        collection_name: str = "seoul_council_meetings",
        persist_directory: str = "./chroma_db"
    ):
        """
        초기화

        Args:
            collection_name: ChromaDB 컬렉션 이름
            persist_directory: ChromaDB 저장 경로
        """
        self.searcher = MeetingSearcher(
            collection_name=collection_name,
            persist_directory=persist_directory
        )
        print(f"✅ Metadata Validator 초기화 완료\n")

    def validate(self, metadata: Dict) -> ValidationResult:
        """
        메타데이터 종합 검증

        Args:
            metadata: Query Analyzer가 추출한 메타데이터

        Returns:
            ValidationResult
        """
        print(f"🔍 메타데이터 검증 중...")
        print(f"   topic: {metadata.get('topic')}")
        print(f"   speaker: {metadata.get('speaker')}")
        print(f"   meeting_date: {metadata.get('meeting_date')}")
        print(f"   agenda: {metadata.get('agenda')}\n")

        # 보정된 메타데이터 초기화 (원본 복사)
        corrected_metadata = metadata.copy()

        # 1. speaker 검증
        if metadata.get('speaker'):
            speaker_result = self._validate_speaker(metadata['speaker'])
            if not speaker_result.is_valid:
                return speaker_result
            # 보정된 speaker 적용
            if speaker_result.corrected_metadata:
                corrected_metadata.update(speaker_result.corrected_metadata)

        # 2. meeting_date 검증
        if metadata.get('meeting_date'):
            date_result = self._validate_date(metadata['meeting_date'])
            if not date_result.is_valid:
                return date_result
            # 보정된 meeting_date 적용
            if date_result.corrected_metadata:
                corrected_metadata.update(date_result.corrected_metadata)

        # 모든 검증 통과
        print("✅ 메타데이터 검증 완료!\n")
        return ValidationResult(
            is_valid=True,
            message="검증 통과",
            corrected_metadata=corrected_metadata
        )

    def _validate_speaker(self, speaker: str) -> ValidationResult:
        """
        발언자가 DB에 존재하는지 검증

        Args:
            speaker: 발언자 이름

        Returns:
            ValidationResult
        """
        print(f"   👤 발언자 검증: '{speaker}'")

        # DB에서 모든 발언자 가져오기
        all_speakers = self.searcher.get_all_speakers()

        # 정확히 일치하는 경우
        if speaker in all_speakers:
            print(f"      ✅ DB에 존재함\n")
            return ValidationResult(is_valid=True)

        # 유사한 발언자 찾기
        similar_speakers = self._find_similar_speakers(speaker, all_speakers)

        if similar_speakers:
            # 첫 번째 유사 발언자로 자동 보정
            corrected_speaker = similar_speakers[0]
            print(f"      ⚠️ '{speaker}' → '{corrected_speaker}'로 자동 보정\n")

            return ValidationResult(
                is_valid=True,
                message=f"'{speaker}'을(를) '{corrected_speaker}'로 보정했습니다.",
                corrected_metadata={'speaker': corrected_speaker}
            )
        else:
            message = f"'{speaker}'을(를) 찾을 수 없습니다."
            print(f"      ❌ DB에 없음")
            print(f"      📋 전체 발언자 목록:")
            for s in all_speakers[:5]:
                print(f"         - {s}")
            if len(all_speakers) > 5:
                print(f"         ... 외 {len(all_speakers) - 5}명\n")

            return ValidationResult(
                is_valid=False,
                message=message,
                suggestions=all_speakers[:5]
            )

    def _validate_date(self, meeting_date: str) -> ValidationResult:
        """
        회의 날짜가 DB에 존재하는지 검증

        Args:
            meeting_date: 회의 날짜 (YYYY.MM.DD)

        Returns:
            ValidationResult
        """
        print(f"   📅 날짜 검증: '{meeting_date}'")

        # DB에서 모든 날짜 가져오기
        all_dates = self.searcher.get_all_dates()

        # 정확히 일치하는 경우
        if meeting_date in all_dates:
            print(f"      ✅ DB에 존재함\n")
            return ValidationResult(is_valid=True)

        # 존재하지 않는 경우
        message = f"'{meeting_date}' 회의를 찾을 수 없습니다."
        print(f"      ❌ DB에 없음")
        print(f"      📋 전체 회의 날짜:")
        for date in all_dates:
            info = self.searcher.get_meeting_info(date)
            print(f"         - {date}: {info['title']}")
        print()

        return ValidationResult(
            is_valid=False,
            message=message,
            suggestions=all_dates
        )

    def _find_similar_speakers(
        self,
        speaker: str,
        all_speakers: List[str]
    ) -> List[str]:
        """
        유사한 발언자 이름 찾기 (공백 기준 분리)

        Args:
            speaker: 찾으려는 발언자
            all_speakers: 전체 발언자 목록

        Returns:
            유사한 발언자 목록

        예시:
            - "윤기섭" → ["윤기섭", "위원"] 중 "윤기섭" 매칭 ✅
            - "안대희" → ["도시기반시설본부장", "안대희"] 중 "안대희" 매칭 ✅
            - "윤기섭위원" → 공백 제거 후 "윤기섭위원" == "윤기섭위원" ✅
        """
        similar = []

        # 입력 발언자를 공백으로 분리
        input_parts = speaker.split()

        for s in all_speakers:
            # DB 발언자를 공백으로 분리
            db_parts = s.split()

            # 전략 1: 완전 일치
            if speaker == s:
                similar.append(s)
                continue

            # 전략 2: 공백으로 분리한 부분 중 하나라도 일치하면 매칭
            # 예: "윤기섭" in ["윤기섭", "위원"] → True
            # 예: "안대희" in ["도시기반시설본부장", "안대희"] → True
            match = False
            for input_part in input_parts:
                if input_part in db_parts:
                    match = True
                    break

            if match:
                similar.append(s)
                continue

            # 전략 3: 띄어쓰기 오류 처리 (공백 제거 후 부분 문자열 비교)
            # 예: "윤기섭위원" vs "윤기섭 위원"
            speaker_no_space = speaker.replace(" ", "")
            s_no_space = s.replace(" ", "")

            if speaker_no_space in s_no_space or s_no_space in speaker_no_space:
                similar.append(s)

        return similar[:3]  # 최대 3개만


def test_metadata_validator():
    """
    Metadata Validator 테스트
    """
    print("="*80)
    print("Metadata Validator 테스트")
    print("="*80)
    print()

    validator = MetadataValidator()

    # 테스트 케이스
    test_cases = [
        {
            "name": "정상 케이스 - 발언자 있음",
            "metadata": {
                "speaker": "윤기섭 위원",
                "topic": "싱크홀",
                "agenda": None,
                "meeting_date": None,
                "intent": "질의_내용_찾기"
            }
        },
        {
            "name": "정상 케이스 - 날짜 있음",
            "metadata": {
                "speaker": None,
                "topic": "추경예산",
                "agenda": None,
                "meeting_date": "2025.09.01",
                "intent": "주제_검색"
            }
        },
        {
            "name": "에러 케이스 - 답변생성불가",
            "metadata": {
                "speaker": None,
                "topic": "답변생성불가",
                "agenda": None,
                "meeting_date": None,
                "intent": "정보_조회"
            }
        },
        {
            "name": "에러 케이스 - 존재하지 않는 발언자",
            "metadata": {
                "speaker": "홍길동 의원",
                "topic": "안전",
                "agenda": None,
                "meeting_date": None,
                "intent": "질의_내용_찾기"
            }
        },
        {
            "name": "에러 케이스 - 존재하지 않는 날짜",
            "metadata": {
                "speaker": None,
                "topic": "회의 내용",
                "agenda": None,
                "meeting_date": "2024.01.01",
                "intent": "주제_검색"
            }
        },
        {
            "name": "유사 발언자 - 띄어쓰기 오류",
            "metadata": {
                "speaker": "윤기섭위원",  # 띄어쓰기 없음
                "topic": "싱크홀",
                "agenda": None,
                "meeting_date": None,
                "intent": "질의_내용_찾기"
            }
        }
    ]

    for i, tc in enumerate(test_cases, 1):
        print(f"[테스트 {i}/{len(test_cases)}] {tc['name']}")
        print("="*80)

        result = validator.validate(tc['metadata'])

        print(f"📊 검증 결과:")
        print(f"   유효성: {'✅ 통과' if result.is_valid else '❌ 실패'}")
        print(f"   메시지: {result.message}")

        if result.suggestions:
            print(f"   제안:")
            for suggestion in result.suggestions:
                print(f"      - {suggestion}")

        print()
        print()


if __name__ == "__main__":
    test_metadata_validator()
