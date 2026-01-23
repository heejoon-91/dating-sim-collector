"""
채팅 데이터 전처리 모듈

5개 플랫폼(KAKAO, FACEBOOK, INSTAGRAM, BAND, NATEON)의 채팅 데이터를
정제하여 ChromaDB 벡터 DB에 저장할 수 있는 형태로 변환합니다.

제외되는 카테고리:
- 2: 주거와생활
- 3: 교통
- 5: 군대
- 6: 교육
- 7: 가족
- 14: 사회이슈
- 15: 타 국가 이슈
- 17: 건강
- 18: 상거래 전반
- 19: 방송/연예
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# 제외할 카테고리 번호 (파일명에서 추출)
EXCLUDED_CATEGORIES = {2, 3, 5, 6, 7, 14, 15, 17, 18, 19}

# 제거할 채팅 표현 패턴들
CHAT_NOISE_PATTERNS = [
    r"\s*키+\s*",  # 키, 키키, 키키키 등
    r"\s*ㅋ+\s*",  # ㅋ, ㅋㅋ, ㅋㅋㅋ 등
    r"\s*ㅎ+\s*",  # ㅎ, ㅎㅎ, ㅎㅎㅎ 등
    r"\s*ㄱㄱ+\s*",  # ㄱㄱ
    r"\s*ㅇㅇ+\s*",  # ㅇㅇ
    r"\s*ㅜ+\s*",  # ㅜㅜ
    r"\s*ㅠ+\s*",  # ㅠㅠ
    r"\s*헤헤+\s*",  # 헤헤
    r"\s*하하+\s*",  # 하하
    r"\s*호호+\s*",  # 호호
    r"\s*히히+\s*",  # 히히
    r"\s*웅+\s*",  # 웅
    r"\s*앜+\s*",  # 앜
    r"\s*엌+\s*",  # 엌
    r"\s*ㄷㄷ+\s*",  # ㄷㄷ
    r"\s*;;;+\s*",  # ;;;
    r"\s*\.\.\.+\s*",  # ...
]


def get_category_from_filename(filename: str) -> Optional[int]:
    """
    파일명에서 카테고리 번호를 추출합니다.
    예: KAKAO_448_18.json -> 448

    파일명 형식: {PLATFORM}_{CATEGORY}_{NUM}.json
    """
    pattern = r"[A-Z]+_\d+_(\d+)\.json"
    match = re.match(pattern, filename)
    if match:
        return int(match.group(1))
    return None


def should_exclude_file(filename: str) -> bool:
    """
    파일을 제외해야 하는지 확인합니다.
    """
    category = get_category_from_filename(filename)
    if category is None:
        return False
    return category in EXCLUDED_CATEGORIES


def clean_text(text: str) -> str:
    """
    채팅 텍스트에서 불필요한 표현을 제거합니다.
    """
    cleaned = text
    for pattern in CHAT_NOISE_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned)

    # 연속된 공백을 하나로 줄임
    cleaned = re.sub(r"\s+", " ", cleaned)

    # 앞뒤 공백 제거
    cleaned = cleaned.strip()

    return cleaned


def extract_conversation_from_file(file_path: Path) -> List[Dict]:
    """
    JSON 파일에서 대화 데이터를 추출합니다.

    Returns:
        대화 청크 리스트. 각 청크는 다음 필드를 포함:
        - conversation_id: 대화 식별자
        - platform: 플랫폼 이름
        - subject: 대화 주제
        - speaker_type: 화자 유형 (1:1 등)
        - dialogue: 정제된 대화 텍스트
        - turns: 개별 발화 리스트
    """
    conversations = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"Error reading {file_path}: {e}")
        return conversations

    # 플랫폼 추출
    filename = file_path.name
    platform = filename.split("_")[0]

    # info 배열 처리
    info_list = data.get("info", [])
    for info in info_list:
        annotations = info.get("annotations", {})
        lines = annotations.get("lines", [])

        if not lines:
            continue

        # 메타데이터 추출
        subject = annotations.get("subject", "")
        speaker_type = annotations.get("speaker_type", "")

        # 대화 턴 처리
        turns = []
        cleaned_dialogue_parts = []

        for line in lines:
            norm_text = line.get("norm_text", "")
            if not norm_text:
                continue

            # 텍스트 정제
            cleaned_text = clean_text(norm_text)
            if not cleaned_text:
                continue

            speaker = line.get("speaker", {})
            speech_act = line.get("speechAct", "")

            turn = {
                "speaker_id": speaker.get("id", ""),
                "speaker_sex": speaker.get("sex", ""),
                "speaker_age": speaker.get("age", ""),
                "text": cleaned_text,
                "speech_act": speech_act,
            }
            turns.append(turn)
            cleaned_dialogue_parts.append(cleaned_text)

        if not turns:
            continue

        # 전체 대화 텍스트 생성
        dialogue = "\n".join(cleaned_dialogue_parts)

        conversation = {
            "conversation_id": f"{platform}_{info.get('id', '')}",
            "platform": platform,
            "subject": subject,
            "speaker_type": speaker_type,
            "dialogue": dialogue,
            "turns": turns,
            "source_file": filename,
        }
        conversations.append(conversation)

    return conversations


def process_all_data(data_dir: str) -> Tuple[List[Dict], Dict]:
    """
    모든 플랫폼의 채팅 데이터를 처리합니다.

    Args:
        data_dir: 데이터 디렉토리 경로

    Returns:
        (처리된 대화 리스트, 통계 정보)
    """
    all_conversations = []
    stats = {
        "total_files": 0,
        "excluded_files": 0,
        "processed_files": 0,
        "total_conversations": 0,
        "by_platform": {},
    }

    data_path = Path(data_dir)

    # 모든 플랫폼 폴더 순회
    for platform_dir in sorted(data_path.iterdir()):
        if not platform_dir.is_dir():
            continue

        platform_name = platform_dir.name
        platform_stats = {"total": 0, "excluded": 0, "processed": 0, "conversations": 0}

        # JSON 파일 순회
        json_files = list(platform_dir.glob("*.json"))

        for json_file in json_files:
            stats["total_files"] += 1
            platform_stats["total"] += 1

            # 제외할 파일인지 확인
            if should_exclude_file(json_file.name):
                stats["excluded_files"] += 1
                platform_stats["excluded"] += 1
                continue

            # 대화 추출
            conversations = extract_conversation_from_file(json_file)

            stats["processed_files"] += 1
            platform_stats["processed"] += 1

            stats["total_conversations"] += len(conversations)
            platform_stats["conversations"] += len(conversations)

            all_conversations.extend(conversations)

        stats["by_platform"][platform_name] = platform_stats

    return all_conversations, stats


def save_processed_data(conversations: List[Dict], output_path: str) -> None:
    """
    처리된 대화 데이터를 JSON 파일로 저장합니다.
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w", encoding="utf-8") as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(conversations)} conversations to {output}")


def main():
    """메인 실행 함수"""
    # 현재 스크립트 위치 기준으로 경로 설정
    script_dir = Path(__file__).parent
    data_dir = script_dir / "data"
    output_path = script_dir / "processed" / "chat_data_cleaned_v2.json"

    print("=" * 60)
    print("채팅 데이터 전처리 시작")
    print("=" * 60)
    print(f"\n데이터 디렉토리: {data_dir}")
    print(f"출력 파일: {output_path}")
    print(f"\n제외할 카테고리: {sorted(EXCLUDED_CATEGORIES)}")
    print()

    # 데이터 처리
    conversations, stats = process_all_data(str(data_dir))

    # 통계 출력
    print("\n" + "=" * 60)
    print("처리 통계")
    print("=" * 60)
    print(f"총 파일 수: {stats['total_files']}")
    print(f"제외된 파일 수: {stats['excluded_files']}")
    print(f"처리된 파일 수: {stats['processed_files']}")
    print(f"총 대화 수: {stats['total_conversations']}")

    print("\n플랫폼별 통계:")
    for platform, pstats in stats["by_platform"].items():
        print(f"  {platform}:")
        print(f"    - 총 파일: {pstats['total']}")
        print(f"    - 제외됨: {pstats['excluded']}")
        print(f"    - 처리됨: {pstats['processed']}")
        print(f"    - 대화 수: {pstats['conversations']}")

    # 결과 저장
    if conversations:
        save_processed_data(conversations, str(output_path))
        print(f"\n처리 완료! {output_path}에 저장됨")
    else:
        print("\n처리된 대화가 없습니다.")


if __name__ == "__main__":
    main()
