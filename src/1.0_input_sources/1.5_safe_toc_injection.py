import json
import fitz
import os

def inject_toc_safely(json_path, pdf_path, output_path, page_offset):
    """
    안전한 PDF 목차(TOC) 주입 함수 (재무관리 가이드북 워크플로우 백업용)
    - json_path: 계층형 목차 데이터가 담긴 JSON 파일 경로
    - pdf_path: 단원별로 분할된 원본 PDF 파일 경로 (읽기 전용)
    - output_path: 목차가 주입되어 새롭게 생성될 PDF 파일 경로 (안전 원칙)
    - page_offset: 원본 인쇄 페이지 번호와 분할된 PDF 물리 페이지 번호 간의 오프셋 조정값
    """
    # 1. JSON 파일 읽기 (원본 보존)
    with open(json_path, 'r', encoding='utf-8') as f:
        toc_data = json.load(f)

    toc_list = []
    
    # 2. 계층형 데이터를 평면화(Flatten)하는 재귀 함수
    def traverse(nodes, level):
        for node in nodes:
            title = node.get("title", "")
            
            # 페이지 오프셋 적용 및 최소 페이지(1) 방어 로직
            # 인덱스 오류 방지를 위해 1보다 작은 페이지 번호가 나오지 않도록 보정
            target_page = max(1, node.get("page", 1) + page_offset)
            
            # PyMuPDF TOC 포맷: [레벨(int), 제목(str), 물리적 페이지(int)]
            toc_list.append([level, title, target_page])
            
            if "children" in node:
                traverse(node["children"], level + 1)

    # 3. 데이터 변환 실행
    traverse(toc_data, 1)

    # 4. 비파괴적 PDF 수정 및 새 파일 저장
    try:
        doc = fitz.open(pdf_path)
        doc.set_toc(toc_list)        # 추출된 목차 리스트를 PDF에 덮어씌움
        doc.save(output_path)        # 원본을 덮어쓰지 않고 새로운 이름으로 저장!
        doc.close()
        print(f"Injection successful! Saved to: {output_path}")
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")

# ----------------- 실행부 (Step-by-Step) -----------------
if __name__ == "__main__":
    # 예시: 챕터 2 단일 대상 타겟팅 및 오프셋(-23) 적용
    JSON_FILE = r"C:\Users\greme\Desktop\재무관리_단원별_최종\chap2_toc.json"
    SOURCE_PDF = r"C:\Users\greme\Desktop\재무관리_단원별_최종\Chapter_02.pdf"
    OUTPUT_PDF = r"C:\Users\greme\Desktop\재무관리_단원별_최종\Chapter_02_목차주입본.pdf"
    OFFSET = -23

    # 실제 실행 시 주석 해제하여 사용
    # inject_toc_safely(JSON_FILE, SOURCE_PDF, OUTPUT_PDF, OFFSET)
    pass
