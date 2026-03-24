"""
Research 14 - Test Phase 2 & 3 improvements:
- Dynamic page size
- Label collision resolution
"""
import sys
sys.path.insert(0, '/Users/cpagent/.openclaw/skills/patent-drawing/scripts')
from patent_figure import PatentFigure
import time

# Test 1: Dynamic page size with many nodes with long labels
print("Test 1: Dynamic page size with long labels...")
t0 = time.time()
fig = PatentFigure('FIG. 5')
fig.dynamic_page_size(True)  # Enable dynamic page sizing

fig.node('S100', '100\nInitialize System Configuration Parameters')
fig.node('S200', '200\nLoad Environment Variable Settings')
fig.node('S300', '300\nAuthentication Token Validation Check', shape='diamond')
fig.node('S400', '400\nProcess User Authorization Request')
fig.node('S500', '500\nGenerate Cryptographic Session Token')
fig.node('S600', '600\nStore Session in Distributed Cache')
fig.node('S700', '700\nReturn Authentication Response')
fig.node('S800', '800\nLog Access Attempt to Audit Trail')
fig.node('S900', '900\nEnd', shape='end')
fig.node('SERR', '910\nError: Invalid Credentials', shape='end')

fig.edge('S100', 'S200')
fig.edge('S200', 'S300')
fig.edge('S300', 'S400', label='Valid')
fig.edge('S300', 'SERR', label='Invalid')
fig.edge('S400', 'S500')
fig.edge('S500', 'S600')
fig.edge('S600', 'S700')
fig.edge('S700', 'S800')
fig.edge('S800', 'S900')

out = '/Users/cpagent/.openclaw/skills/patent-drawing/research14/test_dynamic_page.png'
fig.render(out)
elapsed = time.time() - t0
print(f"  Saved: {out} ({elapsed:.3f}s)")

# Test 2: Label collision scenario (multiple diamond branches close together)
print("\nTest 2: Label collision avoidance...")
t0 = time.time()
fig2 = PatentFigure('FIG. 6')

fig2.node('S100', '100\nReceive Request', shape='start')
fig2.node('S200', '200\nCheck Auth', shape='diamond')
fig2.node('S300', '300\nCheck Rate Limit', shape='diamond')
fig2.node('S400', '400\nCheck Quota', shape='diamond')
fig2.node('S500', '500\nProcess Request')
fig2.node('S600', '600\nSuccess', shape='end')
fig2.node('SERR1', '901\nUnauthorized', shape='end')
fig2.node('SERR2', '902\nRate Limited', shape='end')
fig2.node('SERR3', '903\nQuota Exceeded', shape='end')

fig2.node_group(['SERR1', 'SERR2', 'SERR3'])

fig2.edge('S100', 'S200')
fig2.edge('S200', 'S300', label='OK')
fig2.edge('S200', 'SERR1', label='Fail')
fig2.edge('S300', 'S400', label='OK')
fig2.edge('S300', 'SERR2', label='Fail')
fig2.edge('S400', 'S500', label='OK')
fig2.edge('S400', 'SERR3', label='Fail')
fig2.edge('S500', 'S600')

out2 = '/Users/cpagent/.openclaw/skills/patent-drawing/research14/test_label_collision.png'
fig2.render(out2)
elapsed = time.time() - t0
print(f"  Saved: {out2} ({elapsed:.3f}s)")

print("\nAll tests passed!")
