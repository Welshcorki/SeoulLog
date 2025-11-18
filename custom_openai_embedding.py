"""
Custom OpenAI Embedding Function for ChromaDB
OpenAI API v1.0+ 호환
"""

from typing import List
import os
from openai import OpenAI


class CustomOpenAIEmbeddingFunction:
    """
    OpenAI API v1.0+ 호환 Embedding Function
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = "text-embedding-3-small"
    ):
        """
        초기화

        Args:
            api_key: OpenAI API 키 (None이면 환경변수에서 가져옴)
            model_name: 사용할 embedding 모델
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model_name
        self.client = OpenAI(api_key=self.api_key)

    def __call__(self, input: List[str]) -> List[List[float]]:
        """
        텍스트 리스트를 embedding으로 변환

        Args:
            input: 텍스트 리스트

        Returns:
            Embeddings (리스트의 리스트)
        """
        # OpenAI API v1.0+ 방식
        response = self.client.embeddings.create(
            input=input,
            model=self.model_name
        )

        # Embedding 추출 및 정렬
        embeddings = [item.embedding for item in response.data]

        return embeddings
