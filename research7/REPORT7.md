# Research7: EdgeRouter — Rounded Corners, Obstacle Avoidance, Channel Offset

**Date:** 2026-03-24  
**Researcher:** Momo (common agent)  
**Background:** Andy(lanore78) reported that corner joints on bent arrows looked rough/disconnected in the existing annotate()-based drawing system. Research7 builds a completely self-contained orthogonal edge router from scratch, independent of matplotlib's high-level API.

---

## Problem Statement

The existing `patent_drawing_lib.py` / `patent_figure.py` system uses:
- `ax.plot()` for line segments (with OVERSHOOT = 0.02" hack to reduce corner gaps)
- `ax.annotate()` with `FancyArrowPatch` for arrowheads
- Simple `d.arrow_route()` with no corner smoothing, no obstacle avoidance, no overlap prevention

This results in:
1. **Corner gap** — even with OVERSHOOT, joints look "snapped", not smooth
2. **Arrow-through-box** — routes can pass through intermediate node boxes
3. **Loopback overlap** — multiple loopbacks on same x-channel stack on top of each other

---

## Solution: `edge_router.py`

New file: `~/.openclaw/skills/patent-drawing/scripts/edge_router.py`

### Architecture

```
EdgeRouter
├── add_obstacle(x1, y1, x2, y2)     → Register node bounding boxes
├── route(src_pt, dst_pt, src_side, dst_side) → Compute orthogonal waypoints  
├── make_path(waypoints)              → Build matplotlib.path.Path with Bezier arcs
├── make_arrowhead(tip, direction)    → Build filled triangle arrowhead Path
├── draw(ax, waypoints, ...)          → Render path + arrowhead via PathPatch
└── draw_label(ax, waypoints, text)   → Place edge label on longest segment
```

### Feature 1: Rounded Corners (Bezier CURVE3)

The key insight: at each interior waypoint B, instead of connecting A→B→C as two meeting lines, we:
1. Draw a LINE_TO (B - unit(A→B) × radius) — stop before the corner
2. Draw a CURVE3 with control=B, end=(B + unit(B→C) × radius) — smooth arc

```python
# At corner B between A and C:
arc_entry = B - uAB * radius    # end of incoming segment
arc_exit  = B + uBC * radius    # start of outgoing segment
# LINETO arc_entry → CURVE3(control=B, end=arc_exit)
```

Radius is clamped to `min(corner_radius, dist_AB/2, dist_BC/2)` to prevent overshoot on short segments.

**Comparison (Phase 2C corner zoom):**
- `annotate()` with OVERSHOOT: abrupt, slightly disconnected
- `EdgeRouter r=0.0`: sharp but continuous (no gap)
- `EdgeRouter r=0.08"`: subtle, professional-looking arc
- `EdgeRouter r=0.15"`: clearly visible smooth turn

### Feature 2: Orthogonal Path Calculation

`route()` determines the initial path based on `src_side` / `dst_side` exit directions:

| src_side | dst_side | Path type |
|----------|----------|-----------|
| bottom   | top      | Z-path or straight (normal flow) |
| top      | bottom   | Z-path reversed |
| bottom   | bottom   | U-path downward |
| right    | left     | Z-path horizontal |
| bottom   | left     | L-path (V then H) |
| right    | top      | L-path (H then V) |

### Feature 3: Obstacle Avoidance

Uses `_seg_intersects_rect()` (parametric Cohen-Sutherland clipping) to detect when a segment crosses a registered obstacle box. On collision:
- Vertical segments: bypass left or right of obstacle
- Horizontal segments: bypass above or below obstacle
- Up to 5 rerouting passes per path

**Phase 6 Validation Finding:** When comparing default vs EdgeRouter r=0.08:
- `phase6A_simple_flow_default.png`: warning "Arrow passes through box 130"  
- `phase6A_simple_flow_r08.png`: **no such warning** — obstacle avoidance fired

### Feature 4: Channel Offset

`_get_channel_offset()` tracks which vertical (V) and horizontal (H) channels have been used. Each new path using an already-claimed channel gets an offset:
- 1st user: offset = 0
- 2nd user: +step (0.12")
- 3rd user: -step
- 4th user: +2*step
- etc.

This prevents loopback arrows from stacking on top of each other.

### Feature 5: Path-based Arrowhead

Instead of `ax.annotate(arrowstyle='->')`, we build a filled triangle `mpath.Path`:
```python
# tip = arrowhead tip (exact box boundary)
# base center = tip - direction * head_length
# left/right = base ± perpendicular * head_width
```

Rendered as `mpatches.PathPatch(facecolor=color, edgecolor=color, linewidth=0)` — solid, clean, no matplotlib mutation_scale issues.

---

## Integration into patent_figure.py (Phase 3)

Added `corner_radius` to `style()` parameters. When set, the `_draw()` method:

1. Creates an `EdgeRouter` instance
2. Registers all rendered node boxes as obstacles
3. Monkey-patches `d.arrow_route()` and `d.arrow_bidir_route()` to use `EdgeRouter.draw()`
4. Falls back gracefully to original behavior on `ImportError`

**Usage:**
```python
fig = PatentFigure('FIG. 6')
fig.style(corner_radius=0.08)   # Enable EdgeRouter
# ... nodes and edges ...
fig.render('output.png')
```

Original `annotate()` behavior retained as fallback (default, no `corner_radius` set).

---

## Generated Figures

### Phase 1: EdgeRouter Unit Tests
| File | Description |
|------|-------------|
| `phase1_path_shapes.png` | 8 path types: straight, L, Z, U, S, complex |
| `phase1_corner_radius.png` | r=0, 0.05, 0.12, 0.25 comparison |
| `phase1_arrowheads.png` | 8 directions, bidir, labels |
| `phase1_auto_routing.png` | 6 route() scenarios |
| `phase1_obstacle_avoidance.png` | Vertical + horizontal bypass |
| `phase1_channel_offset.png` | 3 loopbacks with/without offset |

### Phase 2: Old vs New Comparison
| File | Description |
|------|-------------|
| `phase2A_flowchart_compare.png` | FIG.6-style: annotate() vs EdgeRouter |
| `phase2B_loopback_compare.png` | Loopback arrows: corner joint comparison |
| `phase2C_corner_zoom.png` | Zoomed corner: 4 methods side by side |

### Phase 3: PatentFigure Integration
| File | Description |
|------|-------------|
| `phase3_fig6_default.png` | Standard FIG.6 (no EdgeRouter) |
| `phase3_fig6_edgerouter.png` | FIG.6 with corner_radius=0.08 |
| `phase3_fig6_edgerouter_r15.png` | FIG.6 with corner_radius=0.15 |
| `phase3_lr_edgerouter.png` | LR layout with EdgeRouter |
| `phase3_multi_loopback.png` | Multiple loopbacks with EdgeRouter |

### Phase 4+5: Avoidance + Offset
| File | Description |
|------|-------------|
| `phase4_obstacle_avoidance.png` | Arrow rerouting before/after |
| `phase5_channel_offset.png` | Triple loopback channel separation |

### Phase 6: Quality Validation (3 figure types × 2 methods)
| File | Description |
|------|-------------|
| `phase6A_simple_flow_default.png` | Simple flow — annotate() |
| `phase6A_simple_flow_r08.png` | Simple flow — EdgeRouter r=0.08 |
| `phase6B_lr_diagram_default.png` | LR block diagram — annotate() |
| `phase6B_lr_diagram_r08.png` | LR block diagram — EdgeRouter r=0.08 |
| `phase6C_deep_flow_default.png` | Deep flow — annotate() |
| `phase6C_deep_flow_r08.png` | Deep flow — EdgeRouter r=0.08 |

---

## Key Findings

### ✅ Successes
1. **Bezier rounded corners work correctly** — CURVE3 with radius clamping produces smooth arcs even on short segments
2. **Path-based arrowheads** — cleaner than FancyArrowPatch, no mutation_scale issues
3. **Obstacle avoidance fires** — confirmed by absence of "arrow passes through box" warnings in EdgeRouter output vs default
4. **Transparent integration** — monkey-patching `d.arrow_route()` means all existing routing logic in `patent_figure.py` (skip channels, loopback channels, LR mid channels) is preserved
5. **Fallback is safe** — `ImportError` on missing `edge_router.py` silently falls back to original behavior

### ⚠️ Limitations / Known Issues
1. **Obstacle avoidance is per-segment only** — complex multi-box blocking scenarios may require multiple passes; currently up to 5 passes but not guaranteed optimal
2. **Channel offset tracks by x/y coordinate** — floating point rounding means `round(x, 3)` must match; adjacent channels with slightly different x won't be grouped
3. **Arrowhead size differs slightly** from annotate() `mutation_scale=12` — may want to calibrate `ARROW_HEAD_LENGTH` and `ARROW_HEAD_WIDTH` against USPTO comparison
4. **No global A\* routing** — paths are computed independently, not as a global optimization; could still cross in complex diagrams
5. **label placement** in monkey-patched `arrow_route()` uses a simplified approach compared to `_render_route()`'s `_best_label_segment()` logic

---

## Research8 Direction

1. **Calibrate arrowhead size** — measure annotate()'s effective arrowhead at DPI 300 and match ARROW_HEAD_LENGTH/WIDTH
2. **Integrate channel offset into PatentFigure loopback routing** — currently loopback channels are computed in `patent_figure.py` manually; could delegate to EdgeRouter
3. **A\* routing** — proper grid-based pathfinding for complex multi-obstacle scenarios
4. **Corner radius per-edge** — `fig.edge(..., corner_radius=0.12)` for individual control
5. **Dashed line rounded corners** — currently `linestyle='--'` on PathPatch can look different from SOLID; investigate

---

## File Changes

- **New:** `scripts/edge_router.py` — EdgeRouter class (full implementation)
- **Modified:** `scripts/patent_figure.py` — Phase 7 EdgeRouter integration block in `_draw()`
- **New:** `research7/` — all test scripts and output PNGs
