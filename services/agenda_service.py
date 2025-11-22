"""
안건 서비스 - 안건 CRUD 비즈니스 로직

책임:
- 안건 CRUD 비즈니스 로직
- 안건 상세 조회
- Top 안건 조회
- 포맷된 안건 상세 (첨부 문서 포함)
"""

from typing import List, Dict, Optional
from repositories.agenda_repository import AgendaRepository
import json


class AgendaService:
    """
    안건 서비스

    Repository 계층을 호출하여 안건 관련 비즈니스 로직을 수행합니다.
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
            {
                "agenda_id": str,
                "title": str,
                "meeting_title": str,
                "meeting_date": str,
                "meeting_url": str,
                "main_speaker": str,
                "all_speakers": str,
                "speaker_count": int,
                "chunk_count": int,
                "combined_text": str,
                "ai_summary": str,
                "key_issues": List[str] or None,
                "status": str,
                "chunks": List[Dict]
            }

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
            {
                "agenda_title": str,
                "summary": str,
                "attachments": List[Dict],
                "combined_text": str
            }

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
        Top 안건 조회 (최신 + 활발한 논의)

        Args:
            limit: 조회 개수

        Returns:
            Top 안건 리스트
            [
                {
                    "agenda_id": str,
                    "title": str,
                    "meeting_title": str,
                    "meeting_date": str,
                    "ai_summary": str,
                    "chunk_count": int,
                    "main_speaker": str,
                    "status": str
                },
                ...
            ]
        """
        agendas = self.agenda_repo.find_top_agendas(
            limit=limit,
            exclude_titles_like=['%개의%', '%산회%']
        )

        # Repository의 agenda_title → Pydantic 모델의 title 필드로 매핑
        return [
            {
                "agenda_id": agenda['agenda_id'],
                "title": agenda['agenda_title'],  # 필드명 매핑
                "meeting_title": agenda['meeting_title'],
                "meeting_date": agenda['meeting_date'],
                "ai_summary": agenda.get('ai_summary'),
                "chunk_count": agenda['chunk_count'],
                "main_speaker": agenda['main_speaker'],
                "status": agenda['status']
            }
            for agenda in agendas
        ]

    def _parse_json_field(self, json_str: Optional[str]) -> Optional[any]:
        """
        JSON 문자열 파싱

        Args:
            json_str: JSON 문자열

        Returns:
            파싱된 객체 또는 None
        """
        if not json_str:
            return None

        try:
            return json.loads(json_str)
        except:
            return None
