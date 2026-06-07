# PDF 분할 및 목차(TOC) 주입 자동화 워크플로우

이 문서는 방대한 분량의 원본 교재(PDF)나 문서를 단원별로 분할하고, 텍스트 형태의 목차 데이터를 구조화하여 분할된 각 PDF 파일에 정확하게 주입(Indexing)하는 전체 자동화 프로세스를 설명합니다.

특정 과목에 국한되지 않고, **어떠한 형태의 대용량 PDF 교재라도 단원별로 깔끔하게 나누고 탐색 가능한 목차를 연동하는 일반적인 방법론**을 다룹니다.

---

## 1. 목차 데이터 추출 및 구조화 (Text to JSON)

원본 교재의 텍스트, OCR 결과, 또는 AI 비전 모델을 통해 목차(TOC) 텍스트를 추출합니다. 추출된 평문 목차를 기계가 읽을 수 있는 계층형 JSON 구조로 변환합니다.

### JSON 구조 예시
```json
[
  {
    "title": "제1장. 기본 개념",
    "page": 4,
    "children": [
      {
        "title": "1. 서론",
        "page": 4
      },
      {
        "title": "2. 본론",
        "page": 10
      }
    ]
  }
]
```
- `title`: 목차에 표시될 제목
- `page`: 원본 교재에 **인쇄되어 있는 논리적인 페이지 번호**
- `children`: 하위 목차 (계층 구조 지원)

---

## 2. 원본 PDF 단원별 분할 (PDF Segmentation)

`PyMuPDF(fitz)` 라이브러리를 사용하여 거대한 마스터 PDF를 챕터별로 쪼개어 개별 파일로 저장합니다. 
이때 원본 PDF의 0-based index(물리적 페이지)를 기준으로 `from_page`와 `to_page`를 설정합니다.

```python
import fitz

src_doc = fitz.open("master_book.pdf")
chapter_doc = fitz.open()

# 물리적 페이지 인덱스 기준 (예: 24번째 장부터 52번째 장까지)
chapter_doc.insert_pdf(src_doc, from_page=23, to_page=51)
chapter_doc.save("Chapter_02.pdf")
chapter_doc.close()
```

---

## 3. 페이지 오프셋 캘리브레이션 (Offset Calibration) ⭐ 핵심

이 워크플로우에서 가장 주의해야 할, **가장 중요한 핵심 단계**입니다.

JSON 데이터에 적힌 페이지는 "책 하단에 적혀 있는 숫자(인쇄된 번호)"입니다. 하지만 분할되어 새로 만들어진 `Chapter_02.pdf` 문서는 **무조건 1페이지부터 다시 시작**하게 됩니다.
따라서 사용자가 PDF 뷰어에서 목차를 클릭했을 때 정확한 위치로 이동하게 하려면 **오프셋(Offset)**을 계산해 주어야 합니다.

### 오프셋 계산 공식
> **`새 PDF의 물리적 페이지 = 책에 인쇄된 페이지 번호 + 오프셋`**

**예시 시나리오:**
- 제2단원이 책의 **24페이지**부터 시작합니다. (JSON의 `page: 24`)
- 분할된 `Chapter_02.pdf`에서는 이 24페이지가 **문서의 첫 번째 장(1페이지)**이 됩니다.
- 계산: `24 + Offset = 1`  $\rightarrow$  **`Offset = -23`**

만약 원본 파일의 표지나 빈 페이지를 분할 파일에 그대로 포함시켰다면, 오프셋은 `0`이 되거나 책에 따라 다르게 변할 수 있으므로, **분할된 새 문서의 첫 내용이 물리적으로 몇 페이지인지 확인하여 역산**해야 합니다.

---

## 4. 목차 데이터 최종 주입 (TOC Injection)

JSON 구조를 순회하면서 계산된 `page_offset`을 적용하여 실제 PDF에 목차를 주입합니다.

### 핵심 코드 로직
```python
import fitz
import json

# 설정값
pdf_path = "Chapter_02.pdf"
json_path = "chap2_toc.json"
output_path = "Chapter_02_TOC_Injected.pdf"
page_offset = -23  # 계산된 오프셋

# JSON 로드
with open(json_path, 'r', encoding='utf-8') as f:
    toc_data = json.load(f)

toc_list = []

# 계층형 JSON을 PyMuPDF 주입 포맷으로 평탄화
def traverse(nodes, level):
    for node in nodes:
        title = node.get("title", "")
        # 인쇄된 페이지에 오프셋을 더해 실제 PDF의 물리적 페이지로 변환
        page = max(1, node.get("page", 1) + page_offset) 
        
        toc_list.append([level, title, page])
        
        if "children" in node:
            traverse(node["children"], level + 1)

traverse(toc_data, 1)

# 문서 열기 및 목차 세팅
doc = fitz.open(pdf_path)
doc.set_toc(toc_list)
doc.save(output_path)
doc.close()
```

## 💡 요약
1. 텍스트 목차를 **계층형 JSON**으로 만든다.
2. 마스터 PDF를 **물리적 페이지(0-index)** 기준으로 분할한다.
3. 원본 책의 페이지와 새로 생성된 PDF의 시작 페이지 차이를 역산하여 **오프셋(Offset)**을 구한다.
4. JSON에 오프셋을 반영하여 **물리적 페이지 번호**를 구한 뒤 PyMuPDF로 주입한다.
