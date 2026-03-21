---
name: patent-drawing
description: Generate USPTO-compliant patent drawings using Python matplotlib. Use when creating patent figures (block diagrams, flowcharts, data flow diagrams, system architecture), generating FIG. 1-N drawings for patent specifications, or fixing/regenerating existing patent drawings. Triggers on "patent drawing", "도면 생성", "FIG.", "특허 도면", "USPTO drawing".
---

# Patent Drawing Skill

Generate USPTO-compliant patent drawings using the `patent_drawing_lib.py` library (v2.6).

## Setup

Library location: `<skill_dir>/patent_drawing_lib.py`

Import in drawing scripts:
```python
import sys
sys.path.insert(0, '<skill_dir>')
from patent_drawing_lib import Drawing
```

## Quick Start

```python
d = Drawing("fig1.png", fig_num="1")
d.boundary(0.55, 1.10, 7.90, 10.15, label='1000')

# ✅ 참조번호는 반드시 첫 줄, 그 뒤에 개행(\n)
b1 = d.box(2.0, 8.5, 4.0, 0.7, '100\nMy Component')
b2 = d.box(2.0, 7.3, 4.0, 0.7, '200\nNext Component')

d.arrow_v(b1, b2)
d.save()  # 자동 검증 + 저장
```

## ⚠️ 절대 규칙 (위반 시 도면 재생성)

### 1. 참조번호 배치
- 참조번호는 **반드시 텍스트 맨 첫 줄**에 단독 배치
- 참조번호 뒤에 **반드시 개행문자(\n)** 추가하여 본문과 분리
- 다른 도면 참조(교차참조)는 "see 810", "ref. 200" 형태로 별도 표기 가능

```python
# ✅ 올바른 예
'806\nMulti-Touch Attribution Engine'
'200\nPlatform Dashboard / Settlement System'

# ❌ 잘못된 예
'Multi-Touch Attribution Engine  806'     # 뒤에 붙음
'806  Multi-Touch Attribution Engine'     # 개행 없이 같은 줄
'Platform Dashboard / Settlement System  200'  # 뒤에 붙음
```

### 2. 화살표 양쪽 끝 도형 연결 (Dangling 금지)
- 모든 화살표의 **머리(head)와 꼬리(tail)는 반드시 어떤 박스의 변(edge)에 연결**
- 어떤 도형에도 안 닿는 화살표 → 잘못 그린 것 또는 불필요 → 즉시 제거/수정
- 라이브러리 v2.6이 자동 검증: `Dangling head/tail detected` 경고

### 3. 화살표 최소 길이
- 화살표는 **"화살표처럼 보여야"** 한다 — 촉(▶)만 보이고 shaft(선)가 없으면 실패
- **최소 shaft: 0.44"** (라이브러리 MIN_ARROW)
- **라벨 있는 화살표: 최소 0.80"** (라벨 텍스트가 보여야 함)
- 길이 부족 → **한두 박스만 밀지 말고 전체 도형 재배치**

### 4. 화살표 라벨 공간
- 화살표에 라벨이 있는데 도형 사이 간격이 부족하면 → 라벨이 잘려서 안 보임
- 해결: **도형 간 거리 확보를 위해 전체 레이아웃 재배치**
- 최소 라벨 구간 shaft: 0.80"

### 5. 화살촉이 도착 박스에 의해 가려지는 문제
- 화살표 shaft(선)는 박스 fill 뒤로 숨는 것이 정상 (깔끔한 진입)
- 하지만 **화살촉(▶)까지 가려지면 안 됨** — 화살표가 끊긴 것처럼 보임
- 근본 원인: 화살촉 zorder가 박스 fill zorder보다 낮을 때 발생
- 라이브러리 v5.1에서 Z_ARROWHEAD=13으로 수정하여 해결됨
- **검증**: 도착 박스 상단/좌측에 화살촉이 보이는지 비전 검증 시 확인

### 6. 화살표가 텍스트 관통 금지
- 화살표 경로가 다른 박스의 텍스트를 **관통(취소선처럼 보이는 현상)하면 안 됨**
- 해결: 화살표 방향 변경 또는 박스 위치 재배치

## 도면 생성 후 필수 검증 절차

### Step 1: 라이브러리 자동 검증 확인
`save()` 호출 시 자동 검증. `✓`이면 통과, `⚠`이면 반드시 수정.
```
✓  fig1.png                    → 통과
⚠  fig1.png                    → 수정 필요
   · Dangling head detected     → 화살표 끝이 도형에 안 닿음
   · Arrow too short             → 도형 간격 확보 필요
   · ref number at END           → 참조번호를 첫 줄로 이동
   · Labeled arrow too short     → 라벨 공간 확보 필요
```

### Step 2: 비전 모델 검증 (생성 후 반드시 실행)
이미지를 비전 모델에 보내서 확인:
```
화살표들이 모두 논리적으로 올바른지, 이상한 화살표
(방향 오류, dead-end, 겹침, 어색한 경로, 텍스트 관통)가 있는지 확인해줘
```

### Step 3: 체크리스트 (수동 확인)
아래 항목 중 ✅ 표시는 라이브러리가 자동 검증. 비전 모델로 확인 필요한 항목만 수동 체크.

- ✅ 모든 화살표의 머리/꼬리가 도형에 연결되어 있는가? (검증 #7)
- ✅ 화살표 shaft가 최소 0.44" 이상인가? (검증 #4)
- ✅ 화살표 라벨이 잘려 보이지 않는 곳은 없는가? (검증 #8)
- ✅ 참조번호가 박스 내부 맨 첫 줄에 있는가? (검증 #6, #9c)
- ✅ 참조번호가 아예 없는 박스는 없는가? (검증 #9c)
- ✅ 텍스트가 10pt 이상인가? (검증 #9a)
- ✅ 특수기호/유니코드 아래첨자 없는가? (검증 #9b)
- ✅ dead-end 노드(출력 화살표 없는 중간 박스)가 없는가? (검증 #10)
- ✅ 화살표가 다른 박스 텍스트를 관통하지 않는가? (검증 #11)
- [ ] 모든 박스 텍스트가 잘림 없이 완전히 보이는가? (비전 확인)
- [ ] 화살촉(▶)이 도착 박스의 흰색 fill에 가려지지 않는가? (비전 확인)
- [ ] 화살표 방향이 논리적으로 올바른가? (비전 확인)

### Step 4: 문제 발견 시
1. 코드 수정
2. 재생성
3. Step 1~3 반복
4. `✓` + 비전 통과 + 체크리스트 전체 통과 시에만 완료

## API Reference

### 핵심 메서드
| 메서드 | 용도 |
|--------|------|
| `Drawing(filename, fig_num)` | 새 도면 생성 |
| `boundary(x1,y1,x2,y2,label)` | 전체 시스템 경계 (dashed) |
| `box(x,y,w,h,text,fs)` | 박스 + 텍스트 (→ BoxRef) |
| `arrow_v(src,dst,label)` | 수직 직선 화살표 |
| `arrow_h(src,dst,label)` | 수평 직선 화살표 |
| `arrow_route(steps,label,label_pos)` | 꺾인 화살표 |
| `line(x1,y1,x2,y2)` | 화살촉 없는 연결선 |
| `label(x,y,text)` | 독립 텍스트 라벨 |
| `fig_label(y)` | FIG. N 라벨 |
| `save()` | 렌더링 + 자동 검증 + PNG 저장 |

### BoxRef 속성
```python
b.cx, b.cy         # 중심 좌표
b.top, b.bot        # 상하 y
b.left, b.right     # 좌우 x
b.top_mid()         # (cx, top)
b.bot_mid()         # (cx, bot)
b.left_mid()        # (left, cy)
b.right_mid()       # (right, cy)
b.side("top")       # top_mid() 과 동일
```

### arrow_route steps 명령어
```python
(x, y)              # 절대 좌표
("right_to", x)     # x까지 수평 이동
("left_to", x)      # x까지 수평 이동
("up_to", y)        # y까지 수직 이동
("down_to", y)      # y까지 수직 이동
("right", dx)       # dx만큼 우측
("left", dx)        # dx만큼 좌측
("up", dy)          # dy만큼 상승
("down", dy)        # dy만큼 하강
```

## 라이브러리 자동 검증 항목 (v5.2)

| # | 검증 | 내용 |
|---|------|------|
| 1 | 박스 boundary 내부 | 모든 박스가 boundary 안에 있는지 |
| 2 | 박스 마진 | boundary와 최소 0.30" 여백 |
| 3 | 라벨 boundary 내부 | 독립 라벨이 boundary 넘지 않는지 |
| 4 | 화살표 최소 길이 | shaft ≥ 0.44" (MIN_ARROW) |
| 5 | 라벨 박스 겹침 | 라벨이 박스 내부에 위치하는지 |
| 6 | 참조번호 위치 | 텍스트 뒤에 참조번호 붙으면 경고 |
| 7 | 화살표 양끝 연결 | Dangling head/tail 감지 |
| 8 | 라벨 화살표 길이 | 라벨 있는 화살표 shaft ≥ 0.80" |
| 0 | 텍스트 박스 초과 | 실측 렌더링 크기로 텍스트가 박스 밖으로 나가는지 검사 |
| 9a | 텍스트 최소 10pt | auto-fit 결과가 10pt 미달이면 경고 (§1.84(p)(3)) |
| 9b | 특수기호/아래첨자 | ★ © ₁ 등 인쇄 불안전 문자 감지 |
| 9c | 참조번호 누락 | 박스 첫 줄에 3~4자리 숫자 없으면 경고 |
| 10 | Dead-end 박스 | 입력↑ 출력=0인 중간 박스 자동 감지 |
| 11 | 화살표 관통 | 화살표 경로가 박스 텍스트 영역 관통 감지 |

## USPTO 형식 규칙

| 규칙 | 내용 |
|------|------|
| 텍스트 크기 | 최소 10pt (§1.84(p)(3)) |
| 폰트 | 균일 weight, bold 금지 (§1.84(p)(1)) |
| 색상 | 흑백만, 회색 음영 금지 (§1.84(m)) |
| FIG. 라벨 | `FIG. N` 형식, boundary 아래 중앙 (§1.84(u)) |
| 참조번호 | 모든 요소에 번호. 도면 = 명세서 번호 (§1.84(p)) |
| 특수기호 | ★ 같은 장식 기호 지양, 텍스트로 대체 |
| 아래첨자 | t₁ → t1 (인쇄 안전성) |

## 레이아웃 설계 원칙

### 도형 재배치 우선 원칙
- 화살표 길이 부족 → **해당 화살표만 늘리지 말고 전체 도형 재배치**
- 라벨 공간 부족 → **전체 레이아웃 재조정**
- 한 도형만 밀면 다른 곳에서 문제 발생 → 연쇄 수정 필요

### 라우팅 채널 패턴 (피드백 루프)
```
Left channels:  x < content_left
Content column: CL ~ CR
Right channel:  x > content_right
```

### 박스 간격 가이드
| 구간 | 최소 간격 |
|------|-----------|
| 수직 화살표 (라벨 없음) | 0.44" |
| 수직 화살표 (라벨 있음) | 0.80" |
| 수평 화살표 (라벨 없음) | 0.44" |
| 수평 화살표 (라벨 있음) | 0.80" |
| 박스 ↔ boundary | 0.30" |

## 과거 실수 교훈 (반복 금지)

| 실수 | 근본 원인 | 해결 |
|------|-----------|------|
| 참조번호 텍스트 뒤에 붙음 | 습관적으로 "Description 200" 형태 사용 | 첫 줄에 번호 단독 + \n |
| 화살표가 텍스트 관통 (취소선처럼 보임) | 박스 옆에 바로 붙여서 수평 화살표 | 박스 위/아래로 우회하거나 재배치 |
| 화살표 촉만 보이고 shaft 없음 | 도형 간격 0.2" 등 부족 | 전체 재배치로 0.44" 이상 확보. 10+ 박스 시 박스 높이(min 0.45")를 줄이되 간격(min 0.40")은 절대 줄이지 말 것. 분기점 전후는 0.45" 이상 |
| 라벨 잘려서 안 보임 | 도형 사이 공간에 라벨이 안 들어감 | 도형 간 0.80" 이상 확보 |
| dead-end 박스 | 출력 화살표 연결 누락 | 생성 후 비전 모델로 검증 |
| "model config" 화살표 뜬금없음 | 화살표 양쪽 끝이 도형 안 닿음 | Dangling 검증 통과 필수 |
| 동사 시제 불일치 | viewed/browsed vs add/purchase | 동일 카테고리 내 시제 통일 |
| float 오차로 0.44"가 경고 | 부동소수점 비교 | 라이브러리에 epsilon 보정 적용됨 |
| 화살촉이 도착 박스에 가려짐 | Z_ARROWHEAD < Z_BOX_FILL + 대각선 화살촉 날개가 박스 안으로 진입 | Z_ARROWHEAD=13 + 대각선 금지: arrow_v 사용 시 cx 같은지 확인, 다르면 elbow 라우팅 |
| arrow_v로 cx 다른 박스 연결 시 대각선 | arrow_v가 src.cx→dst.cx 직선이라 cx 다르면 사선 | cx 다르면 arrow_route로 elbow(수직+수평+수직) 사용 |
| 화살표 라벨이 인접 박스 텍스트와 겹침 | 좌측 채널 수직 구간에 라벨 배치 시 옆 박스와 근접 | label_pos를 박스가 없는 구간으로 변경. 공간 부족 시 라벨 제거(명세서에서 설명) |
| elbow 화살표 경유점이 밀집하여 교차/혼잡 | 여러 elbow가 같은 VIA_Y에서 수평 이동 | 출발점을 src 하변에서 분산, 각각 다른 x에서 출발 |
| 피드백 루프 라벨이 boundary 밖으로 벗어남 | 좌측/우측 채널이 boundary edge에 너무 가까움 | 라벨 제거하고 화살표만 유지, 또는 채널 x를 boundary+0.30 이상으로 |
