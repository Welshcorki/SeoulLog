import os
from openai import OpenAI
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def rewrite_query(question: str, history: list[tuple[str, str]]) -> str:
    """
    대화 기록을 바탕으로 후속 질문을 독립적인 질문으로 재작성합니다.

    Args:
        question: 사용자의 현재 질문
        history: (질문, 답변) 튜플의 리스트

    Returns:
        독립적으로 재작성된 질문
    """
    if not history:
        print(f"No history, returning original query: {question}")
        return question

    # 대화 기록을 문자열로 변환
    formatted_history = "\n".join([f"사용자: {q}\nAI: {a}" for q, a in history])

    # LLM에게 보낼 프롬프트
    prompt = f"""당신은 대화의 맥락을 파악하여, 사용자의 질문을 벡터 데이터베이스 검색에 최적화된 '독립적인 질문'으로 재작성하는 전문가입니다.\n\n**임무:**\n주어진 '대화 기록'과 '마지막 질문'을 분석하여, 검색에 가장 적합한 단일 질문을 생성하세요.\n\n**규칙:**\n1.  **주제 변경 감지 (가장 중요):** 먼저 '마지막 질문'이 '대화 기록'과 연관된 후속 질문인지, 아니면 완전히 새로운 주제인지 판단하세요.\n    -   **새로운 주제일 경우:** '대화 기록'을 **무시**하고, '마지막 질문'을 **그대로 반환**하세요. (예: 이전 대화가 '부동산'이었는데 마지막 질문이 '인공지능'에 대한 것이면, '인공지능'을 그대로 반환)\n    -   **후속 질문일 경우:** 아래 2번, 3번 규칙에 따라 질문을 재작성하세요.\n\n2.  **맥락 통합:** '마지막 질문'이 '그것', '저기' 등 대명사를 포함하면, '대화 기록'에서 가리키는 구체적인 대상을 찾아 질문에 명시적으로 포함시키세요.\n\n3.  **불필요한 변경 금지:** 만약 '마지막 질문'이 이미 그 자체로 완전한 독립 질문이라면, 변경하지 말고 그대로 반환하세요.\n\n4.  **언어 유지:** 질문은 반드시 한국어로 작성되어야 합니다.\n\n---\n**예시 1: 새로운 주제**\n- 대화 기록:\n  사용자: 서울시 청년 주거 지원 정책에 대해 알려줘.\n  AI: ...정책을 시행하고 있습니다.\n- 마지막 질문: 서울시 인공지능 정책은?\n- **재작성된 질문: 서울시 인공지능 정책은?**\n\n**예시 2: 후속 질문 (대명사 구체화)**\n- 대화 기록:\n  사용자: 서울시 청년 주거 지원 정책에 대해 알려줘.\n  AI: ...정책을 시행하고 있습니다.\n- 마지막 질문: 그것의 신청 자격은 어떻게 돼?\n- **재작성된 질문: 서울시 청년 주거 지원 정책의 신청 자격은 어떻게 되나요?**\n---\n\n**실제 작업:**\n\n# 대화 기록\n{formatted_history}\n\n# 마지막 질문\n{question}\n\n# 재작성된 질문:"""

    try:
        print("Re-writing query with new prompt...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 사용자의 질문을 명확하게 재구성하는 AI 어시스턴트입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0, # 창의성보다는 정확성을 위해 0으로 설정
            max_tokens=500
        )
        content = response.choices[0].message.content
        rewritten_question = content.strip() if content else ""
        
        # 후처리가 필요한 경우 (예: 모델이 "재작성된 질문:"과 같은 접두사를 붙이는 경우)
        if rewritten_question.startswith("재작성된 질문:"):
            rewritten_question = rewritten_question.replace("재작성된 질문:", "").strip()

        print(f"Original query: '{question}'")
        print(f"Rewritten query: '{rewritten_question}'")
        return rewritten_question
    except Exception as e:
        print(f"Error rewriting query: {e}")
        # 오류 발생 시 원래 질문 반환
        return question

if __name__ == '__main__':
    # 테스트용 코드
    sample_history = [
        ("서울시 AI 정책에 대해 알려줘.", "서울시는 '서울특별시 인공지능산업 육성 및 지원 조례안'을 통해 AI 산업을 지원하고 있습니다. 주요 내용은 AI 기술 도입, 전문인력 양성 등입니다.")
    ]
    follow_up_question = "그 조례안은 누가 발의했어?"

    rewritten = rewrite_query(follow_up_question, sample_history)
    
    print("\n--- 쿼리 재작성 테스트 ---")
    print(f"원본 질문: {follow_up_question}")
    print(f"재작성된 질문: {rewritten}")
    # 예상 결과: "서울특별시 인공지능산업 육성 및 지원 조례안은 누가 발의했어?"
