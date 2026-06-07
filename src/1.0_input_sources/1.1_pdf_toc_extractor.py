import fitz  # PyMuPDF 라이브러리: PDF 파일을 읽고 다루기 위한 도구입니다.
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os

def extract_toc_from_pdf(pdf_path):
    """
    PDF 파일에서 목차(TOC) 정보를 추출하는 함수입니다.
    fitz.open()을 통해 문서를 열고, get_toc() 함수로 [계층레벨, 제목, 페이지번호] 리스트를 가져옵니다.
    """
    try:
        # PDF 문서를 엽니다.
        doc = fitz.open(pdf_path)
        # 문서의 목차 정보를 추출합니다.
        # toc 형식: [[1, 'Chapter 1', 5], [2, 'Section 1', 6], ...]
        toc = doc.get_toc()
        doc.close()
        return toc
    except Exception as e:
        print(f"PDF 파싱 중 에러 발생: {e}")
        return []

def build_hierarchy(toc):
    """
    평면적인(flat) 목차 리스트를 트리(Tree) 구조의 딕셔너리로 변환하는 함수입니다.
    하위 목차(자식)를 상위 목차(부모)의 'children' 리스트 안에 넣습니다.
    """
    hierarchy = []
    # 각 레벨별로 가장 최근에 추가된 노드(항목)를 추적하기 위한 스택입니다.
    stack = []
    
    for item in toc:
        level, title, page = item
        # 새 노드를 생성합니다.
        node = {
            "title": title,
            "page": page,
            "children": []
        }
        
        # 현재 레벨이 스택의 길이보다 작거나 같으면, 
        # 즉 이전 항목보다 상위 레벨이거나 같은 레벨이면
        # 스택에서 현재 레벨 이상의 항목들을 빼냅니다(pop).
        while len(stack) >= level:
            stack.pop()
            
        if len(stack) == 0:
            # 스택이 비어있으면 최상위(Root) 레벨이므로 결과 리스트에 직접 추가합니다.
            hierarchy.append(node)
        else:
            # 스택이 비어있지 않으면, 스택의 맨 마지막 항목(부모 노드)의 children에 현재 노드를 추가합니다.
            stack[-1]["children"].append(node)
            
        # 다음 하위 항목을 위해 현재 노드를 스택에 쌓습니다.
        stack.append(node)
        
    return hierarchy

def export_to_json(hierarchy, output_path):
    """
    생성된 트리 구조의 목차를 JSON 파일로 저장하는 함수입니다.
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        # ensure_ascii=False 를 통해 한글이 깨지지 않고 저장되도록 합니다.
        json.dump(hierarchy, f, ensure_ascii=False, indent=4)
    print(f"JSON 파일 생성 완료: {output_path}")

def build_opml_elements(parent_element, nodes):
    """
    XML 구조를 재귀적으로 만들어가는 헬퍼 함수입니다.
    Logseq이나 MarginNote에서 인식할 수 있는 <outline> 태그를 생성합니다.
    """
    for node in nodes:
        # outline 태그를 만들고 text 속성에 목차 제목을 넣습니다.
        outline = ET.SubElement(parent_element, 'outline', text=node["title"])
        # 자식 노드(하위 목차)가 있다면 자기 자신을 다시 호출하여 구조를 완성합니다.
        if node["children"]:
            build_opml_elements(outline, node["children"])

def export_to_opml(hierarchy, output_path):
    """
    생성된 트리 구조의 목차를 OPML 파일로 저장하는 함수입니다.
    OPML은 아웃라이너(Logseq 등) 프로그램에서 주로 쓰이는 XML 기반 규격입니다.
    """
    # OPML 최상위 구조를 잡습니다.
    opml = ET.Element('opml', version='2.0')
    head = ET.SubElement(opml, 'head')
    ET.SubElement(head, 'title').text = "CPA Supergap TOC"
    
    body = ET.SubElement(opml, 'body')
    
    # body 아래에 실제 목차 노드들을 붙여넣습니다.
    build_opml_elements(body, hierarchy)
    
    # 예쁘게 줄바꿈(Indentation) 처리를 하기 위해 minidom을 사용합니다.
    xml_str = ET.tostring(opml, encoding='utf-8')
    parsed_xml = minidom.parseString(xml_str)
    pretty_xml = parsed_xml.toprettyxml(indent="  ")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)
    print(f"OPML 파일 생성 완료: {output_path}")

if __name__ == "__main__":
    # 테스트를 위한 샘플 PDF 파일 경로입니다. (추후 실제 파일 경로로 교체됩니다.)
    # os.path를 이용하여 스크립트 실행 위치에 관계없이 절대경로를 찾아냅니다.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "../.."))
    sample_pdf = os.path.join(project_root, "tests", "samples", "split_part_1.pdf")
    
    # 추출한 결과물을 저장할 경로입니다.
    output_json = os.path.join(project_root, "tests", "samples", "split_part_1_toc.json")
    output_opml = os.path.join(project_root, "tests", "samples", "split_part_1_toc.opml")
    
    print(f"PDF 분석을 시작합니다: {sample_pdf}")
    
    # 1. 목차 추출
    raw_toc = extract_toc_from_pdf(sample_pdf)
    
    if raw_toc:
        print(f"총 {len(raw_toc)}개의 목차 항목이 발견되었습니다.")
        
        # 2. 계층형 트리(Hierarchy)로 변환
        hierarchy_data = build_hierarchy(raw_toc)
        
        # 3. JSON 및 OPML로 저장 (마진노트, Logseq 연동용)
        export_to_json(hierarchy_data, output_json)
        export_to_opml(hierarchy_data, output_opml)
        
        print("모든 작업이 성공적으로 완료되었습니다!")
    else:
        print("목차가 없거나 추출에 실패했습니다. (PDF에 내부 북마크가 없는 경우일 수 있습니다.)")
