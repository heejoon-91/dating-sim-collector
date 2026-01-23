from openai import OpenAI
import streamlit as st
from config.settings import OPENAI_API_KEY, CHAT_MODEL, ANALYSIS_MODEL

# 클라이언트 초기화
if not OPENAI_API_KEY:
    # st.secrets에서 시도 (Streamlit Cloud 배포용)
    if "OPENAI_API_KEY" in st.secrets:
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    else:
        client = None
else:
    client = OpenAI(api_key=OPENAI_API_KEY)

import json


# RAG Service 초기화 (한 번만 로드 - 캐싱)
@st.cache_resource
def get_initialized_rag_service():
    try:
        from services.rag_service import RAGService

        return RAGService()
    except Exception as e:
        print(f"RAG Service Load Failed: {e}")
        return None


rag_service = get_initialized_rag_service()


def get_ai_response(messages):
    """
    OpenAI API를 통해 챗봇 응답을 받아옵니다.
    messages: game_view에서 관리하는 대화 내역 리스트 (System Prompt 포함)
    Returns: dict {"response": str, "score": int}
    """
    if not client:
        return {"response": "🚨 API Key가 설정되지 않았습니다.", "score": 0}

    # [RAG Integration]
    # 원본 messages를 변경하지 않기 위해 복사
    final_messages = list(messages)

    # 마지막 유저 메시지 추출
    last_user_msg = ""
    for msg in reversed(final_messages):
        if msg["role"] == "user":
            last_user_msg = msg["content"]
            break

    # 검색 및 컨텍스트 주입
    if rag_service and last_user_msg:
        context = rag_service.search_context(last_user_msg)
        if context:
            # 시스템 메시지를 찾아서 컨텍스트 추가
            # 보통 messages[0]이 시스템 프롬프트임
            for i, msg in enumerate(final_messages):
                if msg["role"] == "system":
                    new_content = (
                        msg["content"]
                        + f"\n\n[참고 가능한 과거 대화 데이터]\n{context}\n\n위 데이터를 참고하되, 현재 대화 흐름에 맞게 자연스럽게 반응해."
                    )
                    # 해당 메시지만 교체 (딕셔너리 새로 생성)
                    final_messages[i] = {"role": "system", "content": new_content}
                    break

    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=final_messages,
            response_format={"type": "json_object"},  # JSON 모드 강제
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        return {"response": f"🚨 오류 발생: {str(e)}", "score": 0}


def analyze_conversation(history):
    """
    대화 기록을 분석하여 사용자의 연애 성향을 파악합니다.
    history: 각 라운드별 대화 기록 리스트 [{"round": 1, "persona": "EMOTIONAL", "messages": [...], "final_score": 70}, ...]
    Returns: dict (my_persona, ideal_preference, summary)
    """
    from config.prompts import get_analysis_prompt

    if not client:
        return {"error": "API Key가 설정되지 않았습니다."}

    # 대화 내용을 텍스트로 정리
    conversation_text = ""
    for entry in history:
        round_num = entry.get("round", "?")
        persona = entry.get("persona", "UNKNOWN")
        score = entry.get("final_score", "N/A")
        messages = entry.get("messages", [])

        conversation_text += (
            f"\n\n### 라운드 {round_num}: {persona} 타입 (최종 호감도: {score})\n"
        )
        for msg in messages:
            if msg["role"] == "user":
                conversation_text += f"[USER]: {msg['content']}\n"
            elif msg["role"] == "assistant":
                conversation_text += f"[AI]: {msg['content']}\n"

    try:
        response = client.chat.completions.create(
            model=ANALYSIS_MODEL,
            messages=[
                {"role": "system", "content": get_analysis_prompt()},
                {
                    "role": "user",
                    "content": f"다음 대화 기록을 분석해줘:\n{conversation_text}",
                },
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        return {"error": f"분석 실패: {str(e)}"}
