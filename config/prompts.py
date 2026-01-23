# config/prompts.py
import os

# 프롬프트 파일 경로
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def _load_prompt(filename):
    """프롬프트 파일을 읽어서 반환합니다."""
    filepath = os.path.join(PROMPTS_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def get_system_prompt(persona_type, user_gender, user_nickname="OO", rag_context=""):
    """
    persona_type: 'EMOTIONAL', 'LOGICAL', 'TOUGH'
    user_gender: 'M', 'F'
    user_nickname: 사용자 닉네임
    """

    # 상대방 호칭 및 성별 설정
    target_role = "소개팅녀" if user_gender == "M" else "소개팅남"

    # 페르소나별 이름 설정
    names = {
        "M": {"EMOTIONAL": "김민수", "LOGICAL": "이진우", "TOUGH": "박태양"},
        "F": {"EMOTIONAL": "이지은", "LOGICAL": "김서윤", "TOUGH": "박하윤"},
    }

    opponent_gender = "F" if user_gender == "M" else "M"
    current_name = names.get(opponent_gender, {}).get(persona_type, "상대방")

    # 공통 프롬프트 로드 및 변수 치환
    base_prompt = _load_prompt("base.txt").format(
        target_role=target_role, current_name=current_name, user_nickname=user_nickname
    )

    # 페르소나별 프롬프트 로드
    persona_files = {
        "EMOTIONAL": "emotional.txt",
        "LOGICAL": "logical.txt",
        "TOUGH": "tough.txt",
    }

    persona_file = persona_files.get(persona_type)
    if persona_file:
        persona_prompt = _load_prompt(persona_file)
    else:
        persona_prompt = ""

    return base_prompt + "\n\n" + persona_prompt + "\n\n" + rag_context


def get_persona_name(persona_type, user_gender):
    names = {
        "M": {"EMOTIONAL": "김민수", "LOGICAL": "이진우", "TOUGH": "박태양"},
        "F": {"EMOTIONAL": "이지은", "LOGICAL": "김서윤", "TOUGH": "박하윤"},
    }
    opponent_gender = "F" if user_gender == "M" else "M"
    return names.get(opponent_gender, {}).get(persona_type, "알 수 없음")


def get_first_greeting(persona_type, user_gender):
    """
    각 페르소나별 첫 인사말을 반환합니다.
    """
    greetings = {
        "M": {
            "EMOTIONAL": "안녕하세요! 오시느라 고생 많으셨죠? 날씨가 꽤 춥네요 ㅠㅠ 따뜻한 거라도 먼저 시키실래요?",
            "LOGICAL": "안녕하세요. 이진우입니다. 약속 시간 딱 맞춰 오셨네요. 앉으시죠.",
            "TOUGH": "오, 안녕하세요? 사진보다 실물이 훨씬 좋으시네요. 깜짝 놀랐어요 ㅋㅋ",
        },
        "F": {
            "EMOTIONAL": "안녕하세요! 아, 오시느라 너무 고생 많으셨죠? ㅠㅠ 저 방금 왔는데 여기 카페 인테리어가 너무 예뻐서 계속 구경하고 있었어요! 이지은이라고 합니다 ㅎㅎ",
            "LOGICAL": "안녕하세요, 김서윤입니다. 만나서 반가워요. 주말인데 시간 내주셔서 감사합니다.",
            "TOUGH": "어? 안녕하세요! 생각보다 일찍 오셨네요? 저 기다리는 거 잘 못하는데 다행이다 ㅋㅋ",
        },
    }
    opponent_gender = "F" if user_gender == "M" else "M"
    return greetings.get(opponent_gender, {}).get(persona_type, "안녕하세요! 반가워요.")


def get_analysis_prompt():
    """
    사용자의 대화 스타일을 분석하는 시스템 프롬프트를 반환합니다.
    """
    return _load_prompt("analysis.txt")
