# patent-drawing

USPTO-compliant patent drawings — 9 diagram types, zero coordinates.

[![version](https://img.shields.io/badge/version-3.0.0-blue)](https://clawhub.com)
[![python](https://img.shields.io/badge/python-3.9%2B-green)](https://python.org)

## Features

- **9 diagram types**: flowchart, sequence, state, hardware, layered, timing, DFD, ER, suite
- **Zero-coordinate declarative API** — no manual x/y positioning
- **Korean/English auto font detection** — Apple SD Gothic Neo, NanumGothic, fallbacks
- **`from_spec()`** — parse plain-text spec → diagram automatically
- **`quick_draw()`** — one-liner: spec text → USPTO-compliant PNG
- **PatentSuite** — multi-figure PDF export with index
- **CLI** — `patent_draw.py` for batch generation
- **Auto-validation** — dangling arrows, short arrows, ref number placement
- **Auto-split** — large flowcharts (>14 nodes) split across 2 pages

## Quick Start

### One-liner (quick_draw)

```python
import sys
sys.path.insert(0, 'path/to/patent-drawing/scripts')
from patent_figure import quick_draw

result = quick_draw("""
S100: User Login Request
S200: Validate Token
S300: Token Valid?
S400: Return Error
S500: Redirect to Dashboard
""", 'fig1.png', fig_label='FIG. 1')

print(result['pages'])     # ['fig1.png']
print(result['warnings'])  # [] if clean
```

### Flowchart (PatentFigure)

```python
from patent_figure import PatentFigure

fig = PatentFigure('FIG. 1')
fig.node('S100', 'Start', shape='start')
fig.node('S200', 'Process Data')
fig.node('S300', 'Valid?', shape='diamond')
fig.node('S400', 'Error', shape='end')
fig.node('S500', 'Done', shape='end')

fig.edge('S100', 'S200')
fig.edge('S200', 'S300')
fig.edge('S300', 'S400', label='No')
fig.edge('S300', 'S500', label='Yes')

fig.render('fig1.png')
```

### CLI

```bash
# Single figure from spec file
python scripts/patent_draw.py --spec spec.txt --output fig1.png

# Specify diagram type
python scripts/patent_draw.py --spec spec.txt --type state --output fig2.png

# Inline spec
python scripts/patent_draw.py --inline "S100: Start\nS200: Process" --output fig.png

# Suite (multiple figures + PDF)
python scripts/patent_draw.py --suite suite.json --output-dir ./figs/
```

## Diagram Types

| Type | Class | `--type` | Use Case |
|------|-------|----------|----------|
| Flowchart | `PatentFigure` | `flowchart` | Process flows, block diagrams |
| Sequence | `PatentSequence` | `sequence` | Actor message flows |
| State | `PatentState` | `state` | FSM, state transitions |
| Hardware | `PatentHardware` | `hardware` | Hardware block diagrams |
| Layered | `PatentLayered` | `layered` | Software architecture layers |
| Timing | `PatentTiming` | `timing` | Signal timing diagrams |
| DFD | `PatentDFD` | `dfd` | Data flow diagrams |
| ER | `PatentER` | `er` | Entity-relationship diagrams |
| Suite | `PatentSuite` | — | Multi-figure PDF export |

## Directory Structure

```
patent-drawing/
├── SKILL.md              # Agent guide (OpenClaw)
├── README.md             # This file
├── skill.json            # ClawHub metadata
├── .clawhubignore        # Files excluded from publish
└── scripts/
    ├── patent_figure.py       # Main library (PatentFigure + 7 classes + quick_draw)
    ├── patent_drawing_lib.py  # Low-level Drawing API (v8.0)
    ├── patent_suite.py        # PatentSuite (multi-figure PDF)
    ├── patent_draw.py         # CLI entry point
    ├── edge_router.py         # A* obstacle routing
    ├── validate_uspto.py      # USPTO rule validation
    └── DRAWING_GUIDE.md       # Low-level API reference
```

## USPTO Compliance

- Page size: 8.5" × 11" portrait
- Margins: left 1.0", right 0.5", top 1.0", bottom 1.0"
- Minimum font size: 10pt (auto-enforced)
- Reference numbers: first line of text, followed by newline
- Arrow validation: no dangling endpoints, minimum shaft 0.44"

## Requirements

- Python 3.9+
- matplotlib
- numpy

```bash
pip install matplotlib numpy
```

## License

MIT
