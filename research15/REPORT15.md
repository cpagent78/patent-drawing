# Research 15: PatentSuite + Auto Ref Numbers + PDF Export + CLI

## Summary

15차 연구: 복합 도면 Suite, 자동 참조번호 시스템, PDF 내보내기, CLI 인터페이스

---

## Phase 1: PatentSuite — 복합 도면 관리

**파일**: `scripts/patent_suite.py` (신규)

### 핵심 기능

```python
from patent_suite import PatentSuite
from patent_figure import PatentFigure, PatentSequence, PatentState, PatentLayered

suite = PatentSuite('Smart E-Commerce Platform')
suite.add(PatentFigure('FIG. 1'), description='System Overview')
suite.add(PatentSequence('FIG. 2'), description='Login Flow')
suite.add(PatentState('FIG. 3'), description='Device States')
suite.add(PatentLayered('FIG. 4'), description='Software Architecture')

# 일괄 렌더링
paths = suite.render_all('output/')  # → FIG1.png, FIG2.png, FIG3.png, FIG4.png

# Markdown 인덱스
suite.export_index('output/index.md')

# PDF 내보내기 (Pillow 사용)
suite.export_pdf('output/patent_drawings.pdf')
```

### API 요약

| 메서드 | 설명 |
|--------|------|
| `suite.add(figure, description)` | 도면 추가 |
| `suite.render_all(output_dir)` | 전체 PNG 일괄 생성 |
| `suite.export_index(path)` | Markdown 인덱스 생성 |
| `suite.export_pdf(path)` | 전체 도면 PDF 합치기 (Pillow 필요) |
| `suite.check_ref_conflicts()` | 참조번호 충돌 감지 |
| `suite.find_cross_refs()` | 잘못된 도면에 배치된 참조번호 탐지 |

---

## Phase 2: 자동 참조번호 시스템

### 범위 할당 규칙
- FIG. 1 → 100-199번대
- FIG. 2 → 200-299번대
- FIG. N → N×100 ~ N×100+99번대

### 충돌 감지
```python
conflicts = suite.check_ref_conflicts()
# [{'ref': 200, 'used_in': ['FIG. 1', 'FIG. 2']}]

cross_refs = suite.find_cross_refs()
# {('FIG. 1', 210): 'FIG. 2'}  # ref 210 appeared in FIG. 1 but belongs to FIG. 2
```

---

## Phase 3: PDF 내보내기

- **방식**: Pillow (PIL) 라이브러리로 PNG들을 다중 페이지 PDF로 합치기
- **해상도**: 150 DPI
- **타이틀**: suite.title이 PDF 메타데이터로 포함
- **의존성**: `pip install Pillow`

---

## Phase 4: CLI (patent_draw.py)

**파일**: `scripts/patent_draw.py` (신규)

### 단일 도면 생성
```bash
python patent_draw.py --spec spec.txt --output fig1.png --preset uspto
python patent_draw.py --spec spec.txt --type state --output fig2.png
python patent_draw.py --inline "S100: Start\nS200: Process" --output fig.png
```

### Suite 모드
```bash
python patent_draw.py --suite suite.json --output-dir ./figs/
```

### suite.json 형식
```json
{
  "title": "My Invention",
  "figures": [
    {"type": "flowchart", "spec": "spec1.txt", "label": "FIG. 1",
     "description": "System Overview", "output": "fig1.png"},
    {"type": "state", "spec_inline": "IDLE: 100 Idle [initial]\n...",
     "label": "FIG. 2", "description": "State Machine"}
  ],
  "export_pdf": "drawings.pdf",
  "export_index": "index.md"
}
```

### 지원 --type 값
| type | 엔진 |
|------|------|
| `flowchart` | PatentFigure |
| `state` | PatentState |
| `sequence` | PatentSequence |
| `layered` | PatentLayered |
| `timing` | PatentTiming |
| `dfd` | PatentDFD |
| `er` | PatentER |

---

## 생성된 파일

| 파일 | 설명 | 상태 |
|------|------|------|
| `FIG1.png` ~ `FIG4.png` | E-Commerce Suite 4개 도면 | ✓ |
| `index.md` | 도면 인덱스 마크다운 | ✓ |
| `patent_drawings.pdf` | 4개 도면 PDF 합본 | ✓ |
| `cli_test_flowchart.png` | CLI 단일 도면 테스트 | ✓ |
| `suite_out/` | CLI Suite 출력 | ✓ |

---

## 성능

- 4개 도면 일괄 생성: ~0.36s
- CLI 단일 도면: ~0.1s
- PDF export (4페이지): 즉시

---

## 알려진 한계

- PDF export는 Pillow 의존. `pip install Pillow` 필요
- `suite.register_ref()` 는 수동 호출 방식 — 자동 파싱으로 노드의 참조번호 자동 추출은 미구현
- CLI의 `--inline` 에서 `\n` → 실제 줄바꿈 자동 변환

---

*Generated: Research 15 | PatentSuite v1.0 | CLI patent_draw.py v1.0*
