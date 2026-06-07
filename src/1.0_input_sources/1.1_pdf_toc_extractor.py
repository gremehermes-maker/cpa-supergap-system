import os
import sys
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

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
        ttk.Button(toolbar, text="💾 최종 저장 (JSON & OPML)", command=self.save_all).pack(side=tk.LEFT, padx=2)
        
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

        # 트리뷰의 데이터를 딕셔너리로 변환
        self.toc_data = self._get_tree_as_dict()

        try:
            # 1. JSON 덮어쓰기
            with open(self.current_json_path, 'w', encoding='utf-8') as f:
                json.dump(self.toc_data, f, ensure_ascii=False, indent=4)
            
            # 2. OPML 저장
            opml_path = self.current_json_path.replace(".json", ".opml")
            self._save_opml(opml_path)
            
            messagebox.showinfo("성공", f"완벽하게 튜닝된 목차가 저장되었습니다!\n이제 마진노트로 Import 하세요.\n\nJSON: {self.current_json_path}\nOPML: {opml_path}")
        except Exception as e:
            messagebox.showerror("에러", f"저장 중 오류가 발생했습니다:\n{e}")

    def _save_opml(self, filepath):
        opml = Element("opml", version="2.0")
        head = SubElement(opml, "head")
        SubElement(head, "title").text = os.basename(filepath)
        body = SubElement(opml, "body")

        def append_to_opml(parent_elem, nodes):
            for node in nodes:
                title = node.get("title", "")
                outline = SubElement(parent_elem, "outline", text=title)
                children = node.get("children", [])
                if children:
                    append_to_opml(outline, children)

        append_to_opml(body, self.toc_data)
        
        xml_str = tostring(opml, encoding="utf-8")
        parsed_xml = minidom.parseString(xml_str)
        pretty_xml = parsed_xml.toprettyxml(indent="  ")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(pretty_xml)

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

if __name__ == "__main__":
    app = TOCHierarchyEditor()
    app.mainloop()
