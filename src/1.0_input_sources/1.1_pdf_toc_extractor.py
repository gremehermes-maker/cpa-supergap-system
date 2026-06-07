import fitz  # PyMuPDF
import re
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# --- 인간 친화적 드롭다운 옵션과 정규식 매핑 ---
PATTERN_MAP = {
    "1. 2. 3. (아라비아 숫자)": r"^\d+\.\s+",
    "(1) (2) (3) (괄호 숫자)": r"^\(\d+\)\s*",
    "① ② ③ (원문자 숫자)": r"^[①-⑮]\s*",
    "가. 나. 다. (한글)": r"^[가-하]\.\s+",
    "I. II. III. (로마자 대문자)": r"^[IVX]+\.\s+",
    "제1장, 제1편 (장/편 단위)": r"^제\s*\d+\s*[장편절]\s*"
}

class TOCExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CPA Supergap - 1.1 TOC Extractor (V9)")
        self.root.geometry("600x400")
        
        self.pdf_path = ""
        
        # 1. 파일 선택 UI
        frame_file = ttk.LabelFrame(self.root, text="1. 교재 PDF 선택", padding=10)
        frame_file.pack(fill="x", padx=10, pady=5)
        
        self.lbl_file = ttk.Label(frame_file, text="선택된 파일 없음")
        self.lbl_file.pack(side="left", fill="x", expand=True)
        
        btn_file = ttk.Button(frame_file, text="PDF 찾아보기", command=self.select_file)
        btn_file.pack(side="right")
        
        # 2. 마우스 클릭형 목차 규칙 설정 UI
        frame_rules = ttk.LabelFrame(self.root, text="2. 목차 위계 드롭다운 설정 (Point-and-Click)", padding=10)
        frame_rules.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.combos = []
        self.entries = []
        
        options = [
            "[선택 안 함]",
            "[텍스트 직접 입력 (이미지 폰트 추적용)]",
            "제1장, 제1편 (장/편 단위)",
            "1. 2. 3. (아라비아 숫자)",
            "(1) (2) (3) (괄호 숫자)",
            "① ② ③ (원문자 숫자)",
            "가. 나. 다. (한글)",
            "I. II. III. (로마자 대문자)"
        ]
        
        # Level 1 부터 5까지 드롭다운 배치
        for i in range(5):
            row_frame = ttk.Frame(frame_rules)
            row_frame.pack(fill="x", pady=2)
            
            lbl = ttk.Label(row_frame, text=f"Level {i+1}:", width=8)
            lbl.pack(side="left")
            
            # 마우스로 선택하는 콤보박스(드롭다운)
            combo = ttk.Combobox(row_frame, values=options, state="readonly", width=35)
            combo.set("[선택 안 함]")
            combo.pack(side="left", padx=5)
            combo.bind("<<ComboboxSelected>>", self.on_combo_change)
            self.combos.append(combo)
            
            # 텍스트 직접 입력을 골랐을 때만 켜지는 타이핑 칸
            entry = ttk.Entry(row_frame, state="disabled", width=20)
            entry.pack(side="left", padx=5)
            self.entries.append(entry)

        # 3. 추출 실행 버튼
        frame_run = ttk.Frame(self.root, padding=10)
        frame_run.pack(fill="x", padx=10, pady=5)
        
        btn_run = ttk.Button(frame_run, text="MECE 목차 자동 추출 시작!", command=self.run_extraction)
        btn_run.pack(fill="x", ipady=5)
        
    def select_file(self):
        """파일 탐색기를 열어 PDF 파일을 선택합니다."""
        path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if path:
            self.pdf_path = path
            self.lbl_file.config(text=path)
            
    def on_combo_change(self, event):
        """드롭다운 선택 값에 따라 텍스트 입력창을 켜고 끕니다."""
        for i in range(5):
            val = self.combos[i].get()
            if val == "[텍스트 직접 입력 (이미지 폰트 추적용)]":
                self.entries[i].config(state="normal")
            else:
                self.entries[i].delete(0, tk.END)
                self.entries[i].config(state="disabled")

    def run_extraction(self):
        """추출 시작 버튼을 눌렀을 때의 메인 로직입니다."""
        if not self.pdf_path:
            messagebox.showwarning("경고", "PDF 파일을 선택해주세요!")
            return
            
        rules = []
        for i in range(5):
            val = self.combos[i].get()
            text_val = self.entries[i].get()
            
            if val == "[선택 안 함]":
                continue
            elif val == "[텍스트 직접 입력 (이미지 폰트 추적용)]":
                if not text_val:
                    messagebox.showwarning("경고", f"Level {i+1}의 추적용 텍스트를 입력해주세요.")
                    return
                # 추적용 규칙 등록
                rules.append({"type": "font", "text": text_val, "level": i+1})
            else:
                # 드롭다운 선택값을 실제 정규식(Regex)으로 자동 치환하여 등록
                rules.append({"type": "regex", "pattern": PATTERN_MAP[val], "level": i+1})
                
        if not rules:
            messagebox.showwarning("경고", "최소 1개 이상의 규칙을 설정해주세요.")
            return
            
        try:
            self.extract_toc(rules)
            messagebox.showinfo("성공", "목차 추출이 완료되었습니다!\n선택하신 PDF와 같은 폴더에 JSON/OPML 파일이 생성되었습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"추출 중 오류 발생:\n{e}")

    def detect_font_sizes(self, doc, rules):
        """
        사용자가 '텍스트 직접 입력'으로 넘긴 글자의 실제 폰트 크기를 
        PDF에서 스캔하여 알아내는 마법의 함수입니다. (깨진 글자도 찰떡같이 찾습니다!)
        """
        import difflib
        font_rules = [r for r in rules if r["type"] == "font"]
        if not font_rules: return
        
        end_page = min(20, len(doc)) # 초반 20페이지만 스캔해서 크기를 찾아냅니다.
        for r in font_rules:
            target_text = r["text"].replace(" ", "")
            found_size = 0
            
            for page_num in range(end_page):
                page = doc.load_page(page_num)
                blocks = page.get_text("dict")["blocks"]
                for block in blocks:
                    if "lines" not in block: continue
                    for line in block["lines"]:
                        line_text = ""
                        max_size = 0
                        for span in line["spans"]:
                            txt = span["text"].strip()
                            if txt:
                                line_text += txt
                                max_size = max(max_size, span["size"])
                        
                        clean_line = line_text.replace(" ", "")
                        if not clean_line: continue
                        
                        # Fuzzy Matching (유사도 검사): 
                        # PDF 내장 텍스트가 "n フ I 업과시장" 처럼 깨져 있어도 "기업과시장"을 60% 이상 매칭하면 정답으로 간주
                        ratio = difflib.SequenceMatcher(None, target_text, clean_line).ratio()
                        if target_text in clean_line or ratio >= 0.55:
                            # 폰트 사이즈 업데이트 (제일 큰 폰트 기준)
                            found_size = max(found_size, max_size)
                            
            if found_size > 0:
                # 찾은 사이즈보다 아주 살짝 작은 값(오차 감안)을 커트라인으로 세팅
                r["size_threshold"] = found_size - 0.5
            else:
                raise Exception(f"'{r['text']}' 텍스트를 초반 20쪽에서 찾을 수 없습니다. 오타를 확인하거나 다른 확실한 제목을 입력해보세요.")

    def extract_toc(self, rules):
        """
        확정된 규칙(rules)을 바탕으로 PDF 전체를 훑어 목차를 추출하고 위계를 잡습니다.
        """
        doc = fitz.open(self.pdf_path)
        self.detect_font_sizes(doc, rules) # 폰트 크기 자동 역추적 가동!
        
        extracted = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if "lines" not in block: continue
                for line in block["lines"]:
                    line_text = ""
                    max_size = 0
                    is_bold = False
                    
                    for span in line["spans"]:
                        txt = span["text"].strip()
                        if txt:
                            line_text += txt + " "
                            max_size = max(max_size, span["size"])
                            if "Bold" in span["font"] or "Bold" in span["font"].upper():
                                is_bold = True
                                
                    line_text = line_text.strip()
                    if not line_text: continue
                    
                    # 수립된 규칙(폰트 크기 or 정규식)들과 하나하나 매칭해봅니다.
                    matched_level = None
                    for r in rules:
                        if r["type"] == "font":
                            if max_size >= r["size_threshold"]:
                                matched_level = r["level"]
                                break
                        elif r["type"] == "regex":
                            # 정규식 패턴은 기본적으로 본문보다 폰트가 크거나 굵어야(Bold) 인정
                            if max_size > 8.3 or is_bold:
                                if re.match(r["pattern"], line_text):
                                    matched_level = r["level"]
                                    break
                                    
                    if matched_level:
                        extracted.append({
                            "level": matched_level,
                            "title": line_text,
                            "page": page_num + 1
                        })

        # --- 트리(위계) 구조 조립 ---
        hierarchy = []
        stack = []
        
        for item in extracted:
            node = {"title": item["title"], "page": item["page"], "children": []}
            level = item["level"]
            
            while stack and stack[-1]["level"] >= level:
                stack.pop()
                
            if not stack:
                hierarchy.append(node)
            else:
                stack[-1]["node"]["children"].append(node)
                
            stack.append({"level": level, "node": node})
            
        # JSON 및 OPML 저장 처리
        out_dir = os.path.dirname(self.pdf_path)
        base_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
        
        with open(os.path.join(out_dir, f"{base_name}_toc.json"), 'w', encoding='utf-8') as f:
            json.dump(hierarchy, f, ensure_ascii=False, indent=4)
            
        self.export_to_opml(hierarchy, os.path.join(out_dir, f"{base_name}_toc.opml"))
        doc.close()

    def build_opml_elements(self, parent_element, nodes):
        """XML 생성용 헬퍼 함수"""
        for node in nodes:
            outline = ET.SubElement(parent_element, 'outline', text=node["title"])
            if node["children"]:
                self.build_opml_elements(outline, node["children"])

    def export_to_opml(self, hierarchy, output_path):
        """마진노트, Logseq 연동을 위한 OPML 파일 생성"""
        opml = ET.Element('opml', version='2.0')
        head = ET.SubElement(opml, 'head')
        ET.SubElement(head, 'title').text = "CPA Supergap TOC"
        body = ET.SubElement(opml, 'body')
        
        self.build_opml_elements(body, hierarchy)
        
        xml_str = ET.tostring(opml, encoding='utf-8')
        pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)

if __name__ == "__main__":
    root = tk.Tk()
    app = TOCExtractorApp(root)
    root.mainloop()
