"""
2.1_mn_parser.py — MarginNote .marginpkg 패키지 파서 v2
=====================================================
.marginpkg → SQLite 파싱 → 위계 트리 + 이미지 추출

[핵심 발견 사항]
- ZGROUPNOTEID: 이 패키지에선 항상 NULL (사용 안 됨)
- ZMINDLINKS: 부모 → 자식들 방향으로 위계 인코딩 ('|' 구분 UUID 목록)
- ZMEDIA.ZDATA: Apple NSKeyedArchiver(bplist) 안에 PNG 이미지 래핑
- ZFORUMOWNER: TOC 순서를 가진 JSON (bookGroupNotes.tocNoteIds)

[계층 재구성 알고리즘]
  1. 모든 노드의 ZMINDLINKS를 읽음 (부모 → [자식들])
  2. 역방향 매핑 생성 (자식 → 부모)
  3. 부모가 없는 노드 = 루트
  4. ZTOPIC.ZMINDLINKS에 스터디셋 루트 링크 있음
"""

import os
import sys
import zipfile
import tempfile
import sqlite3
import shutil
import plistlib
from pathlib import Path
from typing import Optional

# ============================================================
# ZHIGHLIGHT_STYLE → 카드 포맷 타입 매핑표
# ============================================================
HIGHLIGHT_STYLE_MAP = {
    "mbooks-annotation1": "basic",
    "mbooks-annotation2": "basic",
    "mbooks-annotation3": "cloze",
    "mbooks-annotation4": "cloze",
    "mbooks-annotation5": "highlight",
    "mbooks-annotation6": "basic",
    "mbooks-annotation7": "highlight",
    None: "mindmap_node",
}

NODE_TYPE_MAP = {
    6: "mindmap_node",
    7: "highlight_linked",   # 스터디셋2에 연결된 하이라이트
    256: "highlight",
}


def find_marginpkg(search_dir: str) -> Optional[str]:
    """지정된 폴더에서 .marginpkg 파일을 찾아 경로를 반환합니다."""
    for f in os.listdir(search_dir):
        if f.endswith('.marginpkg'):
            return os.path.join(search_dir, f)
    return None


def unpack_marginpkg(pkg_path: str) -> tuple[str, str]:
    """
    .marginpkg(ZIP)를 임시 폴더에 언패킹합니다.

    반환값: (임시_폴더_경로, SQLite_DB_경로) 튜플
    """
    tmp_dir = tempfile.mkdtemp(prefix='mn_unpack_')
    with zipfile.ZipFile(pkg_path, 'r') as z:
        z.extractall(tmp_dir)

    db_file = None
    for f in os.listdir(tmp_dir):
        if f.endswith('.marginnotes'):
            db_file = os.path.join(tmp_dir, f)
            break

    if not db_file:
        # 서브폴더 탐색
        for root, dirs, files in os.walk(tmp_dir):
            for f in files:
                if f.endswith('.marginnotes'):
                    db_file = os.path.join(root, f)
                    break

    if not db_file:
        raise FileNotFoundError(f".marginnotes 파일을 찾을 수 없습니다: {tmp_dir}")

    return tmp_dir, db_file


def parse_all_nodes(db_path: str) -> list[dict]:
    """
    SQLite DB에서 모든 노드를 파싱하고,
    ZMINDLINKS를 기반으로 parent_id(역방향)를 계산합니다.

    반환값: 노드 딕셔너리 리스트 (parent_id 포함)
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT ZNOTEID, ZNOTETITLE, ZNOTES_TEXT, ZHIGHLIGHT_TEXT,
               ZGROUPNOTEID, ZMINDLINKS, ZHIGHLIGHT_STYLE, ZTYPE,
               ZSTARTPAGE, ZENDPAGE, ZTOPICID, ZMEDIA_LIST,
               ZZINDEX
        FROM ZBOOKNOTE
        WHERE ZNOTEID IS NOT NULL
        ORDER BY ZZINDEX ASC
    """)

    rows = cur.fetchall()

    # 1단계: 기본 노드 맵 구성
    node_map = {}
    for row in rows:
        raw_links = row['ZMINDLINKS'] or ''
        child_ids = [l.strip() for l in raw_links.split('|') if l.strip()]

        raw_media = row['ZMEDIA_LIST'] or ''
        media_ids = [m.strip() for m in raw_media.split('|') if m.strip()]

        raw_style = row['ZHIGHLIGHT_STYLE']
        card_type = HIGHLIGHT_STYLE_MAP.get(raw_style, 'basic')
        ztype = row['ZTYPE'] or 0
        node_type = NODE_TYPE_MAP.get(ztype, f"unknown_{ztype}")

        node_map[row['ZNOTEID']] = {
            "note_id":        row['ZNOTEID'],
            "title":          row['ZNOTETITLE'] or '',
            "text":           row['ZNOTES_TEXT'] or '',
            "highlight_text": row['ZHIGHLIGHT_TEXT'] or '',
            "parent_id":      None,  # 아래에서 ZMINDLINKS 역추적으로 채움
            "child_ids":      child_ids,
            "linked_ids":     child_ids,  # 호환성 유지
            "card_type":      card_type,
            "node_type":      node_type,
            "start_page":     row['ZSTARTPAGE'],
            "end_page":       row['ZENDPAGE'],
            "topic_id":       row['ZTOPICID'],
            "media_ids":      media_ids,
            "raw_style":      raw_style,
            "z_index":        row['ZZINDEX'],
        }

    # 2단계: ZMINDLINKS 역방향 매핑 → parent_id 계산
    # 부모 노드가 ZMINDLINKS에 자식 UUID를 나열하므로,
    # 각 자식에게 그 부모의 ID를 할당
    for nid, node in node_map.items():
        for cid in node['child_ids']:
            if cid in node_map:
                node_map[cid]['parent_id'] = nid

    conn.close()
    return list(node_map.values())


def extract_media(db_path: str) -> dict:
    """
    ZMEDIA 테이블에서 bplist를 파싱하여 실제 이미지 데이터를 추출합니다.

    반환값: {md5: {"data": bytes, "format": "PNG"/"JPEG", "ext": ".png"/".jpg"}}
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT ZMD5, ZDATA FROM ZMEDIA")
    media_map = {}

    for row in cur.fetchall():
        md5, blob = row
        if md5 in media_map or not blob:
            continue

        try:
            plist = plistlib.loads(blob)
            objects = plist.get('$objects', [])

            # NSKeyedArchiver의 $objects 배열에서 가장 큰 bytes 객체 = 이미지
            img_data = None
            for obj in objects:
                if isinstance(obj, bytes) and len(obj) > 100:
                    img_data = obj
                    break

            if img_data:
                header = img_data[:4]
                if header[:3] == b'\xff\xd8\xff':
                    fmt, ext = "JPEG", ".jpg"
                elif header[:4] == b'\x89PNG':
                    fmt, ext = "PNG", ".png"
                else:
                    fmt, ext = "DATA", ".bin"

                media_map[md5] = {"data": img_data, "format": fmt, "ext": ext}
        except Exception:
            pass

    conn.close()
    return media_map


def get_topic_info(db_path: str) -> dict:
    """
    ZTOPIC 테이블에서 스터디셋 메타정보를 가져옵니다.

    반환값: {topic_id: {"title": ..., "pdf_md5": ..., "root_links": [...]}}
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT ZTOPICID, ZTITLE, ZLOCALBOOKMD5, ZMINDLINKS FROM ZTOPIC")
    topics = {}
    for row in cur.fetchall():
        raw_links = row['ZMINDLINKS'] or ''
        root_links = [l.strip() for l in raw_links.split('|') if l.strip()]
        topics[row['ZTOPICID']] = {
            "title":      row['ZTITLE'] or '',
            "pdf_md5":    row['ZLOCALBOOKMD5'] or '',
            "root_links": root_links,
        }

    conn.close()
    return topics


def build_hierarchy(nodes: list[dict]) -> dict:
    """
    평면 노드 리스트를 계층 트리로 재구성합니다.

    반환값: {note_id: node_dict(children 키 포함)} 딕셔너리
    """
    node_map = {n['note_id']: {**n, 'children': []} for n in nodes}

    for nid, node in node_map.items():
        for cid in node['child_ids']:
            if cid in node_map:
                node_map[nid]['children'].append(node_map[cid])

    return node_map


def cleanup_temp(tmp_dir: str):
    """임시 언패킹 폴더를 삭제합니다."""
    try:
        shutil.rmtree(tmp_dir)
    except Exception as e:
        print(f"  [경고] 임시 폴더 삭제 실패: {e}")


# ============================================================
# 단독 실행 테스트
# ============================================================
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    base = 'G:\\'
    items = os.listdir(base)
    inner_drive = os.path.join(base, items[0])

    pkg_path = None
    for s in os.listdir(inner_drive):
        folder = os.path.join(inner_drive, s)
        if os.path.isdir(folder):
            found = find_marginpkg(folder)
            if found:
                pkg_path = found
                break

    if not pkg_path:
        print("ERROR: .marginpkg 파일을 찾을 수 없습니다.")
        sys.exit(1)

    print(f"[파서] 패키지: {pkg_path}")
    tmp_dir, db_path = unpack_marginpkg(pkg_path)

    nodes = parse_all_nodes(db_path)
    topics = get_topic_info(db_path)
    media = extract_media(db_path)

    print(f"[파서] 노드: {len(nodes)}개, 미디어: {len(media)}개")
    print(f"[파서] 스터디셋: {topics}")

    # 위계 확인
    roots = [n for n in nodes if n['parent_id'] is None]
    print(f"[파서] 루트 노드: {len(roots)}개")
    for r in roots:
        print(f"  - {r['title'] or '(제목없음)'} (children={len(r['child_ids'])})")

    cleanup_temp(tmp_dir)
