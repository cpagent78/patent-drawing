"""
gen_fig2_v2.py — SmartLayout v2 CIP FIG.2 테스트
4가지 개선 사항 검증:
  1. 멀티 포트: 동일 면에 N개 화살표 → 자동 분산
  2. 피드백 점선 렌더링
  3. 박스 통과 방지 (safe via_y)
  4. 피드백 채널 분리 (각 피드백 별도 x 레인)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from smart_layout import SmartLayout

OUTPUT = os.path.join(os.path.dirname(__file__), 'test_fig2_v2.png')

def build_cip_fig2():
    layout = SmartLayout('FIG. 2', orientation='portrait')

    # Nodes — CIP AI 특허 FIG.2 구조 (멀티-포트 테스트 포함)
    layout.node('10',  '10\nUser Interface\n& Input Handler')
    layout.node('20',  '20\nContext Analysis Unit')
    layout.node('30',  '30\nKnowledge Retrieval Unit')
    layout.node('40',  '40\nAI Orchestration Engine')
    layout.node('50',  '50\nResponse Generator A')
    layout.node('55',  '55\nResponse Generator B')
    layout.node('60',  '60\nQuality Evaluator')
    layout.node('70',  '70\nOutput Formatter')

    # Rank hints to enforce strict top-to-bottom ordering
    layout.hint_rank('10', 0)
    layout.hint_rank('20', 1)
    layout.hint_rank('30', 1)
    layout.hint_rank('40', 2)
    layout.hint_rank('50', 3)
    layout.hint_rank('55', 3)
    layout.hint_rank('60', 4)
    layout.hint_rank('70', 5)

    # Group same-rank nodes side by side
    layout.hint_group(['20', '30'], direction='horizontal')
    layout.hint_group(['50', '55'], direction='horizontal')

    # Forward edges
    layout.edge('10', '20', label='context req.')
    layout.edge('10', '30', label='knowledge req.')
    # Both 20 and 30 flow into 40 → bottom face: multi-port test
    layout.edge('20', '40', label='context data')
    layout.edge('30', '40', label='knowledge data')
    layout.edge('40', '50', label='task A')
    layout.edge('40', '55', label='task B')
    # Both 50 and 55 flow into 60 → top face: multi-port test
    layout.edge('50', '60', label='response A')
    layout.edge('55', '60', label='response B')
    layout.edge('60', '70', label='approved')

    # Feedback edges (dashed, separate lanes)
    layout.edge('60', '40', label='retry', feedback=True)
    layout.edge('70', '10', label='loop', feedback=True)

    layout.render(OUTPUT)
    print(f'✓ Generated: {OUTPUT}')


if __name__ == '__main__':
    build_cip_fig2()
    print('DONE')
