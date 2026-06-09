"""
4.2_obsidian_wiki.py — Obsidian 볼트 푸셔 v3
=============================================
MarginNote 마인드맵의 위계 구조를 Obsidian 볼트에 폴더/파일로 재현합니다.

[v3 변경사항]
1. 순서 접두어: 01_, 02_ 로 마인드맵 순서 보존 (알파벳 정렬=마인드맵 순서)
2. 파일/폴더 구분: 폴더 인덱스 파일은 {name}.md.md → Obsidian에서 {name}.md 로 표시
3. TOC 노드 = 항상 폴더: 자식 없어도 폴더 생성 (1차/2차 문제를 넣을 공간)
4. PDF 복사: 패키지 내 원본 PDF를 챕터 폴더에 저장
5. 안전성: 기존 파일 절대 덮어쓰지 않음, 삭제 금지

[폴더 구조 예시]
MarginNote/
  01_Chapter_01_목차주입본/
    Chapter_01_목차주입본.pdf         ← 원본 PDF
    01_Chapter_01_목차주입본.md.md    ← 폴더와 구분되는 인덱스 파일
    01_1 재무관리의 이해/
      01_1 재무관리의 이해.md.md
      01_1 기업과 시장/
        01_1 기업과 시장.md.md
        01_1. 기업의 다양한 활동/
          01_1. 기업의 다양한 활동.md.md
          01_(1) 조달(Financing).md     ← 리프: 일반 .md (폴더 아님)
          02_(2) 투자(Investment)/       ← 자식 있으면 폴더
            02_(2) 투자(Investment).md.md
            highlight_F5616A03.md
            이미지.png
"""

import os
import sys
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional


MN_SUBFOLDER = "MarginNote"


def sanitize_filename(name: str) -> str:
    """
    파일명/폴더명에 사용할 수 없는 Windows 특수문자를 제거합니다.
    금지 문자: \\ / : * ? " < > |
    """
    sanitized = re.sub(r'[\\/:*?"<>|]', '_', name)
    sanitized = sanitized.strip('. ')
    if len(sanitized) > 80:
        sanitized = sanitized[:80]
    return sanitized or "unnamed"


def make_prefix(order_index: int) -> str:
    """
    순서 접두어를 생성합니다.
    order_index=1 → "01_", order_index=12 → "12_"
    마인드맵/목차 순서를 파일시스템 알파벳 정렬로 보존합니다.
    """
    return f"{order_index:02d}_"


def build_frontmatter(node: dict, topic_title: str, topic_id: str,
                      depth: int, is_toc: bool) -> str:
    """노드 데이터로 YAML 프론트매터를 생성합니다."""

    linked_yaml = ""
    if node['linked_ids']:
        linked_yaml = "\n" + "\n".join(f'  - "{uid}"' for uid in node['linked_ids'])
    else:
        linked_yaml = " []"

    media_yaml = ""
    if node['media_ids']:
        media_yaml = "\n" + "\n".join(f'  - "{m}"' for m in node['media_ids'])
    else:
        media_yaml = " []"

    today = datetime.now().strftime("%Y-%m-%d")
    pid = f'"{node["parent_id"]}"' if node["parent_id"] else "null"

    return f"""---
# MarginNote 메타데이터 (자동 생성)
note_id: "{node['note_id']}"
title: "{node['title'].replace('"', "'")}"
topic_id: "{topic_id}"
topic_title: "{topic_title}"
depth: {depth}
is_toc: {str(is_toc).lower()}

# 계층 관계
parent_id: {pid}
linked_ids:{linked_yaml}

# 카드 포맷
card_type: "{node['card_type']}"
raw_style: "{node['raw_style'] or ''}"
node_type: "{node['node_type']}"

# PDF 위치
start_page: {node['start_page'] or 'null'}
end_page: {node['end_page'] or 'null'}

# 미디어
media_ids:{media_yaml}

# Anki 연동
weakness_score: 0
anki_lapses: 0
anki_note_id: null
created_at: "{today}"
updated_at: "{today}"
---"""


def build_body(node: dict, image_filenames: list[str]) -> str:
    """노드의 본문(프론트매터 아래)을 구성합니다."""
    parts = []

    if node['title']:
        parts.append(f"# {node['title']}\n")

    if node['highlight_text']:
        parts.append(f"> {node['highlight_text']}\n")

    if node['text']:
        parts.append(f"\n{node['text']}\n")

    for img_name in image_filenames:
        parts.append(f"\n![[{img_name}]]\n")

    if node.get('child_ids'):
        child_links = [f"- [[{cid}]]" for cid in node['child_ids']]
        if child_links:
            parts.append("\n## 하위 노드\n")
            parts.extend(child_links)

    return "\n".join(parts) if parts else "(내용 없음)\n"


def _extract_images(node: dict, media_map: dict) -> list[str]:
    """노드에 연결된 이미지 파일명 목록을 반환합니다."""
    image_filenames = []
    if node['media_ids']:
        for media_ref in node['media_ids']:
            md5_parts = [p.strip() for p in media_ref.split('-') if p.strip()]
            for md5 in md5_parts:
                if md5 in media_map:
                    info = media_map[md5]
                    if info['format'] in ('PNG', 'JPEG'):
                        image_filenames.append(f"{md5}{info['ext']}")
    return image_filenames


def _save_images(image_filenames: list[str], target_dir: Path,
                 media_map: dict):
    """이미지 파일들을 target_dir에 저장합니다 (기존 파일 스킵)."""
    for img_name in image_filenames:
        md5 = img_name.rsplit('.', 1)[0]
        if md5 in media_map:
            img_path = target_dir / img_name
            if not img_path.exists():
                img_path.write_bytes(media_map[md5]['data'])


def _write_md_safe(md_path: Path, content: str, overwrite: bool) -> bool:
    """
    .md 파일을 안전하게 저장합니다.
    overwrite=False이면 기존 파일을 절대 덮어쓰지 않습니다.

    반환값: 실제로 파일을 생성했으면 True, 스킵했으면 False
    """
    if md_path.exists() and not overwrite:
        return False
    md_path.write_text(content, encoding='utf-8')
    return True


def push_node_recursive(
    node: dict,
    node_map: dict,
    parent_dir: Path,
    topic_title: str,
    topic_id: str,
    media_map: dict,
    depth: int,
    order_index: int,
    toc_ids: set,
    overwrite: bool,
    results: dict,
    log_fn=None,
):
    """
    단일 노드를 재귀적으로 폴더/파일 구조로 저장합니다.

    [규칙]
    - TOC 노드 또는 자식이 있는 노드 → 폴더 생성
    - 그 외 리프 노드 → .md 파일만 생성
    - 폴더 인덱스 파일: {prefix}{name}.md.md (Obsidian에서 .md 표시 → 폴더와 구분)
    - 리프 파일: {prefix}{name}.md
    - 순서: order_index로 01_, 02_ 접두어
    """
    title = node['title']
    is_toc = node['note_id'] in toc_ids
    has_children = bool(node.get('child_ids'))
    force_folder = is_toc or has_children

    # 파일/폴더명 결정
    if title:
        safe_name = sanitize_filename(title)
    else:
        short_id = node['note_id'][:8]
        safe_name = f"highlight_{short_id}"

    prefix = make_prefix(order_index)
    image_filenames = _extract_images(node, media_map)

    if force_folder:
        # ── 폴더 생성 ──
        folder_name = f"{prefix}{safe_name}"
        node_dir = parent_dir / folder_name
        node_dir.mkdir(parents=True, exist_ok=True)

        # 폴더 인덱스 파일: {prefix}{name}.md.md
        # → Obsidian에서 "{prefix}{name}.md" 로 표시되어 폴더와 구분됨
        md_filename = f"{prefix}{safe_name}.md.md"
        md_path = node_dir / md_filename

        # 이미지를 이 폴더에 저장
        _save_images(image_filenames, node_dir, media_map)

        # .md 파일 작성
        fm = build_frontmatter(node, topic_title, topic_id, depth, is_toc)
        body = build_body(node, image_filenames)
        wrote = _write_md_safe(md_path, fm + "\n\n" + body, overwrite)

        if wrote:
            results['success'].append(str(md_path))
            if log_fn:
                log_fn(f"  📁 {folder_name}/  →  {md_filename}")
        else:
            results['skipped'].append(str(md_path))
            if log_fn:
                log_fn(f"  ⏭️ 스킵 (이미 존재): {md_filename}")

        # 자식 노드들 재귀 처리 (순서 = ZMINDLINKS 배열 순서)
        for i, cid in enumerate(node['child_ids']):
            if cid in node_map:
                push_node_recursive(
                    node=node_map[cid],
                    node_map=node_map,
                    parent_dir=node_dir,
                    topic_title=topic_title,
                    topic_id=topic_id,
                    media_map=media_map,
                    depth=depth + 1,
                    order_index=i + 1,
                    toc_ids=toc_ids,
                    overwrite=overwrite,
                    results=results,
                    log_fn=log_fn,
                )
    else:
        # ── 리프 노드: .md 파일만 ──
        md_filename = f"{prefix}{safe_name}.md"
        md_path = parent_dir / md_filename

        _save_images(image_filenames, parent_dir, media_map)

        fm = build_frontmatter(node, topic_title, topic_id, depth, is_toc)
        body = build_body(node, image_filenames)
        wrote = _write_md_safe(md_path, fm + "\n\n" + body, overwrite)

        if wrote:
            results['success'].append(str(md_path))
            if log_fn:
                log_fn(f"  📄 {md_filename}")
        else:
            results['skipped'].append(str(md_path))
            if log_fn:
                log_fn(f"  ⏭️ 스킵 (이미 존재): {md_filename}")


def push_all_nodes(
    nodes: list[dict],
    topics: dict,
    vault_path: str,
    media_map: dict = None,
    toc_ids: set = None,
    pdf_files: list = None,
    overwrite: bool = False,
    log_fn=None,
) -> dict:
    """
    모든 노드를 위계 구조 그대로 Obsidian 볼트에 폴더/파일로 저장합니다.

    매개변수:
        nodes       : parse_all_nodes() 반환값
        topics      : get_topic_info() 반환값
        vault_path  : Obsidian 볼트 루트 경로
        media_map   : extract_media() 반환값
        toc_ids     : get_toc_node_ids() 반환값 (TOC 노드는 항상 폴더)
        pdf_files   : get_pdf_files() 반환값 (원본 PDF 경로 리스트)
        overwrite   : False이면 기존 파일 절대 덮어쓰지 않음 (안전)
        log_fn      : 로그 출력 함수 (GUI용)
    """
    if media_map is None:
        media_map = {}
    if toc_ids is None:
        toc_ids = set()
    if pdf_files is None:
        pdf_files = []

    def _log(msg):
        print(msg)
        if log_fn:
            log_fn(msg)

    results = {"success": [], "failed": [], "skipped": [], "total": len(nodes)}

    node_map = {n['note_id']: n for n in nodes}

    # MarginNote 루트 폴더 (삭제하지 않음! 기존 구조 보존)
    mn_root = Path(vault_path) / MN_SUBFOLDER
    mn_root.mkdir(parents=True, exist_ok=True)

    _log(f"\n[Obsidian 푸시] 볼트: {vault_path}")
    _log(f"[Obsidian 푸시] 이미지: {len(media_map)}개 / TOC노드: {len(toc_ids)}개")

    # 루트 노드 찾기 (parent_id가 None)
    root_nodes = [n for n in nodes if n['parent_id'] is None]

    # 중복 하이라이트 루트 필터링 + 순서 부여
    root_order = 0
    skipped_hl = 0
    for root in root_nodes:
        title = root['title']
        if not title and root['node_type'] in ('highlight', 'highlight_linked'):
            skipped_hl += 1
            continue

        root_order += 1
        topic_id = root.get('topic_id', '')
        topic_info = topics.get(topic_id, {})
        topic_title = topic_info.get('title', 'Unknown_Topic')

        push_node_recursive(
            node=root, node_map=node_map,
            parent_dir=mn_root,
            topic_title=topic_title, topic_id=topic_id,
            media_map=media_map,
            depth=0, order_index=root_order,
            toc_ids=toc_ids, overwrite=overwrite,
            results=results, log_fn=log_fn,
        )

        # PDF를 이 챕터 폴더에 복사
        safe_root_name = sanitize_filename(root['title'] or 'Unknown')
        prefix = make_prefix(root_order)
        chapter_dir = mn_root / f"{prefix}{safe_root_name}"
        if chapter_dir.is_dir() and pdf_files:
            for pdf_src in pdf_files:
                pdf_name = os.path.basename(pdf_src)
                pdf_dest = chapter_dir / pdf_name
                if not pdf_dest.exists():
                    shutil.copy2(pdf_src, pdf_dest)
                    _log(f"  📕 PDF 복사: {pdf_name}")
                else:
                    _log(f"  ⏭️ PDF 스킵 (이미 존재): {pdf_name}")

    if skipped_hl:
        _log(f"[Obsidian 푸시] 중복 하이라이트 스킵: {skipped_hl}개")

    _log(f"\n[Obsidian 푸시] 완료: 생성 {len(results['success'])}개"
         f" / 스킵 {len(results['skipped'])}개"
         f" / 실패 {len(results['failed'])}개")
    return results
