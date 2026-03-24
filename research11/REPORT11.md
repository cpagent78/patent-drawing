# Research 11 Report — State Diagrams + Hardware Block Diagrams

**날짜:** 2026-03-24  
**버전:** v2.1-research11  
**기반:** v2.0-research-complete (fd87981)

---

## 생성 도면 목록

### Phase 1: PatentState — 상태 다이어그램

| 파일 | 내용 | 방향 | 상태 수 | 전이 수 |
|------|------|------|--------|--------|
| `state_a_tcp.png` | TCP 연결 상태 머신 | TB | 5 | 6 |
| `state_b_iot.png` | 스마트홈 IoT 기기 상태 | TB | 6 | 8 |
| `state_c_protocol.png` | 프로토콜 핸드셰이크 (self-loop 포함) | LR | 5 | 7 |

### Phase 2: PatentHardware — 하드웨어 블록 다이어그램

| 파일 | 내용 | 도형 종류 |
|------|------|---------|
| `hw_a_cpu.png` | CPU 내부 블록 (ALU, Cache, Bus, Register, MUX, Memory) | chip, register, block, mux, memory_array |
| `hw_b_soc.png` | SoC 아키텍처 (AP, Modem, RF, DRAM, PMIC) | chip, block, memory_array |
| `hw_c_sensor.png` | 센서 인터페이스 회로 (ADC, DSP, Buffer, MCU, MUX) | chip, block, memory_array, mux |

### Phase 3: 회귀 테스트

| 파일 | 결과 |
|------|------|
| `regress_fig6.png` | ✓ PatentFigure 기본 플로우차트 정상 |
| `regress_quick.png` | ✓ quick_draw() 정상 |
| `regress_seq.png` | ✓ PatentSequence 정상 |

---

## 신규 기능

### `PatentState` 클래스
- 상태 노드: FancyBboxPatch 라운드 사각형
- 초기 상태(`initial=True`): 채운 원 + 화살표 (UML 스타일)
- 최종 상태(`final=True`): bull's-eye (이중 원 + 중심점)
- 초기 상태 이중 내선 (double border)
- 자동 레이아웃: TB (BFS rank-based) 및 LR
- Self-loop 지원 (arc3 connectionstyle)
- 양방향 전이 시 호 곡선으로 구분 (rad 오프셋)

### `PatentHardware` 클래스
새 도형 4종:
- `chip()`: 직사각형 + 좌우 핀 라인 (IC 칩 기호)
- `mux()`: 사다리꼴 멀티플렉서 (방향 지정 가능)
- `register()`: 셀로 분할된 레지스터 블록
- `memory_array()`: 행×열 메모리 셀 배열
- `block()`: 기본 직사각형 블록 (기존 유사 기능 편의 메서드)
- `connect()`: 자동 엣지 방향 탐지 화살표

---

## 버그 및 수정 사항

### 발견된 이슈
1. **self-loop 화살표 위치**: `arc3,rad=-0.6` 적용으로 위쪽 공간 활용
2. **양방향 전이 구분**: 역방향 엣지 감지 후 자동 rad 오프셋 (+0.25 / -0.25)
3. **BFS rank에서 누락 노드**: 방문 안 된 노드 → max_rank+1 할당으로 처리
4. **memory_array / register label 위치**: 박스 위에 별도 텍스트로 배치 (내부 공간 부족 시)

### 회귀 경고 (기존 이슈, 새 버그 아님)
- `vertical padding too tight` — PatentFigure의 기존 경고. 신규 코드와 무관.
- `Space usage 57%` — 짧은 명세서의 레이아웃 경고. 기존 동작.

---

## 다음 방향 (Research 12)

- **PatentLayered**: OSI 계층, 마이크로서비스 등 수평 레이어 아키텍처
- **PatentTiming**: SPI/DRAM/I2C 등 하드웨어 타이밍 다이어그램
- 타이밍 다이어그램의 X (don't care) 패턴 지원
- 레이어드 다이어그램의 레이어 간 인터페이스 화살표
