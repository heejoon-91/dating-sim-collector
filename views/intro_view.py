# views/intro_view.py
import streamlit as st
from services.db_service import register_user, create_game_session
import time

def show_intro():
    # 1. 타이틀 및 분위기 조성
    st.title("💖 내 연애 페르소나 찾기")
    st.markdown("""
    혹시 내가 연애할 때 어떤 스타일인지 아시나요?  
    AI 파트너와 3번의 소개팅을 통해 **당신의 진짜 연애 성향**을 분석해 드립니다.
    """)
    
    st.divider() # 구분선

    # 2. 입력 폼
    col1, col2 = st.columns([3, 1]) # 디자인을 위해 칸 나누기
    with col1:
        nickname = st.text_input("닉네임을 입력해주세요 (익명 보장)", placeholder="예: 얼굴빼고 차은우, 얼굴없는 윈터")
    
    gender_kor = st.radio("성별을 선택해주세요", ["남성", "여성"], horizontal=True)
    gender = "M" if gender_kor == "남성" else "F"
    
    # 3. 데이터 수집 동의 (필수)
    agree = st.checkbox("정확한 분석을 위해 대화 내용 수집 및 이용에 동의합니다. (필수)")   
    
    # 4. 시작 버튼
    if st.button("🚀 소개팅 시작하기", use_container_width=True):
        if not nickname:
            st.warning("닉네임을 입력해주세요!")
        elif not agree:
            st.warning("동의 항목에 체크해야 테스트를 시작할 수 있어요.")
        else:
            with st.spinner("소개팅 상대를 매칭 중입니다..."):
                # DB에 유저 저장
                user_id = register_user(nickname, gender)
                
                if user_id:
                    # 게임 세션 생성
                    session_id = create_game_session(user_id)
                    
                    # 세션에 정보 저장 (로그인 처리)
                    st.session_state["user_id"] = user_id
                    st.session_state["session_id"] = session_id
                    st.session_state["nickname"] = nickname
                    st.session_state["gender"] = gender
                    st.session_state["step"] = "story" # 스토리 화면으로 이동
                    
                    time.sleep(1) # 약간의 로딩 연출
                    st.rerun() # 화면 새로고침 -> main.py가 game 화면을 보여줌
                else:
                    st.error("서버 연결에 실패했습니다. 잠시 후 다시 시도해주세요.")