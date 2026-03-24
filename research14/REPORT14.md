# Research 14: Real Patent Reproduction + Quality Improvements

## Summary

14차 연구: 실제 특허 도면 재현 + 레이아웃 고도화 + 화살표 라벨 충돌 해결

---

## Phase 1: 실제 특허 도면 재현

### A. US20160134930A1 — 오프라인 결제 시스템 FIG.3
- **파일**: `fig_a_payment.png`
- **구성**: POS Terminal (100), User Device (110), Payment Server (200), Bank Server (210)
- **특징**: Client/Server 컨테이너 그룹, 양방향 통신 화살표
- **결과**: ✓ 생성 완료 (Bank Server가 terminal node라 dead-end 경고 1건)

### B. 로그인 인증 시스템 — 시퀀스 다이어그램
- **파일**: `fig_b_login_seq.png`
- **구성**: User → Browser → Auth Server → Database
- **메시지 7개**: 자격증명 입력, POST /login, DB 조회, 응답, JWT 토큰, 리다이렉트
- **결과**: ✓ 완전 통과

### C. IoT 스마트홈 — 상태 다이어그램
- **파일**: `fig_c_iot_state.png`
- **상태**: OFF, STANDBY, ACTIVE, UPDATING, ERROR, FACTORY_RESET (6개)
- **전이**: 전원on/off, 페어링, 업데이트, 에러, 리셋 (11개)
- **결과**: ✓ 생성 완료

---

## Phase 2: 레이아웃 엔진 고도화

### 추가된 기능: `dynamic_page_size()`

```python
fig = PatentFigure('FIG. 5')
fig.dynamic_page_size(True)  # 텍스트 길이 기반 동적 페이지 확장
```

**알고리즘**:
1. 모든 노드의 총 글자 수 계산
2. 기준치 (노드당 50자) 대비 초과 비율로 확장 배수 결정
3. TB 방향: BND_Y2 상향 확장 (세로 공간 증가)
4. LR 방향: BND_X2 우향 확장 (가로 공간 증가)
5. 최대 2× 확장으로 과도한 페이지 확대 방지

**위치**: `patent_figure.py` - `PatentFigure._apply_dynamic_page_size()`

---

## Phase 3: 화살표 라벨 겹침 해결

### 추가된 기능: `_resolve_label_collisions()`

**메커니즘**:
1. `_draw()` 시작 시 `d.label()` 를 인터셉트하여 `_deferred_labels`에 누적
2. 모든 화살표 렌더링 완료 후 충돌 감지 알고리즘 실행
3. 충돌 기준: x 간격 < 1.5", y 간격 < 0.18"
4. 충돌 해소: 최대 8회 시도, 위/아래 교대로 0.16" 씩 nudge
5. 흰색 배경 패치는 기존 `LABEL_BG = dict(facecolor='white', ...)` 활용

**참고**: 라이브러리 `patent_drawing_lib.py`의 `LABEL_BG`는 이미 `facecolor='white'`로 설정되어 있음.

---

## 생성된 파일

| 파일 | 설명 | 상태 |
|------|------|------|
| `fig_a_payment.png` | US20160134930A1 블록 다이어그램 | ✓ |
| `fig_b_login_seq.png` | 로그인 시퀀스 다이어그램 | ✓ |
| `fig_c_iot_state.png` | IoT 상태 다이어그램 | ✓ |
| `test_dynamic_page.png` | 동적 페이지 크기 테스트 | ✓ |
| `test_label_collision.png` | 라벨 충돌 해결 테스트 | ✓ |

---

## 코드 변경사항 (patent_figure.py)

1. `PatentFigure.__init__()`: `_dynamic_page: bool = False` 추가
2. `PatentFigure.dynamic_page_size()`: 새 메서드 추가
3. `PatentFigure.render()`: `_apply_dynamic_page_size()` 호출 추가
4. `PatentFigure._apply_dynamic_page_size()`: 새 메서드 (45줄)
5. `PatentFigure._resolve_label_collisions()`: 새 정적 메서드 (40줄)
6. `PatentFigure._draw()`: 라벨 인터셉터 + 충돌 해소 후 플러시

---

## 알려진 한계

- `dynamic_page_size`로 페이지가 확장되어도, 10개+ 노드에서 AUTO_SPLIT이 먼저 동작할 수 있음
- 라벨 충돌 해소는 y-axis 기반으로, 수평 배치된 라벨 간 충돌은 제한적
- 복잡한 분기 다이어그램에서는 여전히 화살표 최소 길이 경고 발생 가능

---

*Generated: Research 14 | PatentFigure v2.5 → v2.6 prep*
