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
        return question

    # 대화 기록을 문자열로 변환
    formatted_history = "\n".join([f"사용자: {q}\nAI: {a}" for q, a in history])

    # LLM에게 보낼 프롬프트
    prompt = f"""대화 기록과 후속 질문이 주어집니다. 후속 질문을 대화 기록 없이도 이해할 수 있는 독립적인 질문으로 재작성해주세요.

# 대화 기록
{formatted_history}

# 후속 질문
{question}

# 재작성된 질문:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 사용자의 질문을 명확하게 재구성하는 AI 어시스턴트입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=200
        )
        rewritten_question = response.choices[0].message.content.strip()
        print(f"Rewritten query: {rewritten_question}")
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
