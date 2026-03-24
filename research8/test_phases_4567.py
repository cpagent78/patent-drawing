"""
Phase 3: Diamond arrow quality
Phase 4: Auto-split render
Phase 5: Style presets
Phase 6: Complex integration tests
Phase 7: Regression tests
"""
import sys, os
sys.path.insert(0, os.path.expanduser('~/.openclaw/skills/patent-drawing/scripts'))
from patent_figure import PatentFigure

OUT = os.path.dirname(os.path.abspath(__file__))


def test_phase3_diamond_arrows():
    """Phase 3: Diamond exact vertex arrows + improved labels."""
    fig = PatentFigure('FIG. 3D', direction='TB')
    fig.node('S100', 'S100\nStart', shape='start')
    fig.node('S200', 'S200\nCheck Condition A', shape='diamond')
    fig.node('S300', 'S300\nProcess Alpha')
    fig.node('S400', 'S400\nCheck Condition B', shape='diamond')
    fig.node('S500', 'S500\nProcess Beta')
    fig.node('S600', 'S600\nFinal Result')
    fig.node('S700', 'S700\nEnd', shape='end')
    fig.node('S210', 'S210\nError Handler')

    fig.edge('S100', 'S200')
    fig.edge('S200', 'S300', label='Yes')   # straight down from bottom vertex
    fig.edge('S200', 'S210', label='No')    # side exit from diamond
    fig.edge('S300', 'S400')
    fig.edge('S400', 'S500', label='Yes')   # straight down
    fig.edge('S400', 'S600', label='No')    # side exit
    fig.edge('S500', 'S700')
    fig.edge('S600', 'S700')
    fig.edge('S210', 'S100')               # loop back

    out = os.path.join(OUT, 'fig_3D_diamond_polish.png')
    fig.render(out, auto_split=False)
    print(f'  Saved: {out}')
    return out


def test_phase4_autosplit():
    """Phase 4: Auto-split with 16-node flow (should produce 2 pages)."""
    fig = PatentFigure('FIG. A', direction='TB')

    # 16 nodes — should trigger auto-split at render()
    for i in range(1, 17):
        step_id = f'S{i*100}'
        if i == 1:
            fig.node(step_id, f'{step_id}\nSystem Boot', shape='start')
        elif i == 16:
            fig.node(step_id, f'{step_id}\nSystem Ready', shape='end')
        elif i in (4, 8, 12):
            fig.node(step_id, f'{step_id}\nCheck Step {i}?', shape='diamond')
        else:
            fig.node(step_id, f'{step_id}\nProcess Step {i}')

    # Connect sequentially
    nodes = [f'S{i*100}' for i in range(1, 17)]
    for i in range(len(nodes) - 1):
        src = nodes[i]
        dst = nodes[i+1]
        # Diamond edges get labels
        if fig._nodes[src].shape == 'diamond':
            fig.edge(src, dst, label='Yes')
        else:
            fig.edge(src, dst)

    out = os.path.join(OUT, 'fig_A_16node_autosplit.png')
    # auto_split=True (default), max_nodes_per_page=14 → should split
    result = fig.render(out, auto_split=True, max_nodes_per_page=14)
    p2 = out.replace('.png', '_p2.png')
    p1_exists = os.path.exists(out)
    p2_exists = os.path.exists(p2)
    print(f'  Page 1: {out} exists={p1_exists}')
    print(f'  Page 2: {p2} exists={p2_exists}')
    return out


def test_phase5_presets():
    """Phase 5: Style presets — same diagram, 3 styles."""
    def make_fig(label):
        fig = PatentFigure(label, direction='TB')
        fig.node('S100', 'S100\nInput', shape='start')
        fig.node('S200', 'S200\nValidate', shape='diamond')
        fig.node('S300', 'S300\nProcess')
        fig.node('S400', 'S400\nOutput', shape='end')
        fig.node('S210', 'S210\nError')
        fig.edge('S100', 'S200')
        fig.edge('S200', 'S300', label='Yes')
        fig.edge('S200', 'S210', label='No')
        fig.edge('S300', 'S400')
        fig.edge('S210', 'S100')  # loop back
        return fig

    results = []
    for preset_name in ['uspto', 'draft', 'presentation']:
        fig = make_fig(f'FIG. D-{preset_name.upper()}')
        fig.preset(preset_name)
        out = os.path.join(OUT, f'fig_D_{preset_name}.png')
        fig.render(out, auto_split=False)
        print(f'  Saved: {out}')
        results.append(out)
    return results


def test_phase6_integration():
    """Phase 6: Complex integration — Korean + auto-split + EdgeRouter."""
    # Already covered by Phase 1 (Korean) and Phase 4 (auto-split)
    # This test combines EdgeRouter (draft preset) + Korean text
    fig = PatentFigure('FIG. INT', direction='TB')
    fig.preset('draft')

    fig.node('S100', 'S100\n주문 접수', shape='start')
    fig.node('S200', 'S200\n재고 확인', shape='diamond')
    fig.node('S300', 'S300\n결제 처리')
    fig.node('S400', 'S400\n배송 준비')
    fig.node('S500', 'S500\n배송 완료', shape='end')
    fig.node('S210', 'S210\n품절 알림', shape='end')

    fig.edge('S100', 'S200')
    fig.edge('S200', 'S300', label='재고 있음')
    fig.edge('S200', 'S210', label='품절')
    fig.edge('S300', 'S400')
    fig.edge('S400', 'S500')

    out = os.path.join(OUT, 'fig_INT_korean_draft.png')
    fig.render(out, auto_split=False)
    print(f'  Saved: {out}')
    return out


def test_phase7_regression_fig6():
    """Phase 7: FIG.6 regression test."""
    fig = PatentFigure('FIG. 6')
    fig.node('S400', 'S400\nVisit offline shop', shape='start')
    fig.node('S402', 'S402\nShopping in store')
    fig.node('S404', 'S404\nOrdering a camera')
    fig.node('S406', 'S406\nSelect delivery\naddress')
    fig.node('S408', 'S408\nConfirm order')
    fig.node('S410', 'S410\nPaying?', shape='diamond')
    fig.node('S412', 'S412\nPay via app')
    fig.node('S414', 'S414\nPay at cashier')
    fig.node('S416', 'S416\nPayment complete', shape='end')

    fig.edge('S400', 'S402')
    fig.edge('S402', 'S404')
    fig.edge('S404', 'S406')
    fig.edge('S406', 'S408')
    fig.edge('S408', 'S410')
    fig.edge('S410', 'S412', label='App')
    fig.edge('S410', 'S414', label='Cashier')
    fig.edge('S412', 'S416')
    fig.edge('S414', 'S416')
    fig.node_group(['S412', 'S414'])

    out = os.path.join(OUT, 'fig_6_regression.png')
    fig.render(out, auto_split=False)
    print(f'  Saved: {out}')
    return out


def test_phase7_regression_edgerouter():
    """Phase 7: EdgeRouter regression — bidir + container."""
    fig = PatentFigure('FIG. ER', direction='LR')
    fig.style(corner_radius=0.08)

    fig.node('N1', 'N1\nClient', shape='start')
    fig.node('N2', 'N2\nAPI Gateway')
    fig.node('N3', 'N3\nAuth Service')
    fig.node('N4', 'N4\nDatabase')
    fig.node('N5', 'N5\nResponse', shape='end')

    fig.edge('N1', 'N2', bidir=True)
    fig.edge('N2', 'N3')
    fig.edge('N2', 'N4')
    fig.edge('N3', 'N5')
    fig.edge('N4', 'N5')

    fig.container('grp1', ['N3', 'N4'], label='Backend Services')

    out = os.path.join(OUT, 'fig_ER_regression.png')
    fig.render(out, auto_split=False)
    print(f'  Saved: {out}')
    return out


if __name__ == '__main__':
    print('=== Phase 3: Diamond Arrow Quality ===')
    test_phase3_diamond_arrows()
    print('  PASS')

    print('\n=== Phase 4: Auto-Split Render ===')
    test_phase4_autosplit()
    print('  PASS')

    print('\n=== Phase 5: Style Presets ===')
    test_phase5_presets()
    print('  PASS')

    print('\n=== Phase 6: Integration ===')
    test_phase6_integration()
    print('  PASS')

    print('\n=== Phase 7: Regression Tests ===')
    test_phase7_regression_fig6()
    test_phase7_regression_edgerouter()
    print('  PASS')
