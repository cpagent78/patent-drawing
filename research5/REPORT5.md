# Patent Drawing Research5 — 자율 연구 보고서

**일자:** 2026-03-24  
**버전:** patent_figure.py Research5  
**연구 목표:** PatentFigure 선언적 엔진 개선 (복잡도 테스트 + 버그 수정 + 신기능)

---

## 생성 도면 목록

| 파일 | 설명 | Phase |
|------|------|-------|
| `fig6_regression.png` | FIG.6 회귀 테스트 (기존 구조 유지 확인) | 1 |
| `fig_phase2a.png` | 다층 분기 플로우차트 16노드 | 2A |
| `fig_phase2b.png` | 3개 컨테이너 블록 다이어그램 (LR) | 2B |
| `fig_phase2c.png` | LR + container 조합 테스트 | 2C |
| `fig_phase4_spec.png` | 명세서 텍스트 파싱 (한국어) | 4 |
| `fig_phase4_spec_en.png` | 명세서 텍스트 파싱 (영어) | 4 |
| `fig_phase5_highlight.png` | 조건부 스타일링 (하이라이트) | 5 |
| `fig_phase5_fromspec.png` | from_spec + highlight 복합 | 5 |

---

## Phase 1: 현황 파악 결과

- FIG.6 회귀 테스트 **통과** (기존 구조 완전 보존)
- 기존 엔진 주요 기능 정상 작동 확인

**발견된 잠재 버그:**
- `edge(src, dst)` 호출 시 dst가 `_nodes`에 없으면 **KeyError 크래시** 발생 (`_skip_edges` 리스트 컴프리헨션에서)

---

## Phase 2: 복잡도 테스트 결과

### Test A (fig_phase2a.png) — 다층 분기 플로우차트 16노드
- **문제:** 루프백 + 분기 + 공간 부족이 겹쳐 많은 단변 경고 발생
- **발생 경고:** `Arrow segment too short`, `Arrow passes through box`
- **근본 원인:** 16노드를 단일 페이지에 배치 시 V_GAP이 최소값 이하로 줄어듦 → `render_multi()` 사용 권장

### Test B (fig_phase2b.png) — 3개 컨테이너 블록 다이어그램 (LR)
- **문제 1:** 대각선 화살표 — LR 모드에서 높이가 다른 노드 간 직선 연결 시 대각선 생성
- **문제 2:** 공간 활용률 51% — 박스 높이가 낮아 세로 공간 낭비
- **문제 3:** 텍스트가 긴 노드에서 컬럼 갭이 좁아져 elbow 세그먼트 단변 경고

### Test C (fig_phase2c.png) — LR + container 조합
- **수정 후 경고 없음** (Dead-end 노드는 의도된 단말)

---

## Phase 3: 버그 수정 내역

### [FIX-R5-01] KeyError 방어 — edge를 non-existent 노드에 연결 시 크래시
- **증상:** `edge('S400', 'S403')` 호출 후 `render()` 시 `KeyError: 'S403'`
- **원인:** `_skip_edges`, `_assign_ranks`, `_find_back_edges`, `_draw` 루프에서 `self._nodes[e.dst_id]` 직접 접근
- **수정:** 
  - `_find_back_edges`: `e.src_id/dst_id not in self._nodes` 가드 추가
  - `_assign_ranks`: DAG 빌드 전 존재 확인
  - `_skip_edges` 리스트 컴프리헨션: `e.src_id in self._nodes and e.dst_id in self._nodes` 조건 추가
  - `_draw` 엣지 루프: `src/dst_id not in self._nodes` 시 `warnings.warn` + `continue`
  - 백엣지 루프: 동일 가드 추가

### [FIX-R5-02] LR 모드 대각선 화살표 → elbow 라우팅으로 교체
- **증상:** LR 레이아웃에서 서로 다른 높이의 컬럼 간 연결 시 대각선 화살표
- **원인:** `rank_diff == 1` 인접 컬럼 연결 시 `[sb.right_mid(), db.left_mid()]` 직선 사용 — 높이가 다르면 대각선
- **수정:** `abs(sb.cy - db.cy) > 0.05` 시 elbow 라우팅:
  - 충분한 갭(≥0.44"×2) → 갭 중심 x 경유 elbow
  - 갭이 좁을 경우 → 공유 inter-column channel x 계산 (`_lr_channel_map` 캐시 활용)
- **파일:** `patent_figure.py` `_draw()` LR rank_diff==1 분기

### [FIX-R5-03] LR 모드 공간 활용률 개선 — 박스 높이 확장
- **수정:** `_measure_nodes()` LR 분기에서 multi-row 레이아웃도 높이 확장 로직 추가
  - single-row: `lr_available_h * 0.65` (기존 55% → 65%)
  - multi-row: 최대 노드 수 기준 `(available_h - v_gap * gaps) / max_nodes_per_col`

### [FIX-R5-04] LR 모드 컬럼 갭 최소값 강화
- **수정:** `_measure_nodes()` LR에서 `MIN_H_GAP = 1.00"` 설정 + `target_box_w = max(min_text_w, target_box_w)` 로 auto-expansion 방지
- **한계:** 박스 텍스트가 길면 (ex: "Business Logic") 실제 갭이 여전히 < 0.88" 가능 → known limitation

---

## Phase 4: 명세서 텍스트 → 도면 파이프라인

### `PatentFigure.from_spec(fig_label, spec_text)` 신기능

**사용법:**
```python
spec = """
S100: 로그인 요청 수신
S200: 자격증명 검증
S300: 검증 실패 시 재시도 횟수 확인
S400: 재시도 횟수 3회 미만 → S200
S500: 재시도 3회 이상 → 계정 잠금
S600: 검증 성공 → 세션 토큰 발급
S700: 토큰을 사용자 단말로 전송
"""
fig = PatentFigure.from_spec('FIG. 7', spec)
fig.render('fig7.png')
```

**파싱 규칙:**
- `Sxxx: 설명` 형식 자동 인식
- `→ Snnn` 또는 `-> Snnn` 으로 끝나면 해당 노드로 back-edge 자동 생성
- 첫 노드 → `start`, 마지막 노드 → `end` 자동 지정
- `→` 리다이렉트가 있는 노드 → `diamond` 자동 지정
- 연속 노드는 자동 forward edge 연결
- 텍스트 내 `→` → `->` 자동 치환 (USPTO 준수)
- 한국어/영어 모두 지원

---

## Phase 5: 신기능 구현

### 신기능 1: `highlight()` — 조건부 스타일링

```python
fig.highlight('S300')                          # 기본: 회색 배경 + 두꺼운 테두리
fig.highlight('S200', bg_color='#E0F0FF')      # 커스텀 배경색
fig.highlight('S100', 'S500', border_lw=3.0)  # 여러 노드 한번에
```

**구현:**
- `self._highlights: dict[str, dict]` 에 스타일 저장
- 노드 그리기 전 `FancyBboxPatch`로 배경 패치 추가 (zorder=4, 노드 뒤)
- 노드 위에 겹쳐 그려짐 → 시각적으로 배경색만 보임

### 신기능 2: `PatentFigure.from_spec()` — 명세서 자동 파싱
(Phase 4에서 설명)

### 신기능 3: Non-existent 노드 edge 안전 처리
- `edge(src, dst)` 에서 src/dst 중 하나가 없어도 **크래시 없이 경고 출력** 후 skip

---

## Phase 6: 회귀 테스트 결과

| 테스트 | 결과 |
|--------|------|
| FIG.6 기본 구조 | ✅ 통과 (동일 경고) |
| bidir 엣지 | ✅ 정상 |
| loop-back 자동 감지 | ✅ 정상 |
| container 그룹 박스 | ✅ 정상 |
| LR 방향 레이아웃 | ✅ 대각선 수정됨 |
| from_spec 파서 | ✅ 정상 |
| highlight 기능 | ✅ 정상 |

---

## 알려진 한계 및 다음 방향 제안

### 알려진 한계

1. **LR 밀집 레이아웃 단변 경고** — 텍스트가 긴 노드(예: "Business Logic")에서 박스가 자동 확장되면 컬럼 갭이 줄어들어 elbow 세그먼트가 0.44" 미만 가능. 근본 해결책: 텍스트 자동 줄바꿈 또는 폰트 축소.

2. **16+ 노드 단일 페이지 오버플로** — Phase 2A처럼 16노드를 한 페이지에 넣으면 V_GAP 부족으로 박스 겹침. `render_multi()` 사용 권장.

3. **from_spec 복잡 조건 미지원** — 분기 조건 레이블(Yes/No), 여러 출력 경로 명시 불가. 현재는 단순 순차 + 단일 루프백만 지원.

### 다음 방향 제안 (Research6)

1. **LR 모드 텍스트 자동 줄바꿈** — 긴 텍스트를 박스 너비에 맞게 2줄로 자동 분할하여 박스가 너무 넓어지는 문제 해결

2. **from_spec 분기 레이블** — `S400: 재시도 < 3 [Yes → S200] [No → S500]` 형식으로 Yes/No 레이블 지원

3. **render_multi 자동 판단** — 16+ 노드 감지 시 자동으로 `render_multi()` 전환 + split_at 최적화

4. **TB 모드 arrow-through-box 방지** — 분기 후 여러 경로가 같은 x 축을 공유할 때 화살표가 다른 박스를 통과하는 문제. 전용 라우팅 채널 (side-rail 시스템) 도입

5. **from_spec 복수 출력 분기** — `S300: 성공? [Yes → S400] [No → S200]` 형식으로 다중 출력 지원

---

*Generated: 2026-03-24 by Research5 subagent*
