"""
4.2_obsidian_wiki.py — Obsidian 볼트 푸셔 v2
=============================================
MarginNote 마인드맵의 위계 구조를 그대로 폴더/파일로 재현합니다.

[폴더 구조 예시]
vault_path/
  MarginNote/
    Chapter_01_목차주입본/
      1 재무관리의 이해/
        1 재무관리의 이해.md          ← 이 노드 자체의 프론트매터+본문
        1 기업과 시장/
          1 기업과 시장.md
          1. 기업의 다양한 활동/
            1. 기업의 다양한 활동.md
            (1) 조달(Financing).md     ← 자식이 없으면 파일만
            (2) 투자(Investment)/
              (2) 투자(Investment).md
              highlight_F5616A03.md    ← 하이라이트(이미지 포함)
            ...

[설계 원칙]
- 자식이 있는 노드 → 폴더 + 폴더 안에 자기 이름.md
- 자식이 없는 노드 → .md 파일만 (리프 노드)
- 파일명 = 마인드맵 제목 그대로 (UUID가 아님!)
- 이미지는 .md와 같은 폴더에 {md5}.png로 저장, 본문에서 임베드
- YAML 프론트매터에 모든 MarginNote 메타데이터 보존
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
    파일명/폴더명으로 사용할 수 없는 특수문자를 제거합니다.
    Windows 파일시스템 금지 문자: \\ / : * ? " < > |
    마침표로 끝나는 것도 방지합니다.
    """
    sanitized = re.sub(r'[\\/:*?"<>|]', '_', name)
    sanitized = sanitized.strip('. ')
    # 너무 긴 이름 제한 (Windows MAX_PATH 대비)
    if len(sanitized) > 80:
        sanitized = sanitized[:80]
    return sanitized or "unnamed"


def build_frontmatter(node: dict, topic_title: str, topic_id: str, depth: int) -> str:
    """
    노드 데이터로 YAML 프론트매터를 생성합니다.
    """
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

    today = datetime.now().strftime("%Y-%m-%d")
    parent_id_str = f'"{node["parent_id"]}"' if node["parent_id"] else "null"

    frontmatter = f"""---
# MarginNote 메타데이터 (자동 생성)
note_id: "{node['note_id']}"
title: "{node['title'].replace('"', "'")}"
topic_id: "{topic_id}"
topic_title: "{topic_title}"
depth: {depth}

# 계층 관계
parent_id: {parent_id_str}
linked_ids:{linked_ids_yaml}

# 카드 포맷
card_type: "{node['card_type']}"
raw_style: "{node['raw_style'] or ''}"
node_type: "{node['node_type']}"

# PDF 위치
start_page: {node['start_page'] or 'null'}
end_page: {node['end_page'] or 'null'}

# 미디어
media_ids:{media_ids_yaml}

# Anki 연동
weakness_score: 0
anki_lapses: 0
anki_note_id: null
created_at: "{today}"
updated_at: "{today}"
---"""
    return frontmatter


def build_body(node: dict, image_filenames: list[str]) -> str:
    """
    노드의 본문(프론트매터 아래)을 구성합니다.
    """
    parts = []

    # 제목이 있으면 H1
    if node['title']:
        parts.append(f"# {node['title']}\n")

    # PDF 하이라이트 원문 (인용)
    if node['highlight_text']:
        parts.append(f"> {node['highlight_text']}\n")

    # 노트 텍스트
    if node['text']:
        parts.append(f"\n{node['text']}\n")

    # 이미지 임베드 (같은 폴더의 이미지 파일)
    for img_name in image_filenames:
        parts.append(f"\n![[{img_name}]]\n")

    # 자식 노드 위키링크 (Obsidian [[링크]])
    if node.get('child_ids'):
        child_links = []
        for cid in node['child_ids']:
            child_links.append(f"- [[{cid}]]")
        if child_links:
            parts.append("\n## 하위 노드\n")
            parts.extend(child_links)

    return "\n".join(parts) if parts else "(내용 없음)\n"


def push_node_recursive(
    node: dict,
    node_map: dict,
    parent_dir: Path,
    topic_title: str,
    topic_id: str,
    media_map: dict,
    depth: int,
    results: dict,
):
    """
    단일 노드를 재귀적으로 폴더/파일 구조로 저장합니다.

    [규칙]
    - 자식이 있는 노드 → 폴더 생성 + 폴더 내에 {제목}.md 생성
    - 자식이 없는 노드 → parent_dir 안에 {제목}.md 파일만 생성
    - 제목이 없는 하이라이트 → highlight_{note_id 앞8자}.md
    """
    title = node['title']
    has_children = bool(node.get('child_ids'))

    # 파일/폴더명 결정
    if title:
        safe_name = sanitize_filename(title)
    else:
        # 제목 없는 노드 (하이라이트 등)
        short_id = node['note_id'][:8]
        safe_name = f"highlight_{short_id}"

    # 이 노드에 연결된 이미지 추출 & 저장
    image_filenames = []
    if node['media_ids']:
        for media_ref in node['media_ids']:
            # media_ref 형태: "md5_1-md5_2-..." (여러 MD5 연결)
            md5_parts = [p.strip() for p in media_ref.split('-') if p.strip()]
            for md5 in md5_parts:
                if md5 in media_map:
                    info = media_map[md5]
                    if info['format'] in ('PNG', 'JPEG'):
                        img_filename = f"{md5}{info['ext']}"
                        image_filenames.append(img_filename)

    if has_children:
        # ── 자식이 있는 노드: 폴더 생성 ──
        node_dir = parent_dir / safe_name
        node_dir.mkdir(parents=True, exist_ok=True)

        # 폴더 안에 자기 자신의 .md 파일 생성
        md_path = node_dir / f"{safe_name}.md"

        # 이미지를 이 폴더에 저장
        for img_name in image_filenames:
            md5 = img_name.rsplit('.', 1)[0]
            if md5 in media_map:
                img_path = node_dir / img_name
                img_path.write_bytes(media_map[md5]['data'])

        # .md 파일 작성
        frontmatter = build_frontmatter(node, topic_title, topic_id, depth)
        body = build_body(node, image_filenames)
        md_path.write_text(frontmatter + "\n\n" + body, encoding='utf-8')
        results['success'].append(str(md_path))

        # 자식 노드들 재귀 처리
        for cid in node['child_ids']:
            if cid in node_map:
                push_node_recursive(
                    node=node_map[cid],
                    node_map=node_map,
                    parent_dir=node_dir,
                    topic_title=topic_title,
                    topic_id=topic_id,
                    media_map=media_map,
                    depth=depth + 1,
                    results=results,
                )
    else:
        # ── 리프 노드: 파일만 생성 ──
        md_path = parent_dir / f"{safe_name}.md"

        # 이미지를 부모 폴더에 저장
        for img_name in image_filenames:
            md5 = img_name.rsplit('.', 1)[0]
            if md5 in media_map:
                img_path = parent_dir / img_name
                img_path.write_bytes(media_map[md5]['data'])

        frontmatter = build_frontmatter(node, topic_title, topic_id, depth)
        body = build_body(node, image_filenames)
        md_path.write_text(frontmatter + "\n\n" + body, encoding='utf-8')
        results['success'].append(str(md_path))


def push_all_nodes(
    nodes: list[dict],
    topics: dict,
    vault_path: str,
    media_map: dict = None,
    overwrite: bool = False,
) -> dict:
    """
    모든 노드를 위계 구조 그대로 Obsidian 볼트에 폴더/파일로 저장합니다.

    매개변수:
        nodes       : parse_all_nodes() 반환값
        topics      : get_topic_info() 반환값
        vault_path  : Obsidian 볼트 루트 경로
        media_map   : extract_media() 반환값
        overwrite   : True이면 기존 MarginNote 폴더 삭제 후 재생성
    """
    if media_map is None:
        media_map = {}

    results = {"success": [], "failed": [], "total": len(nodes)}

    # 노드맵 구성
    node_map = {n['note_id']: n for n in nodes}

    # 기존 MarginNote 폴더 처리
    mn_root = Path(vault_path) / MN_SUBFOLDER
    if overwrite and mn_root.exists():
        import shutil
        shutil.rmtree(mn_root)
        print(f"  [정리] 기존 MarginNote 폴더 삭제")
    mn_root.mkdir(parents=True, exist_ok=True)

    print(f"\n[Obsidian 푸시] 볼트: {vault_path}")
    print(f"[Obsidian 푸시] 이미지: {len(media_map)}개 미디어")

    # 루트 노드 찾기 (parent_id가 None인 노드)
    root_nodes = [n for n in nodes if n['parent_id'] is None]
    print(f"[Obsidian 푸시] 루트 노드: {len(root_nodes)}개")

    # 마인드맵 노드(type=6)와 하이라이트(type=256)를 구분
    # type=256/7이고 루트인 하이라이트는 그냥 루트 밑에 저장
    for root in root_nodes:
        topic_id = root.get('topic_id', '')
        topic_info = topics.get(topic_id, {})
        topic_title = topic_info.get('title', 'Unknown_Topic')

        # type=6 또는 title이 있는 루트 = 마인드맵 구조의 진짜 루트
        # type=256/7이고 title이 없는 = 떠다니는 하이라이트 (특수 처리)
        title = root['title']
        if not title and root['node_type'] in ('highlight', 'highlight_linked'):
            # 떠다니는 하이라이트 → _highlights 폴더에 모음
            hl_dir = mn_root / "_highlights"
            hl_dir.mkdir(exist_ok=True)
            push_node_recursive(
                node=root, node_map=node_map,
                parent_dir=hl_dir,
                topic_title=topic_title, topic_id=topic_id,
                media_map=media_map, depth=0, results=results,
            )
        else:
            push_node_recursive(
                node=root, node_map=node_map,
                parent_dir=mn_root,
                topic_title=topic_title, topic_id=topic_id,
                media_map=media_map, depth=0, results=results,
            )

    print(f"\n[Obsidian 푸시] 완료: 성공 {len(results['success'])}개 / 실패 {len(results['failed'])}개")
    return results


# ============================================================
# 단독 테스트
# ============================================================
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    import importlib.util

    parser_path = Path(__file__).parent.parent / '2.0_marginnote_engine' / '2.1_mn_parser.py'
    spec = importlib.util.spec_from_file_location("mn_parser", parser_path)
    mn_parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mn_parser)

    base = 'G:\\'
    items = os.listdir(base)
    inner_drive = os.path.join(base, items[0])

    pkg_path = vault_path = None
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

    tmp_dir, db_path = mn_parser.unpack_marginpkg(pkg_path)
    nodes = mn_parser.parse_all_nodes(db_path)
    topics = mn_parser.get_topic_info(db_path)
    media = mn_parser.extract_media(db_path)

    result = push_all_nodes(
        nodes=nodes, topics=topics,
        vault_path=vault_path, media_map=media,
        overwrite=True,
    )

    mn_parser.cleanup_temp(tmp_dir)
    print(f"\n성공: {len(result['success'])}개")
