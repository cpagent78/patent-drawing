"""
test_features.py — patent_drawing_lib v9.0 기능 검증
3가지 화살표 품질 개선 기능 시각 테스트
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from patent_drawing_lib import Drawing

OUTPUT = os.path.dirname(__file__)

# ─────────────────────────────────────────────────────────────────────────────
# Feature 2: Arrowhead Clearance (shrinkB=2pt)
# ─────────────────────────────────────────────────────────────────────────────
def test_arrowhead_clearance():
    d = Drawing(os.path.join(OUTPUT, 'feat2_arrowhead_clearance.png'), fig_num='F2')
    b1 = d.box(2.5, 8.5, 2.5, 0.7, '100\nSource')
    b2 = d.box(2.5, 7.2, 2.5, 0.7, '200\nDestination')
    b3 = d.box(2.5, 5.9, 2.5, 0.7, '300\nTerminal')
    d.arrow_v(b1, b2, label='step 1')
    d.arrow_v(b2, b3, label='step 2')
    d.save()
    print('feat2: arrowhead clearance ✓')

# ─────────────────────────────────────────────────────────────────────────────
# Feature 1: Arrival Point Spreading (2→1 and 3→1)
# ─────────────────────────────────────────────────────────────────────────────
def test_arrival_spreading_2to1():
    d = Drawing(os.path.join(OUTPUT, 'feat1a_spread_2to1.png'), fig_num='F1A')
    b1 = d.box(1.2, 8.5, 1.8, 0.65, '100\nSrc A')
    b2 = d.box(4.2, 8.5, 1.8, 0.65, '200\nSrc B')
    dst = d.box(2.2, 7.1, 2.8, 0.65, '300\nDest (2 in)')
    out = d.box(2.2, 5.8, 2.8, 0.65, '400\nOutput')
    d.arrow_v(b1, dst, label='path A')
    d.arrow_v(b2, dst, label='path B')
    d.arrow_v(dst, out)
    d.save()
    print('feat1a: 2→1 spreading ✓')

def test_arrival_spreading_3to1():
    d = Drawing(os.path.join(OUTPUT, 'feat1b_spread_3to1.png'), fig_num='F1B')
    b1 = d.box(0.8, 8.5, 1.6, 0.65, '80\nAlgo A')
    b2 = d.box(2.9, 8.5, 1.6, 0.65, '90\nAlgo B')
    b3 = d.box(5.0, 8.5, 1.6, 0.65, '95\nAlgo C')
    dst = d.box(2.3, 7.1, 3.0, 0.65, '100\nDecision')
    out = d.box(2.3, 5.8, 3.0, 0.65, '110\nOutput')
    d.arrow_v(b1, dst, label='score A')
    d.arrow_v(b2, dst, label='score B')
    d.arrow_v(b3, dst, label='score C')
    d.arrow_v(dst, out)
    d.save()
    print('feat1b: 3→1 spreading ✓')

def test_manual_dst_offset():
    d = Drawing(os.path.join(OUTPUT, 'feat1c_manual_offset.png'), fig_num='F1C')
    b1 = d.box(1.0, 8.5, 1.8, 0.65, '100\nSrc A')
    b2 = d.box(4.5, 8.5, 1.8, 0.65, '200\nSrc B')
    dst = d.box(2.2, 7.1, 2.8, 0.65, '300\nDest')
    out = d.box(2.2, 5.8, 2.8, 0.65, '400\nOutput')
    # Manual offset: explicitly place arrivals
    d.arrow_v(b1, dst, label='left path', dst_offset=-0.5)
    d.arrow_v(b2, dst, label='right path', dst_offset=+0.5)
    d.arrow_v(dst, out)
    d.save()
    print('feat1c: manual dst_offset ✓')

# ─────────────────────────────────────────────────────────────────────────────
# Feature 3: Channel Auto-Avoidance
# ─────────────────────────────────────────────────────────────────────────────
def test_channel_avoidance():
    d = Drawing(os.path.join(OUTPUT, 'feat3_channel_avoidance.png'), fig_num='F3')
    b1 = d.box(2.0, 9.0, 2.5, 0.7, '100\nProcess A')
    b2 = d.box(2.0, 7.8, 2.5, 0.7, '200\nProcess B')
    b3 = d.box(2.0, 6.5, 2.5, 0.7, '300\nProcess C')
    b4 = d.box(2.0, 5.2, 2.5, 0.7, '400\nProcess D')
    d.arrow_v(b1, b2)
    d.arrow_v(b2, b3)
    d.arrow_v(b3, b4)
    # Feedback: right side — channel x exactly at box.right (should be auto-shifted out)
    RIGHT_CHANNEL = b1.right  # intentionally on box right edge
    d.arrow_route([
        b4.right_mid(),
        (RIGHT_CHANNEL, b4.cy),
        (RIGHT_CHANNEL, b1.cy),
        b1.right_mid()
    ], label='feedback')
    d.save()
    print('feat3: channel auto-avoidance ✓')

# ─────────────────────────────────────────────────────────────────────────────
# Combined integration test (FIG.2 style)
# ─────────────────────────────────────────────────────────────────────────────
def test_integration_fig2_style():
    d = Drawing(os.path.join(OUTPUT, 'integration_fig2.png'), fig_num='T5')
    b_start = d.box(1.5, 9.5, 3.5, 0.7, '10\nStart / Init')
    b80  = d.box(0.5, 8.2, 2.2, 0.65, '80\nClassifier A')
    b90  = d.box(3.3, 8.2, 2.2, 0.65, '90\nClassifier B')
    b100 = d.box(1.5, 6.8, 3.5, 0.65, '100\nAggregation Node')
    b110 = d.box(1.5, 5.5, 3.5, 0.65, '110\nResult Processor')
    b_end = d.box(1.5, 4.2, 3.5, 0.7, '120\nOutput / Done')

    d.arrow_v(b_start, b80, label='branch A')
    d.arrow_v(b_start, b90, label='branch B')
    # Two arrows to top of b100 — auto-spread
    d.arrow_v(b80, b100, label='score A')
    d.arrow_v(b90, b100, label='score B')
    d.arrow_v(b100, b110)
    d.arrow_v(b110, b_end)

    # Feedback loop on left side
    CH_X = b_start.left - 0.5
    d.arrow_route([
        b_end.left_mid(),
        (CH_X, b_end.cy),
        (CH_X, b80.cy),
        b80.left_mid()
    ], label='retry loop')

    d.save()
    print('integration: FIG.2 style ✓')


if __name__ == '__main__':
    print('=== patent_drawing_lib v9.0 Feature Tests ===\n')
    test_arrowhead_clearance()
    test_arrival_spreading_2to1()
    test_arrival_spreading_3to1()
    test_manual_dst_offset()
    test_channel_avoidance()
    test_integration_fig2_style()
    print('\n=== All tests complete ===')
    print(f'Output: {OUTPUT}/')
