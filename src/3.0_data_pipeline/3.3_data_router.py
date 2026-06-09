"""
3.3_data_router.py — 데이터 분배 엔진 (핵심 파이프라인 진입점)
=================================================================
.marginpkg 파일을 받아서 전체 파이프라인을 실행합니다.

[처리 흐름]
1. .marginpkg 파일 탐색 또는 경로 직접 지정
2. 2.1_mn_parser.py → 언패킹 + SQLite 파싱 → 노드 리스트
3. 4.2_obsidian_wiki.py → Obsidian 볼트에 .md 파일 생성
4. 원자적 백업 (선택적)
5. 임시 파일 정리

[사용법]
  # 명령줄에서 직접 실행:
  python 3.3_data_router.py
  python 3.3_data_router.py "G:\\내 드라이브\\공부\\test.marginpkg"

  # 다른 모듈에서 임포트:
  from src.data_pipeline import data_router
  data_router.run(pkg_path="...", vault_path="...")
"""

import os
import sys
import shutil
import zipfile
import json
from pathlib import Path
from datetime import datetime

# UTF-8 출력 설정
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# ============================================================
# 경로 설정 (config.yaml이 없을 때 기본값)
# ============================================================
# G 드라이브 '내 드라이브' 안의 '공부' 폴더
# (실제 경로는 아래 find_gdrive_vault() 함수로 자동 탐색)
DEFAULT_VAULT_SUBFOLDER = "공부"   # 볼트가 위치한 서브폴더 이름
DEFAULT_BACKUP_ENABLED = True      # 원자적 백업 활성화 여부


def find_gdrive_root() -> str:
    """
    G 드라이브에서 구글 드라이브 '내 드라이브' 폴더를 찾습니다.

    반환값:
        '내 드라이브' 폴더 전체 경로
    """
    base = 'G:\\'
    if not os.path.exists(base):
        raise FileNotFoundError(f"G: 드라이브를 찾을 수 없습니다. 구글 드라이브가 마운트되어 있는지 확인하세요.")

    items = os.listdir(base)
    if not items:
        raise FileNotFoundError("G: 드라이브가 비어 있습니다.")

    # 첫 번째 폴더가 '내 드라이브'
    inner_drive = os.path.join(base, items[0])
    return inner_drive


def find_vault_and_pkg(inner_drive: str) -> tuple[str, str]:
    """
    '내 드라이브' 안에서 .marginpkg 파일과 볼트 경로를 탐색합니다.

    반환값:
        (vault_path, pkg_path) 튜플
    """
    pkg_path = None
    vault_path = None

    for folder_name in os.listdir(inner_drive):
        folder = os.path.join(inner_drive, folder_name)
        if not os.path.isdir(folder):
            continue
        for fname in os.listdir(folder):
            if fname.endswith('.marginpkg'):
                pkg_path = os.path.join(folder, fname)
                vault_path = folder
                break
        if pkg_path:
            break

    if not pkg_path:
        raise FileNotFoundError("구글 드라이브에서 .marginpkg 파일을 찾을 수 없습니다.")

    return vault_path, pkg_path


def load_parsers():
    """
    2.1_mn_parser 와 4.2_obsidian_wiki 모듈을 동적으로 임포트합니다.
    (상대 경로 임포트 호환성을 위해 importlib 사용)

    반환값:
        (mn_parser 모듈, obsidian_wiki 모듈) 튜플
    """
    import importlib.util

    # 이 파일의 위치: src/3.0_data_pipeline/
    this_dir = Path(__file__).parent
    src_dir = this_dir.parent

    # 2.1_mn_parser.py 경로
    parser_path = src_dir / '2.0_marginnote_engine' / '2.1_mn_parser.py'
    spec_p = importlib.util.spec_from_file_location("mn_parser", str(parser_path))
    mn_parser = importlib.util.module_from_spec(spec_p)
    spec_p.loader.exec_module(mn_parser)

    # 4.2_obsidian_wiki.py 경로
    wiki_path = src_dir / '4.0_knowledge_base' / '4.2_obsidian_wiki.py'
    spec_w = importlib.util.spec_from_file_location("obsidian_wiki", str(wiki_path))
    obsidian_wiki = importlib.util.module_from_spec(spec_w)
    spec_w.loader.exec_module(obsidian_wiki)

    return mn_parser, obsidian_wiki


def create_atomic_backup(pkg_path: str, vault_path: str) -> str:
    """
    원자적 백업: .marginpkg와 Obsidian 볼트의 MarginNote 폴더를
    타임스탬프 .zip으로 묶어 저장합니다.

    '모든 것을 동시에 백업하고 동시에 복원'할 수 있는 보험입니다.

    반환값:
        생성된 백업 .zip 파일 경로
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(vault_path) / "_backups"
    backup_dir.mkdir(exist_ok=True)

    zip_path = backup_dir / f"backup_{timestamp}.zip"

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. .marginpkg 파일 포함
        zf.write(pkg_path, arcname=os.path.basename(pkg_path))

        # 2. Obsidian MarginNote 폴더 포함
        mn_vault_dir = Path(vault_path) / "MarginNote"
        if mn_vault_dir.exists():
            for md_file in mn_vault_dir.rglob('*.md'):
                arcname = str(md_file.relative_to(vault_path))
                zf.write(str(md_file), arcname=arcname)

    return str(zip_path)


def run(pkg_path: str = None, vault_path: str = None, overwrite: bool = True) -> dict:
    """
    데이터 분배 파이프라인 메인 함수.

    매개변수:
        pkg_path   : .marginpkg 파일 경로 (None이면 G 드라이브에서 자동 탐색)
        vault_path : Obsidian 볼트 경로 (None이면 pkg_path와 같은 폴더)
        overwrite  : 기존 .md 파일 덮어쓰기 여부 (기본값: True)

    반환값:
        실행 결과 딕셔너리
    """
    print("=" * 60)
    print("🚀 CPA Supergap 데이터 분배 파이프라인 시작")
    print("=" * 60)

    # ── 1단계: 경로 확인 ──────────────────────────
    if pkg_path is None or vault_path is None:
        print("\n[1단계] 구글 드라이브 탐색 중...")
        try:
            inner_drive = find_gdrive_root()
            vault_path_found, pkg_path_found = find_vault_and_pkg(inner_drive)
            if pkg_path is None:
                pkg_path = pkg_path_found
            if vault_path is None:
                vault_path = vault_path_found
        except FileNotFoundError as e:
            print(f"❌ 경로 탐색 실패: {e}")
            return {"error": str(e)}

    print(f"  패키지: {pkg_path}")
    print(f"  볼트:   {vault_path}")

    # ── 2단계: 모듈 로드 ──────────────────────────
    print("\n[2단계] 파서 모듈 로딩...")
    try:
        mn_parser, obsidian_wiki = load_parsers()
        print("  ✅ 파서 모듈 로딩 완료")
    except Exception as e:
        print(f"  ❌ 모듈 로딩 실패: {e}")
        return {"error": str(e)}

    # ── 3단계: .marginpkg 언패킹 ──────────────────
    print("\n[3단계] .marginpkg 언패킹 중...")
    try:
        tmp_dir, db_path = mn_parser.unpack_marginpkg(pkg_path)
        print(f"  ✅ 언패킹 완료: {db_path}")
    except Exception as e:
        print(f"  ❌ 언패킹 실패: {e}")
        return {"error": str(e)}

    # ── 4단계: SQLite 파싱 + 이미지 추출 ──────────
    print("\n[4단계] MarginNote 데이터 파싱 중...")
    try:
        nodes = mn_parser.parse_all_nodes(db_path)
        topics = mn_parser.get_topic_info(db_path)
        media_map = mn_parser.extract_media(db_path)
        print(f"  ✅ 파싱 완료: {len(nodes)}개 노드, {len(topics)}개 스터디셋, {len(media_map)}개 이미지")
        for tid, tinfo in topics.items():
            print(f"     스터디셋: {tinfo['title']}")
        # 위계 구조 확인
        roots = [n for n in nodes if n['parent_id'] is None]
        print(f"  ✅ 루트 노드: {len(roots)}개")
        for r in roots:
            if r['title']:
                print(f"     루트: {r['title']}")
    except Exception as e:
        mn_parser.cleanup_temp(tmp_dir)
        print(f"  ❌ 파싱 실패: {e}")
        return {"error": str(e)}

    # ── 5단계: Obsidian 볼트로 푸시 ──────────────
    print("\n[5단계] Obsidian 볼트로 위계 폴더/파일 생성 중...")
    try:
        push_result = obsidian_wiki.push_all_nodes(
            nodes=nodes,
            topics=topics,
            vault_path=vault_path,
            media_map=media_map,
            overwrite=overwrite,
        )
    except Exception as e:
        mn_parser.cleanup_temp(tmp_dir)
        print(f"  ❌ Obsidian 푸시 실패: {e}")
        return {"error": str(e)}

    # ── 6단계: 원자적 백업 ────────────────────────
    backup_path = None
    if DEFAULT_BACKUP_ENABLED:
        print("\n[6단계] 원자적 백업 생성 중...")
        try:
            backup_path = create_atomic_backup(pkg_path, vault_path)
            print(f"  ✅ 백업 완료: {backup_path}")
        except Exception as e:
            print(f"  ⚠️ 백업 실패 (계속 진행): {e}")

    # ── 7단계: 임시 파일 정리 ─────────────────────
    print("\n[7단계] 임시 파일 정리...")
    mn_parser.cleanup_temp(tmp_dir)
    print("  ✅ 임시 파일 삭제 완료")

    # ── 최종 결과 ─────────────────────────────────
    result = {
        "pkg_path": pkg_path,
        "vault_path": vault_path,
        "nodes_total": len(nodes),
        "nodes_success": len(push_result['success']),
        "nodes_failed": len(push_result['failed']),
        "failed_ids": push_result['failed'],
        "backup_path": backup_path,
    }

    print("\n" + "=" * 60)
    print("🎉 파이프라인 완료!")
    print(f"   총 노드: {result['nodes_total']}개")
    print(f"   성공: {result['nodes_success']}개")
    print(f"   실패: {result['nodes_failed']}개")
    if backup_path:
        print(f"   백업: {backup_path}")
    print("=" * 60)

    return result


# ============================================================
# 명령줄 실행 진입점
# ============================================================
if __name__ == "__main__":
    # 명령줄 인수로 .marginpkg 경로를 직접 지정할 수 있음
    # 없으면 G 드라이브에서 자동 탐색
    pkg_arg = sys.argv[1] if len(sys.argv) > 1 else None

    result = run(
        pkg_path=pkg_arg,
        vault_path=None,   # None이면 패키지와 같은 폴더를 볼트로 사용
        overwrite=True,    # 테스트: 항상 덮어쓰기
    )

    # 결과 저장
    if "error" not in result:
        out_path = Path(__file__).parent.parent.parent / "scratch" / "last_run_result.json"
        out_path.parent.mkdir(exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n[결과 저장] {out_path}")
