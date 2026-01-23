# dating-sim-collector

```
dating-sim-collector/
├── assets/
│   └── images/            # 캐릭터 프로필 이미지 등 정적 파일
├── config/
│   ├── prompts.py         # [핵심] 시스템 프롬프트 (가스라이팅, 플러팅 등 시나리오)
│   └── settings.py        # 모델명, 가격 설정, 상수 관리
├── services/              # 백엔드 로직 (UI와 분리)
│   ├── 
      # Supabase 연결 및 CRUD 함수
│   └── llm_service.py     # OpenAI API 호출 및 응답 처리
├── views/                 # 화면 UI (페이지별 분리)
│   ├── intro_view.py      # 1단계: 동의서 및 닉네임 입력
│   ├── game_view.py       # 2단계: 3연속 채팅 게임
│   └── result_view.py     # 3단계: 최종 선택 및 분석 리포트
├── main.py                # [메인] 앱 실행 및 페이지 라우팅 (State 관리)
├── requirements.txt       # 의존성 패키지 목록
├── .env		   # [보안] API Key (OpenAI, Supabase) 관리
└── README.md
```
`chroma_service.py` 실행시키면 chomadb 생성
