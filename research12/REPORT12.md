# Research 12 Report — Layered Architecture + Timing Diagrams

**날짜:** 2026-03-24  
**버전:** v2.2-research12  
**기반:** v2.1-research11 (7ef8dd0)

---

## 생성 도면 목록

### Phase 1: PatentLayered — 레이어드 아키텍처

| 파일 | 내용 | 레이어 수 | 컴포넌트 수 |
|------|------|---------|-----------|
| `layered_a_osi.png` | OSI 7계층 모델 | 7 | 17 |
| `layered_b_microservice.png` | 마이크로서비스 아키텍처 | 3 | 12 |
| `layered_c_embedded.png` | 임베디드 시스템 소프트웨어 스택 | 4 | 9 |

### Phase 2: PatentTiming — 타이밍 다이어그램

| 파일 | 내용 | 신호 수 | 마커 수 |
|------|------|--------|--------|
| `timing_a_spi.png` | SPI 통신 프로토콜 타이밍 | 4 | 2 |
| `timing_b_dram.png` | DRAM 읽기 사이클 (X 패턴 포함) | 5 | 3 |
| `timing_c_i2c.png` | I2C 데이터 전송 타이밍 | 3 | 3 |

### 회귀 테스트

| 파일 | 결과 |
|------|------|
| `regress_r11_state.png` | ✓ PatentState R11 정상 |
| `regress_r11_hw.png` | ✓ PatentHardware R11 정상 |

---

## 신규 기능

### `PatentLayered` 클래스
- 전체 너비 수평 밴드 레이어
- 각 레이어 내 컴포넌트 박스 균등 배치
- 레이어 간격 자동 계산 (n_gaps × IFACE_H)
- 인터페이스 화살표 (레이어 사이 수직 방향)
- 참조번호 + 레이어명 좌측에 표시
- USPTO 흑백 규격 준수

### `PatentTiming` 클래스
- 클록 신호: square wave 자동 생성 (period 지정)
- 데이터 신호: 0/1 리스트 → 전환 사선 포함 파형
- X (don't care) 패턴: 지그재그 파형
- 신호명 + 참조번호 좌측 표시
- 수직 타임 마커 (점선 + 라벨)
- 데이터 라벨 파형 위 표시
- 시간축 자동 눈금

---

## 버그 및 수정 사항

### 발견된 이슈 및 수정
1. **레이어 간격 계산**: `n_gaps × IFACE_H`를 총 높이에서 제외하여 레이어 높이 균등 분배
2. **타이밍 파형 X 패턴**: `'X'` 또는 `'x'` 값 처리 → 4개 지그재그 점 생성
3. **클록 파형 종료**: `max_t` 초과 방지를 위해 while loop 조건 정리
4. **전환 사선 방향**: 이전 레벨과 현재 레벨 비교로 상승/하강 엣지 정확히 처리

### 개선 가능 사항 (13차 예정)
- 타이밍 다이어그램 신호 간격 좀 더 넓게 (현재 SIGNAL_GAP=0.15")
- 레이어드 다이어그램 컴포넌트 텍스트 넘침 방지 개선

---

## 다음 방향 (Research 13)

- **PatentDFD**: 데이터 플로우 다이어그램 (Yourdon 스타일)
- **PatentER**: ER 다이어그램 (엔티티-관계 모델)
- **통합 품질 개선**: 화살표 라벨 겹침, LR 레이아웃 너비, 시퀀스 번호 등
- **quick_draw() 확장**: 새 다이어그램 타입 지원
- **SKILL.md 최종 업데이트**
