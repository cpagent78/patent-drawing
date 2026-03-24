"""
Research 14 - Phase 1A: US20160134930A1 (Offline Payment System) - FIG.3 Block Diagram
POS Terminal, Payment Server, Bank Server, User Device
with Client/Server container grouping
"""
import sys
sys.path.insert(0, '/Users/cpagent/.openclaw/skills/patent-drawing/scripts')
from patent_figure import PatentFigure

fig = PatentFigure('FIG. 3', direction='LR')

# Client group
fig.node('POS',  '100\nPOS Terminal', shape='process')
fig.node('USER', '110\nUser Device',  shape='process')

# Server group
fig.node('PAY',  '200\nPayment Server', shape='process')
fig.node('BANK', '210\nBank Server',    shape='process')

# Group side-by-side
fig.node_group(['POS', 'USER'])
fig.node_group(['PAY', 'BANK'])

# Edges - bidirectional communication
fig.edge('POS',  'PAY',  label='txn request', bidir=True)
fig.edge('USER', 'PAY',  label='auth token',  bidir=True)
fig.edge('PAY',  'BANK', label='settle',      bidir=True)

# Containers
fig.container('client', ['POS', 'USER'], label='010\nClient Group')
fig.container('server', ['PAY', 'BANK'], label='020\nServer Group')

out = '/Users/cpagent/.openclaw/skills/patent-drawing/research14/fig_a_payment.png'
fig.render(out)
print(f"Saved: {out}")
