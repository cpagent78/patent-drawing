"""
Phase 1 Test: Korean Font Rendering
"""
import sys, os
sys.path.insert(0, os.path.expanduser('~/.openclaw/skills/patent-drawing/scripts'))
from patent_figure import PatentFigure, _KOREAN_FONT

OUT = os.path.dirname(os.path.abspath(__file__))

def test_korean_payment_flow():
    """B: 한글 텍스트 포함 결제 플로우"""
    fig = PatentFigure('FIG. B', direction='TB')
    fig.node('S100', 'S100\n결제 요청 수신', shape='start')
    fig.node('S200', 'S200\n사용자 인증')
    fig.node('S300', 'S300\n인증 성공?', shape='diamond')
    fig.node('S400', 'S400\n결제 수단 선택')
    fig.node('S500', 'S500\n결제 처리')
    fig.node('S600', 'S600\n결제 완료?', shape='diamond')
    fig.node('S700', 'S700\n영수증 발행')
    fig.node('S800', 'S800\n오류 알림', shape='end')
    fig.node('S900', 'S900\n결제 성공', shape='end')
    fig.node('S150', 'S150\n인증 실패 처리', shape='end')

    fig.edge('S100', 'S200')
    fig.edge('S200', 'S300')
    fig.edge('S300', 'S400', label='예')
    fig.edge('S300', 'S150', label='아니오')
    fig.edge('S400', 'S500')
    fig.edge('S500', 'S600')
    fig.edge('S600', 'S700', label='예')
    fig.edge('S600', 'S800', label='아니오')
    fig.edge('S700', 'S900')

    out = os.path.join(OUT, 'fig_B_korean.png')
    # Disable auto_split to keep on one page (10 nodes)
    fig.render(out, auto_split=False)
    print(f'  Saved: {out}')
    return out

if __name__ == '__main__':
    print('=== Phase 1: Korean Font Test ===')
    print(f'  Font in use: {_KOREAN_FONT}')
    test_korean_payment_flow()
    print('  PASS')
