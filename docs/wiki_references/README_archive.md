# CPA Super-gap System (초격차 학습 자동화 시스템)

이 프로젝트는 CPA 수험생을 위한 **초격차 학습 자동화 시스템**의 단일 저장소(Monorepo)입니다.
Windows와 Mac 환경 모두에서 인간 지휘관(Commander)과 여러 AI 에이전트들이 원활하게 협업할 수 있도록 구성되었습니다.

---

## 🧭 에이전트 필수 숙지 가이드 (Agent Context)

> **⚠️ 어떤 환경(Windows/Mac)에서 깨어난 에이전트이든, 코드를 수정하기 전에 이 섹션을 완벽히 숙지해야 합니다.**

이 프로젝트는 지휘관의 "숫자 지시"에 따라 1:1로 매칭되는 파일 시스템 아키텍처를 가지고 있습니다.
지휘관이 **"3.2 작업해"** 라고 지시하면, 에이전트는 무조건 `src/3.0_data_pipeline/3.2_image_optimizer.py` 파일을 열어 작업해야 합니다.

### 📌 [1.0 ~ 8.0] 시스템 아키텍처 다이어그램 및 소스 코드 매핑

아래 다이어그램은 각 기능의 **"기존 한글 명칭"**과 **"실제 개발되는 파이썬 파일명"**을 함께 매핑한 최종 구조도입니다. 프로젝트 루트의 `CPA_최종_시스템_구조도_V3.html`을 브라우저에서 열면 더 크게 볼 수 있습니다.

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

👉 **에이전트 행동 지침**: 시스템 구조와 배경 지식에 대해 의문이 생기면 즉시 `docs/wiki_references/AI_REFERENCE_WIKI.md` 문서를 열어 과거 마스터플랜과 한계점 극복 로그를 읽어라.

---

## 🚀 빠른 시작 가이드 (Windows 환경 우선)

지휘관 및 팀원들이 시스템을 실행하고 테스트할 수 있도록 돕는 매뉴얼입니다.

### 1. 사전 준비 (Prerequisites)
- **Python 3.10 이상** 설치 (설치 시 `Add Python to PATH` 체크 필수)
- **Git** 설치 (버전 관리용)

### 2. 프로젝트 세팅
1. 명령 프롬프트(CMD)나 PowerShell을 열고 프로젝트 폴더로 이동합니다.
   ```cmd
   cd C:\경로\CPA_Supergap_System
   ```
2. 필요한 파이썬 라이브러리를 설치합니다.
   ```cmd
   pip install -r requirements.txt
   ```

### 3. 환경 설정 (config.yaml)
`config/config.yaml` 파일을 열고, Windows 환경에 맞는 경로(`windows:` 하위)를 본인의 PC 환경에 맞게 수정합니다.
- `pdf_input_dir`: PDF 파일들이 모여있는 폴더 경로
- `output_dir`: 추출된 결과물(OPML 등)이 저장될 폴더 경로

### 4. 모듈 실행 테스트 (예: 1.1 TOC 추출기)
가장 처음 구동해볼 수 있는 파이프라인은 [1.1] 모듈입니다.
```cmd
python src/1.0_input_sources/1.1_pdf_toc_extractor.py
```
