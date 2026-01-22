# views/result_view.py
import streamlit as st
import time
from services.llm_service import analyze_conversation
from services.db_service import update_game_session, save_analysis_result
from config.prompts import get_persona_name


def show_result():
    # 세션 데이터 가져오기
    history = st.session_state.get("history", [])
    affection_scores = st.session_state.get("affection_scores", {})
    user_gender = st.session_state.get("gender", "F")
    fail_reason = st.session_state.get("fail_reason", None)
    nickname = st.session_state.get("nickname", "익명")

    # 상대방 이름 가져오기
    name1 = get_persona_name("EMOTIONAL", user_gender)
    name2 = get_persona_name("LOGICAL", user_gender)
    name3 = get_persona_name("TOUGH", user_gender)

    # ============================================
    # STEP 1: 최종 선택 (점수 안 보여주고 느낌으로 선택)
    # ============================================
    if "final_choice" not in st.session_state:
        st.title("💌 소개팅이 끝났습니다!")

        # 실패로 끝난 경우
        if fail_reason:
            st.warning(f"💔 {fail_reason}")
        else:
            st.success("3명의 상대와 소개팅을 모두 마쳤습니다!")

        st.divider()
        st.subheader("누구와 연락처를 교환하시겠어요?")
        st.caption("점수는 공개하지 않습니다. 대화할 때의 느낌을 떠올려보세요! 💭")

        st.divider()

        # 선택지 (점수 없이)
        choice_options = [
            f"🥺 {name1} (공감형) - 리액션 좋고 다정했던 사람",
            f"🤓 {name2} (이성형) - 차분하고 진지했던 사람",
            f"😉 {name3} (직진형) - 장난스럽고 적극적이었던 사람",
            "❌ 아무도 선택하지 않음",
        ]

        selected = st.radio(
            "마음에 드는 상대를 선택해주세요:", choice_options, index=None
        )

        if st.button(
            "선택 완료 → 분석 결과 보기",
            type="primary",
            use_container_width=True,
            disabled=(selected is None),
        ):
            # 선택 결과 매핑
            choice_map = {
                choice_options[0]: "EMOTIONAL",
                choice_options[1]: "LOGICAL",
                choice_options[2]: "TOUGH",
                choice_options[3]: "NONE",
            }
            st.session_state["final_choice"] = choice_map.get(selected, "UNKNOWN")
            st.rerun()

        return  # 여기서 중단 (선택 먼저)

    # ============================================
    # STEP 2: 분석 결과 표시 (선택 완료 후)
    # ============================================
    final_choice = st.session_state.get("final_choice", "UNKNOWN")

    # 분석 실행 (캐싱)
    if "analysis_result" not in st.session_state:
        if history:
            with st.spinner("대화 내용을 분석 중입니다... 🔍"):
                result = analyze_conversation(history)
                st.session_state["analysis_result"] = result
        else:
            st.session_state["analysis_result"] = {
                "error": "분석할 대화 기록이 없습니다."
            }

    analysis = st.session_state["analysis_result"]

    # 오류 체크
    if "error" in analysis:
        st.error(analysis["error"])
        if st.button("처음으로 돌아가기"):
            st.session_state.clear()
            st.rerun()
        return

    my_persona = analysis.get("my_persona", {})
    compatibility = analysis.get("compatibility", {})
    insights = analysis.get("insights", {})

    # =============================================
    # 1. 메인 타이틀: 당신의 연애 스타일
    # =============================================
    style_name = my_persona.get("style", "알 수 없음")
    my_type = my_persona.get("type", "UNKNOWN")

    st.title(f"💖 {nickname}님의 연애 스타일")
    st.header(f'**"{style_name}"**')

    # 유저 타입 배지
    type_emoji = {
        "EMOTIONAL": "🥺 공감형",
        "LOGICAL": "🤓 이성형",
        "TOUGH": "😉 직진형",
    }
    st.info(f"당신의 타입: **{type_emoji.get(my_type, '알 수 없음')}**")

    keywords = my_persona.get("keywords", [])
    if keywords:
        st.markdown(" | ".join([f"`{k}`" for k in keywords]))

    st.divider()

    # =============================================
    # 2. AI 추천 상대 + 호감도 공개
    # =============================================
    st.subheader("💘 가장 잘 맞는 상대")

    best_match = compatibility.get("best_match", "UNKNOWN")
    best_match_name = get_persona_name(best_match, user_gender)

    # 호감도 점수 가져오기
    score_map = {"EMOTIONAL": 1, "LOGICAL": 2, "TOUGH": 3}
    best_score = affection_scores.get(score_map.get(best_match, 1), 50)

    st.success(
        f"🎯 **{best_match_name}** 타입과 가장 잘 맞습니다! (호감도 {best_score}점)"
    )
    st.markdown(f"**왜 잘 맞을까요?** {compatibility.get('best_reason', '-')}")

    st.divider()

    # =============================================
    # 3. 스타일 호환성 분석 (NEW!)
    # =============================================
    st.subheader("🔄 스타일 호환성 분석")

    col_sim, col_opp = st.columns(2)

    with col_sim:
        similar_style = compatibility.get("similar_style", "UNKNOWN")
        similar_name = (
            get_persona_name(similar_style, user_gender)
            if similar_style != "UNKNOWN"
            else "알 수 없음"
        )
        st.markdown(f"**비슷한 스타일**: {similar_name}")
        st.caption(compatibility.get("similar_chemistry", "-"))

    with col_opp:
        opposite_style = compatibility.get("opposite_style", "UNKNOWN")
        opposite_name = (
            get_persona_name(opposite_style, user_gender)
            if opposite_style != "UNKNOWN"
            else "알 수 없음"
        )
        st.markdown(f"**반대 스타일**: {opposite_name}")
        st.caption(compatibility.get("opposite_chemistry", "-"))

    st.divider()

    # =============================================
    # 4. 각 상대별 호감도 + 간단 피드백
    # =============================================
    st.subheader("📊 각 상대방이 느낀 호감도")

    col1, col2, col3 = st.columns(3)

    with col1:
        score1 = affection_scores.get(1, 50)
        st.metric(label=f"🥺 {name1}", value=f"{score1}점")
        if score1 >= 70:
            st.caption("💕 좋은 인상을 남겼어요!")
        elif score1 >= 40:
            st.caption("🤔 나쁘지 않았어요")
        else:
            st.caption("😢 아쉬웠어요")

    with col2:
        score2 = affection_scores.get(2, 50)
        st.metric(label=f"🤓 {name2}", value=f"{score2}점")
        if score2 >= 70:
            st.caption("💕 좋은 인상을 남겼어요!")
        elif score2 >= 40:
            st.caption("🤔 나쁘지 않았어요")
        else:
            st.caption("😢 아쉬웠어요")

    with col3:
        score3 = affection_scores.get(3, 50)
        st.metric(label=f"😉 {name3}", value=f"{score3}점")
        if score3 >= 70:
            st.caption("💕 좋은 인상을 남겼어요!")
        elif score3 >= 40:
            st.caption("🤔 나쁘지 않았어요")
        else:
            st.caption("😢 아쉬웠어요")

    st.divider()

    # =============================================
    # 5. 당신의 선택 vs AI 추천 비교
    # =============================================
    st.subheader("💕 당신의 선택")

    if final_choice == "NONE":
        st.info("아무도 선택하지 않으셨습니다.")
    else:
        chosen_name = get_persona_name(final_choice, user_gender)
        if final_choice == best_match:
            st.success(f"**{chosen_name}**님을 선택하셨습니다! AI 분석과 일치해요 🎯")
        else:
            best_match_name = get_persona_name(best_match, user_gender)
            st.info(f"**{chosen_name}**님을 선택하셨습니다!")
            st.caption(f"AI는 {best_match_name}님을 추천했지만, 마음은 마음대로죠 💕")

    st.divider()

    # =============================================
    # 6. 연애 인사이트 (NEW!)
    # =============================================
    st.subheader("💡 연애 인사이트")

    # 긍정적인 모습
    st.markdown(f"✅ **잘한 점**: {insights.get('positive', '-')}")

    # 개선할 점
    st.markdown(f"📈 **개선하면 좋을 점**: {insights.get('improvement', '-')}")

    # 연애 팁
    st.info(f"💡 **연애 팁**: {insights.get('dating_tip', '-')}")

    # 주의사항 (있으면)
    warning = insights.get("warning", "")
    # warning이 리스트인 경우 문자열로 변환
    if isinstance(warning, list):
        warning = ", ".join(str(w) for w in warning if w)
    if warning and warning != "-" and str(warning).lower() != "none":
        st.warning(f"⚠️ **주의**: {warning}")

    st.divider()

    # =============================================
    # 7. 강점과 약점
    # =============================================
    st.subheader("🪞 연애에서의 강점과 약점")

    col_a, col_b = st.columns(2)
    with col_a:
        st.success(f"**강점**: {my_persona.get('strength', '-')}")
    with col_b:
        st.warning(f"**보완할 점**: {my_persona.get('weakness', '-')}")

    st.divider()

    # =============================================
    # 8. 전체 요약
    # =============================================
    st.subheader("📝 분석 요약")
    st.markdown(analysis.get("summary", "분석 결과 없음"))

    st.divider()

    # DB 저장 (자동)
    if "db_saved" not in st.session_state:
        session_id = st.session_state.get("session_id")
        if session_id:
            # 세션 업데이트
            update_game_session(
                session_id=session_id,
                final_choice=final_choice,
                my_persona=my_persona,
                ideal_preference=compatibility,
            )
            # 분석 결과 저장
            save_analysis_result(session_id, analysis)
            st.session_state["db_saved"] = True

    st.success("🎉 분석 결과가 저장되었습니다. 참여해주셔서 감사합니다!")

    # 다시 하기 버튼
    if st.button("처음부터 다시 하기", use_container_width=True):
        st.session_state.clear()
        st.rerun()
