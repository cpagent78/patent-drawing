"""
Phase 3: PatentFigure EdgeRouter Integration Test
Generates FIG.6-style figures with and without corner_radius.
"""
import sys, os
sys.path.insert(0, os.path.expanduser('~/.openclaw/skills/patent-drawing/scripts'))

OUT = os.path.expanduser('~/.openclaw/skills/patent-drawing/research7')

from patent_figure import PatentFigure


def test_fig6_default():
    """FIG.6 with default settings (no EdgeRouter)."""
    fig = PatentFigure('FIG. 6')
    fig.node('S400', 'S400\nVisit offline shop', shape='start')
    fig.node('S402', 'S402\nShopping in store')
    fig.node('S404', 'S404\nOrdering a camera')
    fig.node('S410', 'S410\nPaying?', shape='diamond')
    fig.node('S412', 'S412\nProcess payment')
    fig.node('S406', 'S406\nNo-pay process')
    fig.node('S416', 'S416\nPayment complete', shape='end')

    fig.edge('S400', 'S402')
    fig.edge('S402', 'S404')
    fig.edge('S404', 'S410')
    fig.edge('S410', 'S412', label='Yes')
    fig.edge('S410', 'S406', label='No')
    fig.edge('S412', 'S416')
    fig.edge('S406', 'S404')  # loop-back

    out = os.path.join(OUT, 'phase3_fig6_default.png')
    fig.render(out)
    print(f"Saved: {out}")


def test_fig6_edgerouter():
    """FIG.6 with EdgeRouter corner_radius=0.08."""
    fig = PatentFigure('FIG. 6')
    fig.style(corner_radius=0.08)
    fig.node('S400', 'S400\nVisit offline shop', shape='start')
    fig.node('S402', 'S402\nShopping in store')
    fig.node('S404', 'S404\nOrdering a camera')
    fig.node('S410', 'S410\nPaying?', shape='diamond')
    fig.node('S412', 'S412\nProcess payment')
    fig.node('S406', 'S406\nNo-pay process')
    fig.node('S416', 'S416\nPayment complete', shape='end')

    fig.edge('S400', 'S402')
    fig.edge('S402', 'S404')
    fig.edge('S404', 'S410')
    fig.edge('S410', 'S412', label='Yes')
    fig.edge('S410', 'S406', label='No')
    fig.edge('S412', 'S416')
    fig.edge('S406', 'S404')  # loop-back

    out = os.path.join(OUT, 'phase3_fig6_edgerouter.png')
    fig.render(out)
    print(f"Saved: {out}")


def test_fig6_edgerouter_large():
    """FIG.6 with EdgeRouter corner_radius=0.15 (more visible)."""
    fig = PatentFigure('FIG. 6')
    fig.style(corner_radius=0.15)
    fig.node('S400', 'S400\nVisit offline shop', shape='start')
    fig.node('S402', 'S402\nShopping in store')
    fig.node('S404', 'S404\nOrdering a camera')
    fig.node('S410', 'S410\nPaying?', shape='diamond')
    fig.node('S412', 'S412\nProcess payment')
    fig.node('S406', 'S406\nNo-pay process')
    fig.node('S416', 'S416\nPayment complete', shape='end')

    fig.edge('S400', 'S402')
    fig.edge('S402', 'S404')
    fig.edge('S404', 'S410')
    fig.edge('S410', 'S412', label='Yes')
    fig.edge('S410', 'S406', label='No')
    fig.edge('S412', 'S416')
    fig.edge('S406', 'S404')  # loop-back

    out = os.path.join(OUT, 'phase3_fig6_edgerouter_r15.png')
    fig.render(out)
    print(f"Saved: {out}")


def test_lr_edgerouter():
    """LR layout with EdgeRouter."""
    fig = PatentFigure('FIG. 7', direction='LR')
    fig.style(corner_radius=0.08)

    fig.node('100', '100\nClient\nBrowser')
    fig.node('110', '110\nAPI\nGateway')
    fig.node('120', '120\nAuth\nService')
    fig.node('130', '130\nBusiness\nLogic')
    fig.node('140', '140\nDatabase')

    fig.edge('100', '110')
    fig.edge('110', '120')
    fig.edge('110', '130')
    fig.edge('130', '140')
    fig.edge('120', '130', bidir=True)

    out = os.path.join(OUT, 'phase3_lr_edgerouter.png')
    fig.render(out)
    print(f"Saved: {out}")


def test_multi_loopback():
    """Multiple loopbacks test with EdgeRouter."""
    fig = PatentFigure('FIG. 8')
    fig.style(corner_radius=0.10)

    fig.node('S100', 'S100\nInitialize', shape='start')
    fig.node('S200', 'S200\nFetch Data')
    fig.node('S210', 'S210\nValid?', shape='diamond')
    fig.node('S220', 'S220\nProcess')
    fig.node('S230', 'S230\nStore Result')
    fig.node('S240', 'S240\nMore data?', shape='diamond')
    fig.node('S300', 'S300\nFinalize', shape='end')

    fig.edge('S100', 'S200')
    fig.edge('S200', 'S210')
    fig.edge('S210', 'S220', label='Yes')
    fig.edge('S210', 'S200', label='No')   # loop-back 1
    fig.edge('S220', 'S230')
    fig.edge('S230', 'S240')
    fig.edge('S240', 'S200', label='Yes')  # loop-back 2
    fig.edge('S240', 'S300', label='No')

    out = os.path.join(OUT, 'phase3_multi_loopback.png')
    fig.render(out)
    print(f"Saved: {out}")


if __name__ == '__main__':
    print("Running Phase 3 integration tests...")
    test_fig6_default()
    test_fig6_edgerouter()
    test_fig6_edgerouter_large()
    test_lr_edgerouter()
    test_multi_loopback()
    print("All Phase 3 integration tests complete.")
