"""
안건 검색 서비스 - 검색 파이프라인 비즈니스 로직

책임:
- 검색 파이프라인 전체 조율
- 쿼리 분석 → ChromaDB 검색 → 그룹핑 → 필터링 → SQLite 조회 → 포맷팅
- agenda_type 필터링 (procedural, discussion, other 제외)
"""

from typing import List, Dict, Optional
from repositories.agenda_repository import AgendaRepository
from repositories.chroma_repository import ChromaRepository
from search.query_analyzer import QueryAnalyzer
from search.simple_query_analyzer import SimpleQueryAnalyzer
from search.metadata_validator import MetadataValidator
from utils.cost_tracker import CostTracker
import json


class AgendaSearchService:
    """
    안건 검색 서비스

    검색 파이프라인:
    1. 쿼리 분석 (QueryAnalyzer)
    2. 메타데이터 검증 (MetadataValidator)
    3. ChromaDB 벡터 검색
    4. 안건별 그룹핑 (최고 유사도만 선택)
    5. agenda_type 필터링 (실제 안건만 표시)
    6. SQLite 조회 (안건 상세 정보)
    7. 결과 포맷팅
    """

    # agenda_type 필터링: 실제 안건만 표시 (절차/토론/기타 제외)
    EXCLUDED_AGENDA_TYPES = ["procedural", "discussion", "other"]

    def __init__(
        self,
        chroma_repo: ChromaRepository,
        agenda_repo: AgendaRepository,
        analyzer: QueryAnalyzer,
        validator: Optional[MetadataValidator] = None,
        cost_tracker: Optional[CostTracker] = None
    ):
        """
        초기화

        Args:
            chroma_repo: ChromaDB Repository
            agenda_repo: 안건 Repository
            analyzer: 쿼리 분석기 (QueryAnalyzer 또는 SimpleQueryAnalyzer)
            validator: 메타데이터 검증기 (optional)
            cost_tracker: 전역 비용 추적기 (optional)
        """
        self.chroma_repo = chroma_repo
        self.agenda_repo = agenda_repo
        self.analyzer = analyzer
        self.validator = validator
        self.global_cost_tracker = cost_tracker

    async def search(
        self,
        query: str,
        n_results: int = 5
    ) -> List[Dict]:
        """
        검색 파이프라인 실행

        Args:
            query: 사용자 쿼리
            n_results: 반환할 안건 개수

        Returns:
            검색 결과 리스트 (Dict 형태, SearchResult와 동일한 구조)
        """
        print(f"🔍 검색 요청: {query}")

        # 검색별 비용 추적
        search_cost_tracker = CostTracker()

        # Step 1: 쿼리 분석
        analyzed_metadata = self._analyze_query(query, search_cost_tracker)

        # Step 2: 메타데이터 검증 및 필터 구성
        where_filter = None
        if self.validator and (analyzed_metadata.get('speaker') or analyzed_metadata.get('meeting_date')):
            is_valid, where_filter, corrected_metadata = self._validate_metadata(analyzed_metadata)

            if not is_valid:
                # 검증 실패 시 빈 결과 반환
                return []

            # 보정된 메타데이터 사용
            if corrected_metadata:
                analyzed_metadata = corrected_metadata

        # where_filter가 아직 None이면 구성
        if where_filter is None:
            where_filter = self._build_where_filter(analyzed_metadata)

        # Step 3: ChromaDB 청크 검색
        chunk_results = self._search_chunks(
            query, n_results, where_filter, search_cost_tracker
        )

        # Step 4: 안건별 그룹핑
        agenda_scores = self._group_by_agenda(chunk_results)

        # Step 5: 유사도 순 정렬 + 상위 N개 선택
        sorted_agendas = sorted(
            agenda_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:n_results]

        agenda_ids = [agenda_id for agenda_id, _ in sorted_agendas]

        # Step 6: SQLite 조회 (agenda_type 필터링 적용)
        agendas = self.agenda_repo.find_by_agenda_ids(
            agenda_ids=agenda_ids,
            exclude_agenda_types=self.EXCLUDED_AGENDA_TYPES
        )

        # Step 7: 결과 포맷팅
        results = self._format_results(agendas, agenda_scores)

        # 비용 출력 및 누적
        self._track_cost(search_cost_tracker)

        print(f"   최종 안건 결과: {len(results)}건\n")

        return results

    def _analyze_query(
        self,
        query: str,
        cost_tracker: CostTracker
    ) -> Dict:
        """
        쿼리 분석

        Args:
            query: 사용자 쿼리
            cost_tracker: 비용 추적기

        Returns:
            분석된 메타데이터
        """
        analyzed_metadata = self.analyzer.analyze(query)

        # QueryAnalyzer 사용 시 비용 추적
        if isinstance(self.analyzer, QueryAnalyzer):
            query_tokens = cost_tracker.count_tokens(query)
            cost_tracker.add_chat_cost(
                input_tokens=500 + query_tokens,  # 시스템 프롬프트 + 쿼리
                output_tokens=100,  # JSON 출력 (평균)
                model="gpt-4o-mini"
            )

        print(f"   분석 결과:")
        print(f"     - speaker: {analyzed_metadata.get('speaker')}")
        print(f"     - topic: {analyzed_metadata.get('topic')}")
        print(f"     - meeting_date: {analyzed_metadata.get('meeting_date')}")

        return analyzed_metadata

    def _validate_metadata(
        self,
        metadata: Dict
    ) -> tuple[bool, Optional[Dict], Optional[Dict]]:
        """
        메타데이터 검증

        Args:
            metadata: 분석된 메타데이터

        Returns:
            (is_valid, where_filter, corrected_metadata)
        """
        if not self.validator:
            return True, None, None

        validation_result = self.validator.validate(metadata)

        if not validation_result.is_valid:
            print(f"   ⚠️ 검증 실패: {validation_result.message}")
            if validation_result.suggestions:
                print(f"   💡 혹시 이것을 찾으셨나요?")
                for suggestion in validation_result.suggestions[:3]:
                    print(f"      - {suggestion}")
            return False, None, None

        # 보정된 메타데이터 확인
        corrected_metadata = validation_result.corrected_metadata
        if corrected_metadata:
            print(f"   보정된 메타데이터:")
            print(f"     - speaker: {corrected_metadata.get('speaker')}")
            print(f"     - meeting_date: {corrected_metadata.get('meeting_date')}")

        # where 필터 구성
        where_filter = self._build_where_filter(
            corrected_metadata if corrected_metadata else metadata
        )

        return True, where_filter, corrected_metadata

    def _build_where_filter(self, metadata: Dict) -> Optional[Dict]:
        """
        ChromaDB where 필터 구성

        Args:
            metadata: 메타데이터

        Returns:
            ChromaDB where 필터 또는 None
        """
        where_conditions = []

        if metadata.get('speaker'):
            where_conditions.append({'speaker': metadata['speaker']})
        if metadata.get('meeting_date'):
            where_conditions.append({'meeting_date': metadata['meeting_date']})

        # 여러 조건이 있으면 $and로 묶기
        if len(where_conditions) == 1:
            return where_conditions[0]
        elif len(where_conditions) > 1:
            return {'$and': where_conditions}

        return None

    def _search_chunks(
        self,
        query: str,
        n_results: int,
        where_filter: Optional[Dict],
        cost_tracker: CostTracker
    ) -> Dict:
        """
        ChromaDB 청크 검색

        Args:
            query: 검색 쿼리
            n_results: 안건 개수
            where_filter: 메타데이터 필터
            cost_tracker: 비용 추적기

        Returns:
            ChromaDB 검색 결과
        """
        # Embedding 비용 추적
        cost_tracker.add_embedding_cost(
            text=query,
            model="text-embedding-3-small"
        )

        # ChromaDB 검색 (안건별 그룹핑 고려하여 더 많이 검색)
        chunk_results = self.chroma_repo.search(
            query=query,
            n_results=min(20, n_results * 4),
            where_filter=where_filter
        )

        print(f"   청크 검색 결과: {len(chunk_results['ids'][0])}개")

        if where_filter:
            print(f"   필터 적용: {where_filter}")

        return chunk_results

    def _group_by_agenda(self, chunk_results: Dict) -> Dict[str, float]:
        """
        안건별 그룹핑 (최고 유사도만 선택)

        Args:
            chunk_results: ChromaDB 검색 결과

        Returns:
            {agenda_id: max_similarity}
        """
        agenda_scores = {}

        for i, chunk_id in enumerate(chunk_results['ids'][0]):
            metadata = chunk_results['metadatas'][0][i]
            distance = chunk_results['distances'][0][i]

            # Cosine similarity 계산
            # ChromaDB cosine distance는 0~2 범위 (0=동일, 2=완전반대)
            # similarity = 1 - (distance / 2)로 0~1 범위로 정규화
            similarity = 1 - (distance / 2)

            agenda_id = metadata.get('agenda_id')
            if not agenda_id:
                continue

            # 디버깅: 첫 3개 결과 출력
            if i < 3:
                print(f"   [DEBUG] chunk #{i}: distance={distance:.4f}, "
                      f"similarity={similarity:.4f}, agenda_id={agenda_id}")

            # 안건별 최고 유사도만 유지
            if agenda_id not in agenda_scores:
                agenda_scores[agenda_id] = similarity
            else:
                agenda_scores[agenda_id] = max(agenda_scores[agenda_id], similarity)

        print(f"   그룹핑된 안건 수: {len(agenda_scores)}개")

        return agenda_scores

    def _format_results(
        self,
        agendas: List[Dict],
        agenda_scores: Dict[str, float]
    ) -> List[Dict]:
        """
        결과 포맷팅

        Args:
            agendas: 안건 리스트
            agenda_scores: 안건별 유사도 점수

        Returns:
            포맷팅된 결과 리스트
        """
        results = []

        for agenda in agendas:
            agenda_id = agenda['agenda_id']
            similarity = agenda_scores.get(agenda_id, 0.0)

            # AI 요약
            ai_summary = agenda.get('ai_summary') or ""
            if not ai_summary:
                combined_text = agenda.get('combined_text', '')
                ai_summary = combined_text[:200].strip()
                if len(combined_text) > 200:
                    ai_summary += "..."

            # 핵심 의제 파싱 (JSON 문자열 → 리스트)
            key_issues = None
            if agenda.get('key_issues'):
                try:
                    key_issues = json.loads(agenda['key_issues'])
                except:
                    pass

            results.append({
                "agenda_id": agenda_id,
                "title": agenda.get('agenda_title', '제목 없음'),
                "ai_summary": ai_summary,
                "key_issues": key_issues,
                "main_speaker": agenda.get('main_speaker', '발언자 없음'),
                "all_speakers": agenda.get('all_speakers', ''),
                "speaker_count": agenda.get('speaker_count', 0),
                "meeting_date": agenda.get('meeting_date', '날짜 없음'),
                "meeting_title": agenda.get('meeting_title', ''),
                "status": agenda.get('status', '심사중'),
                "similarity": round(similarity, 4),
                "chunk_count": agenda.get('chunk_count', 0),
                "meeting_url": agenda.get('meeting_url', '')
            })

        return results

    def _track_cost(self, search_cost_tracker: CostTracker):
        """
        비용 출력 및 전역 추적기에 누적

        Args:
            search_cost_tracker: 검색별 비용 추적기
        """
        cost_summary = search_cost_tracker.get_summary()

        print(f"\n💰 검색 비용:")
        print(f"   Embedding: {cost_summary['breakdown'].get('embedding', {}).get('cost', 0)*1300:.4f}원")
        if 'chat' in cost_summary['breakdown']:
            print(f"   QueryAnalyzer: {cost_summary['breakdown']['chat']['cost']*1300:.4f}원")
        print(f"   총 비용: {cost_summary['total_cost_krw']}")

        # 전역 추적기에 누적
        if self.global_cost_tracker:
            self.global_cost_tracker.total_cost += search_cost_tracker.total_cost
            for key, value in search_cost_tracker.costs_breakdown.items():
                if key not in self.global_cost_tracker.costs_breakdown:
                    self.global_cost_tracker.costs_breakdown[key] = {
                        "tokens": 0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "cost": 0.0,
                        "calls": 0
                    }
                for subkey, subvalue in value.items():
                    if subkey in self.global_cost_tracker.costs_breakdown[key]:
                        self.global_cost_tracker.costs_breakdown[key][subkey] += subvalue
