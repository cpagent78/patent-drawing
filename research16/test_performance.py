"""
Research 16 - Phase 4: Performance benchmark
30-node diagram generation timing
"""
import sys, time
sys.path.insert(0, '/Users/cpagent/.openclaw/skills/patent-drawing/scripts')
import patent_drawing_lib as lib

# Clear caches for cold measurement
lib.Drawing._FIT_FONT_CACHE.clear()
lib.Drawing._MEASURE_TEXT_CACHE.clear()

from patent_figure import PatentFigure

def build_30node_fig(label='FIG. BENCH'):
    fig = PatentFigure(label)
    for i in range(30):
        shape = 'diamond' if i % 5 == 0 else 'process'
        fig.node(f'S{i*10:03}', f'{i*10:03}\nProcess Step {i}', shape=shape)
        if i > 0:
            fig.edge(f'S{(i-1)*10:03}', f'S{i*10:03}')
    return fig

# Cold run (fresh caches)
fig_cold = build_30node_fig('FIG. COLD')
t_cold = time.time()
fig_cold.render('/tmp/bench_cold.png', auto_split=False)
t_cold = time.time() - t_cold
print(f"Cold run (30 nodes): {t_cold:.3f}s")

# Warm run (caches populated)
fig_warm = build_30node_fig('FIG. WARM')
t_warm = time.time()
fig_warm.render('/tmp/bench_warm.png', auto_split=False)
t_warm = time.time() - t_warm
print(f"Warm run (30 nodes): {t_warm:.3f}s")

# Cache stats
print(f"Cache: measure_text={len(lib.Drawing._MEASURE_TEXT_CACHE)} entries, fit_font={len(lib.Drawing._FIT_FONT_CACHE)} entries")

# Goal check
TARGET = 0.5
if t_cold <= TARGET:
    print(f"✓ Cold run {t_cold:.3f}s meets target {TARGET}s")
else:
    print(f"⚠ Cold run {t_cold:.3f}s exceeds target {TARGET}s (but {t_warm:.3f}s warm is good)")

# Normal-use benchmark: suite of 4 figures
lib.Drawing._FIT_FONT_CACHE.clear()
lib.Drawing._MEASURE_TEXT_CACHE.clear()

from patent_suite import PatentSuite
from patent_figure import PatentSequence, PatentState, PatentLayered

suite = PatentSuite('Benchmark Suite')
for n in range(1, 5):
    f = PatentFigure(f'FIG. {n}', direction='LR')
    for i in range(6):
        f.node(f'N{i}', f'{n*100+i*10}\nComponent {i}')
        if i > 0:
            f.edge(f'N{i-1}', f'N{i}', bidir=True)
    suite.add(f, description=f'Figure {n}')

t_suite = time.time()
suite.render_all('/tmp/bench_suite/')
t_suite = time.time() - t_suite
print(f"\n4-figure LR suite: {t_suite:.3f}s total ({t_suite/4:.3f}s avg per fig)")
