# PatentFigure 전체 연구 총결산 (1~16차)

## 연구 타임라인

| 차수 | 커밋 | 주요 성과 |
|------|------|-----------|
| R1-3 | 기반 구축 | 기본 Drawing API, 박스/화살표, USPTO 규칙 |
| R4-5 | v1.0 | autobox, boundary, 참조번호 검증 |
| R6   | Phase 6 | PatentFigure 선언적 엔진, from_spec, container |
| R7   | Phase 7 | EdgeRouter, A* 장애물 회피, Bezier 곡선 |
| R8   | Phase 8 | 한글 폰트, 프리셋, auto-split |
| R9   | Phase 9 | PatentSequence, bus, label_back, 에러 복구 |
| R10  | v2.0 | quick_draw(), USPTO 검증기, Cloud/IoT 도형 |
| R11  | Phase 11 | PatentState, PatentHardware |
| R12  | Phase 12 | PatentLayered, PatentTiming |
| R13  | v2.5 | PatentDFD, PatentER |
| R14  | v2.6 prep | 실제 특허 재현, dynamic_page_size, 라벨 충돌 해결 |
| R15  | CLI | PatentSuite, PDF export, patent_draw.py CLI |
| R16  | v3.0 | 실전 특허 시뮬레이션, 성능 최적화, 캐싱 |

---

## 지원 도면 타입 9종 (v3.0)

| # | 타입 | 클래스 | 용도 |
|---|------|--------|------|
| 1 | 플로우차트 | `PatentFigure` | 절차/알고리즘 플로우 |
| 2 | 시퀀스 | `PatentSequence` | 시스템 간 통신 |
| 3 | 상태 | `PatentState` | UML 상태 머신 |
| 4 | 하드웨어 | `PatentHardware` | IC/회로 블록 |
| 5 | 레이어드 | `PatentLayered` | 소프트웨어 아키텍처 |
| 6 | 타이밍 | `PatentTiming` | 신호 타이밍 |
| 7 | 데이터플로우 | `PatentDFD` | 데이터 흐름 |
| 8 | ER | `PatentER` | 데이터베이스 스키마 |
| 9 | 클라우드/IoT | `cloud()`, `iot_stack()` | 클라우드/IoT 아키텍처 |

---

## 알려진 한계 + 미래 방향

### 현재 한계
1. **30-node cold render**: 0.619s (목표 0.5s 미달 — ft2font C 렌더링 한계)
2. **LR 루프백**: LR 방향에서 back-edge 미지원
3. **2페이지 분할만**: render_multi()는 최대 2페이지
4. **패턴 기반 DFD 레이아웃**: 좌표 수동 입력 필요
5. **PDF 내보내기**: Pillow 외부 의존성

### 미래 방향
1. **SVG 내보내기**: PNG 대신 벡터 포맷 지원
2. **인터랙티브 편집**: VSCode 확장 또는 웹 UI
3. **자동 특허 명세서 생성**: 도면 → 특허 청구항 텍스트
4. **3페이지+ 분할**: render_multi 확장
5. **LR back-edge**: 상단 채널 루프백 지원
6. **실시간 미리보기**: Jupyter 위젯 통합

---

## 핵심 파일 목록

```
~/.openclaw/skills/patent-drawing/
├── SKILL.md                      ← 스킬 문서 (v3.0)
├── scripts/
│   ├── patent_drawing_lib.py     ← 저수준 Drawing API (캐싱 추가)
│   ├── patent_figure.py          ← PatentFigure + 8개 다이어그램 클래스
│   ├── patent_suite.py           ← PatentSuite (R15 신규)
│   ├── patent_draw.py            ← CLI (R15 신규)
│   ├── edge_router.py            ← A* EdgeRouter
│   └── validate_uspto.py         ← USPTO 검증기
├── research14/                   ← R14 결과
├── research15/                   ← R15 결과
└── research16/                   ← R16 결과
```

---

## 성능 요약

| 지표 | 값 |
|------|-----|
| 단일 도면 (6노드) | ~0.07s |
| 단일 도면 (15노드) | ~0.15s |
| 단일 도면 (30노드, cold) | ~0.62s |
| 단일 도면 (30노드, warm) | ~0.31s |
| 4-figure suite | ~0.30s total |
| 7-figure patent simulation | ~0.64s total |

*v3.0-research-complete*
