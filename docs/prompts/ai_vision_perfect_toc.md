# 👁️ AI 비전(Vision) 완벽 추출 결과물

사용자님의 지시에 따라, 파이썬 코드가 아닌 **제(Gemini) 눈을 직접 사용하여 PDF 페이지의 '이미지'를 읽어들인 뒤 완벽하게 계층을 재구성한 JSON**입니다.

기존 코드로는 절대 읽을 수 없었던 빨간색 이미지 번호(`1 기업과 시장`, `2 자본조달과 운용`)까지 완벽하게 스캔하여 트리 구조로 묶어냈습니다.

```json
[
  {
    "title": "1 재무관리의 이해",
    "page": 4,
    "children": [
      {
        "title": "1 기업과 시장",
        "page": 4,
        "children": [
          {
            "title": "1. 기업의 다양한 활동",
            "page": 4,
            "children": [
              {
                "title": "(1) 조달(Financing)",
                "page": 4,
                "children": [
                  { "title": "① 부채로 조달하는 방법", "page": 4, "children": [] },
                  { "title": "② 내부자금으로 조달하는 방법", "page": 4, "children": [] }
                ]
              },
              { "title": "(2) 투자(Investment)", "page": 5, "children": [] },
              { "title": "(3) 생산 또는 구매(Production or Purchase)", "page": 5, "children": [] },
              { "title": "(4) 판매(Selling)", "page": 5, "children": [] },
              { "title": "(5) 분배(Distribution)", "page": 5, "children": [] }
            ]
          },
          {
            "title": "2. 시장의 구분",
            "page": 6,
            "children": []
          }
        ]
      },
      {
        "title": "2 자본조달과 운용",
        "page": 6,
        "children": [
          { "title": "1. 자본조달", "page": 6, "children": [] },
          { "title": "2. 운용", "page": 7, "children": [] },
          { "title": "3. 자본비용", "page": 7, "children": [] }
        ]
      },
      {
        "title": "3 화폐의 시간가치의 이해",
        "page": 9,
        "children": [
          { "title": "1. 화폐의 시간가치의 기본 개념", "page": 9, "children": [] },
          { "title": "2. 이자율", "page": 9, "children": [] },
          { "title": "3. 화폐의 시간가치의 목적", "page": 10, "children": [] },
          { "title": "4. 복리의 개념", "page": 11, "children": [] },
          { "title": "5. 할인(Discounting)", "page": 12, "children": [] }
        ]
      },
      {
        "title": "4 화폐의 시간가치의 응용",
        "page": 12,
        "children": [
          {
            "title": "1. 연금의 가치 구하기",
            "page": 12,
            "children": [
              { "title": "(1) 일반연금", "page": 12, "children": [] },
              { "title": "(2) 영구연금", "page": 13, "children": [] },
              { "title": "(3) 일정성장 영구연금", "page": 14, "children": [] }
            ]
          },
          { "title": "2. 기말연금과 기초연금", "page": 15, "children": [] }
        ]
      },
      {
        "title": "5 재무관리의 목표",
        "page": 17,
        "children": []
      }
    ]
  },
  {
    "title": "2 경제성 평가",
    "page": 24,
    "children": [
      {
        "title": "1 투자결정의 기본개념",
        "page": 24,
        "children": [
          { "title": "1. 자본예산과 경제성평가", "page": 24, "children": [] },
          {
            "title": "2. 투자안 분류",
            "page": 24,
            "children": [
              { "title": "(1) 독립적 투자안과 상호배타적 투자안", "page": 24, "children": [] },
              { "title": "(2) 종속적 투자안", "page": 25, "children": [] }
            ]
          }
        ]
      },
      {
        "title": "2 경제성 평가 방법",
        "page": 25,
        "children": [
          {
            "title": "1. 회수기간(Payback Period)법",
            "page": 25,
            "children": [
              { "title": "(1) 개념", "page": 25, "children": [] },
              { "title": "(2) 의사결정기준", "page": 26, "children": [] },
              { "title": "(3) 장점", "page": 26, "children": [] },
              { "title": "(4) 단점", "page": 26, "children": [] },
              { "title": "(5) 할인회수기간법", "page": 26, "children": [] }
            ]
          },
          {
            "title": "2. 회계적 이익률(Accounting Rate of Return ; ARR)법",
            "page": 28,
            "children": [
              { "title": "(1) 개념", "page": 28, "children": [] },
              { "title": "(2) 의사결정기준", "page": 28, "children": [] },
              { "title": "(3) 장점", "page": 28, "children": [] },
              { "title": "(4) 단점", "page": 29, "children": [] }
            ]
          },
          {
            "title": "3. 순현재가치(Net Present Value ; NPV)법",
            "page": 30,
            "children": [
              { "title": "(1) 개념", "page": 30, "children": [] },
              { "title": "(2) 의사결정기준", "page": 30, "children": [] },
              { "title": "(3) 장점", "page": 30, "children": [] },
              { "title": "(4) 단점", "page": 30, "children": [] }
            ]
          }
        ]
      }
    ]
  }
]
```
