# Research 13 Report — DFD + ER + Quality + Integration

**날짜:** 2026-03-24  
**버전:** v2.5-research-complete  
**기반:** v2.2-research12 (b109782)

---

## 생성 도면 목록

### Phase 1: PatentDFD — 데이터 플로우 다이어그램

| 파일 | 내용 | 요소 수 | 흐름 수 |
|------|------|--------|--------|
| `dfd_a_auth.png` | 인증 시스템 DFD (User, Auth, Processing, DB, Log) | 5 | 6 |
| `dfd_b_order.png` | E-commerce 주문 처리 DFD | 7 | 7 |
| `dfd_c_iot.png` | IoT 데이터 파이프라인 DFD | 6 | 6 |

### Phase 2: PatentER — ER 다이어그램

| 파일 | 내용 | 엔티티 수 | 관계 수 |
|------|------|---------|--------|
| `er_a_ecommerce.png` | E-commerce ER (User, Order, Product) | 3 | 2 |
| `er_b_iot.png` | IoT 기기 ER (Device, Owner, Reading) | 3 | 2 |
| `er_c_patent.png` | 특허 데이터베이스 ER (Patent, Inventor, Claim) | 3 | 2 |

### Phase 3: 시퀀스 다이어그램 메시지 번호

| 파일 | 내용 | 메시지 수 |
|------|------|---------|
| `seq_numbered.png` | 4-actor OAuth 시퀀스 (번호 포함 메시지) | 8 |

### Phase 4: quick_draw() 확장 테스트

| 파일 | 타입 | 결과 |
|------|------|------|
| `qd_tb.png` | flowchart TB | ✓ 9 nodes |
| `qd_lr.png` | flowchart LR | ✓ 6 nodes |
| `qd_state.png` | state | ✓ 3 states |
| `qd_seq.png` | sequence | ✓ 2 messages |
| `qd_layered.png` | layered | ✓ 3 layers |
| `qd_timing.png` | timing | ✓ 3 signals |

### Phase 5: 전체 회귀

| 파일 | 결과 |
|------|------|
| `regress_state.png` | ✓ PatentState |
| `regress_layered.png` | ✓ PatentLayered |
| `regress_timing.png` | ✓ PatentTiming |
| `regress_dfd.png` | ✓ PatentDFD |
| `regress_er.png` | ✓ PatentER |
| `regress_figure.png` | ✓ PatentFigure |

---

## 신규 기능

### `PatentDFD` 클래스
- 외부 엔티티: FancyBboxPatch 사각형
- 프로세스: Ellipse 타원
- 데이터 저장소: Yourdon 스타일 (양쪽 열린 수평 사각형 — 왼쪽 수직선만)
- 자동 링 레이아웃: 위치 미지정 시 원형 배치
- 엣지 포인트 계산: 각 형태에 맞는 경계면 교차점

### `PatentER` 클래스
- 엔티티: 제목 행 + 구분선 + 속성 행 목록
- PK 속성: `(PK)` 감지 → 수동 밑줄 선 그리기
- 관계: 마름모 (Polygon) + 라벨
- 카디널리티: 연결선 위에 굵은 텍스트 표기
- 자동 수평 배치 레이아웃 (엔티티 간격 균등)

### `quick_draw()` 확장
새 `diagram_type` 파라미터 추가:
- `'state'`: `_quick_draw_state()` 라우팅 → PatentState
- `'sequence'`: `_quick_draw_sequence()` 라우팅 → PatentSequence
- `'layered'`: `_quick_draw_layered()` 라우팅 → PatentLayered
- `'timing'`: `_quick_draw_timing()` 라우팅 → PatentTiming
- 각 타입별 간단한 텍스트 스펙 파싱 지원

### SKILL.md 업데이트
- 6종 신규 클래스 모두 문서화
- quick_draw() 확장 사용법 추가
- 도표 타입 선택 가이드 추가
- 버전 v2.0 → v2.5로 업데이트

---

## 버그 수정

### PatentER `textprops` 오류 수정
- **문제**: `ax.text(..., textprops={...})` → matplotlib에 없는 파라미터
- **수정**: `textprops` 키워드 제거, PK 밑줄은 별도 `ax.plot()` 직선으로 처리
- **상태**: ✅ 수정 완료

---

## 11~13차 전체 요약

| 연구 | 신기능 | 생성 도면 |
|------|------|---------|
| Research 11 | PatentState, PatentHardware | 6개 |
| Research 12 | PatentLayered, PatentTiming | 6개 |
| Research 13 | PatentDFD, PatentER, quick_draw 확장 | 15개 |
| **합계** | **6종 새 클래스** | **27개** |

---

## 다음 방향 (14차 이후 제안)

- **PatentState self-loop 개선**: 더 큰 루프 반경, 레이블 충돌 방지
- **PatentHardware 버스 연결**: 수평 버스 바에 여러 chip 연결 (bus topology)
- **PatentDFD 레벨 표기**: DFD 레벨 0/1/2 구분
- **PatentER Crow's Foot**: 현재 숫자 표기 외 Crow's Foot 노테이션 지원
- **통합 테스트**: validate_uspto.py로 모든 research 폴더 자동 검증
- **레이아웃 최적화**: PatentDFD ring 레이아웃 → 위상 정렬 기반으로 개선
