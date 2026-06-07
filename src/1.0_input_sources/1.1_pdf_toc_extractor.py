import os
import sys
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
import fitz  # PyMuPDF
class TOCHierarchyEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CPA Supergap System - 1.1 목차 계층 에디터 (TOC Hierarchy Editor)")
        self.geometry("800x600")
        
        # 파일 경로
        self.current_json_path = None
        self.toc_data = []

        self._create_ui()

    def _create_ui(self):
        # 상단 툴바
        toolbar = ttk.Frame(self)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="📂 JSON 초안 불러오기", command=self.load_json).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="💾 최종 저장 및 PDF 북마크 주입", command=self.save_all).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        ttk.Button(toolbar, text="➕ 노드 추가", command=self.add_node).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="✏️ 노드 수정", command=self.edit_node).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🗑️ 노드 삭제", command=self.delete_node).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        ttk.Button(toolbar, text="➡️ 하위로 (들여쓰기)", command=self.indent_node).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="⬅️ 상위로 (내어쓰기)", command=self.outdent_node).pack(side=tk.LEFT, padx=2)

        # 트리뷰
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.tree = ttk.Treeview(tree_frame, columns=("Page",), selectmode="browse")
        self.tree.heading("#0", text="목차 제목 (Title)", anchor=tk.W)
        self.tree.heading("Page", text="페이지 (Page)", anchor=tk.W)
        self.tree.column("#0", width=600)
        self.tree.column("Page", width=100)

        # 스크롤바
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        # 드래그 앤 드롭 이벤트 바인딩
        self.tree.bind("<ButtonPress-1>", self.on_drag_start)
        self.tree.bind("<ButtonRelease-1>", self.on_drag_release)
        self._drag_data = {"item": None}

    def load_json(self):
        filepath = filedialog.askopenfilename(
            title="AI가 추출한 목차 JSON 파일 선택",
            filetypes=[("JSON Files", "*.json")]
        )
        if not filepath:
            return
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.toc_data = json.load(f)
            self.current_json_path = filepath
            self._rebuild_tree()
            messagebox.showinfo("성공", "JSON 파일을 성공적으로 불러왔습니다.\n마우스로 시각적으로 계층을 다듬어 보세요!")
        except Exception as e:
            messagebox.showerror("에러", f"파일을 불러오는 중 오류가 발생했습니다:\n{e}")

    def _rebuild_tree(self):
        # 기존 노드 전부 삭제
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # 재귀적으로 노드 추가
        def insert_nodes(parent_id, nodes):
            for node in nodes:
                title = node.get("title", "제목 없음")
                page = node.get("page", "")
                
                item_id = self.tree.insert(parent_id, "end", text=title, values=(page,))
                
                children = node.get("children", [])
                if children:
                    insert_nodes(item_id, children)
                    self.tree.item(item_id, open=True) # 기본적으로 펼쳐두기

        insert_nodes("", self.toc_data)

    def _get_tree_as_dict(self):
        def build_dict(item_id):
            children = self.tree.get_children(item_id)
            result = []
            for child in children:
                title = self.tree.item(child, "text")
                page = self.tree.item(child, "values")[0]
                node = {
                    "title": title,
                    "page": int(page) if str(page).isdigit() else page,
                    "children": build_dict(child)
                }
                result.append(node)
            return result
        return build_dict("")

    def save_all(self):
        if not self.current_json_path:
            messagebox.showwarning("경고", "먼저 JSON 파일을 불러오세요.")
            return

        # 1. 덮어씌울 원본 PDF 파일 선택
        pdf_path = filedialog.askopenfilename(
            title="목차(북마크)를 주입할 원본 PDF 파일 선택",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if not pdf_path:
            return

        # 트리뷰의 데이터를 딕셔너리로 변환
        self.toc_data = self._get_tree_as_dict()

        try:
            # 2. JSON 덮어쓰기 (백업 및 DB 연동용)
            with open(self.current_json_path, 'w', encoding='utf-8') as f:
                json.dump(self.toc_data, f, ensure_ascii=False, indent=4)
            
            # 3. PDF에 강제 주입 (Injection)
            self._inject_pdf_bookmarks(pdf_path)
            
        except Exception as e:
            messagebox.showerror("에러", f"저장 중 오류가 발생했습니다:\n{e}")

    def _inject_pdf_bookmarks(self, pdf_path):
        # Treeview 데이터를 PyMuPDF용 평면 리스트로 변환: [level, title, page]
        toc_list = []
        
        def traverse(item_id, level):
            children = self.tree.get_children(item_id)
            for child in children:
                title = self.tree.item(child, "text")
                page = self.tree.item(child, "values")[0]
                try:
                    page_num = int(page)
                except ValueError:
                    page_num = 1
                
                toc_list.append([level, title, page_num])
                traverse(child, level + 1)
                
        traverse("", 1)

        # PyMuPDF로 원본 PDF 열기
        doc = fitz.open(pdf_path)
        
        # 새로운 북마크 삽입
        doc.set_toc(toc_list)
        
        # 새 파일명으로 저장 (_목차주입본.pdf)
        base_name, ext = os.path.splitext(pdf_path)
        output_pdf_path = f"{base_name}_목차주입본{ext}"
        
        doc.save(output_pdf_path)
        doc.close()
        
        messagebox.showinfo("대성공!", f"완벽하게 튜닝된 목차가 원본 PDF에 강제 주입되었습니다!\n이제 마진노트로 Import 하세요.\n\n주입된 파일: {output_pdf_path}")

    def add_node(self):
        selected = self.tree.selection()
        title = simpledialog.askstring("노드 추가", "새 노드의 제목을 입력하세요:")
        if not title: return
        page = simpledialog.askinteger("노드 추가", "페이지 번호를 입력하세요:", initialvalue=1)
        if page is None: page = ""
        
        if selected:
            # 선택한 노드의 자식으로 추가
            parent = selected[0]
            item = self.tree.insert(parent, "end", text=title, values=(page,))
            self.tree.item(parent, open=True)
            self.tree.selection_set(item)
        else:
            # 최상위 노드로 추가
            item = self.tree.insert("", "end", text=title, values=(page,))
            self.tree.selection_set(item)

    def edit_node(self):
        selected = self.tree.selection()
        if not selected: return
        item = selected[0]
        
        current_title = self.tree.item(item, "text")
        current_page = self.tree.item(item, "values")[0]
        
        new_title = simpledialog.askstring("노드 수정", "제목:", initialvalue=current_title)
        if new_title is None: return
        new_page = simpledialog.askinteger("노드 수정", "페이지:", initialvalue=int(current_page) if str(current_page).isdigit() else 1)
        if new_page is None: return
        
        self.tree.item(item, text=new_title, values=(new_page,))

    def delete_node(self):
        selected = self.tree.selection()
        if not selected: return
        if messagebox.askyesno("삭제 확인", "선택한 노드와 하위 노드를 모두 삭제하시겠습니까?"):
            for item in selected:
                self.tree.delete(item)

    def indent_node(self):
        selected = self.tree.selection()
        if not selected: return
        item = selected[0]
        
        # 이전 형제 노드를 찾아서 그 자식으로 넣음
        prev_sibling = self.tree.prev(item)
        if prev_sibling:
            self.tree.move(item, prev_sibling, "end")
            self.tree.item(prev_sibling, open=True)

    def outdent_node(self):
        selected = self.tree.selection()
        if not selected: return
        item = selected[0]
        
        # 현재 부모를 찾아서 그 부모의 형제로 올림
        parent = self.tree.parent(item)
        if parent:
            grandparent = self.tree.parent(parent)
            # parent의 바로 다음 위치에 삽입
            idx = self.tree.index(parent) + 1
            self.tree.move(item, grandparent, idx)

    # --- 마우스 드래그 앤 드롭 로직 ---
    def on_drag_start(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self._drag_data["item"] = item

    def on_drag_release(self, event):
        if not self._drag_data["item"]:
            return
            
        dragged_item = self._drag_data["item"]
        target_item = self.tree.identify_row(event.y)
        
        self._drag_data["item"] = None
        
        if not target_item or target_item == dragged_item:
            return

        # 방어 로직: 부모를 자기 자신의 자식으로 넣으려는 경우 방지 (무한 루프 방지)
        def is_descendant(node, possible_descendant):
            children = self.tree.get_children(node)
            if possible_descendant in children:
                return True
            for child in children:
                if is_descendant(child, possible_descendant):
                    return True
            return False

        if is_descendant(dragged_item, target_item):
            messagebox.showwarning("경고", "상위 노드를 하위 노드 안으로 이동할 수 없습니다.")
            return

        # 타겟 노드의 바로 '아래(다음 형제)' 위치로 이동시킴
        parent = self.tree.parent(target_item)
        idx = self.tree.index(target_item)
        self.tree.move(dragged_item, parent, idx + 1)

if __name__ == "__main__":
    app = TOCHierarchyEditor()
    app.mainloop()
