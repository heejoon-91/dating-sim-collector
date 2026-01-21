from views.intro_view import show_intro
from views.story_view import show_story
from views.game_view import show_game
from views.result_view import show_result
import streamlit as st
import os
from dotenv import load_dotenv

# 1. 환경 변수 로드 (.env 파일 읽기)
load_dotenv()

# [팁] 배포 환경(Streamlit Cloud)에서는 .env 파일이 없으므로,
# os.getenv가 실패하면 st.secrets를 찾아보게 하는 안전장치를 두면 좋습니다.
def get_secret(key):
    return os.getenv(key) or st.secrets.get(key)

# API 키 확인 (디버깅용, 배포 시 삭제 권장)
if not get_secret("OPENAI_API_KEY"):
    st.error("🚨 API 키가 설정되지 않았습니다. .env 파일을 확인해주세요.")
    st.stop()

# ---------------------------------------------------------
# 2. 세션 상태(State) 초기화
# ---------------------------------------------------------
if "step" not in st.session_state:
    st.session_state["step"] = "intro" # 초기 상태: intro, story, game, result

if "user_data" not in st.session_state:
    st.session_state["user_data"] = {} # 유저 정보(닉네임 등) 저장

if "game_logs" not in st.session_state:
    st.session_state["game_logs"] = [] # 대화 로그 임시 저장

# ---------------------------------------------------------
# 3. 메인 실행 로직
# ---------------------------------------------------------
def main():
    current_step = st.session_state["step"]
    
    if current_step == "intro":
        show_intro()
    elif current_step == "story":
        show_story()
    elif current_step == "game":
        show_game()
    elif current_step == "result":
        show_result()
    else:
        st.error("알 수 없는 오류가 발생했습니다.")

if __name__ == "__main__":
    main()