"""
Custom OpenAI Embedding Function for ChromaDB
OpenAI API v1.0+ 호환
"""

# 1. 필요한 모듈과 타입들을 임포트합니다.
# cast는 "이 변수는 이 타입이 확실해"라고 알려주는 역할을 합니다.
from typing import List, Optional, cast
import os
from openai import OpenAI
from chromadb import EmbeddingFunction, Documents, Embeddings

# 2. ChromaDB의 EmbeddingFunction을 상속받도록 클래스를 정의합니다.
# 이렇게 해야 ChromaDB가 "아, 이건 내가 쓸 수 있는 함수구나"라고 인식합니다.
class CustomOpenAIEmbeddingFunction(EmbeddingFunction):
    """
    OpenAI API v1.0+ 호환 Embedding Function
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "text-embedding-3-small"
    ):
        """
        초기화
        """
        # 3. API 키 처리: 입력값 -> 환경변수 -> 빈 문자열 순으로 확인
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or ""
        self.model_name = model_name
        self.client = OpenAI(api_key=self.api_key)

    def __call__(self, input: Documents) -> Embeddings:
        """
        텍스트 리스트를 embedding으로 변환
        """
        # 4. OpenAI API를 호출하여 임베딩을 생성합니다.
        response = self.client.embeddings.create(
            input=input,
            model=self.model_name
        )

        # 결과에서 임베딩 데이터만 추출합니다.
        embeddings = [item.embedding for item in response.data]

        # 5. 타입 캐스팅 (핵심 수정 사항)
        # Python 리스트(List[List[float]])를 ChromaDB의 Embeddings 타입으로 
        # 강제 변환(cast)하여 빨간 줄(타입 에러)을 없앱니다.
        return cast(Embeddings, embeddings)