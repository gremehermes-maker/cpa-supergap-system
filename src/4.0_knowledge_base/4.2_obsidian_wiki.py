"""
4.2_obsidian_wiki.py — Obsidian 볼트 푸셔
==========================================
MarginNote 파서가 추출한 노드 데이터를
Obsidian 볼트 폴더 안에 .md 파일로 생성합니다.

[파일 저장 구조]
vault_path/
  MarginNote/
    {스터디셋_제목}/
      {ZNOTEID}.md    ← 각 노드 하나 = 파일 하나

[.md 파일 구조]
---
(YAML 프론트매터: MarginNote의 모든 메타데이터)
---

(본문: 제목 + 텍스트)

[핵심 설계 원칙]
- ZNOTEID를 파일명으로 사용 → 제목 변경 시에도 안정적
- 기존 파일이 있으면 프론트매터만 업데이트하고 본문은 보존
- weakness_score는 초기 0으로 설정 (Anki lapses 연동 시 자동 증가)
"""

import os
import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Optional

# ============================================================
# Obsidian 볼트 내 MarginNote 전용 서브폴더 이름
# ============================================================
MN_SUBFOLDER = "MarginNote"


def sanitize_filename(name: str) -> str:
    """
    파일명으로 사용할 수 없는 특수문자를 제거합니다.
    Windows 파일시스템에서 금지된 문자: \\ / : * ? " < > |
    """
    # 금지 문자 → 언더스코어 치환
    sanitized = re.sub(r'[\\/:*?"<>|]', '_', name)
    # 앞뒤 공백 및 점 제거
    sanitized = sanitized.strip('. ')
    return sanitized or "unnamed"


def build_frontmatter(node: dict, topic_title: str, topic_id: str) -> str:
    """
    MarginNote 노드 데이터로 YAML 프론트매터 블록을 생성합니다.

    매개변수:
        node        : 2.1_mn_parser.py가 반환한 노드 딕셔너리
        topic_title : 소속 스터디셋 제목 (예: 'Chapter_01_목차주입본 #1')
        topic_id    : 소속 스터디셋 UUID

    반환값:
        YAML 프론트매터 문자열 (--- 블록 포함)
    """
    # linked_ids를 YAML 리스트 형태로 변환
    linked_ids_yaml = ""
    if node['linked_ids']:
        linked_ids_yaml = "\n" + "\n".join(f"  - \"{uid}\"" for uid in node['linked_ids'])
    else:
        linked_ids_yaml = " []"

    media_ids_yaml = ""
    if node['media_ids']:
        media_ids_yaml = "\n" + "\n".join(f"  - \"{m}\"" for m in node['media_ids'])
    else:
        media_ids_yaml = " []"

    # 현재 날짜
    today = datetime.now().strftime("%Y-%m-%d")

    # 부모 노드 ID (None이면 "null")
    parent_id_str = f'"{node["parent_id"]}"' if node["parent_id"] else "null"

    frontmatter = f"""---
# =====================================================
# MarginNote 메타데이터 (자동 생성 - 수동 편집 금지)
# =====================================================
note_id: "{node['note_id']}"
title: "{node['title'].replace('"', "'")}"
topic_id: "{topic_id}"
topic_title: "{topic_title}"

# 계층 관계
parent_id: {parent_id_str}
linked_ids:{linked_ids_yaml}

# 카드 포맷 타입 (ZHIGHLIGHT_STYLE에서 매핑)
# basic | cloze | highlight | mindmap_node
card_type: "{node['card_type']}"
raw_style: "{node['raw_style'] or ''}"
node_type: "{node['node_type']}"

# PDF 위치 정보
start_page: {node['start_page'] or 'null'}
end_page: {node['end_page'] or 'null'}

# 미디어 첨부
media_ids:{media_ids_yaml}

# =====================================================
# Anki/Hermes 연동 데이터 (자동 업데이트)
# =====================================================
weakness_score: 0
anki_lapses: 0
anki_note_id: null

# 생성/수정 일자
created_at: "{today}"
updated_at: "{today}"
---"""

    return frontmatter


def push_node_to_obsidian(
    node: dict,
    vault_path: str,
    topic_title: str,
    topic_id: str,
    overwrite: bool = False
) -> str:
    """
    단일 노드를 Obsidian 볼트의 .md 파일로 저장합니다.

    [저장 경로]
    vault_path/MarginNote/{topic_title}/{note_id}.md

    매개변수:
        node        : 파서가 반환한 노드 딕셔너리
        vault_path  : Obsidian 볼트 루트 폴더 경로
        topic_title : 스터디셋 제목
        topic_id    : 스터디셋 UUID
        overwrite   : True이면 기존 파일 덮어쓰기

    반환값:
        생성된 .md 파일 경로
    """
    # 저장 폴더 경로 결정
    safe_topic = sanitize_filename(topic_title)
    target_dir = Path(vault_path) / MN_SUBFOLDER / safe_topic
    target_dir.mkdir(parents=True, exist_ok=True)

    # 파일명 = ZNOTEID.md (UUID 기반 → 안정적)
    md_filename = f"{node['note_id']}.md"
    md_path = target_dir / md_filename

    # 이미 파일이 존재하고 overwrite=False이면 프론트매터만 갱신
    if md_path.exists() and not overwrite:
        existing_content = md_path.read_text(encoding='utf-8')
        # 기존 본문(--- 블록 이후) 보존
        parts = existing_content.split('---', 2)
        if len(parts) >= 3:
            body_content = parts[2]
        else:
            body_content = existing_content
        new_frontmatter = build_frontmatter(node, topic_title, topic_id)
        final_content = new_frontmatter + "\n" + body_content
    else:
        # 새 파일 생성
        frontmatter = build_frontmatter(node, topic_title, topic_id)

        # 본문 구성:
        # 1. 마인드맵 제목 (H1)
        # 2. 하이라이트 원문 (인용)
        # 3. 노트 텍스트
        body_parts = []

        if node['title']:
            body_parts.append(f"# {node['title']}\n")

        if node['highlight_text']:
            body_parts.append(f"> {node['highlight_text']}\n")

        if node['text']:
            body_parts.append(f"\n{node['text']}\n")

        # 연결된 카드 위키링크 (Obsidian [[링크]])
        if node['linked_ids']:
            body_parts.append("\n## 연결된 카드\n")
            for uid in node['linked_ids']:
                body_parts.append(f"- [[{uid}]]\n")

        body = "\n".join(body_parts) if body_parts else "(내용 없음)\n"
        final_content = frontmatter + "\n\n" + body

    # 파일 저장
    md_path.write_text(final_content, encoding='utf-8')
    return str(md_path)


def push_all_nodes(
    nodes: list[dict],
    topics: dict,
    vault_path: str,
    overwrite: bool = False
) -> dict:
    """
    모든 노드를 Obsidian 볼트에 .md 파일로 저장합니다.

    매개변수:
        nodes       : 파서가 반환한 전체 노드 리스트
        topics      : get_topic_info() 반환값
                      {topic_id: {"title": ..., "pdf_md5": ...}}
        vault_path  : Obsidian 볼트 루트 폴더 경로
        overwrite   : 기존 파일 덮어쓰기 여부

    반환값:
        {
            "success": 성공한 파일 목록,
            "failed": 실패한 노드 ID 목록,
            "total": 전체 수,
        }
    """
    success = []
    failed = []

    print(f"\n[Obsidian 푸시] 볼트 경로: {vault_path}")
    print(f"[Obsidian 푸시] 총 {len(nodes)}개 노드 처리 시작...")

    for i, node in enumerate(nodes):
        try:
            # 소속 스터디셋 정보 조회
            topic_id = node['topic_id'] or ''
            topic_info = topics.get(topic_id, {})
            topic_title = topic_info.get('title', 'Unknown_Topic')

            # .md 파일 생성
            md_path = push_node_to_obsidian(
                node=node,
                vault_path=vault_path,
                topic_title=topic_title,
                topic_id=topic_id,
                overwrite=overwrite,
            )

            success.append(md_path)
            print(f"  [{i+1}/{len(nodes)}] ✅ {node['title'][:40] or '(제목없음)'}")

        except Exception as e:
            failed.append(node['note_id'])
            print(f"  [{i+1}/{len(nodes)}] ❌ {node['note_id']}: {e}")

    result = {
        "success": success,
        "failed": failed,
        "total": len(nodes),
    }

    print(f"\n[Obsidian 푸시] 완료: 성공 {len(success)}개 / 실패 {len(failed)}개")
    return result


# ============================================================
# 단독 실행 테스트
# ============================================================
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.path.insert(0, str(Path(__file__).parent.parent / '2.0_marginnote_engine'))

    # 파서 임포트
    import importlib.util
    parser_path = Path(__file__).parent.parent / '2.0_marginnote_engine' / '2.1_mn_parser.py'
    spec = importlib.util.spec_from_file_location("mn_parser", parser_path)
    mn_parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mn_parser)

    # G 드라이브에서 .marginpkg 탐색
    base = 'G:\\'
    items = os.listdir(base)
    inner_drive = os.path.join(base, items[0])

    pkg_path = None
    vault_path = None
    for s in os.listdir(inner_drive):
        folder = os.path.join(inner_drive, s)
        if os.path.isdir(folder):
            found = mn_parser.find_marginpkg(folder)
            if found:
                pkg_path = found
                vault_path = folder
                break

    if not pkg_path:
        print("ERROR: .marginpkg 파일을 찾을 수 없습니다.")
        sys.exit(1)

    print(f"[테스트] 패키지: {pkg_path}")
    print(f"[테스트] 볼트: {vault_path}")

    # 언패킹 및 파싱
    tmp_dir, db_path = mn_parser.unpack_marginpkg(pkg_path)
    nodes = mn_parser.parse_all_nodes(db_path)
    topics = mn_parser.get_topic_info(db_path)

    # Obsidian으로 푸시
    result = push_all_nodes(
        nodes=nodes,
        topics=topics,
        vault_path=vault_path,
        overwrite=True,  # 테스트: 항상 덮어쓰기
    )

    # 정리
    mn_parser.cleanup_temp(tmp_dir)

    print(f"\n[테스트 완료]")
    print(f"  성공: {len(result['success'])}개")
    print(f"  실패: {len(result['failed'])}개")
    if result['success']:
        print(f"  첫 번째 파일: {result['success'][0]}")
