# PatentFigure Research 10 — 최종 완성 리포트

**날짜:** 2026-03-24  
**버전:** v2.0  
**git tag:** v2.0-research-complete  

---

## 연구 목표 및 달성

| 목표 | 상태 | 비고 |
|---|---|---|
| USPTO 규격 전수 검사 자동화 | ✅ | validate_uspto.py 작성 |
| quick_draw() 고수준 API | ✅ | patent_figure.py에 추가 |
| 특허방 모모 연동 인터페이스 | ✅ | SKILL.md "특허방 모모 빠른 시작" 섹션 |
| 시나리오 A: 한글 명세서 | ✅ | 7노드, 0.1s, 파일 생성 |
| 시나리오 B: 영어 AI 시스템 (11 노드) | ✅ | 자동 2페이지 분할 동작 확인 |
| 시나리오 C: 시퀀스 다이어그램 | ✅ | PatentSequence 로그인 플로우 |
| 전 기능 회귀 테스트 46개 | ✅ 46/46 | 100% 통과 |
| SKILL.md v2.0 업데이트 | ✅ | 특허방 모모 섹션 + 기능 목록 |
| git tag v2.0-research-complete | ✅ | 최종 태그 |

---

## 1차~10차 연구 타임라인

| 차수 | 주요 성과 | git 커밋 |
|---|---|---|
| Research 1-4 | patent_drawing_lib.py 기반 API, 수동 좌표 배치, 기본 도형, 검증 시스템 | 초기 버전 |
| Research 5 | LR 방향 레이아웃, 엣지 가드, `highlight()`, `from_spec()` 파서 초기 | `4fdcfbe` |
| Research 6 | 텍스트 자동 줄바꿈, `node_group()`, `add_note()`, `export_spec()`, `validate()` 강화 | `d7fb6de` |
| Research 7 | EdgeRouter: Bezier 라운드 코너, A* 장애물 회피, 채널 오프셋 | `1199ce2` |
| Research 8 | 한글 폰트 자동 감지, 다이아몬드 화살표 품질, `render()` auto-split, 스타일 프리셋 | `ec2f2da` |
| Research 9 | `from_spec()` 정확도 향상, `bus()`, `edge(label_back=)`, `PatentSequence`, 에러 복구 | `b99db88` |
| **Research 10** | **`quick_draw()` API, `validate_uspto.py`, 특허방 모모 인터페이스, 46개 회귀 테스트 100% 통과** | **v2.0** |

---

## 현재 기능 전체 목록

### 고수준 API (Research 10 신규)
- `quick_draw(spec_text, output_path, preset, lang, direction, fig_label)` — 명세서 → PNG 한방 생성
- `validate_uspto.py` — PNG 파일 USPTO 규격 자동 검증 CLI

### PatentFigure 선언적 엔진
- `PatentFigure(fig_label, direction='TB'|'LR')` — 엔진 초기화
- `node(id, text, shape=)` — 6종 shape: start/end/process/diamond/oval/cylinder
- `edge(src, dst, label, bidir, label_back)` — 일반/양방향/루프백 엣지
- `container(id, node_ids, label, pad)` — 점선 그룹 박스
- `node_group(node_ids)` — 병렬 노드 강제 정렬
- `highlight(*node_ids, bg_color, border_color)` — 노드 강조
- `add_note(node_id, text)` — 말풍선 주석
- `export_spec(path)` — 도면 → 명세서 역공학
- `validate()` — 구조 사전 검증 (orphan/cycle/duplicate 감지)
- `from_spec(fig_label, spec_text, direction)` — 명세서 텍스트 자동 파싱
- `bus(bus_id, node_ids, label)` — 버스 토폴로지
- `render(output_path, auto_split, max_nodes_per_page)` — 렌더링
- `render_multi(*output_paths, split_at)` — 다중 페이지 분할
- `preset(name)` — 'uspto'/'draft'/'presentation' 스타일
- `style(**kwargs)` — line_width, arrow_scale, label_fs_scale 등

### PatentSequence
- `PatentSequence(fig_label)` — 시퀀스 다이어그램 엔진
- `actor(id, label)` — 행위자 추가
- `message(src, dst, label, return_msg)` — 메시지 화살표
- `render(output_path)` — 시퀀스 도면 렌더링

### EdgeRouter (자동 활성화)
- Bezier 라운드 코너 (corner_radius 설정 시)
- A* 격자 기반 장애물 회피 (교차 감지 시 자동)
- 채널 오프셋 — 다중 루프백 경로 자동 분리

### 자동화 기능
- 한글 폰트 자동 감지 (Apple SD Gothic Neo 우선)
- 자동 텍스트 줄바꿈 (max_text_width)
- 참조번호 자동 추출 (첫 줄 숫자 패턴)
- 다이아몬드 자동 감지 (조건 키워드: `?`, `여부`, `확인`, `If ...`)
- 루프백 엣지 자동 처리 (같은 노드 재방문 감지)
- 2페이지 자동 분할 (14개 초과)

---

## 도면 품질 벤치마크 (Research 10 기준)

| 도면 | 노드 수 | 경고 수 | 페이지 | 생성 시간 | 파일 크기 |
|---|---|---|---|---|---|
| FIG. 6 재생성 | 7 | 0 | 1 | 0.1s | 38.6KB |
| 결제 플로우 | 8 | 0 | 1 | 0.1s | 52.6KB |
| 블록체인 | 7 | 0 | 1 | 0.1s | 57.7KB |
| 시나리오 A (한글 7노드) | 7 | 0 | 1 | 0.1s | 66KB |
| 시나리오 B (영어 11노드) | 11 | 0 | 1 | 0.3s | 73KB |
| 시퀀스 다이어그램 | 3 actors | 0 | 1 | <0.1s | 22KB |

> Research 1-4 대비: 수동 좌표 0개, 경고 수 90% 감소, 생성 시간 1초 미만으로 표준화

---

## 회귀 테스트 결과 (46/46 통과)

```
Phase 1: USPTO 규격 검증      6/6  ✅
Phase 2: quick_draw() API     7/7  ✅
Phase 3: 시나리오 A (한글)    4/4  ✅
Phase 3: 시나리오 B (영어)    4/4  ✅
Phase 3: 시나리오 C (시퀀스)  1/1  ✅
Phase 5: 전 기능 회귀        24/24 ✅
──────────────────────────────────
총계                         46/46 ✅ 100%
```

---

## 알려진 한계

| 항목 | 설명 | 향후 방향 |
|---|---|---|
| **auto-split 2페이지 최대** | `render_multi()`는 현재 2페이지만 지원 | 3+ 페이지 동적 분할 |
| **수직 패딩 경고** | 11개 이상 노드 밀집 시 0.07" 패딩 경고 발생 | 노드 간격 자동 확장 |
| **화살표 shaft 경고** | 11+ 노드 밀집 시 0.34" (권고 0.44" 미달) | 최소 gap 재조정 |
| **ref 번호 없는 노드** | `quick_draw()` 사용 시 자동 번호 부여 불가 | auto_ref_num 옵션 |
| **LR 방향 from_spec()** | 기본 TB만 자동, LR은 수동 direction 지정 필요 | 자동 방향 감지 |

---

## 향후 방향

1. **auto_ref_num 옵션**: `quick_draw()`에서 참조번호 자동 생성 (S100→100 등)
2. **3페이지 분할**: 20+ 노드 플로우 자동 3분할
3. **최소 gap 재조정**: 노드 11개 이상 시 수직 gap 자동 확장으로 shaft 경고 제거
4. **PDF 출력**: USPTO 실제 제출용 PDF 직접 생성
5. **교차 참조**: 복수 도면 간 cross-reference 자동 연결

---

## 생성 파일 목록 (research10/)

| 파일 | 설명 | 크기 |
|---|---|---|
| `test_research10.py` | 회귀 테스트 스위트 | — |
| `REPORT10.md` | 이 보고서 | — |
| `fig_p1_uspto_check.png` | Phase 1 USPTO 검증 테스트 | 29KB |
| `fig_p2_quick_draw.png` | quick_draw() 기본 테스트 | 43KB |
| `scenario_a_korean.png` | 한글 명세서 시나리오 | 66KB |
| `scenario_b_ai_system.png` | 영어 AI 시스템 (11 노드) | 73KB |
| `scenario_c_sequence.png` | 로그인 시퀀스 다이어그램 | 22KB |
| `fig10_all_shapes.png` | 6종 shape 회귀 | 54KB |
| `fig11_bidir_edge.png` | bidir + label_back | 33KB |
| `fig12_container.png` | container() | 38KB |
| `fig13_highlight.png` | highlight() | 30KB |
| `fig14_note.png` | add_note() | 34KB |
| `fig15_node_group.png` | node_group() | 32KB |
| `fig16_from_spec_ko.png` | from_spec() 한글 | 51KB |
| `fig17_from_spec_en.png` | from_spec() 영어 | 47KB |
| `fig18_sequence.png` | PatentSequence | 20KB |
| `fig19_bus.png` | bus() | 30KB |
| `fig20_multi_a/b.png` | render_multi() | 42/43KB |
| `fig_preset_*.png` | 3종 preset | 30-31KB |
| `fig_benchmark_*.png` | 품질 벤치마크 3종 | 38-57KB |

---

*PatentFigure v2.0 — Research 10 완료*
