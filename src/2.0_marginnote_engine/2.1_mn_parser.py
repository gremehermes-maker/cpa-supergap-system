"""
2.1_mn_parser.py — MarginNote .marginpkg 패키지 파서
=====================================================
.marginpkg 파일을 열어서 내부 SQLite(.marginnotes)를
파싱하고, 노드 데이터를 Python 딕셔너리 리스트로 반환합니다.

[핵심 테이블 구조 (실제 DB 분석 결과)]
ZBOOKNOTE 테이블:
  - ZNOTEID        : 고유 UUID (변하지 않음, 모든 시스템의 PK)
  - ZNOTETITLE     : 노드 제목 (마인드맵에서 보이는 텍스트)
  - ZNOTES_TEXT    : 노드 본문 텍스트
  - ZGROUPNOTEID   : 부모 노드의 ZNOTEID (None이면 최상위)
  - ZMINDLINKS     : 연결된 카드 UUID 목록 ('|'로 구분)
  - ZHIGHLIGHT_STYLE: 색상 코드 (카드 포맷 타입 결정)
  - ZTYPE          : 노드 타입 (6=마인드맵노드, 256=하이라이트)
  - ZSTARTPAGE     : 원본 PDF의 시작 페이지
  - ZENDPAGE       : 원본 PDF의 끝 페이지
  - ZHIGHLIGHT_TEXT: PDF에서 하이라이트한 원본 텍스트
  - ZMEDIA_LIST    : 첨부 미디어 UUID 목록
  - ZTOPICID       : 소속 스터디셋(Topic) ID
"""

import os
import sys
import zipfile
import tempfile
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

# ============================================================
# ZHIGHLIGHT_STYLE → 카드 포맷 타입 매핑표
# (실제 DB에서 발견된 값들)
# 추후 사용자가 정확한 매핑 확인 후 수정 가능
# ============================================================
HIGHLIGHT_STYLE_MAP = {
    "mbooks-annotation1": "basic",          # 색상 1
    "mbooks-annotation2": "basic",          # 색상 2
    "mbooks-annotation3": "cloze",          # 색상 3 (빈칸)
    "mbooks-annotation4": "cloze",          # 색상 4 (빈칸)
    "mbooks-annotation5": "highlight",      # 색상 5 (형광펜)
    "mbooks-annotation6": "basic",          # 색상 6
    "mbooks-annotation7": "highlight",      # 색상 7 (형광펜)
    None: "mindmap_node",                   # 색상 없음 = 마인드맵 노드
}

# ============================================================
# ZTYPE 값 설명
# ============================================================
NODE_TYPE_MAP = {
    6: "mindmap_node",    # 마인드맵 카드 노드
    256: "highlight",     # PDF 하이라이트 노드
}


def find_marginpkg(search_dir: str) -> Optional[str]:
    """
    지정된 폴더에서 .marginpkg 파일을 찾아 경로를 반환합니다.

    매개변수:
        search_dir: 탐색할 폴더 경로

    반환값:
        .marginpkg 파일 경로 (없으면 None)
    """
    for f in os.listdir(search_dir):
        if f.endswith('.marginpkg'):
            return os.path.join(search_dir, f)
    return None


def unpack_marginpkg(pkg_path: str) -> tuple[str, str]:
    """
    .marginpkg 파일을 임시 폴더에 언패킹합니다.

    .marginpkg = ZIP 형식
    내부: .marginnotes (SQLite DB) + PDF 등

    매개변수:
        pkg_path: .marginpkg 파일 전체 경로

    반환값:
        (임시_폴더_경로, SQLite_DB_파일_경로) 튜플
    """
    tmp_dir = tempfile.mkdtemp(prefix='mn_unpack_')

    with zipfile.ZipFile(pkg_path, 'r') as z:
        z.extractall(tmp_dir)

    # .marginnotes 파일 탐색
    db_file = None
    for f in os.listdir(tmp_dir):
        if f.endswith('.marginnotes'):
            db_file = os.path.join(tmp_dir, f)
            break

    if not db_file:
        raise FileNotFoundError(f".marginnotes 파일을 찾을 수 없습니다: {tmp_dir}")

    return tmp_dir, db_file


def parse_all_nodes(db_path: str) -> list[dict]:
    """
    SQLite DB에서 모든 ZBOOKNOTE 노드를 파싱하여
    Python 딕셔너리 리스트로 반환합니다.

    각 딕셔너리(노드)가 가지는 키:
        - note_id       : ZNOTEID (UUID)
        - title         : ZNOTETITLE (제목)
        - text          : ZNOTES_TEXT (본문)
        - highlight_text: ZHIGHLIGHT_TEXT (PDF 하이라이트 원문)
        - parent_id     : ZGROUPNOTEID (부모 노드 ID, None이면 최상위)
        - linked_ids    : ZMINDLINKS 파싱 결과 (리스트)
        - card_type     : ZHIGHLIGHT_STYLE 매핑 결과
        - node_type     : ZTYPE 설명 문자열
        - start_page    : ZSTARTPAGE
        - end_page      : ZENDPAGE
        - topic_id      : ZTOPICID (소속 스터디셋)
        - media_ids     : ZMEDIA_LIST 파싱 결과 (리스트)
        - raw_style     : ZHIGHLIGHT_STYLE 원본 값

    매개변수:
        db_path: .marginnotes SQLite 파일 경로

    반환값:
        노드 딕셔너리 리스트
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 모든 노드 조회 (삭제된 노드 제외)
    cur.execute("""
        SELECT
            ZNOTEID,
            ZNOTETITLE,
            ZNOTES_TEXT,
            ZHIGHLIGHT_TEXT,
            ZGROUPNOTEID,
            ZMINDLINKS,
            ZHIGHLIGHT_STYLE,
            ZTYPE,
            ZSTARTPAGE,
            ZENDPAGE,
            ZTOPICID,
            ZMEDIA_LIST,
            ZHIGHLIGHT_DATE,
            ZNOTE_DATE,
            ZZINDEX
        FROM ZBOOKNOTE
        WHERE ZNOTEID IS NOT NULL
        ORDER BY ZZINDEX ASC
    """)

    rows = cur.fetchall()
    nodes = []

    for row in rows:
        # ZMINDLINKS: 'UUID1|UUID2|...' 형태를 리스트로 파싱
        raw_links = row['ZMINDLINKS'] or ''
        linked_ids = [uid.strip() for uid in raw_links.split('|') if uid.strip()] if raw_links else []

        # ZMEDIA_LIST: 마찬가지로 '|' 구분
        raw_media = row['ZMEDIA_LIST'] or ''
        media_ids = [m.strip() for m in raw_media.split('|') if m.strip()] if raw_media else []

        # ZHIGHLIGHT_STYLE → card_type 매핑
        raw_style = row['ZHIGHLIGHT_STYLE']
        card_type = HIGHLIGHT_STYLE_MAP.get(raw_style, 'basic')

        # ZTYPE → node_type 설명
        ztype = row['ZTYPE'] or 0
        node_type = NODE_TYPE_MAP.get(ztype, f"unknown_{ztype}")

        node = {
            "note_id":        row['ZNOTEID'],
            "title":          row['ZNOTETITLE'] or '',
            "text":           row['ZNOTES_TEXT'] or '',
            "highlight_text": row['ZHIGHLIGHT_TEXT'] or '',
            "parent_id":      row['ZGROUPNOTEID'],  # None이면 최상위 루트
            "linked_ids":     linked_ids,
            "card_type":      card_type,
            "node_type":      node_type,
            "start_page":     row['ZSTARTPAGE'],
            "end_page":       row['ZENDPAGE'],
            "topic_id":       row['ZTOPICID'],
            "media_ids":      media_ids,
            "raw_style":      raw_style,
            "z_index":        row['ZZINDEX'],
        }
        nodes.append(node)

    conn.close()
    return nodes


def get_topic_info(db_path: str) -> dict:
    """
    ZTOPIC 테이블에서 스터디셋(Topic) 메타정보를 가져옵니다.
    (스터디셋 제목, PDF MD5 등)

    반환값:
        {topic_id: {"title": ..., "pdf_md5": ...}, ...} 딕셔너리
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT ZTOPICID, ZTITLE, ZLOCALBOOKMD5 FROM ZTOPIC")
    topics = {}
    for row in cur.fetchall():
        topics[row['ZTOPICID']] = {
            "title":   row['ZTITLE'] or '',
            "pdf_md5": row['ZLOCALBOOKMD5'] or '',
        }

    conn.close()
    return topics


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

    # G 드라이브에서 .marginpkg 탐색
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

    print(f"[파서] 패키지 경로: {pkg_path}")

    # 언패킹
    tmp_dir, db_path = unpack_marginpkg(pkg_path)
    print(f"[파서] DB 경로: {db_path}")

    # 노드 파싱
    nodes = parse_all_nodes(db_path)
    topics = get_topic_info(db_path)

    print(f"\n[파서] 총 {len(nodes)}개 노드 파싱 완료")
    print(f"[파서] 스터디셋: {topics}")

    # 샘플 출력
    print("\n=== 노드 샘플 (처음 5개) ===")
    for i, node in enumerate(nodes[:5]):
        print(f"\n  [{i+1}] {node['title'] or '(제목없음)'}")
        print(f"       ID: {node['note_id']}")
        print(f"       타입: {node['node_type']} / 카드: {node['card_type']}")
        print(f"       부모: {node['parent_id']}")
        print(f"       링크: {node['linked_ids']}")
        print(f"       텍스트: {node['text'][:50]}")

    # 정리
    cleanup_temp(tmp_dir)
    print(f"\n[파서] 임시 파일 정리 완료")
