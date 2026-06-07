# Phase 0 완료 매뉴얼 — 도구 설치 + 파이프라인 검증

> 작성일: 2026-06-06
> 상태: ✅ 완료

---

## 1. 설치된 도구

| 도구 | 버전 | 설치 방법 | 경로 |
|------|------|----------|------|
| Anki | 25.09 | `brew install --cask anki` | `/Applications/Anki.app` |
| AnkiConnect 플러그인 | 최신 | GitHub에서 직접 다운로드 | `~/Library/Application Support/Anki2/addons21/2055492159/` |
| Obsidian | 1.12.7 | `brew install --cask obsidian` | `/Applications/Obsidian.app` |
| MarginNote Sync 플러그인 | 1.0.0 | GitHub Cheendfdf/marginnote-obsidian-sync | Obsidian vault 내 |
| MarginNote 4 | 기존 설치 | App Store | `/Applications/MarginNote 4.app` |

---

## 2. 주요 경로

```
MarginNote4 DB (자동 저장 위치):
  ~/Library/Containers/QReader.MarginStudy.easy/
    Data/Library/Private Documents/
      MN4NotebookDatabase/0/MarginNotes.sqlite

Anki 데이터:
  ~/Library/Application Support/Anki2/사용자 1/

AnkiConnect 플러그인:
  ~/Library/Application Support/Anki2/addons21/2055492159/

Obsidian Vault:
  ~/Documents/CPA_StudyBase/

AnkiConnect 설정:
  포트: 8765
  바인딩: 127.0.0.1
```

---

## 3. 파이프라인 구조

```
MarginNote4
  │  (내보내기: 스터디셋 백업 .marginpkg)
  ▼
.marginpkg 파일 (ZIP 형식)
  │  (unzip → .marginnotes 파일 = SQLite DB)
  ▼
Python 스크립트가 SQLite 읽기
  │
  ├── ZBOOKNOTE 테이블 → 노드 제목, PDF 발췌, ZMINDLINKS (계층 구조 추적)
  ├── ZBOOKCOMMENT 테이블 → 트리거 코멘트 파싱
  │     ├── 주의: → ⚠ 함정 카드 (+ 맥락 경로)
  │     ├── 절차: → 📋 절차 카드 (+ 맥락 경로)
  │     ├── 강사: → 🎤 강사 보충 카드 (+ 맥락 경로)
  │     ├── 공식: → 공식 카드
  │     ├── 분개: → 분개 카드
  │     ├── 오답: → 오답 분석 카드
  │     ├── 빈출  → 태그만 추가
  │     ├── 가림: → Image Occlusion
  │     └── 연결: → 다중 목차 태그
  ▼
AnkiConnect API (http://localhost:8765)
  │
  ▼
Anki 카드 자동 생성 (각 카드의 앞면에 `단원 > 파트 > 세부항목` 형태의 위치 맥락 포함)
  │  (AnkiWeb 동기화)
  ▼
Galaxy AnkiDroid 복습
```

---

## 4. DB 구조 (MarginNote4)

### ZBOOKNOTE (노드)

| 컬럼 | 내용 |
|------|------|
| `ZNOTEID` | 노드 고유 ID (UUID) |
| `ZNOTETITLE` | 노드 제목 |
| `ZHIGHLIGHT_TEXT` | PDF 발췌 텍스트 |
| `ZGROUPNOTEID` | 부모 노드 ID (계층 구조) |
| `ZTOPICID` | 소속 노트북 ID |
| `ZTYPE` | 노드 타입 (7=일반, 256=마인드맵, 3=그룹, 4=기타) |
| `ZZINDEX` | 정렬 순서 |
| `ZMINDLINKS` | 자식 노드들의 ID 리스트 (`|`로 구분). 계층 구조의 '부모-자식' 관계 추적에 사용됨. |
| `ZNOTES_TEXT` | 노트 텍스트 |
| `ZNOTES` | 노트 (blob) |

### ZBOOKCOMMENT (코멘트)

| 컬럼 | 내용 |
|------|------|
| `ZCOMMENTID` | 코멘트 고유 ID |
| `ZCOMMENTTEXT` | **코멘트 텍스트 (트리거 파싱 대상)** |
| `ZMARKNOTEID` | 연결된 노드의 ZNOTEID |
| `ZTOPICID` | 소속 노트북 ID |
| `ZDATE` | 작성 시각 (Apple epoch) |

### ZTOPIC (노트북/스터디셋)

| 컬럼 | 내용 |
|------|------|
| `ZTOPICID` | 노트북 고유 ID |
| `ZTITLE` | 노트북 이름 |

---

## 5. 검증 결과 (Phase 0)

### 테스트 일시
2026-06-06 21:52 KST

### 테스트 내용
재무관리 스터디셋에 테스트 코멘트 3개를 DB에 직접 삽입 후 Anki 카드 생성

### 생성된 카드

| 트리거 | 맥락(경로) | 앞면 | 뒷면 |
|--------|------------|------|------|
| `주의:` | 📍 4 경제성평가 방법간 비교(2)... > 1. NPV 법과 PI 법의 평가 비교 | ⚠ 주의할 점은? | NPV와 PI의 결과가 상반되면 반드시 NPV를 우선한다. PI는 비율이므로 투자규모를 반영하지 못한다. |
| `절차:` | 📍 ... > 3. 상반되는 의사결정 해결 > 1) 증분현금흐름을 통해 통한 해결 | 📋 절차는? | 1. 두 투자안의 현금흐름 차이(증분) 계산 → 2. 증분현금흐름의 NPV 계산 → 3. 증분NPV > 0 → 큰 안 선택 → 4. 증분NPV < 0 → 작은 안 선택 |
| `강사:` | 📍 4 경제성평가 방법간 비교(2)... > 2. 평가결과가 상반될 수 있는 두 투자안 비교 | 🎤 강사 보충 설명 | 시험에서 NPV vs PI 상반 문제 나오면, 증분현금흐름으로 풀어도 NPV 기준 판단과 동일한 결과 |

### 결과
✅ 3장 모두 Anki `CPA::재무관리` 덱에 정상 생성

---

## 6. AnkiConnect 사용법 요약

### Anki 실행 확인
```bash
curl -s http://localhost:8765 -X POST -H "Content-Type: application/json" \
  -d '{"action":"version","version":6}'
# 정상 응답: {"result": 6, "error": null}
```

### 덱 생성
```python
anki("createDeck", deck="CPA::재무관리")
```

### 카드 추가
```python
anki("addNote", note={
    "deckName": "CPA::재무관리",
    "modelName": "Basic",
    "fields": {"Front": "앞면", "Back": "뒷면"},
    "tags": ["CPA::재무관리", "트리거::주의"]
})
```

---

## 7. 주의사항

- **Anki가 실행 중이어야** AnkiConnect가 작동함 (port 8765)
- **MarginNote4 DB 직접 수정은 위험** → 내보낸 .marginpkg 파일을 사용
- **.marginpkg = ZIP 파일** → unzip하면 .marginnotes (SQLite) + PDF 원본
- **AnkiWeb 계정** 필요 → Mac ↔ Galaxy 동기화용 (미설정 상태)

---

## 8. 다음 단계 (Phase 1)

- [ ] 1과목 1장 선택하여 수동 검증
- [ ] MarginNote4에서 실제 트리거 코멘트 작성 시작
- [ ] 전체 트리거 파싱 스크립트 완성
- [ ] AnkiWeb 계정 생성 + Galaxy 동기화
- [ ] SRS 스케줄링 설정 (유형별 학습 단계/최대 간격)
