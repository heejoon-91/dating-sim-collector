import streamlit as st
import time
from services.llm_service import get_ai_response
from services.db_service import save_chat_log, save_affinity_log
from config.prompts import get_system_prompt, get_persona_name, get_first_greeting

# 한 사람당 최대 대화 횟수
MAX_TURNS = 10

def show_game():
    st.title(f"{st.session_state.get('nickname', '익명')}님의 소개팅 💕")
    
    # 0. 기본 설정값 가져오기
    user_gender = st.session_state.get("gender", "F") # 기본값 F
    # - (수정) 닉네임 가져오기
    user_nickname = st.session_state.get("nickname", "OO")
    
    # 세션 상태 초기화
    if "current_round" not in st.session_state:
        st.session_state["current_round"] = 1
        
    current_round = st.session_state["current_round"]
    
    # 라운드별 설정
    ROUND_TYPES = {1: "EMOTIONAL", 2: "LOGICAL", 3: "TOUGH"}
    current_type = ROUND_TYPES[current_round]
    
    # 이름 가져오기
    persona_name = get_persona_name(current_type, user_gender)
    
    ROUND_LABELS = {
        1: f"1라운드: {persona_name} (공감형 🥺)",
        2: f"2라운드: {persona_name} (이성형 🤓)",
        3: f"3라운드: {persona_name} (직진형 😉)"
    }

    # 대화 히스토리 초기화 (앱 켜질 때 or 라운드 변경 직후 메시지가 비어있을 때 contents가 비어있으면 초기화)
    if "messages" not in st.session_state:
        # [수정 1] 프롬프트 생성 시 user_nickname 전달
        sys_prompt = get_system_prompt(current_type, user_gender, user_nickname)
        # 첫 인사 생성
        greeting = get_first_greeting(current_type, user_gender)
        
        st.session_state["messages"] = [
            {"role": "system", "content": sys_prompt},
            {"role": "assistant", "content": greeting}
        ]

    # 호감도 초기화 (라운드별 개별 점수)
    if "affection_scores" not in st.session_state:
        st.session_state["affection_scores"] = {1: 50, 2: 50, 3: 50}

    # 2. UI 표시
    # 현재 상대방 정보 + 남은 대화 횟수
    turn_count = len([m for m in st.session_state["messages"] if m["role"] == "user"])
    remaining = MAX_TURNS - turn_count
    
    col1, col2 = st.columns([4, 1])
    with col1:
        st.subheader(f"💬 {persona_name}님과 대화 중")
    with col2:
        st.metric(label="남은 대화", value=f"{remaining}회")
    
    # 대화 시간 제한 안내
    if remaining <= 3 and remaining > 0:
        st.warning(f"⏰ {persona_name}님과의 대화가 {remaining}회 남았습니다!")

    # 채팅 기록 표시
    for msg in st.session_state["messages"]:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    # 대기 중인 메시지 처리 (AI 응답 생성)
    if st.session_state.get("pending_message"):
        # AI 응답 생성
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("입력 중... ▌")
            
            result = get_ai_response(st.session_state["messages"])
                
            ai_text = result.get("response", "...")
            
            # === [여기 수정] 점수 변환 안전장치 추가 ===
            try:
                score_delta = int(result.get("score", 0))
            except (ValueError, TypeError):
                score_delta = 0
            # =========================================
            
            # 호감도 업데이트 (현재 라운드)
            prev_score = st.session_state["affection_scores"][current_round]
            new_score = max(0, min(100, prev_score + score_delta))
            st.session_state["affection_scores"][current_round] = new_score
            
            # === 호감도 변경 로그 DB 저장 ===
            session_id = st.session_state.get("session_id")
            if session_id:
                # 현재 턴 번호 계산
                turn_index = len([m for m in st.session_state["messages"] if m["role"] == "user"])
                
                # 사용자의 마지막 메시지 가져오기 (호감도 변화를 유발한 메시지)
                user_messages = [m for m in st.session_state["messages"] if m["role"] == "user"]
                trigger_message = user_messages[-1]["content"] if user_messages else None
                
                # LLM이 reason을 반환했다면 사용, 없으면 None
                reason = result.get("reason", None)
                
                save_affinity_log(
                    session_id=session_id,
                    partner_type=current_type,
                    turn_index=turn_index,
                    score_change=score_delta,
                    current_score=new_score,
                    reason=reason,
                    trigger_message=trigger_message
                )
            # ================================
            
            # 점수 변화 알림
            if score_delta > 0:
                st.toast(f"{persona_name}의 호감도가 올랐습니다! (+{score_delta}) 😍")
            elif score_delta < 0:
                st.toast(f"{persona_name}의 호감도가 떨어졌습니다.. ({score_delta}) 😢")

            # 타자기 효과
            full_response = ""
            for chunk in ai_text.split():
                full_response += chunk + " "
                time.sleep(0.05)
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
        
        # AI 메시지 저장
        st.session_state["messages"].append({"role": "assistant", "content": full_response})
        
        # pending 상태 해제 (AI 응답 완료)
        st.session_state["pending_message"] = None
        
        # 게임 오버 체크
        if new_score <= 0:
            st.error(f"💔 {persona_name}님이 실망하여 자리를 떠났습니다...")
            
            # 채팅 로그 DB 저장
            session_id = st.session_state.get("session_id")
            if session_id:
                turn_count = len([m for m in st.session_state["messages"] if m["role"] == "user"])
                save_chat_log(session_id, current_type, st.session_state["messages"], turn_count)
            
            time.sleep(3)
            st.session_state["fail_reason"] = f"{persona_name} 호감도 부족"
            st.session_state["step"] = "result" # 결과 화면(실패)으로 이동
            st.rerun()
        
        # 대화 횟수 제한 체크 (10회 달성 시 자동 종료)
        current_turns = len([m for m in st.session_state["messages"] if m["role"] == "user"])
        if current_turns >= MAX_TURNS:
            st.info(f"⏰ {persona_name}님과의 소개팅 시간이 종료되었습니다!")
            time.sleep(2)
            
            # 채팅 로그 DB 저장
            session_id = st.session_state.get("session_id")
            if session_id:
                save_chat_log(session_id, current_type, st.session_state["messages"], current_turns)
            
            # 히스토리 저장
            if "history" not in st.session_state:
                st.session_state["history"] = []
            st.session_state["history"].append({
                "round": current_round,
                "persona": current_type,
                "messages": st.session_state["messages"],
                "final_score": st.session_state["affection_scores"][current_round]
            })
            
            # 다음 라운드로 이동
            if current_round < 3:
                st.session_state["current_round"] += 1
                next_round = st.session_state["current_round"]
                next_type = ROUND_TYPES[next_round]
                next_name = get_persona_name(next_type, user_gender)
                
                new_sys_prompt = get_system_prompt(next_type, user_gender, user_nickname)
                new_greeting = get_first_greeting(next_type, user_gender)
                st.session_state["messages"] = [
                    {"role": "system", "content": new_sys_prompt},
                    {"role": "assistant", "content": new_greeting}
                ]
                st.toast(f"{next_name}님과의 대화가 시작됩니다!")
                time.sleep(1)
                st.rerun()
            else:
                st.success("모든 소개팅이 종료되었습니다! 결과를 분석합니다.")
                time.sleep(1)
                st.session_state["step"] = "result"
                st.rerun()
        
        # AI 응답 완료 후 화면 새로고침 (입력창 다시 활성화)
        st.rerun()

    # 4. 라운드 종료 / 넘기기 (임시 버튼)
    st.divider()
    st.divider()
    if st.button("다음 라운드로 넘어가기 (대화 종료)"):
        # 채팅 로그 DB 저장
        session_id = st.session_state.get("session_id")
        if session_id:
            turn_count = len([m for m in st.session_state["messages"] if m["role"] == "user"])
            save_chat_log(session_id, current_type, st.session_state["messages"], turn_count)
        
        # 현재 대화 로그 저장 (history - 로컬)
        if "history" not in st.session_state:
            st.session_state["history"] = []
            
        st.session_state["history"].append({
            "round": current_round,
            "persona": current_type,
            "messages": st.session_state["messages"],
            "final_score": st.session_state["affection_scores"][current_round]
        })
        
        # 다음 라운드 진행 판단
        if current_round < 3:
            st.session_state["current_round"] += 1
            next_round = st.session_state["current_round"]
            
            # 다음 라운드 정보 준비
            next_type = ROUND_TYPES[next_round]
            next_name = get_persona_name(next_type, user_gender)
            
            # [수정 2] 다음 라운드 프롬프트 생성 시에도 user_nickname 전달
            new_sys_prompt = get_system_prompt(next_type, user_gender, user_nickname)
            new_greeting = get_first_greeting(next_type, user_gender)
            
            st.session_state["messages"] = [
                {"role": "system", "content": new_sys_prompt},
                {"role": "assistant", "content": new_greeting}
            ]
            
            st.toast(f"{next_name}님과의 대화가 시작됩니다!")
            time.sleep(1)
            st.rerun()
        else:
            # 모든 라운드 종료 -> 결과 화면
            st.success("모든 소개팅이 종료되었습니다! 결과를 분석합니다.")
            time.sleep(1)
            st.session_state["step"] = "result"
            st.rerun()

    # 5. 사용자 입력 처리
    prompt = st.chat_input("메시지를 입력하세요...")
    
    if prompt:
        # 마지막 메시지가 user인지 확인 (연속 user 입력 방지)
        messages = st.session_state.get("messages", [])
        last_message_is_user = False
        for msg in reversed(messages):
            if msg["role"] != "system":
                last_message_is_user = (msg["role"] == "user")
                break
        
        # 마지막이 assistant 메시지일 때만 새 입력 허용
        if not last_message_is_user and not st.session_state.get("pending_message"):
            st.session_state["messages"].append({"role": "user", "content": prompt})
            st.session_state["pending_message"] = prompt
            st.rerun()
        # 그 외의 경우는 조용히 무시 (화면에도 안 나옴)

