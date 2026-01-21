# views/story_view.py
import streamlit as st
import time

def show_story():
    """
    게임 시작 전 스토리/상황 설명 화면
    """
    nickname = st.session_state.get("nickname", "익명")
    gender = st.session_state.get("gender", "F")
    
    # 성별에 따른 표현
    partner_word = "남자" if gender == "F" else "여자"
    
    st.title("📱 카톡이 왔습니다")
    
    st.divider()
    
    # 스토리 텍스트
    st.markdown(f"""
    ### 💬 친구에게서 온 메시지
    
    > *"야 {nickname}아, 너 요즘 외롭다며?"*
    > 
    > *"마침 내가 아는 {partner_word} 중에 너한테 맞을 것 같은 사람들 있어."*
    > 
    > *"근데 다들 바빠서... 이번 주말에 3명 다 만나야 해 ㅋㅋ"*
    > 
    > *"괜찮지? 커피 한 잔씩만 하면 되니까!"*
    """)
    
    st.divider()
    
    # 상황 설명 박스
    st.info("""
    ☕ **오늘의 미션**
    
    - 하루에 3명의 소개팅 상대를 만납니다
    - 각 상대와 **10번씩** 대화할 수 있어요 (커피 한 잔 분량!)
    - 대화 스타일에 따라 상대방의 **호감도**가 변합니다
    - 호감도가 0이 되면 상대방이 자리를 뜰 수도 있으니 조심하세요!
    """)
    
    st.divider()
    
    # 3명의 상대 미리보기
    st.subheader("오늘 만날 소개팅 상대들")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **1번째 상대** 🥺
        
        *"리액션 좋고 다정한 스타일"*
        """)
    
    with col2:
        st.markdown("""
        **2번째 상대** 🤓
        
        *"차분하고 진지한 스타일"*
        """)
    
    with col3:
        st.markdown("""
        **3번째 상대** 😉
        
        *"장난스럽고 적극적인 스타일"*
        """)
    
    st.divider()
    
    # 시작 버튼
    if st.button("☕ 첫 번째 소개팅 하러 가기", type="primary", use_container_width=True):
        st.session_state["step"] = "game"
        st.rerun()
    
    # 돌아가기 버튼
    if st.button("← 다시 정보 입력하기", use_container_width=True):
        st.session_state.clear()
        st.rerun()
