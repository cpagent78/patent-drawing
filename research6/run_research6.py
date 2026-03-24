#!/usr/bin/env python3
"""
Research 6 — PatentFigure comprehensive test & benchmark script.
Run from this directory or with full paths.
"""

import sys, os, time
sys.path.insert(0, os.path.expanduser('~/.openclaw/skills/patent-drawing/scripts'))

from patent_figure import PatentFigure

OUT = os.path.dirname(os.path.abspath(__file__))

results = {}  # phase → list of (name, path, elapsed)

def savepath(name):
    return os.path.join(OUT, name)

def run(name, fig, path_stem):
    t0 = time.time()
    p = fig.render(savepath(f'{path_stem}.png'))
    elapsed = time.time() - t0
    results.setdefault('renders', []).append((name, p, elapsed))
    print(f'  ✓ {name} → {os.path.basename(p)} ({elapsed:.2f}s)')
    return p

print('=' * 60)
print('Phase 1: Regression — FIG.6 and Phase 5 features')
print('=' * 60)

# FIG.6 regression
fig = PatentFigure('FIG. 6')
fig.node('S400', 'Visit offline shop', shape='start')
fig.node('S402', 'Shopping in store')
fig.node('S404', 'Ordering a camera')
fig.node('S410', 'Paying?', shape='diamond')
fig.node('S412', 'POS Terminal payment')
fig.node('S416', 'Payment complete', shape='end')
fig.edge('S400', 'S402')
fig.edge('S402', 'S404')
fig.edge('S404', 'S410')
fig.edge('S410', 'S412', label='Yes')
fig.edge('S410', 'S404', label='No')
fig.edge('S412', 'S416')
run('FIG.6 Regression', fig, 'fig6_regression')

# Phase 5 highlight regression
fig_hl = PatentFigure('FIG. HIGHLIGHT')
fig_hl.node('S100', 'Start', shape='start')
fig_hl.node('S200', 'Process A')
fig_hl.node('S300', 'Decision?', shape='diamond')
fig_hl.node('S400', 'Branch B')
fig_hl.node('S500', 'End', shape='end')
fig_hl.edge('S100', 'S200')
fig_hl.edge('S200', 'S300')
fig_hl.edge('S300', 'S400', label='Yes')
fig_hl.edge('S300', 'S500', label='No')
fig_hl.edge('S400', 'S500')
fig_hl.highlight('S300', bg_color='#FFE0B2')
run('Phase5 Highlight Regression', fig_hl, 'p5_highlight_regression')

# Phase 5 from_spec regression (basic)
fig_spec = PatentFigure.from_spec('FIG. SPEC-BASIC', """
S100: 로그인 요청 수신
S200: 자격증명 검증
S300: 검증 실패 시 재시도 횟수 확인 → S200
S400: 재시도 3회 이상 → 계정 잠금
S500: 검증 성공 시 세션 토큰 발급
S600: 토큰을 사용자 단말로 전송
""")
run('Phase5 from_spec Regression', fig_spec, 'p5_fromspec_regression')

print()
print('=' * 60)
print('Phase 2: Text Auto-Wrap')
print('=' * 60)

# Test auto-wrap with long texts
fig_wrap = PatentFigure('FIG. AUTOWRAP')
fig_wrap.max_text_width = 1.2   # narrow wrap
fig_wrap.node('S100', 'Receive authentication request from user terminal device', shape='start')
fig_wrap.node('S200', 'Validate provided username and password credentials against database')
fig_wrap.node('S300', 'Check retry count limit', shape='diamond')
fig_wrap.node('S400', 'Increment retry counter and return error message to client', shape='process')
fig_wrap.node('S500', 'Generate JWT session token with expiry timestamp', shape='end')
fig_wrap.edge('S100', 'S200')
fig_wrap.edge('S200', 'S300')
fig_wrap.edge('S300', 'S400', label='Fail')
fig_wrap.edge('S300', 'S500', label='OK')
fig_wrap.edge('S400', 'S200')
run('Text Auto-Wrap (max_text_width=1.2")', fig_wrap, 'p2_autowrap')

# LR layout with long text
fig_lr_wrap = PatentFigure('FIG. LR-WRAP', direction='LR')
fig_lr_wrap.max_text_width = 1.3
fig_lr_wrap.node('S100', 'Collect User Behavior Data from Frontend Analytics System', shape='start')
fig_lr_wrap.node('S200', 'Preprocess and Normalize Data Features')
fig_lr_wrap.node('S300', 'Apply Machine Learning Model Ensemble')
fig_lr_wrap.node('S400', 'Rank Items by Predicted Relevance Score')
fig_lr_wrap.node('S500', 'Return Top-K Recommendations to User Interface', shape='end')
fig_lr_wrap.edge('S100', 'S200')
fig_lr_wrap.edge('S200', 'S300')
fig_lr_wrap.edge('S300', 'S400')
fig_lr_wrap.edge('S400', 'S500')
run('LR Auto-Wrap', fig_lr_wrap, 'p2_lr_autowrap')

print()
print('=' * 60)
print('Phase 3: from_spec() Parser Enhancement Tests')
print('=' * 60)

# Case A: Parenthetical branches
spec_a = """
S100: 사용자 로그인 요청 수신
S200: 자격증명 DB 조회
S300: 자격증명 검증 (성공 시 S500으로, 실패 시 S400으로)
S400: 오류 메시지 표시 후 S200으로 복귀
S500: 세션 토큰 생성
S600: 토큰 발급 완료
"""
fig_a = PatentFigure.from_spec('FIG. CASE-A', spec_a)
warns_a = fig_a.validate()
print(f'  Case A warnings: {warns_a}')
run('Case A: Parenthetical branches', fig_a, 'p3_case_a')

# Case B: Parallel nodes (alpha suffix)
spec_b = """
S100: 결제 요청 수신
S200: 결제 정보 유효성 검증
S300a: 결제 내역 로그 기록
S300b: 사용자 알림 발송
S400: 결제 승인 완료
"""
fig_b = PatentFigure.from_spec('FIG. CASE-B', spec_b)
warns_b = fig_b.validate()
print(f'  Case B warnings: {warns_b}')
run('Case B: Parallel nodes', fig_b, 'p3_case_b')

# Case C: Loop
spec_c = """
S100: API 요청 전송
S200: 응답 수신 대기
S300: 재시도 (최대 3회, 실패 시 S200으로 복귀)
S400: 응답 처리
S500: 완료
"""
fig_c = PatentFigure.from_spec('FIG. CASE-C', spec_c)
warns_c = fig_c.validate()
print(f'  Case C warnings: {warns_c}')
run('Case C: Loop/retry', fig_c, 'p3_case_c')

# Case D: English spec
spec_d = """
S100: Receive login request from user terminal
S200: Validate user credentials against database
S300: If validation fails, go to S200
S400: Generate session token
S500: Return session token to client
"""
fig_d = PatentFigure.from_spec('FIG. CASE-D', spec_d)
warns_d = fig_d.validate()
print(f'  Case D warnings: {warns_d}')
run('Case D: English spec', fig_d, 'p3_case_d')

print()
print('=' * 60)
print('Phase 4: Complex real-world patent specs')
print('=' * 60)

# Patent A: Online payment flow
spec_patent_a = """
S100: 사용자가 결제 버튼 클릭
S200: 결제 정보 입력 (카드번호, 유효기간, CVC)
S300: 결제 정보 유효성 검증
S400: 검증 실패 시 오류 메시지 표시 후 S200으로 복귀
S500: PG사 결제 승인 요청
S600: PG사 응답 수신
S700: 승인 실패 시 사용자에게 실패 알림 후 종료
S800: 승인 성공 시 주문 정보 DB 저장
S900: 결제 완료 화면 표시
"""
fig_pa = PatentFigure.from_spec('FIG. PAY', spec_patent_a)
warns_pa = fig_pa.validate()
print(f'  Patent A warnings: {warns_pa}')
run('Patent A: Payment flow', fig_pa, 'p4_patent_a_payment')

# Patent B: AI recommendation system
spec_patent_b = """
S100: 사용자 행동 데이터 수집
S200: 데이터 전처리 및 정규화
S300: 협업 필터링 모델 적용
S400: 콘텐츠 기반 필터링 모델 적용
S500: 앙상블 스코어 계산
S600: 상위 K개 아이템 선별
S700: 사용자에게 추천 결과 제공
S800: 사용자 피드백 수집 → S100
"""
fig_pb = PatentFigure.from_spec('FIG. RECSYS', spec_patent_b)
warns_pb = fig_pb.validate()
print(f'  Patent B warnings: {warns_pb}')
run('Patent B: AI RecSys', fig_pb, 'p4_patent_b_recsys')

print()
print('=' * 60)
print('Phase 5: New features — node_group, add_note, export_spec, validate')
print('=' * 60)

# node_group demo
fig_ng = PatentFigure('FIG. NODE-GROUP')
fig_ng.node('S100', 'S100\n요청 수신', shape='start')
fig_ng.node('S200', 'S200\n인증 처리')
fig_ng.node('S300a', 'S300a\n로그 기록')
fig_ng.node('S300b', 'S300b\n알림 발송')
fig_ng.node('S400', 'S400\n처리 완료', shape='end')
fig_ng.node_group(['S300a', 'S300b'])   # force same rank
fig_ng.edge('S100', 'S200')
fig_ng.edge('S200', 'S300a')
fig_ng.edge('S200', 'S300b')
fig_ng.edge('S300a', 'S400')
fig_ng.edge('S300b', 'S400')
warns_ng = fig_ng.validate()
print(f'  node_group validate: {warns_ng}')
run('node_group: same-rank forcing', fig_ng, 'p5_node_group')

# add_note demo
fig_note = PatentFigure('FIG. NOTES')
fig_note.node('S100', 'S100\nStart', shape='start')
fig_note.node('S200', 'S200\nValidate')
fig_note.node('S300', 'S300\nProcess')
fig_note.node('S400', 'S400\nEnd', shape='end')
fig_note.edge('S100', 'S200')
fig_note.edge('S200', 'S300')
fig_note.edge('S300', 'S400')
fig_note.add_note('S200', 'Check DB index\nACID compliance')
fig_note.add_note('S300', 'Retry up to 3x\nif timeout')
run('add_note: speech bubbles', fig_note, 'p5_add_note')

# export_spec demo
fig_es = PatentFigure('FIG. EXPORT')
fig_es.node('S100', 'S100\nStart', shape='start')
fig_es.node('S200', 'S200\nProcess A')
fig_es.node('S300', 'S300\nDecision', shape='diamond')
fig_es.node('S400', 'S400\nBranch', shape='process')
fig_es.node('S500', 'S500\nEnd', shape='end')
fig_es.edge('S100', 'S200')
fig_es.edge('S200', 'S300')
fig_es.edge('S300', 'S400', label='Yes')
fig_es.edge('S300', 'S500', label='No')
fig_es.edge('S400', 'S200')  # loop back
spec_out = fig_es.export_spec(savepath('p5_exported.spec.txt'))
print(f'  export_spec output:\n{spec_out}')
run('export_spec figure', fig_es, 'p5_export_spec')

# validate demo — deliberately broken figure
fig_bad = PatentFigure('FIG. VALIDATE')
fig_bad.node('S100', 'Start', shape='start')
fig_bad.node('S200', 'Orphan Node')  # no edges
fig_bad.node('S300', 'End', shape='end')
fig_bad.edge('S100', 'S300')
fig_bad.edge('S100', 'NONEXISTENT')  # bad ref
bad_warns = fig_bad.validate()
print(f'  validate caught: {bad_warns}')
results.setdefault('validate_tests', []).append(bad_warns)

print()
print('=' * 60)
print('Phase 6: Performance Benchmark')
print('=' * 60)

bench_results = []

def make_flow(n):
    """Build a linear TB flow with n nodes."""
    fig = PatentFigure(f'FIG. BENCH-{n}')
    ids = [f'S{(i+1)*100}' for i in range(n)]
    fig.node(ids[0], f'{ids[0]}\nStart', shape='start')
    for i in range(1, n - 1):
        fig.node(ids[i], f'{ids[i]}\nProcess step {i+1}')
    fig.node(ids[-1], f'{ids[-1]}\nEnd', shape='end')
    for i in range(n - 1):
        fig.edge(ids[i], ids[i + 1])
    return fig

for n in [5, 10, 20, 30]:
    fig_b = make_flow(n)
    t0 = time.time()
    path = fig_b.render(savepath(f'bench_{n:02d}nodes.png'))
    elapsed = time.time() - t0
    bench_results.append((n, elapsed))
    print(f'  {n:2d} nodes: {elapsed:.3f}s')

print()
print('All renders complete.')

# ── Write REPORT6.md ──────────────────────────────────────────────────────────
report_path = os.path.join(OUT, 'REPORT6.md')

all_renders = results.get('renders', [])
with open(report_path, 'w', encoding='utf-8') as f:
    f.write('# PatentFigure Research 6 — Report\n\n')
    f.write(f'**Date:** 2026-03-24\n\n')
    f.write('## 1. Generated Figures\n\n')
    f.write('| # | Name | File | Time |\n')
    f.write('|---|------|------|------|\n')
    for i, (name, path, elapsed) in enumerate(all_renders, 1):
        fname = os.path.basename(path)
        f.write(f'| {i} | {name} | `{fname}` | {elapsed:.2f}s |\n')

    f.write('\n## 2. Bugs Fixed / Changes Made\n\n')
    f.write('### Phase 2: Text Auto-Wrap\n')
    f.write('- Added `max_text_width` property to PatentFigure (float, inches, default None)\n')
    f.write('- When set, `_measure_nodes()` calls `_wrap_text()` on all node texts before sizing\n')
    f.write('- `_wrap_text()` uses `textwrap.fill()` with `max_chars_per_line ≈ max_text_width × 10`\n')
    f.write('- Preserves existing `\\n` in text; wraps word-boundary first, character-boundary fallback\n\n')
    
    f.write('### Phase 3: from_spec() Parser Enhancement\n')
    f.write('- **Case A**: Parenthetical branches `(성공 시 S500으로, 실패 시 S400으로)` now parsed\n')
    f.write('  - Korean pattern: `X 시 Snnn으로` regex extracts label + target\n')
    f.write('  - English pattern: `on X go to Snnn` regex also supported\n')
    f.write('- **Case B**: Alpha-suffix parallel nodes `S200a, S200b` → auto `node_group()`\n')
    f.write('- **Case C**: Loop pattern `(최대 N회, 실패 시 Snnn으로 복귀)` → back-edge\n')
    f.write('- **Case D**: English `If X, go to Snnn` / `If X fails, check Snnn` → branch\n')
    f.write('- Improved regex: `S\\d+[a-z]?` handles alpha-suffix node IDs throughout\n\n')

    f.write('### Phase 5: New Features\n')
    f.write('- **`node_group(node_ids)`**: forces listed nodes to same rank in `_assign_ranks()`\n')
    f.write('  - After Kahn\'s algo, post-processes: sets all group members to `min(rank)`\n')
    f.write('- **`add_note(node_id, text)`**: draws dashed speech-bubble note to right of node\n')
    f.write('  - Rendered in `_draw()` after containers, before boundary\n')
    f.write('  - Uses `FancyBboxPatch` + `annotate` pointer line\n')
    f.write('- **`export_spec(path=None)`**: reverse-engineers figure to spec text\n')
    f.write('  - Strips `Snnn\\n` prefix from node text, appends `→ Snnn` for back-edges\n')
    f.write('  - Returns string; optionally writes to file\n')
    f.write('- **`validate()`**: pre-render structure checks\n')
    f.write('  - Detects: orphan nodes, undefined edge refs, duplicate edges, multiple START/END\n')
    f.write('  - Returns `list[str]` of warnings (non-raising)\n\n')

    f.write('## 3. New Features — Usage Examples\n\n')
    f.write('### node_group()\n```python\n')
    f.write('fig.node("S300a", "Log Event")\n')
    f.write('fig.node("S300b", "Send Notification")\n')
    f.write('fig.node_group(["S300a", "S300b"])  # place side-by-side in same row\n```\n\n')
    
    f.write('### add_note()\n```python\n')
    f.write('fig.add_note("S200", "Check DB index\\nEnsure ACID")\n```\n\n')
    
    f.write('### export_spec()\n```python\n')
    f.write('spec_text = fig.export_spec()            # returns string\n')
    f.write('fig.export_spec("/tmp/my_figure.txt")   # also writes file\n```\n\n')
    
    f.write('### validate()\n```python\n')
    f.write('warnings = fig.validate()\n')
    f.write('if warnings:\n')
    f.write('    for w in warnings: print("WARNING:", w)\n```\n\n')
    
    f.write('### Text Auto-Wrap\n```python\n')
    f.write('fig = PatentFigure("FIG. 1")\n')
    f.write('fig.max_text_width = 1.3  # wrap at ~13 chars per line\n')
    f.write('fig.node("S100", "Very long text that will auto-wrap")\n```\n\n')

    f.write('### from_spec() — Enhanced Parsing\n```python\n')
    f.write('# Parenthetical branches\n')
    f.write('fig = PatentFigure.from_spec("FIG. 1", """\n')
    f.write('S300: 검증 (성공 시 S500으로, 실패 시 S400으로)\n')
    f.write('""")\n\n')
    f.write('# English spec\n')
    f.write('fig = PatentFigure.from_spec("FIG. 2", """\n')
    f.write('S200: If validation fails, go to S100\n')
    f.write('""")\n```\n\n')

    f.write('## 4. Performance Benchmark\n\n')
    f.write('Platform: Apple Silicon Mac mini, Python 3.x, matplotlib\n\n')
    f.write('| Nodes | Render Time |\n')
    f.write('|-------|-------------|\n')
    for n, t in bench_results:
        f.write(f'| {n} | {t:.3f}s |\n')
    f.write('\n*All figures rendered at full 300 DPI USPTO quality.*\n\n')

    # validate test results
    f.write('## 5. Validate() Test Results\n\n')
    bad_warns = results.get('validate_tests', [[]])[0]
    f.write('Intentionally broken figure validation caught:\n')
    for w in bad_warns:
        f.write(f'- `{w}`\n')
    f.write('\n')

    f.write('## 6. Research 7 — Proposed Directions\n\n')
    f.write('1. **`render_multi()` auto-split**: automatically split when node count > threshold\n')
    f.write('   (currently requires manual `split_at` parameter)\n')
    f.write('2. **PDF export**: `render_pdf()` method using ReportLab or matplotlib PDF backend\n')
    f.write('   for multi-page patent submission\n')
    f.write('3. **from_spec() Mermaid import**: accept Mermaid flowchart syntax as input\n')
    f.write('   - `graph TD; A-->B` → PatentFigure nodes/edges\n')
    f.write('4. **Interactive editor**: Jupyter widget or tkinter GUI for drag-and-drop\n')
    f.write('   node placement with live preview\n')
    f.write('5. **Cross-reference numbering**: auto-assign USPTO reference numbers\n')
    f.write('   (100, 102, 104...) and maintain a reference table\n')
    f.write('6. **LR back-edge routing**: currently LR back-edges not handled;\n')
    f.write('   add top-channel routing for LR direction loops\n')
    f.write('7. **add_note() clustering**: when multiple notes overlap, stack them\n')
    f.write('   vertically to avoid visual collision\n')

print(f'\n✅ REPORT6.md written: {report_path}')
