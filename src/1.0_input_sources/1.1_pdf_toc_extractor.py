import os
import sys
import platform
import yaml
from pathlib import Path

# PyMuPDF
try:
    import fitz
except ImportError:
    print("PyMuPDF(fitz) 라이브러리가 설치되지 않았습니다. 'pip install -r requirements.txt'를 실행해주세요.")
    sys.exit(1)

def load_config():
    """운영체제에 맞는 환경 설정을 config.yaml에서 불러옵니다."""
    # 현재 스크립트 위치 기준으로 config.yaml 경로 탐색 (상대 경로로 OS 독립적 확보)
    base_dir = Path(__file__).resolve().parent.parent.parent
    config_path = base_dir / "config" / "config.yaml"
    
    if not config_path.exists():
        print(f"설정 파일을 찾을 수 없습니다: {config_path}")
        sys.exit(1)
        
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)
        
    os_system = platform.system().lower()
    if os_system == "windows":
        print("[System] Windows 환경을 감지했습니다.")
        return config_data.get("windows", {})
    elif os_system == "darwin":
        print("[System] macOS 환경을 감지했습니다.")
        return config_data.get("mac", {})
    else:
        print(f"[System] 지원하지 않는 OS입니다: {os_system}")
        sys.exit(1)

def extract_toc_from_pdf(pdf_path):
    """PDF 파일에서 내장된 북마크(TOC)를 추출합니다."""
    print(f"📄 PDF 분석 중: {pdf_path.name}")
    try:
        doc = fitz.open(pdf_path)
        toc = doc.get_toc() # 형식: [[level, title, page_number], ...]
        doc.close()
        return toc
    except Exception as e:
        print(f"❌ PDF 열기 실패: {e}")
        return []

def generate_opml(toc, output_path):
    """추출된 TOC를 바탕으로 MarginNote 임포트용 OPML 파일을 생성합니다."""
    if not toc:
        print("⚠️ 목차(TOC) 데이터가 없습니다. OPML을 생성하지 않습니다.")
        return
        
    print(f"📝 OPML 생성 시작 (총 {len(toc)}개 노드)")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<opml version="2.0">\n')
        f.write('  <head>\n')
        f.write(f'    <title>CPA MarginNote Import</title>\n')
        f.write('  </head>\n')
        f.write('  <body>\n')
        
        current_level = 0
        for item in toc:
            level, title, page = item
            
            # 특수문자 이스케이프
            title_safe = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;")
            
            # 레벨이 깊어질 때
            if level > current_level:
                pass # 이전 노드를 닫지 않고 열어둠 (계층 구조)
            # 레벨이 같거나 얕아질 때
            elif level <= current_level:
                # 닫아야 할 만큼 닫음
                for _ in range(current_level - level + 1):
                    f.write("  " * (current_level + 1) + "</outline>\n")
                    current_level -= 1
            
            # 현재 노드 열기
            f.write("  " * (level) + f'<outline text="{title_safe}">\n')
            current_level = level
            
        # 남은 태그 모두 닫기
        while current_level > 0:
            f.write("  " * (current_level) + "</outline>\n")
            current_level -= 1
            
        f.write('  </body>\n')
        f.write('</opml>\n')
        
    print(f"✅ OPML 저장 완료: {output_path}")

def main():
    config = load_config()
    
    pdf_input_dir = Path(config.get("pdf_input_dir", ""))
    output_dir = Path(config.get("output_dir", ""))
    
    # 출력 폴더 생성 (없으면)
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 출력 폴더를 생성했습니다: {output_dir}")
        
    if not pdf_input_dir.exists():
        print(f"❌ PDF 입력 폴더를 찾을 수 없습니다: {pdf_input_dir}")
        print("config.yaml의 경로 설정을 확인해주세요.")
        sys.exit(1)
        
    # PDF 폴더 탐색
    pdf_files = list(pdf_input_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"⚠️ {pdf_input_dir} 에 PDF 파일이 없습니다.")
        return
        
    for pdf_path in pdf_files:
        toc_data = extract_toc_from_pdf(pdf_path)
        if toc_data:
            out_filename = pdf_path.stem + "_MarginNote_Import.opml"
            out_filepath = output_dir / out_filename
            generate_opml(toc_data, out_filepath)

if __name__ == "__main__":
    main()
