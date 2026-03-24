# Research 9 Report — PatentFigure 9차 자율 연구

**날짜**: 2026-03-24  
**엔진 버전**: patent_figure.py (Phase 9 + Research 8 → Research 9)  
**총 생성 도면**: 13개 PNG

---

## 생성 도면 목록

| 파일 | 설명 | 기능 |
|------|------|------|
| `fig1_medical_spec.png` | 의료 진단 시스템 (10노드, 분기) | Phase 1: from_spec() 정확도 |
| `fig2_blockchain_spec.png` | 블록체인 스마트컨트랙트 (병렬) | Phase 1: 병렬 노드 그룹 |
| `fig3_architecture_lr.png` | 클라이언트-서버-DB 3계층 | Phase 2: LR 블록다이어그램 |
| `fig4_iot_topology.png` | IoT 센서→게이트웨이→클라우드 | Phase 2: IoT 토폴로지 |
| `fig5_ai_pipeline.png` | AI 데이터 파이프라인 | Phase 2: 수평 파이프라인 |
| `fig6_bus_connection.png` | CPU-Memory-GPU-Storage 버스 | Phase 2: bus() 신규 기능 |
| `fig7_sequence.png` | User-Server-DB 시퀀스 | Phase 3: PatentSequence 신규 |
| `fig8_error_recovery.png` | 에러 복구 테스트 | Phase 5: 빈텍스트/중복/긴텍스트 |
| `fig9_regression_flowchart.png` | 주문 처리 플로우 회귀 | Phase 7: FIG.6 회귀 |
| `fig10_korean_regression.png` | 결제 프로세스 (한글) | Phase 7: 한글 회귀 |
| `fig11_preset_uspto.png` | USPTO 스타일 | Phase 7: 프리셋 회귀 |
| `fig12_preset_draft.png` | Draft 스타일 | Phase 7: 프리셋 회귀 |
| `fig13_preset_presentation.png` | Presentation 스타일 | Phase 7: 프리셋 회귀 |

---

## Phase 1: from_spec() 실전 정확도 강화 ✅

### 개선 사항

**문제 1: 결정 키워드 미탐지**  
이전: `S400: 진단 신뢰도 임계값(0.85) 초과 여부 판단` → `process` 형태  
수정: `_has_decision_kw()` 함수 추가. 한국어 결정 키워드 목록:
```
여부 판단, 여부를 판단, 여부확인, 여부 확인, 판단, 확인, 검증, 검사, 비교
```
결과: `S400` `S700` → 자동으로 `diamond` 형태 적용 ✓

**문제 2: "후 종료" 패턴 미처리**  
이전: `S800: 전문의 거부 시 수동 진단 프로세스로 전환 후 종료` → 단순 process  
수정: `_has_implicit_end()` 탐지 + 합성 END 노드 자동 생성
```python
_end_S800 → "850\nEnd" (S800 + 50 규칙으로 번호 자동 생성)
```
결과: 암묵적 종료 분기가 명시적 다이아몬드 + END 노드로 표현됨 ✓

**문제 3: 참조번호 형식 (Sxxx → 숫자만)**  
이전: `S100\n텍스트` → USPTO 검증기에서 "no reference number" 경고  
수정: `Sxxx` → `xxx` (숫자만 추출해서 첫 줄에 배치)
```python
S100 → "100\n텍스트"   # 검증기 통과 ✓
S600a → "600\n토큰 차감 처리"  # 알파 suffix는 텍스트에 포함
```

**병렬 노드 (S600a/b/c) → node_group() 자동**  
동일 숫자 prefix + 알파벳 suffix 감지 → `fig.node_group(['S600a', 'S600b', 'S600c'])` 자동 적용 ✓

### 평가 결과

| 명세서 | 노드 수 | 올바른 diamond | back-edge | 병렬 그룹 |
|--------|---------|----------------|-----------|-----------|
| 의료 진단 | 11 (+ 1 synth) | 3/3 ✓ | S500→S100 ✓ | N/A |
| 블록체인 | 14 (+ 2 synth) | 2/2 ✓ | N/A | 1 ✓ |

---

## Phase 2: 블록 다이어그램 완성 ✅

### bus() 신규 기능

```python
fig.bus('DATA_BUS', ['CPU', 'MEM', 'GPU', 'STORE'], label='810\nData Bus')
```

- 수평/수직 버스 바 (두꺼운 선 3pt)
- 각 노드에서 stub 연결선 자동 그리기
- 버스 양 끝 캡 마커
- 레이블 자동 배치 (좌측/우측)
- `fig6_bus_connection.png` → ✓ (경고 없음)

### label_back= 양방향 라벨

```python
fig.edge('CLI', 'LB', label='HTTPS', label_back='response', bidir=True)
```

- 전방 라벨: 화살표 위에 배치 (bidir일 때 +0.14" 위)
- 후방 라벨: 화살표 아래 배치 (-0.18" 아래)
- 겹침 방지 로직 적용

---

## Phase 3: 시퀀스 다이어그램 (PatentSequence) ✅

### 구현 내용

새 클래스 `PatentSequence` 추가 (`patent_figure.py` 하단):

```python
seq = PatentSequence('FIG. 7')
seq.actor('User', 'user')
seq.actor('Server', 'server')
seq.actor('DB', 'db')
seq.message('user', 'server', 'login(id, pw)')
seq.message('db', 'server', 'result', return_msg=True)  # 점선
seq.render('fig7_seq.png')
```

**렌더링 요소:**
- 액터 박스 (FancyBboxPatch, 흰 배경)
- 수직 라이프라인 (점선, 1.3pt)
- 전방 메시지: 실선 화살표 →
- 반환 메시지: 점선 화살표 ←
- 라벨: 화살표 위에 중앙 정렬
- USPTO 경계선 + FIG. 라벨

**비전 평가**: 8.5/10 — 구조 깔끔, 화살표 방향 정확, 하단 여백 약간 과다

---

## Phase 5: 에러 복구 및 안정성 ✅

`node()` 메서드에 3가지 에러 복구 추가:

| 케이스 | 동작 |
|--------|------|
| 빈 텍스트 `node('S100', '')` | `warnings.warn` + id 폴백 |
| 중복 ID `node('S100', ...)` 2번 | `warnings.warn` + 덮어쓰기 |
| 200자+ 텍스트 | `warnings.warn` + `_wrap_text()` 자동 적용 |

`validate()`에 2가지 추가:

| 검사 | 내용 |
|------|------|
| 아웃고잉 없는 비-END 노드 | "possibly missing connection" 경고 |
| 순환 감지 (DFS) | "Cycle detected: A → B → A" (최대 3개) |

---

## Phase 7: 회귀 테스트 결과

| 도면 | 결과 | 비고 |
|------|------|------|
| fig9 (주문 처리 회귀) | ⚠ | short arrows (압축 레이아웃) |
| fig10 (한글 회귀) | ⚠ | 기존 known issue |
| fig11 (preset_uspto) | ⚠ | 기존 known issue |
| fig12 (preset_draft) | ⚠ | dead-end false positive (루프백) |
| fig13 (preset_presentation) | ⚠ | dead-end false positive (루프백) |

모든 회귀 도면 정상 생성 확인. ⚠는 기존 known issue (레이아웃 압축, dead-end 검출기 false positive).

---

## 버그 수정

| 버그 | 수정 |
|------|------|
| from_spec() 결정 키워드 미탐지 | `_has_decision_kw()` 추가 |
| from_spec() "후 종료" 패턴 무시 | `_has_implicit_end()` + synth END 노드 |
| from_spec() Sxxx 참조번호 형식 오류 | 숫자만 추출 (S100 → "100") |
| bidir label_back 겹침 | y offset +0.14/-0.18" 적용 |
| validate() 순환 미보고 | DFS cycle detection 추가 |

---

## 10차 연구 방향

1. **from_spec() 더 복잡한 패턴**: 영어+한국어 혼합, GOTO 표현식 개선
2. **PatentSequence 개선**: activation bar (실행 구간 사각형), combined fragments (opt/loop/alt)
3. **버스 토폴로지 공식화**: 여러 버스 계층 (PCIe bus, Memory bus, I2C bus) 
4. **LR 단방향 화살표 세그먼트 단축 문제 해결**: 인접 컬럼 간 갭을 MIN_H_GAP 이하로 줄이지 않도록 box width 자동 조정 개선
5. **validate() 개선**: from_spec() 합성 노드 suppress 옵션 (Multiple END nodes 경고 노이즈 감소)
6. **시퀀스 다이어그램 페이지 유효 활용**: 메시지 영역에 맞게 경계선 동적 조정
