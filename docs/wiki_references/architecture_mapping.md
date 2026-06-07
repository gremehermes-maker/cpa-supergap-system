# CPA 초격차 시스템 - 디렉토리와 원본 구조도(위키) 매핑 다이어그램

지휘관님께서 보시던 원본 **[시스템 구조도]**의 노드들이, 실제 우리가 작업할 **[소스 코드 폴더(디렉토리)]**와 어떻게 1:1로 정확하게 매칭되는지 시각화한 다이어그램입니다.

새로 매긴 목차가 아니라, **원본 위키의 번호 체계(1.0 ~ 7.0)를 소스 코드 폴더명에 그대로 박아넣은 것**입니다. 이를 통해 코드만 봐도 시스템 구조도의 어느 부분인지 즉각적으로 알 수 있습니다.

```mermaid
graph TD
    %% [1.0] 교재 및 자료 입력단 (Input Sources)
    subgraph 1.0_Inputs [1.0 학습 소스 입력단]
        1.1("1.1 기본서 PDF<br/>(1.1_pdf_toc_extractor.py)") -- "TR_1.1_to_1.4\n(TOC 추출)" --> 1.4("1.4 TOC-URL 매핑 DB<br/>(1.4_toc_url_mapper.py)")
        1.2("1.2 1차 문제집<br/>(1.2_mcq_slicer.py)") -- "TR_1.2_to_2.1\n(문항 슬라이싱)" --> 2.1
        1.3("1.3 2차 연습서<br/>(1.3_essay_slicer.py)") -- "TR_1.3_to_2.1\n(물음 분할)" --> 2.1
    end

    %% [2.0] MarginNote 4
    subgraph 2.0_MarginNote [2.0 MarginNote 4 엔진]
        2.1("2.1 마인드맵 & 노드<br/>(2.1_mindmap_node.py)")
        2.2("2.2 ZCOLOR 색상 트리거<br/>(2.2_zcolor_trigger.py)")
        2.3("2.3 ZGROUPNOTEID 위계<br/>(2.3_zgroup_hierarchy.py)")
        2.4("2.4 marginnote4app:// 고유 URL<br/>(2.4_marginnote_url.py)")
        
        1.4 -- "TR_1.4_to_2.1\n(뼈대 역삽입)" --> 2.1
        2.1 --- 2.2
        2.1 --- 2.3
        2.1 --- 2.4
    end

    %% [3.0] 파이프라인
    subgraph 3.0_Pipeline [3.0 백그라운드 파이프라인]
        3.1("3.1 스키마 무결성 검사<br/>(3.1_schema_checker.py)")
        3.2("3.2 이미지 최적화 / Webp<br/>(3.2_image_optimizer.py)")
        3.3("3.3 데이터 분배 엔진<br/>(3.3_data_router.py)")
        
        2.2 -- "TR_2.X_to_3.1\n(DB 후킹)" --> 3.1
        2.3 -- "TR_2.X_to_3.1\n(DB 후킹)" --> 3.1
        3.1 --> 3.2 --> 3.3
    end

    %% [4.0] 지식베이스
    subgraph 4.0_Knowledge [4.0 마크다운 지식베이스]
        4.1("4.1 Logseq (2차 아웃라이너)<br/>(4.1_logseq_outliner.py)")
        4.2("4.2 Obsidian (LLM Wiki)<br/>(4.2_obsidian_wiki.py)")
        
        3.3 -- "TR_3.3_to_4.1\n(Logseq 푸시)" --> 4.1
        3.3 -- "TR_3.3_to_4.2\n(Obsidian 푸시)" --> 4.2
    end

    %% [5.0] Anki
    subgraph 5.0_Anki [5.0 Anki 스케줄러]
        5.1("5.1 FSRS 스케줄러 알고리즘<br/>(5.1_fsrs_algorithm.py)")
        5.2("5.2 ZNOTEID 중복 방지<br/>(5.2_znoteid_dedup.py)")
        5.3("5.3 Daily Mini Deck 추출<br/>(5.3_daily_mini_deck.py)")
        
        3.3 -- "TR_3.3_to_5.1\n(카드 생성)" --> 5.1
        5.1 --- 5.2
        5.1 --> 5.3
    end

    %% [6.0 & 7.0] 모바일 및 에이전트
    subgraph 6.0_7.0_Agents [6.0 모바일 & 7.0 에이전트]
        6.1("6.1 모바일 Anki 뷰어<br/>(6.1_mobile_anki.py)")
        6.2("6.2 Slack/Telegram Inbox<br/>(6.2_telegram_inbox.py)")
        7.1("7.1 스케줄러 & Inbox 봇<br/>(7.1_scheduler_bot.py)")
        7.2("7.2 Tutor 봇 : Claude 3.5<br/>(7.2_tutor_bot.py)")
        7.3("7.3 Checker 봇 : Qwen/Gemini<br/>(7.3_checker_bot.py)")
        7.4("7.4 URL 매핑 연결 봇<br/>(7.4_url_linker_bot.py)")
        
        5.3 -- "TR_5.3_to_6.1\n(덱 푸시)" --> 6.1
        6.1 -.-> 6.2
        6.2 -- "TR_6.2_to_7.1\n(메시지 수신)" --> 7.1
        
        4.2 -. "TR_4.2_to_7.2\n(지식 검색)" .-> 7.2
        7.2 <--"TR_7.2_to_7.3\n(교차 검증)"--> 7.3
        7.4 -. "TOC_Mapping.json 참조" .-> 1.4
    end
```

## 🛠️ 최고 사령관 전용 커뮤니케이션 가이드

본 매핑 룰은 Google Drive에 동기화되어 있으며, 어떠한 환경(OS)에서도 에이전트들은 이 문서를 SSOT(Single Source of Truth)로 삼습니다.

지휘관님께서는 작업 시 **"명령어 + 번호"** 조합으로 지시하십시오.

**[예시]**
- *"1.4에 URL 매핑하는 정규식 추가해"* 👉 `src/1.0_input_sources/1.4_toc_url_mapper.py` 수정
- *"3.2 이미지 최적화 Webp 화질을 80%로 낮춰"* 👉 `src/3.0_data_pipeline/3.2_image_optimizer.py` 수정
- *"7.2 프롬프트를 수정해서 회계학 답변 퀄리티를 올려"* 👉 `src/7.0_hermes_agents/7.2_tutor_bot.py` 수정

이처럼 숫자만으로 시스템 100%를 장악하실 수 있습니다.
