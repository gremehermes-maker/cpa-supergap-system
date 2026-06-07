# CPA 학습 자동화 시스템 — 궁극의 통합 마스터플랜 (The Ultimate Master Plan)

> **💡 [통합 가이드]**
> 본 문서는 기존의 마스터플랜 뼈대(Phase 0~4)와 최신 AI 자율 에이전트 확장팩(Phase 5~6), 그리고 이를 실제 코딩으로 구현하기 위한 **초정밀 마이크로 실행 계획(Micro-Execution Plan)**을 하나로 집대성한 최종본입니다. 단 하나의 내용 유실도 없이 모든 전략과 코딩 스크립트 단위의 작업 지시가 포함되어 있습니다.

---

## 🔗 [Reference] 시스템 세부 연동 매뉴얼
아래 문서들은 본 마스터플랜의 구체적인 하위 규정집입니다. 필요시 함께 참조하십시오.
* **[CPA_카드생성규칙_매뉴얼](file:///Users/na/Desktop/CPA_카드생성규칙_매뉴얼.md)**: `주의:`, `절차:` 등 트리거를 Anki 카드로 변환하는 상세 규칙
* **[CPA_통합_시스템_매뉴얼_v2](file:///Users/na/Desktop/CPA_통합_시스템_매뉴얼_v2.md)**
* **[CPA_카드_매뉴얼](file:///Users/na/Desktop/CPA_카드_매뉴얼.md)**
* **[CPA_시스템_한계점_및_개선안_최종본](file:///Users/na/Desktop/CPA_시스템_한계점_및_개선안_최종본.md)**: 예상 가능한 구조적 취약점 및 헤르메스 에이전트/TOC 자동 매핑 기반의 궁극적 해결책

---

## 1. 코어 아키텍처 및 데이터 파이프라인 (The Circular Workflow)

데이터는 '구조 뼈대 생성'부터 '약점 역추적'까지 완벽한 순환 고리(Loop)를 형성합니다.

```mermaid
graph TD
    A[기본서 TOC 및 문항 자르기 시스템] -->|아웃라이너 뼈대 OPML 생성| B[MarginNote 4 역삽입 Import]
    B -->|사용자 학습: 선 긋기로 오답 원인 연결| C[MarginNote SQLite DB]
    C -->|Python 1차 변환| D[Logseq & Obsidian 마크다운 Vault]
    D -->|Python 2차 변환| E[Anki 자동 복습기]
    E -->|오답(Lapse) 통계 발생| F[Obsidian 대시보드 랭킹 산출]
    F -->|약점 역추적 피드백| E
```

### 각 시스템의 구체적 역할 분담
| 시스템 | 역할 (기능) | 상세 설명 |
|--------|-----------|---------|
| **MarginNote4** | 창고 & 입력단 | 잘려진 문제 뼈대 위에서 학습. 마우스 시각적 선 긋기로 약점 원인 개념을 연결. |
| **Logseq** | 카드 통제실 | 다중 위계(공통자료 -> 물음)를 완벽히 통제. |
| **Obsidian** | 메타인지 대시보드 | Anki 오답 통계와 마진노트 연결망을 취합해 약점 랭킹 제공. |
| **Anki** | 자동 복습기 | 망각곡선 제어 및 약점 역추적 복습 큐 제공. |

---

## 2. Phase 별 시스템 개념 설계 (Conceptual Design)

### [Phase 0] 교재 3대 아키텍처 자동화 및 TOC 역삽입
1. **기본서**: 문항이 아닌 '목차(TOC)' 그 자체를 파싱하여 기본 개념 아웃라이너 트리를 구축합니다.
2. **1차/2차 문제집**: 페이지 통째가 아니라 객관식은 [문제]+[해설], 2차 연습서는 [공통자료]+[물음1]+[해설1] 단위로 정밀하게 분리하여 자릅니다.
3. **역삽입**: 마진노트와 Logseq에 Import 하여 완벽한 빈 마인드맵 트리를 펼칩니다.

### [Phase 1~2] 사용자 학습 및 단일 진실 공급원(Markdown) 구축
1. **학습 및 선긋기**: 잘려진 목차 위에서 `주의:` 등의 트리거로 타이핑하고, 연습서를 틀렸을 때 원인 개념 노드와 점선으로 연결합니다.
2. **마크다운 변환 엔진**: 마진노트 DB를 뜯어내어 뼈대를 보존한 채 마크다운으로 변환합니다. 선형 연결 데이터를 파일 프론트매터에 `원인개념: [[자산손상]]`으로 기록합니다.

### [Phase 3~4] Anki 딥링크 적용 및 궁극의 약점 역추적 시스템
1. **미니멀리즘 딥링크**: 카드 뒷면에 `[ M ]`, `[ L ]`, `[ O ]` 아이콘 버튼을 삽입해 전체 맥락으로 순간이동합니다.
2. **통합 대시보드 랭킹**: Anki 오답 횟수와 MarginNote 선 긋기 원인을 결합해 취약도 랭킹을 산출합니다.
3. **Drill-Down 복습 큐**: 2차 문제에서 털리면 다음날 안키에서 해당 개념의 '기본서 개념 카드'와 '1차 객관식 문제'를 모조리 긁어모아 강제 복습시킵니다.

### [Phase 5] 카파시(Karpathy) LLM OS 및 구글 스페이스 에이전트 확장
1. **최상위 비서 에이전트 (Chief Secretary)**: 구글 스페이스(Calendar/Tasks)와 연동되어 사용자의 공부 외적인 일상을 통제합니다. 캘린더에 "저녁 회식"이 있으면 하위 스케줄러 에이전트에게 지시해 안키 복습을 내일로 자동 연기시킵니다.
2. **LLM OS 메모리 아키텍처 (Memory Editor)**: 1만 토큰의 긴 대화를 매번 읽히지 않습니다. 전담 에이전트가 세션 종료 시 대화의 정수만 뽑아 하드디스크(`LLM_Wiki/User_State.md`)에 단 한 줄로 기록합니다. (예: "사용자는 현재 리스회계 보증잔존가치 파트에 취약함.") 튜터는 이 한 줄(RAM)만 읽고 소통합니다.
3. **특화 에이전트 팀 구성**: Tutor(RAG+검색), Scheduler(행동조정), Checker(환각방지) 에이전트들이 Slack을 통해 소통하고 상호 검증합니다.

### [Phase 6] 무제한 스냅샷 백업 프로토콜
- 5TB 구글 드라이브 용량을 바탕으로, 에이전트가 파일을 수정하기 전 무조건 모든 마크다운과 DB를 `YYYYMMDD_HHMMSS.zip`으로 묶어 무한정 보존하여 절대적인 복구력을 확보합니다.

---

## 3. 초정밀 실행 계획 (Micro-Execution Plan)
*위의 개념 설계(Phase 0~6)를 실제로 코딩하기 위한 가장 작은 단위의 스크립트 개발 목록입니다.*

### [Phase 0] 교재 분해 파이프라인
*   **Task 0.1 [PDF Parser]:** 기본서 PDF 북마크 추출 및 JSON 파싱 스크립트.
*   **Task 0.2 [1차 문제 Slicer]:** 객관식 문제집 (문제+해설) 크롭 스크립트.
*   **Task 0.3 [2차 문제 Slicer]:** 연습서 위계(공통자료->물음->해설) 기반 정밀 크롭 알고리즘.
*   **Task 0.4 [OPML Generator]:** 마진노트/Logseq Import용 뼈대 파일 생성.

### [Phase 1~2] 마진노트 DB 추출 및 마크다운 엔진
*   **Task 1.1 [SQLite Connector]:** 마진노트 로컬 DB 읽기 권한 연결.
*   **Task 1.2 [Node Extractor]:** 텍스트 및 하이라이트 추출.
*   **Task 1.3 [Link Parser]:** 오답 원인 '선 긋기(연결선)' 데이터 추출 및 매핑.
*   **Task 1.4 [MD Writer]:** 추출 데이터를 프론트매터가 포함된 마크다운으로 변환.
*   **Task 1.5 [Media Exporter]:** 크롭된 이미지 파일을 Obsidian Vault로 물리적 복사.

### [Phase 3] Anki 동기화 및 딥링크 브릿지
*   **Task 3.1 [Trigger Parser]:** 마크다운 내 카드 생성 규칙 정규표현식 파싱.
*   **Task 3.2 [AnkiConnect API 모듈]:** 안키 로컬 서버와 통신하는 API 클라이언트.
*   **Task 3.3 [HTML DeepLink Builder]:** 카드 뒷면에 앱 간 이동 딥링크 주입.
*   **Task 3.4 [Sync Controller]:** 변경된 노트만 골라서 동기화하는 로직.

### [Phase 4] RAG 기반 강의 텍스트 파이프라인
*   **Task 4.1 [Transcript Watcher]:** 새로운 `.srt` / `.txt` 파일 감지.
*   **Task 4.2 [Chunking & Cleaning]:** 소형 LLM(GPT-4o-mini 등)으로 회계 전문 용어 오탈자를 1차 자동 교정하고, LangChain의 `SemanticChunker`를 사용해 의미가 바뀌는 문맥 단위로 쪼개기.
*   **Task 4.3 [Vector DB Ingestion]:** 교정/청킹된 텍스트를 로컬 ChromaDB에 적재.

### [Phase 5] LLM OS 및 구글 스페이스 통합 에이전트
*   **Task 5.1 [Agent Docker Compose & Chief Secretary]:** 최상위 구글 캘린더 비서 에이전트와 하위 4개 에이전트를 묶어서 실행하는 `docker-compose.yml` 세팅.
*   **Task 5.2 [Slack Bot Integration]:** 에이전트간 Slack 채널 통신망 구축.
*   **Task 5.3 [Memory Editor (RAM -> Disk)]:** 세션 종료 시 Slack 대화 기록을 파싱하고 핵심만 요약하여 `LLM_Wiki/User_State.md` 파일에 기록하는 전담 스크립트.
*   **Task 5.4 [Tutor Agent (RAG+Web)]:** Vector DB 검색 및 답변 생성 로직.
*   **Task 5.5 [Checker Agent (Cross-Validation)]:** 환각 방지 프롬프트 체인.
*   **Task 5.6 [Scheduler Agent (Action)]:** Anki/Obsidian 듀데이트 수정 및 승인 UI.

### [Phase 6] 무제한 스냅샷 백업 시스템
*   **Task 6.1 [Zip Archiver]:** 폴더 전체 초고속 압축 스크립트.
*   **Task 6.2 [G-Drive Sync & Pre-hook]:** 에이전트 작업 전 무조건 백업 실행 보장 로직.
