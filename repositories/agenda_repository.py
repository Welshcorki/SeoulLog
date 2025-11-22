"""
안건 Repository - SQLite DB 접근

책임:
- SQLite DB 연결 관리
- 안건 테이블 CRUD
- 청크 테이블 조회
"""

import sqlite3
from typing import List, Dict, Optional
from contextlib import contextmanager


class AgendaRepository:
    """
    안건 데이터 접근 계층

    순수 CRUD 작업만 수행하며, 비즈니스 로직은 포함하지 않습니다.
    """

    def __init__(self, db_path: str = "data/sqlite_DB/agendas.db"):
        """
        초기화

        Args:
            db_path: SQLite DB 경로
        """
        self.db_path = db_path

    @contextmanager
    def get_connection(self):
        """
        DB 연결 컨텍스트 매니저

        Yields:
            sqlite3.Connection: DB 연결 객체
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Dict-like access
        try:
            yield conn
        finally:
            conn.close()

    def find_by_id(self, agenda_id: str) -> Optional[Dict]:
        """
        안건 ID로 조회

        Args:
            agenda_id: 안건 ID

        Returns:
            안건 딕셔너리 또는 None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT agenda_id, agenda_title, meeting_title, meeting_date,
                       meeting_url, main_speaker, all_speakers, speaker_count,
                       chunk_count, chunk_ids, combined_text, ai_summary,
                       key_issues, attachments, agenda_type, status, created_at
                FROM agendas
                WHERE agenda_id = ?
            ''', (agenda_id,))

            row = cursor.fetchone()
            return dict(row) if row else None

    def find_by_agenda_ids(
        self,
        agenda_ids: List[str],
        exclude_agenda_types: List[str] = None
    ) -> List[Dict]:
        """
        여러 안건 ID로 조회 + agenda_type 필터링

        Args:
            agenda_ids: 안건 ID 리스트
            exclude_agenda_types: 제외할 agenda_type 리스트 (예: ['procedural', 'discussion', 'other'])

        Returns:
            안건 리스트
        """
        if not agenda_ids:
            return []

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # WHERE 조건 구성
            placeholders = ','.join('?' * len(agenda_ids))
            params = list(agenda_ids)

            where_clause = f'agenda_id IN ({placeholders})'

            # agenda_type 필터링
            if exclude_agenda_types:
                type_placeholders = ','.join('?' * len(exclude_agenda_types))
                where_clause += f' AND agenda_type NOT IN ({type_placeholders})'
                params.extend(exclude_agenda_types)

            query = f'''
                SELECT agenda_id, agenda_title, meeting_title, meeting_date,
                       meeting_url, main_speaker, all_speakers, speaker_count,
                       chunk_count, ai_summary, key_issues, status, agenda_type,
                       combined_text
                FROM agendas
                WHERE {where_clause}
            '''

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def find_top_agendas(
        self,
        limit: int = 5,
        exclude_titles_like: List[str] = None,
        exclude_agenda_types: List[str] = None
    ) -> List[Dict]:
        """
        Top 안건 조회 (최신 + 활발한 논의)

        Args:
            limit: 조회 개수
            exclude_titles_like: 제외할 제목 패턴 리스트 (예: ['%개의%', '%산회%'])
            exclude_agenda_types: 제외할 안건 타입 리스트 (예: ['procedural', 'discussion', 'other'])

        Returns:
            Top 안건 리스트
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # WHERE 조건 구성
            where_conditions = []
            params = []

            if exclude_titles_like:
                for pattern in exclude_titles_like:
                    where_conditions.append(f"agenda_title NOT LIKE '{pattern}'")

            where_conditions.append("chunk_count > 10")

            # agenda_type 필터링
            if exclude_agenda_types:
                type_placeholders = ','.join('?' * len(exclude_agenda_types))
                where_conditions.append(f'agenda_type NOT IN ({type_placeholders})')
                params.extend(exclude_agenda_types)

            where_clause = ' AND '.join(where_conditions)

            query = f'''
                SELECT agenda_id, agenda_title, meeting_title, meeting_date,
                       ai_summary, chunk_count, main_speaker, status
                FROM agendas
                WHERE {where_clause}
                ORDER BY meeting_date DESC, chunk_count DESC
                LIMIT ?
            '''

            params.append(limit)
            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def find_chunks_by_agenda_id(self, agenda_id: str) -> List[Dict]:
        """
        안건 ID로 청크 조회

        Args:
            agenda_id: 안건 ID

        Returns:
            청크 리스트 (chunk_index 순)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT chunk_id, speaker, full_text, chunk_index
                FROM agenda_chunks
                WHERE agenda_id = ?
                ORDER BY chunk_index
            ''', (agenda_id,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def find_all(self, limit: int = None) -> List[Dict]:
        """
        전체 안건 조회

        Args:
            limit: 조회 개수 제한 (None이면 전체)

        Returns:
            안건 리스트
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = '''
                SELECT agenda_id, agenda_title, meeting_title, meeting_date,
                       main_speaker, speaker_count, chunk_count, status, agenda_type
                FROM agendas
                ORDER BY meeting_date DESC
            '''

            if limit:
                query += f' LIMIT {limit}'

            cursor.execute(query)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]
