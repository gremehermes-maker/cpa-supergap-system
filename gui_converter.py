"""
MarginNote → Obsidian 변환기 GUI
================================
바탕화면에서 더블클릭으로 실행할 수 있는 GUI 앱입니다.

[기능]
- .marginpkg 파일 선택 (파일 탐색기)
- Obsidian 볼트 폴더 선택 (폴더 탐색기)
- "변환 시작" 버튼으로 1회 실행
- 진행 로그 실시간 표시
- 안전 정책: 기존 파일 덮어쓰기 금지, 삭제 금지

[사용법]
1. 바탕화면의 "MarginNote 변환기.bat" 더블클릭
2. .marginpkg 파일 경로 선택
3. Obsidian 볼트 폴더 선택
4. "변환 시작" 클릭
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from pathlib import Path

# UTF-8 출력 설정
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


class MarginNoteConverterApp:
    """MarginNote → Obsidian 변환기 메인 GUI 클래스"""

    def __init__(self):
        # ── 메인 윈도우 설정 ──
        self.root = tk.Tk()
        self.root.title("MarginNote → Obsidian 변환기")
        self.root.geometry("750x620")
        self.root.resizable(True, True)
        self.root.configure(bg="#1e1e2e")

        # 색상 팔레트 (다크 모드)
        self.colors = {
            "bg":       "#1e1e2e",
            "surface":  "#2a2a3e",
            "text":     "#cdd6f4",
            "accent":   "#89b4fa",
            "success":  "#a6e3a1",
            "warning":  "#f9e2af",
            "error":    "#f38ba8",
            "btn_bg":   "#313244",
            "btn_hover":"#45475a",
        }

        # 변환 중 플래그
        self.is_running = False
        self.conversion_done = False

        self._build_ui()
        self._set_defaults()

    def _build_ui(self):
        """GUI 위젯들을 배치합니다."""
        c = self.colors

        # ── 제목 ──
        title_frame = tk.Frame(self.root, bg=c["bg"])
        title_frame.pack(fill="x", padx=20, pady=(15, 5))
        tk.Label(
            title_frame, text="📘 MarginNote → Obsidian 변환기",
            font=("Segoe UI", 16, "bold"), fg=c["accent"], bg=c["bg"]
        ).pack(anchor="w")
        tk.Label(
            title_frame, text="마진노트 패키지를 옵시디언 위계 폴더 구조로 변환합니다",
            font=("Segoe UI", 9), fg="#6c7086", bg=c["bg"]
        ).pack(anchor="w")

        # ── .marginpkg 파일 선택 ──
        pkg_frame = tk.LabelFrame(
            self.root, text="  📦 변환할 MarginNote 파일 (.marginpkg)  ",
            font=("Segoe UI", 10, "bold"), fg=c["text"], bg=c["surface"],
            relief="groove", bd=1
        )
        pkg_frame.pack(fill="x", padx=20, pady=(10, 5))

        inner_pkg = tk.Frame(pkg_frame, bg=c["surface"])
        inner_pkg.pack(fill="x", padx=10, pady=8)

        self.pkg_var = tk.StringVar()
        self.pkg_entry = tk.Entry(
            inner_pkg, textvariable=self.pkg_var,
            font=("Segoe UI", 9), bg="#181825", fg=c["text"],
            insertbackground=c["text"], relief="flat", bd=0
        )
        self.pkg_entry.pack(side="left", fill="x", expand=True, ipady=4)

        self.pkg_btn = tk.Button(
            inner_pkg, text="📂 찾기", font=("Segoe UI", 9),
            bg=c["btn_bg"], fg=c["text"], relief="flat",
            activebackground=c["btn_hover"], cursor="hand2",
            command=self._browse_pkg
        )
        self.pkg_btn.pack(side="right", padx=(8, 0))

        # ── Obsidian 볼트 폴더 선택 ──
        vault_frame = tk.LabelFrame(
            self.root, text="  📁 Obsidian 볼트 폴더 (저장 위치)  ",
            font=("Segoe UI", 10, "bold"), fg=c["text"], bg=c["surface"],
            relief="groove", bd=1
        )
        vault_frame.pack(fill="x", padx=20, pady=5)

        inner_vault = tk.Frame(vault_frame, bg=c["surface"])
        inner_vault.pack(fill="x", padx=10, pady=8)

        self.vault_var = tk.StringVar()
        self.vault_entry = tk.Entry(
            inner_vault, textvariable=self.vault_var,
            font=("Segoe UI", 9), bg="#181825", fg=c["text"],
            insertbackground=c["text"], relief="flat", bd=0
        )
        self.vault_entry.pack(side="left", fill="x", expand=True, ipady=4)

        self.vault_btn = tk.Button(
            inner_vault, text="📂 찾기", font=("Segoe UI", 9),
            bg=c["btn_bg"], fg=c["text"], relief="flat",
            activebackground=c["btn_hover"], cursor="hand2",
            command=self._browse_vault
        )
        self.vault_btn.pack(side="right", padx=(8, 0))

        # ── 안전 정책 표시 ──
        safety_frame = tk.Frame(self.root, bg=c["bg"])
        safety_frame.pack(fill="x", padx=20, pady=(5, 5))
        tk.Label(
            safety_frame, text="🛡️ 안전 정책: 기존 파일 덮어쓰기 금지 / 삭제 금지 / 1회 실행만 허용",
            font=("Segoe UI", 9), fg=c["warning"], bg=c["bg"]
        ).pack(anchor="w")

        # ── 변환 시작 버튼 ──
        btn_frame = tk.Frame(self.root, bg=c["bg"])
        btn_frame.pack(fill="x", padx=20, pady=5)

        self.start_btn = tk.Button(
            btn_frame, text="🚀 변환 시작",
            font=("Segoe UI", 12, "bold"),
            bg="#89b4fa", fg="#1e1e2e",
            activebackground="#74c7ec", activeforeground="#1e1e2e",
            relief="flat", cursor="hand2", padx=20, pady=6,
            command=self._start_conversion
        )
        self.start_btn.pack(fill="x")

        # ── 로그 출력 영역 ──
        log_frame = tk.LabelFrame(
            self.root, text="  📋 변환 로그  ",
            font=("Segoe UI", 10, "bold"), fg=c["text"], bg=c["surface"],
            relief="groove", bd=1
        )
        log_frame.pack(fill="both", expand=True, padx=20, pady=(5, 15))

        self.log_text = scrolledtext.ScrolledText(
            log_frame, font=("Consolas", 9),
            bg="#181825", fg=c["text"],
            insertbackground=c["text"], relief="flat", bd=0,
            wrap="word", state="disabled"
        )
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # ── 상태바 ──
        self.status_var = tk.StringVar(value="대기 중...")
        status_bar = tk.Label(
            self.root, textvariable=self.status_var,
            font=("Segoe UI", 9), fg="#6c7086", bg="#11111b",
            anchor="w", padx=10, pady=3
        )
        status_bar.pack(fill="x", side="bottom")

    def _set_defaults(self):
        """기본값을 설정합니다 (구글 드라이브 공부 폴더)."""
        try:
            base = 'G:\\'
            if os.path.exists(base):
                items = os.listdir(base)
                if items:
                    inner = os.path.join(base, items[0])
                    # 볼트 기본 경로
                    for s in os.listdir(inner):
                        folder = os.path.join(inner, s)
                        if os.path.isdir(folder):
                            for f in os.listdir(folder):
                                if f.endswith('.marginpkg'):
                                    self.pkg_var.set(os.path.join(folder, f))
                                    self.vault_var.set(folder)
                                    return
        except Exception:
            pass

    def _browse_pkg(self):
        """파일 탐색기로 .marginpkg 파일을 선택합니다."""
        path = filedialog.askopenfilename(
            title="MarginNote 파일 선택",
            filetypes=[
                ("MarginNote 패키지", "*.marginpkg"),
                ("모든 파일", "*.*"),
            ],
            initialdir="G:\\"
        )
        if path:
            self.pkg_var.set(path)

    def _browse_vault(self):
        """폴더 탐색기로 Obsidian 볼트 폴더를 선택합니다."""
        path = filedialog.askdirectory(
            title="Obsidian 볼트 폴더 선택",
            initialdir=self.vault_var.get() or "G:\\"
        )
        if path:
            self.vault_var.set(path)

    def _log(self, msg: str):
        """로그 메시지를 GUI에 추가합니다 (스레드 안전)."""
        def _append():
            self.log_text.config(state="normal")
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.root.after(0, _append)

    def _set_status(self, msg: str):
        """상태바 텍스트를 업데이트합니다."""
        self.root.after(0, lambda: self.status_var.set(msg))

    def _start_conversion(self):
        """변환 시작 버튼 클릭 핸들러."""
        # 이미 실행된 경우 차단
        if self.conversion_done:
            messagebox.showinfo("알림", "이미 변환이 완료되었습니다.\n새 변환을 하려면 프로그램을 다시 실행하세요.")
            return
        if self.is_running:
            return

        # 입력 검증
        pkg_path = self.pkg_var.get().strip()
        vault_path = self.vault_var.get().strip()

        if not pkg_path:
            messagebox.showwarning("경고", ".marginpkg 파일 경로를 선택해주세요.")
            return
        if not os.path.isfile(pkg_path):
            messagebox.showerror("오류", f"파일이 존재하지 않습니다:\n{pkg_path}")
            return
        if not vault_path:
            messagebox.showwarning("경고", "Obsidian 볼트 폴더를 선택해주세요.")
            return
        if not os.path.isdir(vault_path):
            messagebox.showerror("오류", f"폴더가 존재하지 않습니다:\n{vault_path}")
            return

        # UI 잠금
        self.is_running = True
        self.start_btn.config(state="disabled", text="⏳ 변환 중...", bg="#45475a")
        self.pkg_btn.config(state="disabled")
        self.vault_btn.config(state="disabled")

        # 별도 스레드에서 변환 실행 (UI 멈춤 방지)
        thread = threading.Thread(
            target=self._run_conversion,
            args=(pkg_path, vault_path),
            daemon=True,
        )
        thread.start()

    def _run_conversion(self, pkg_path: str, vault_path: str):
        """별도 스레드에서 실행되는 변환 로직."""
        try:
            self._set_status("모듈 로딩 중...")
            self._log("=" * 50)
            self._log("🚀 MarginNote → Obsidian 변환 시작")
            self._log("=" * 50)
            self._log(f"  패키지: {pkg_path}")
            self._log(f"  볼트:   {vault_path}")

            # 모듈 동적 임포트
            import importlib.util
            src_dir = Path(__file__).parent / "src"

            parser_path = src_dir / '2.0_marginnote_engine' / '2.1_mn_parser.py'
            spec_p = importlib.util.spec_from_file_location("mn_parser", str(parser_path))
            mn_parser = importlib.util.module_from_spec(spec_p)
            spec_p.loader.exec_module(mn_parser)

            wiki_path = src_dir / '4.0_knowledge_base' / '4.2_obsidian_wiki.py'
            spec_w = importlib.util.spec_from_file_location("obsidian_wiki", str(wiki_path))
            obsidian_wiki = importlib.util.module_from_spec(spec_w)
            spec_w.loader.exec_module(obsidian_wiki)

            self._log("\n[1/4] .marginpkg 언패킹 중...")
            self._set_status("언패킹 중...")
            tmp_dir, db_path = mn_parser.unpack_marginpkg(pkg_path)
            self._log(f"  ✅ 언패킹 완료")

            self._log("\n[2/4] MarginNote 데이터 파싱 중...")
            self._set_status("데이터 파싱 중...")
            nodes = mn_parser.parse_all_nodes(db_path)
            topics = mn_parser.get_topic_info(db_path)
            media_map = mn_parser.extract_media(db_path)
            toc_ids = mn_parser.get_toc_node_ids(db_path)
            pdf_files = mn_parser.get_pdf_files(tmp_dir)
            self._log(f"  ✅ 노드: {len(nodes)}개 / 이미지: {len(media_map)}개")
            self._log(f"  ✅ TOC노드: {len(toc_ids)}개 / PDF: {len(pdf_files)}개")

            self._log("\n[3/4] Obsidian 볼트로 저장 중...")
            self._set_status("Obsidian 저장 중...")
            result = obsidian_wiki.push_all_nodes(
                nodes=nodes,
                topics=topics,
                vault_path=vault_path,
                media_map=media_map,
                toc_ids=toc_ids,
                pdf_files=pdf_files,
                overwrite=False,   # 절대 덮어쓰지 않음!
                log_fn=self._log,
            )

            self._log("\n[4/4] 임시 파일 정리...")
            self._set_status("정리 중...")
            mn_parser.cleanup_temp(tmp_dir)

            # 완료 메시지
            self._log("\n" + "=" * 50)
            self._log("🎉 변환 완료!")
            self._log(f"   생성: {len(result['success'])}개")
            self._log(f"   스킵: {len(result['skipped'])}개 (이미 존재)")
            self._log(f"   실패: {len(result['failed'])}개")
            self._log("=" * 50)

            self._set_status(
                f"✅ 완료 — 생성 {len(result['success'])}개"
                f" / 스킵 {len(result['skipped'])}개"
            )

            self.conversion_done = True
            self.root.after(0, lambda: self.start_btn.config(
                text="✅ 변환 완료", bg="#a6e3a1", fg="#1e1e2e"
            ))

        except Exception as e:
            self._log(f"\n❌ 오류 발생: {e}")
            import traceback
            self._log(traceback.format_exc())
            self._set_status(f"❌ 오류: {e}")
            self.root.after(0, lambda: self.start_btn.config(
                state="normal", text="🚀 변환 시작", bg="#89b4fa"
            ))
        finally:
            self.is_running = False

    def run(self):
        """GUI 이벤트 루프를 시작합니다."""
        self.root.mainloop()


# ============================================================
# 프로그램 진입점
# ============================================================
if __name__ == "__main__":
    app = MarginNoteConverterApp()
    app.run()
