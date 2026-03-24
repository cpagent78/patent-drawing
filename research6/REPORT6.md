# PatentFigure Research 6 — Report

**Date:** 2026-03-24

## 1. Generated Figures

| # | Name | File | Time |
|---|------|------|------|
| 1 | FIG.6 Regression | `fig6_regression.png` | 0.08s |
| 2 | Phase5 Highlight Regression | `p5_highlight_regression.png` | 0.05s |
| 3 | Phase5 from_spec Regression | `p5_fromspec_regression.png` | 0.07s |
| 4 | Text Auto-Wrap (max_text_width=1.2") | `p2_autowrap.png` | 0.09s |
| 5 | LR Auto-Wrap | `p2_lr_autowrap.png` | 0.11s |
| 6 | Case A: Parenthetical branches | `p3_case_a.png` | 0.07s |
| 7 | Case B: Parallel nodes | `p3_case_b.png` | 0.06s |
| 8 | Case C: Loop/retry | `p3_case_c.png` | 0.05s |
| 9 | Case D: English spec | `p3_case_d.png` | 0.07s |
| 10 | Patent A: Payment flow | `p4_patent_a_payment.png` | 0.15s |
| 11 | Patent B: AI RecSys | `p4_patent_b_recsys.png` | 0.11s |
| 12 | node_group: same-rank forcing | `p5_node_group.png` | 0.05s |
| 13 | add_note: speech bubbles | `p5_add_note.png` | 0.06s |
| 14 | export_spec figure | `p5_export_spec.png` | 0.05s |

## 2. Bugs Fixed / Changes Made

### Phase 2: Text Auto-Wrap
- Added `max_text_width` property to PatentFigure (float, inches, default None)
- When set, `_measure_nodes()` calls `_wrap_text()` on all node texts before sizing
- `_wrap_text()` uses `textwrap.fill()` with `max_chars_per_line ≈ max_text_width × 10`
- Preserves existing `\n` in text; wraps word-boundary first, character-boundary fallback

### Phase 3: from_spec() Parser Enhancement
- **Case A**: Parenthetical branches `(성공 시 S500으로, 실패 시 S400으로)` now parsed
  - Korean pattern: `X 시 Snnn으로` regex extracts label + target
  - English pattern: `on X go to Snnn` regex also supported
- **Case B**: Alpha-suffix parallel nodes `S200a, S200b` → auto `node_group()`
- **Case C**: Loop pattern `(최대 N회, 실패 시 Snnn으로 복귀)` → back-edge
- **Case D**: English `If X, go to Snnn` / `If X fails, check Snnn` → branch
- Improved regex: `S\d+[a-z]?` handles alpha-suffix node IDs throughout

### Phase 5: New Features
- **`node_group(node_ids)`**: forces listed nodes to same rank in `_assign_ranks()`
  - After Kahn's algo, post-processes: sets all group members to `min(rank)`
- **`add_note(node_id, text)`**: draws dashed speech-bubble note to right of node
  - Rendered in `_draw()` after containers, before boundary
  - Uses `FancyBboxPatch` + `annotate` pointer line
- **`export_spec(path=None)`**: reverse-engineers figure to spec text
  - Strips `Snnn\n` prefix from node text, appends `→ Snnn` for back-edges
  - Returns string; optionally writes to file
- **`validate()`**: pre-render structure checks
  - Detects: orphan nodes, undefined edge refs, duplicate edges, multiple START/END
  - Returns `list[str]` of warnings (non-raising)

## 3. New Features — Usage Examples

### node_group()
```python
fig.node("S300a", "Log Event")
fig.node("S300b", "Send Notification")
fig.node_group(["S300a", "S300b"])  # place side-by-side in same row
```

### add_note()
```python
fig.add_note("S200", "Check DB index\nEnsure ACID")
```

### export_spec()
```python
spec_text = fig.export_spec()            # returns string
fig.export_spec("/tmp/my_figure.txt")   # also writes file
```

### validate()
```python
warnings = fig.validate()
if warnings:
    for w in warnings: print("WARNING:", w)
```

### Text Auto-Wrap
```python
fig = PatentFigure("FIG. 1")
fig.max_text_width = 1.3  # wrap at ~13 chars per line
fig.node("S100", "Very long text that will auto-wrap")
```

### from_spec() — Enhanced Parsing
```python
# Parenthetical branches
fig = PatentFigure.from_spec("FIG. 1", """
S300: 검증 (성공 시 S500으로, 실패 시 S400으로)
""")

# English spec
fig = PatentFigure.from_spec("FIG. 2", """
S200: If validation fails, go to S100
""")
```

## 4. Performance Benchmark

Platform: Apple Silicon Mac mini, Python 3.x, matplotlib

| Nodes | Render Time |
|-------|-------------|
| 5 | 0.050s |
| 10 | 0.143s |
| 20 | 0.446s |
| 30 | 0.889s |

*All figures rendered at full 300 DPI USPTO quality.*

## 5. Validate() Test Results

Intentionally broken figure validation caught:
- `Edge references undefined dest node: 'NONEXISTENT'`
- `Orphan node (no edges): 'S200' (text='Orphan Node')`

## 6. Research 7 — Proposed Directions

1. **`render_multi()` auto-split**: automatically split when node count > threshold
   (currently requires manual `split_at` parameter)
2. **PDF export**: `render_pdf()` method using ReportLab or matplotlib PDF backend
   for multi-page patent submission
3. **from_spec() Mermaid import**: accept Mermaid flowchart syntax as input
   - `graph TD; A-->B` → PatentFigure nodes/edges
4. **Interactive editor**: Jupyter widget or tkinter GUI for drag-and-drop
   node placement with live preview
5. **Cross-reference numbering**: auto-assign USPTO reference numbers
   (100, 102, 104...) and maintain a reference table
6. **LR back-edge routing**: currently LR back-edges not handled;
   add top-channel routing for LR direction loops
7. **add_note() clustering**: when multiple notes overlap, stack them
   vertically to avoid visual collision
