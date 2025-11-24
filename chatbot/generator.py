import os
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict

# .env 파일에서 환경 변수 로드
load_dotenv()

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_answer(query: str, documents: List[Dict]) -> str:
    """
    검색된 문서를 바탕으로 사용자의 질문에 대한 답변을 생성합니다.

    Args:
        query: 사용자의 질문 (재작성된 쿼리)
        documents: Retriever가 검색한 문서 리스트

    Returns:
        LLM이 생성한 최종 답변
    """
    if not documents:
        return "관련 정보를 찾을 수 없습니다. 다른 질문을 시도해 주세요."

    # 검색된 문서 내용을 컨텍스트로 조합
    context = "\n\n---\n\n".join([doc['text'] for doc in documents])

    # LLM에게 보낼 프롬프트
    system_prompt = "당신은 서울시의회 회의록 전문가입니다. 주어진 '문서' 내용을 바탕으로 '질문'에 대해 답변해주세요. 문서에 없는 내용은 답변하지 말고, 정보가 부족하다면 '문서에서 관련 정보를 찾을 수 없습니다'라고 솔직하게 답변하세요."
    
    user_prompt = f"""# 문서
{context}

# 질문
{query}

# 답변
"""

    print(f"💬 답변 생성 중... (query: {query})")

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        answer = response.choices[0].message.content.strip()
        print(f"   -> 답변 생성 완료")
        return answer
    except Exception as e:
        print(f"❌ 답변 생성 중 오류 발생: {e}")
        return "답변을 생성하는 중에 오류가 발생했습니다."

if __name__ == '__main__':
    # 테스트용 코드
    test_query = "서울시 AI 조례안의 주요 내용이 뭐야?"
    test_documents = [
        {
            "text": "경제실장 주용태입니다. 본 조례안은 인공지능 산업의 체계적인 육성과 지원을 위한 법적 근거를 마련하기 위함입니다. 주요 내용으로는 인공지능 기술의 공공 및 민간 부문 도입 촉진, 전문인력 양성 프로그램 운영, 그리고 관련 기업에 대한 재정적 지원 방안을 포함하고 있습니다.",
            "similarity": 0.85,
            "source": "agenda_001"
        },
        {
            "text": "김의원입니다. 전문인력 양성 프로그램의 구체적인 계획이 부족해 보입니다. 예산안을 보면 실제 교육보다는 단기 세미나에 치중되어 있는데, 실질적인 효과가 있을지 의문입니다.",
            "similarity": 0.78,
            "source": "agenda_001"
        }
    ]

    print(f"\n--- Generator 테스트 (query: '{test_query}') ---")
    final_answer = generate_answer(test_query, test_documents)
    print("\n[최종 생성 답변]")
    print(final_answer)
