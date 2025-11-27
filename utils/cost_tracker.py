"""
API 비용 추적 유틸리티

OpenAI API 사용량 및 비용을 추적합니다.
"""

import tiktoken
from typing import Dict, Optional, Any


class CostTracker:
    """
    OpenAI API 비용 추적기
    """

    # OpenAI 가격표 (2024년 기준, USD)
    PRICING = {
        # Embedding 모델
        "text-embedding-3-small": {
            "input": 0.020 / 1_000_000  # $0.020 per 1M tokens
        },
        "text-embedding-3-large": {
            "input": 0.130 / 1_000_000  # $0.130 per 1M tokens
        },

        # Chat 모델
        "gpt-4o-mini": {
            "input": 0.150 / 1_000_000,   # $0.150 per 1M tokens
            "output": 0.600 / 1_000_000   # $0.600 per 1M tokens
        },
        "gpt-4o": {
            "input": 2.50 / 1_000_000,    # $2.50 per 1M tokens
            "output": 10.00 / 1_000_000   # $10.00 per 1M tokens
        },
        "gpt-4-turbo": {
            "input": 10.00 / 1_000_000,
            "output": 30.00 / 1_000_000
        },

        # Gemini 모델 (2025년 기준, USD)
        "gemini-2.5-pro": {
            "input": 1.25 / 1_000_000,    # $1.25 per 1M tokens
            "output": 5.00 / 1_000_000    # $5.00 per 1M tokens
        },
        "gemini-2.5-flash": {
            "input": 0.075 / 1_000_000,   # $0.075 per 1M tokens
            "output": 0.30 / 1_000_000    # $0.30 per 1M tokens
        }
    }

    def __init__(self):
        """초기화"""
        self.total_cost = 0.0
        self.costs_breakdown = {}

    def count_tokens(self, text: str, model: str = "gpt-4o-mini") -> int:
        """
        텍스트의 토큰 수 계산

        Args:
            text: 입력 텍스트
            model: 모델 이름

        Returns:
            토큰 수
        """
        # Embedding 모델은 cl100k_base 인코딩 사용
        if "embedding" in model:
            encoding = tiktoken.get_encoding("cl100k_base")
        else:
            # Chat 모델도 cl100k_base 사용 (gpt-4, gpt-3.5-turbo)
            encoding = tiktoken.get_encoding("cl100k_base")

        tokens = encoding.encode(text)
        return len(tokens)

    def add_embedding_cost(
        self,
        text: str,
        model: str = "text-embedding-3-small"
    ) -> Dict[str, Any]:
        """
        Embedding API 비용 추가

        Args:
            text: 임베딩할 텍스트
            model: Embedding 모델명

        Returns:
            비용 정보 딕셔너리
        """
        tokens = self.count_tokens(text, model)

        if model not in self.PRICING:
            print(f"⚠️ 알 수 없는 모델: {model}")
            return {"tokens": tokens, "cost": 0.0}

        cost = tokens * self.PRICING[model]["input"]

        self.total_cost += cost

        if "embedding" not in self.costs_breakdown:
            self.costs_breakdown["embedding"] = {
                "tokens": 0,
                "cost": 0.0,
                "calls": 0
            }

        self.costs_breakdown["embedding"]["tokens"] += tokens
        self.costs_breakdown["embedding"]["cost"] += cost
        self.costs_breakdown["embedding"]["calls"] += 1

        return {
            "tokens": tokens,
            "cost": cost,
            "cost_usd": f"${cost:.6f}",
            "cost_krw": f"₩{cost * 1300:.4f}"  # 환율 1300원 가정
        }

    def add_chat_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "gpt-4o-mini"
    ) -> Dict[str, Any]:
        """
        Chat API 비용 추가

        Args:
            input_tokens: 입력 토큰 수
            output_tokens: 출력 토큰 수
            model: Chat 모델명

        Returns:
            비용 정보 딕셔너리
        """
        if model not in self.PRICING:
            print(f"⚠️ 알 수 없는 모델: {model}")
            return {"input_tokens": input_tokens, "output_tokens": output_tokens, "cost": 0.0}

        input_cost = input_tokens * self.PRICING[model]["input"]
        output_cost = output_tokens * self.PRICING[model]["output"]
        total_cost = input_cost + output_cost

        self.total_cost += total_cost

        if "chat" not in self.costs_breakdown:
            self.costs_breakdown["chat"] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0,
                "calls": 0
            }

        self.costs_breakdown["chat"]["input_tokens"] += input_tokens
        self.costs_breakdown["chat"]["output_tokens"] += output_tokens
        self.costs_breakdown["chat"]["cost"] += total_cost
        self.costs_breakdown["chat"]["calls"] += 1

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
            "cost_usd": f"${total_cost:.6f}",
            "cost_krw": f"₩{total_cost * 1300:.4f}"
        }

    def add_gemini_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "gemini-2.5-flash"
    ) -> Dict[str, Any]:
        """
        Gemini API 비용 추가

        Args:
            input_tokens: 입력 토큰 수
            output_tokens: 출력 토큰 수
            model: Gemini 모델명

        Returns:
            비용 정보 딕셔너리
        """
        if model not in self.PRICING:
            print(f"⚠️ 알 수 없는 모델: {model}")
            return {"input_tokens": input_tokens, "output_tokens": output_tokens, "cost": 0.0}

        input_cost = input_tokens * self.PRICING[model]["input"]
        output_cost = output_tokens * self.PRICING[model]["output"]
        total_cost = input_cost + output_cost

        self.total_cost += total_cost

        if "gemini" not in self.costs_breakdown:
            self.costs_breakdown["gemini"] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0,
                "calls": 0,
                "models": {}
            }

        self.costs_breakdown["gemini"]["input_tokens"] += input_tokens
        self.costs_breakdown["gemini"]["output_tokens"] += output_tokens
        self.costs_breakdown["gemini"]["cost"] += total_cost
        self.costs_breakdown["gemini"]["calls"] += 1

        # 모델별 세부 통계
        if model not in self.costs_breakdown["gemini"]["models"]:
            self.costs_breakdown["gemini"]["models"][model] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0,
                "calls": 0
            }

        self.costs_breakdown["gemini"]["models"][model]["input_tokens"] += input_tokens
        self.costs_breakdown["gemini"]["models"][model]["output_tokens"] += output_tokens
        self.costs_breakdown["gemini"]["models"][model]["cost"] += total_cost
        self.costs_breakdown["gemini"]["models"][model]["calls"] += 1

        return {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
            "cost_usd": f"${total_cost:.6f}",
            "cost_krw": f"₩{total_cost * 1300:.4f}"
        }

    def get_summary(self) -> Dict:
        """
        전체 비용 요약

        Returns:
            비용 요약 딕셔너리
        """
        summary = {
            "total_cost_usd": f"${self.total_cost:.6f}",
            "total_cost_krw": f"₩{self.total_cost * 1300:.4f}",
            "breakdown": self.costs_breakdown
        }

        return summary

    def print_summary(self):
        """비용 요약 출력"""
        print("\n" + "="*60)
        print("💰 API 비용 요약")
        print("="*60)

        if "embedding" in self.costs_breakdown:
            emb = self.costs_breakdown["embedding"]
            print(f"\n📊 Embedding API:")
            print(f"   호출 횟수: {emb['calls']}회")
            print(f"   총 토큰: {emb['tokens']:,}개")
            print(f"   비용: ${emb['cost']:.6f} (₩{emb['cost']*1300:.4f})")

        if "chat" in self.costs_breakdown:
            chat = self.costs_breakdown["chat"]
            print(f"\n💬 Chat API (QueryAnalyzer):")
            print(f"   호출 횟수: {chat['calls']}회")
            print(f"   입력 토큰: {chat['input_tokens']:,}개")
            print(f"   출력 토큰: {chat['output_tokens']:,}개")
            print(f"   비용: ${chat['cost']:.6f} (₩{chat['cost']*1300:.4f})")

        if "gemini" in self.costs_breakdown:
            gemini = self.costs_breakdown["gemini"]
            print(f"\n🤖 Gemini API:")
            print(f"   호출 횟수: {gemini['calls']}회")
            print(f"   입력 토큰: {gemini['input_tokens']:,}개")
            print(f"   출력 토큰: {gemini['output_tokens']:,}개")
            print(f"   비용: ${gemini['cost']:.6f} (₩{gemini['cost']*1300:.4f})")

            # 모델별 세부 통계
            if "models" in gemini and gemini["models"]:
                print(f"\n   모델별 상세:")
                for model_name, stats in gemini["models"].items():
                    print(f"   • {model_name}:")
                    print(f"     - 호출: {stats['calls']}회")
                    print(f"     - 토큰: {stats['input_tokens']:,} in + {stats['output_tokens']:,} out")
                    print(f"     - 비용: ${stats['cost']:.6f} (₩{stats['cost']*1300:.4f})")

        print(f"\n💵 총 비용: ${self.total_cost:.6f} (₩{self.total_cost*1300:.4f})")
        print("="*60 + "\n")

    def reset(self):
        """비용 추적 초기화"""
        self.total_cost = 0.0
        self.costs_breakdown = {}


# 전역 비용 추적기
global_cost_tracker = CostTracker()


if __name__ == "__main__":
    # 테스트
    tracker = CostTracker()

    # Embedding 비용 테스트
    query = "인공지능 관련 회의록을 찾아주세요"
    emb_cost = tracker.add_embedding_cost(query)
    print(f"쿼리 Embedding 비용: {emb_cost['cost_krw']}")

    # Chat 비용 테스트
    chat_cost = tracker.add_chat_cost(
        input_tokens=500,  # 프롬프트 + 쿼리
        output_tokens=50,  # JSON 응답
        model="gpt-4o-mini"
    )
    print(f"QueryAnalyzer 비용: {chat_cost['cost_krw']}")

    # 전체 요약
    tracker.print_summary()
