# Patent Drawing Guide — patent_drawing_lib.py v2.6

## 1. 빠른 시작

```python
import sys
sys.path.insert(0, '<skill_dir>')
from patent_drawing_lib import Drawing

d = Drawing("output/fig1.png", fig_num="1")

# 경계 (dashed boundary)
d.boundary(0.55, 1.10, 7.90, 10.15, label='1000')

# ✅ 참조번호 첫 줄 + 개행
b1 = d.box(2.0, 8.5, 4.5, 0.6, '100\nMy Component')
b2 = d.box(2.0, 7.3, 4.5, 0.6, '200\nNext Component')

# 화살표
d.arrow_v(b1, b2)               # 수직 직선
d.arrow_h(b1, b2, label="data") # 수평 직선

# 저장 (자동 검증 포함)
d.save()
```

---

## 2. 핵심 API

### `Drawing(filename, fig_num, dpi=150)`
새 도면 생성. 페이지 크기 8.5" × 11" 고정.

### `box(x, y, w, h, text, fs=None)` → BoxRef
- `x, y`: 박스 **좌하단** 좌표 (인치)
- `w, h`: 가로/세로 크기
- `text`: **첫 줄에 참조번호, \n으로 구분** (`'100\nMy Component'`)
- `fs`: 폰트 크기 (기본 10pt, 긴 텍스트는 7~9 사용)
- 반환: `BoxRef` (`.cx`, `.cy`, `.top`, `.bot`, `.left`, `.right`)

### BoxRef 메서드
```python
b.top_mid()    # (cx, top) — 상변 중앙
b.bot_mid()    # (cx, bot) — 하변 중앙
b.left_mid()   # (left, cy) — 좌변 중앙
b.right_mid()  # (right, cy) — 우변 중앙
b.side("top")  # top_mid()과 동일
```

### `arrow_v(src, dst, label='', label_side='right')`
수직 직선 화살표. src.bot → dst.top.

### `arrow_h(src, dst, label='', label_above=True)`
수평 직선 화살표. src.right → dst.left.

### `arrow_route(steps, label='', label_pos=1, label_dx=0.18, label_ha='left', ls='-')`
꺾인 화살표. 마지막 점에 화살촉.

**steps 명령어:**
| 형태 | 설명 |
|------|------|
| `(x, y)` | 절대 좌표 |
| `("right_to", x)` | x까지 수평 |
| `("left_to", x)` | x까지 수평 |
| `("up_to", y)` | y까지 수직 |
| `("down_to", y)` | y까지 수직 |
| `("right", dx)` | dx만큼 우측 |
| `("left", dx)` | dx만큼 좌측 |
| `("up", dy)` | dy만큼 상승 |
| `("down", dy)` | dy만큼 하강 |

예시:
```python
d.arrow_route([
    b1.right_mid(),          # 출발: b1 우측 중앙
    ('right_to', 7.0),       # x=7.0까지
    ('up_to', b2.cy),        # b2 중심 높이까지
    b2.right_mid(),          # 도착: b2 우측 중앙
], label='feedback', label_pos=2)
```

### `boundary(x1, y1, x2, y2, label='', is_page_boundary=True)`
- `is_page_boundary=False`: 내부 그룹 경계 (일부 요소가 밖에 있을 때)

### `line(x1, y1, x2, y2, ls='-')`
화살촉 없는 단순 선분. 데이터 흐름 등에 사용.

### `label(x, y, text, ha='center', fs=None)`
독립 텍스트 라벨.

### `fig_label(y=None)`
FIG. N 라벨. y 생략 시 boundary bottom - 0.30" 자동 배치.

---

## 3. ⚠️ 절대 규칙 (위반 시 재생성)

### 3-1. 참조번호 배치
```python
'806\nAttribution Engine'              # ✅ 첫 줄 + 개행
'Attribution Engine  806'              # ❌ 뒤에 붙음
'806  Attribution Engine'              # ❌ 개행 없이 같은 줄
```

### 3-2. 화살표 양끝 도형 연결
- 머리와 꼬리 모두 반드시 박스 edge에 닿아야 함
- 라이브러리가 `Dangling head/tail detected` 자동 경고

### 3-3. 화살표 최소 길이
| 종류 | 최소 길이 |
|------|-----------|
| 라벨 없는 화살표 | 0.44" |
| 라벨 있는 화살표 | 0.80" |

길이 부족 → **전체 도형 재배치** (한두 개만 밀지 말 것)

### 3-4. 화살표 텍스트 관통 금지
화살표가 박스 텍스트를 가로질러 취소선처럼 보이면 → 경로 변경 또는 박스 재배치

### 3-5. 특수기호 지양
- ★ → "(Conversion)" 등 텍스트로 대체
- 아래첨자 t₁ → t1 (인쇄 안전)

---

## 4. 자동 검증 항목 (v2.6)

`save()` 시 자동 실행. 8개 항목:

| # | 검증 | 경고 메시지 |
|---|------|-------------|
| 1 | 박스 boundary 내부 | `Box "...": right > boundary` |
| 2 | 박스-boundary 마진 | `left margin 0.15" < 0.3" min` |
| 3 | 라벨 boundary 내부 | `Label "..." is ABOVE boundary top` |
| 4 | 화살표 최소 길이 | `Arrow too short (0.30")` |
| 5 | 라벨-박스 겹침 | `Label "..." may overlap a box` |
| 6 | 참조번호 위치 | `ref number "200" at end of line` |
| 7 | 화살표 양끝 연결 | `Dangling head/tail detected` |
| 8 | 라벨 화살표 길이 | `Labeled arrow shaft too short` |

---

## 5. 도면 생성 후 검증 절차

### Step 1: 라이브러리 `✓` 확인
```
✓  fig1.png    → 통과 (Step 2로)
⚠  fig1.png    → 경고 수정 후 재실행
```

### Step 2: 비전 모델 검증
생성된 이미지를 비전 모델에 보내서:
- 화살표 방향/연결 정상 여부
- dead-end 박스 유무
- 텍스트 잘림/겹침
- 취소선처럼 보이는 화살표

### Step 3: 체크리스트
- [ ] 화살표 양끝 도형 연결
- [ ] 화살표 shaft ≥ 0.44"
- [ ] 라벨 공간 충분 (잘림 없음)
- [ ] 참조번호 첫 줄 + \n
- [ ] 텍스트 완전히 보임
- [ ] dead-end 없음
- [ ] 화살표 텍스트 관통 없음

---

## 6. USPTO 형식 요약

| 규칙 | 내용 |
|------|------|
| 텍스트 | 최소 10pt (§1.84(p)(3)) |
| 폰트 | 균일, bold 금지 (§1.84(p)(1)) |
| 색상 | 흑백만 (§1.84(m)) |
| FIG. 라벨 | boundary 아래 중앙 (§1.84(u)) |
| 참조번호 | 도면=명세서 일치 (§1.84(p)) |
| 여백 | 박스-boundary 최소 0.30" |

---

## 7. 레이아웃 패턴

### 라우팅 채널 (피드백 루프용)
```
LR1 = 0.85  (좌측 채널 1)
LR2 = 1.45  (좌측 채널 2, LR1+0.60)
CL  = 2.00  (콘텐츠 좌측, LR2+0.40)
CR  = 6.80  (콘텐츠 우측)
RR1 = 7.20  (우측 채널, CR+0.40)
```

### 간격 가이드
| 구간 | 최소 |
|------|------|
| 수직/수평 화살표 (라벨 없음) | 0.44" |
| 수직/수평 화살표 (라벨 있음) | 0.80" |
| 박스 ↔ boundary | 0.30" |

---

## 8. 과거 실수 → 교훈 (반복 금지)

| 실수 | 원인 | 해결 |
|------|------|------|
| 참조번호 뒤에 붙음 | "Description 200" 습관 | 첫 줄 단독 + \n |
| 화살표 텍스트 관통 | 박스 옆 바로 수평 화살표 | 위/아래 우회 또는 재배치 |
| 촉만 보이고 shaft 없음 | 도형 간격 부족 | 전체 재배치 0.44"+ |
| 라벨 잘림 | 도형 사이 공간 부족 | 0.80"+ 확보 |
| dead-end 박스 | 출력 화살표 누락 | 비전 모델 검증 |
| 동사 시제 불일치 | viewed vs add | 카테고리 내 통일 |
| float 0.44"가 경고 | 부동소수점 | epsilon 보정 (v2.6) |

---

## 9. 렌더링 순서 (zorder)

| 순서 | 요소 | zorder |
|------|------|--------|
| 1 | Boundary frame | 1 |
| 2 | 화살표/선 | 4~5 |
| 3 | 독립 라벨 | 7 |
| 4 | 박스 white fill | 10 |
| 5 | 박스 border | 11 |
| 6 | 박스 text | 12 |
| 7 | 화살촉 (route 마지막) | 13 |

→ 화살표 선이 박스 white fill 뒤로 자동 숨김 (관통 방지)
