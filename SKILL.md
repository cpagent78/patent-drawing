---
name: patent-drawing
description: Generate USPTO-compliant patent drawings using Python matplotlib. Use when creating patent figures (block diagrams, flowcharts, data flow diagrams, system architecture), generating FIG. 1-N drawings for patent specifications, or fixing/regenerating existing patent drawings. Triggers on "patent drawing", "도면 생성", "FIG.", "특허 도면", "USPTO drawing".
version: 3.0.0
---

# Patent Drawing Skill v3.0

USPTO 규격 특허 도면을 Python + matplotlib으로 자동 생성한다.
좌표 계산 없이 선언형 API로 9종 도면 타입을 지원한다.

**라이브러리 위치:** `<skill_dir>/scripts/`

## 지원 도면 타입 (9종)

| 타입 | 클래스 | `--type` | 용도 |
|------|--------|----------|------|
| 플로우차트 / 블록 다이어그램 | `PatentFigure` | `flowchart` | 처리 흐름, 시스템 구성도 |
| 시퀀스 다이어그램 | `PatentSequence` | `sequence` | 행위자 간 메시지 흐름 |
| 상태 다이어그램 | `PatentState` | `state` | FSM, 상태 전이 |
| 하드웨어 블록 | `PatentHardware` | `hardware` | 하드웨어 구성, 회로 |
| 계층 아키텍처 | `PatentLayered` | `layered` | 소프트웨어 레이어 |
| 타이밍 다이어그램 | `PatentTiming` | `timing` | 신호, 시간 축 |
| 데이터 플로우 | `PatentDFD` | `dfd` | DFD, 프로세스↔스토어 |
| ER 다이어그램 | `PatentER` | `er` | 엔티티 관계 |
| 도면 세트 | `PatentSuite` | — | 여러 도면 → PDF |

---

## Quick Start — quick_draw() 한 줄 생성

```python
import sys
sys.path.insert(0, '<skill_dir>/scripts')
from patent_figure import quick_draw

spec = """
S100: 사용자 로그인 요청
S200: 토큰 검증
S300: 검증 실패? (Yes→S400, No→S500)
S400: 오류 응답 반환
S500: 대시보드 이동
"""
result = quick_draw(spec, 'fig1.png')
print(result['pages'])     # ['fig1.png']
print(result['warnings'])  # [] if clean
```

**quick_draw() 파라미터:**

```python
quick_draw(
    spec_text,              # 명세서 텍스트 (한글/영어 자동 감지)
    output_path,            # 출력 PNG 경로
    preset='uspto',         # 'uspto' | 'draft' | 'presentation'
    direction='TB',         # 'TB' (위→아래) | 'LR' (좌→우)
    fig_label='FIG. 1',     # 도면 번호
    diagram_type='flowchart' # 9종 타입 중 선택
)
# Returns: {'pages': [...], 'node_count': int, 'warnings': [...], 'validation': {...}}
```

---

## PatentFigure (플로우차트/블록 다이어그램)

```python
from patent_figure import PatentFigure

fig = PatentFigure('FIG. 1', direction='TB')  # 'TB' | 'LR'

# 노드 정의 (shape: process/start/end/diamond/oval/cylinder)
fig.node('S100', '시작', shape='start')
fig.node('S200', '데이터 처리')
fig.node('S300', '검증 성공?', shape='diamond')
fig.node('S400', '오류 처리', shape='end')
fig.node('S500', '완료', shape='end')

# 엣지 (화살표)
fig.edge('S100', 'S200')
fig.edge('S200', 'S300')
fig.edge('S300', 'S400', label='No')
fig.edge('S300', 'S500', label='Yes')

# 그룹 박스 (점선)
fig.container('grp1', ['S200', 'S300'], label='310\nProcessing Group')

fig.render('fig1.png')
```

**from_spec() — 텍스트 파싱:**
```python
fig = PatentFigure.from_spec('FIG. 2', """
S100: 사용자 요청
S200: 처리
S300: 완료
""")
fig.render('fig2.png')
```

---

## PatentSequence (시퀀스 다이어그램)

```python
from patent_figure import PatentSequence

seq = PatentSequence('FIG. 3')
seq.actor('Client')
seq.actor('Server')
seq.actor('DB')

seq.message('Client', 'Server', 'POST /login')
seq.message('Server', 'DB', 'SELECT user')
seq.message('DB', 'Server', 'user row', return_arrow=True)
seq.message('Server', 'Client', '200 OK', return_arrow=True)

seq.render('fig3.png')
```

---

## PatentState (상태 다이어그램)

```python
from patent_figure import PatentState

st = PatentState('FIG. 4')
st.state('IDLE', '대기 상태')
st.state('ACTIVE', '활성')
st.state('ERROR', '오류')

st.transition('IDLE', 'ACTIVE', '요청 수신')
st.transition('ACTIVE', 'IDLE', '완료')
st.transition('ACTIVE', 'ERROR', '오류 발생')
st.transition('ERROR', 'IDLE', '초기화')

st.render('fig4.png')
```

---

## PatentHardware (하드웨어 블록)

```python
from patent_figure import PatentHardware

hw = PatentHardware('FIG. 5')
hw.node('100', 'CPU')
hw.node('200', 'Memory Controller')
hw.node('300', 'DRAM')
hw.node('400', 'Flash Storage')

hw.connect('100', '200', 'PCIe x16')
hw.connect('200', '300', 'DDR5')
hw.connect('200', '400', 'NVMe')

hw.render('fig5.png')
```

---

## PatentLayered (계층 아키텍처)

```python
from patent_figure import PatentLayered

lay = PatentLayered('FIG. 6')
lay.layer('UI', ['웹 브라우저', '모바일 앱'])
lay.layer('API', ['REST Gateway', 'GraphQL'])
lay.layer('Service', ['인증', '결제', '추천'])
lay.layer('Data', ['PostgreSQL', 'Redis', 'S3'])

lay.render('fig6.png')
```

---

## PatentTiming (타이밍 다이어그램)

```python
from patent_figure import PatentTiming

tim = PatentTiming('FIG. 7')
tim.signal('CLK',  [0,1,0,1,0,1,0,1])
tim.signal('DATA', [0,0,1,1,0,0,1,1])
tim.signal('ACK',  [0,0,0,1,1,0,0,0])

tim.render('fig7.png')
```

---

## PatentDFD (데이터 플로우)

```python
from patent_figure import PatentDFD

dfd = PatentDFD('FIG. 8')
dfd.process('P1', '주문 처리')
dfd.store('D1', '주문 DB')
dfd.entity('E1', '고객')

dfd.flow('E1', 'P1', '주문 요청')
dfd.flow('P1', 'D1', '저장')

dfd.render('fig8.png')
```

---

## PatentER (ER 다이어그램)

```python
from patent_figure import PatentER

er = PatentER('FIG. 9')
er.entity('User', ['id', 'name', 'email'])
er.entity('Order', ['id', 'date', 'total'])
er.entity('Product', ['id', 'name', 'price'])

er.relation('User', 'Order', '1', 'N', '주문')
er.relation('Order', 'Product', 'N', 'M', '포함')

er.render('fig9.png')
```

---

## PatentSuite (도면 세트 + PDF)

```python
from patent_figure import PatentFigure, PatentSequence
from patent_suite import PatentSuite

suite = PatentSuite('My Invention')

fig1 = PatentFigure('FIG. 1')
# ... 노드/엣지 추가 ...
suite.add(fig1, description='System Overview')

fig2 = PatentSequence('FIG. 2')
# ... 추가 ...
suite.add(fig2, description='Login Flow')

suite.render_all(output_dir='./output/')
suite.export_pdf('patent_drawings.pdf')
suite.export_index('index.md')  # 도면 목록 마크다운
```

---

## CLI 사용법

**스크립트 위치:** `<skill_dir>/scripts/patent_draw.py`

```bash
# 단일 도면 생성 (spec 파일)
python patent_draw.py --spec spec.txt --output fig1.png --preset uspto

# 도면 타입 지정
python patent_draw.py --spec spec.txt --type state --output fig2.png

# 인라인 스펙 (한 줄)
python patent_draw.py --inline "S100: Start\nS200: Process\nS100->S200" --output fig.png

# Suite (JSON 디스크립터)
python patent_draw.py --suite suite.json --output-dir ./figs/
```

**suite.json 형식:**
```json
{
  "title": "My Invention",
  "figures": [
    {"type": "flowchart", "spec": "spec1.txt", "label": "FIG. 1",
     "description": "System Overview", "output": "fig1.png"},
    {"type": "sequence", "spec": "spec2.txt", "label": "FIG. 2",
     "description": "Login Flow", "output": "fig2.png"}
  ],
  "export_pdf": "patent_drawings.pdf",
  "export_index": "index.md"
}
```

**지원 --type 값:** `flowchart`, `state`, `sequence`, `layered`, `timing`, `dfd`, `er`

---

## USPTO 규격 핵심 규칙

### 1. 참조번호 위치 (필수)
```python
# ✅ 올바른 — 참조번호 첫 줄, 개행으로 분리
'100\nMy Component'

# ❌ 잘못됨
'My Component 100'    # 뒤에 붙음
'My Component\n100'   # 참조번호가 아래에
```

### 2. 화살표 규칙
- 모든 화살표 양 끝은 반드시 박스 경계에 연결 (dangling 금지)
- 최소 shaft 길이: 0.44" (화살촉만 보이면 안 됨)
- 라벨 있는 화살표: 최소 0.80" shaft

### 3. 자동 검증
`render()` / `save()` 호출 시 자동 검증:
```
✓  fig1.png              → 통과
⚠  fig1.png              → 수정 필요
   · Dangling head        → 화살표 끝 박스에 미연결
   · Arrow too short      → 도형 간격 확보 필요
   · ref number at END    → 참조번호를 첫 줄로
```

### 4. 비전 검증 (생성 후 권장)
```
화살표들이 모두 논리적으로 올바른지, 이상한 화살표
(방향 오류, dead-end, 겹침, 어색한 경로)가 있는지 확인해줘
```

---

## 한글 폰트 안내

라이브러리 임포트 시 자동으로 한글 폰트를 감지·설정한다.

**우선순위:**
1. Apple SD Gothic Neo (macOS — 기본)
2. AppleGothic (macOS 폴백)
3. NanumGothic / NanumMyeongjo (오픈 폰트)
4. Arial Unicode MS (광범위 유니코드)
5. DejaVu Sans (폴백, 한글 미지원이나 graceful)

폰트 감지는 `_setup_korean_font()`가 자동 실행하므로 별도 설정 불필요.

---

## 모모 빠른 시작 가이드

### 사용자가 명세서를 주면 → 이것만 실행

```python
import sys
sys.path.insert(0, '/Users/cpagent/.openclaw/skills/patent-drawing/scripts')
from patent_figure import quick_draw

result = quick_draw(명세서_텍스트, '/tmp/fig1.png')
# diagram_type='auto' 기본값 → 자동으로 타입 감지
print(f"감지된 도면 타입: {result['detected_type']}")
print(f"판단 근거: {result['detection_reason']}")
print(f"신뢰도: {result['detection_confidence']:.2f}")
# 생성 후 image() 도구로 비전 검증 권장
```

### 도면 타입 자동 감지 기준

| 도면 타입 | 감지 키워드/패턴 | 예시 명세서 |
|-----------|-----------------|-------------|
| 플로우차트 | S100, S200 단계 | "S100: 로그인 요청..." |
| 시퀀스 | Actor 간 메시지, HTTP, 요청/응답 | "User → Server: POST /login" |
| 상태 | 상태, 전이, IDLE/ACTIVE | "IDLE 상태에서 이벤트 발생 시..." |
| 계층 | Layer, 계층, 티어 | "Application Layer 위에..." |
| 타이밍 | CLK, 신호, HIGH/LOW | "CLK 신호 rising edge 시..." |
| DFD | 데이터 흐름, 처리, 저장소 | "입력 데이터가 처리 모듈로..." |
| ER | 엔티티, PK, 1:N 관계 | "User 엔티티는 Order와 1:N..." |
| 하드웨어 | 칩, 회로, MCU, 버스 | "MCU에서 ADC를 통해..." |

### 불확실할 때 모모가 물어보는 대화 흐름

`detection_confidence < 0.75` 이면 사용자에게 확인:

> "명세서를 분석한 결과 **[타입]** 도면이 적합해 보입니다. 맞나요?  
> 아니라면 다음 중 선택해주세요: 플로우차트 / 시퀀스 / 상태 / 계층 / 타이밍 / DFD / ER / 하드웨어"

그 후 사용자 선택 결과로 재실행:
```python
result = quick_draw(명세서_텍스트, '/tmp/fig1.png', diagram_type='sequence')
```

### 타입 직접 지정 (자동 감지 무시)

```python
result = quick_draw(spec, '/tmp/fig1.png', diagram_type='state')     # 상태 다이어그램
result = quick_draw(spec, '/tmp/fig1.png', diagram_type='sequence')  # 시퀀스
result = quick_draw(spec, '/tmp/fig1.png', diagram_type='layered')   # 계층 아키텍처
result = quick_draw(spec, '/tmp/fig1.png', diagram_type='timing')    # 타이밍
result = quick_draw(spec, '/tmp/fig1.png', diagram_type='flowchart') # 플로우차트 강제
```

### 스크립트 import 경로 (항상 이 패턴 사용)
```python
import sys
sys.path.insert(0, '/Users/cpagent/.openclaw/skills/patent-drawing/scripts')
from patent_figure import PatentFigure, PatentSequence, quick_draw
from patent_suite import PatentSuite
from detect_type import detect_diagram_type  # 타입만 감지할 때
```

### 도면 생성 체크리스트
1. `quick_draw()` 실행 (diagram_type='auto' 기본값)
2. `result['detection_confidence']` 확인 — 0.75 미만이면 사용자에게 확인
3. `image()` 도구로 비전 검증
4. ⚠ 경고 있으면 수정 후 재생성
