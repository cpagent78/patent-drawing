"""
Research 15 - Test PatentSuite: Multi-Figure, PDF export, CLI
"""
import sys, os, time
sys.path.insert(0, '/Users/cpagent/.openclaw/skills/patent-drawing/scripts')
from patent_figure import PatentFigure, PatentSequence, PatentState, PatentLayered
from patent_suite import PatentSuite

OUT = '/Users/cpagent/.openclaw/skills/patent-drawing/research15'
os.makedirs(OUT, exist_ok=True)

print("=== Research 15: PatentSuite Test ===\n")

t0 = time.time()

# Create suite
suite = PatentSuite('Smart E-Commerce Platform')

# FIG. 1: System overview (LR block diagram)
fig1 = PatentFigure('FIG. 1', direction='LR')
fig1.node('MOBILE', '100\nMobile App', shape='process')
fig1.node('WEB',    '110\nWeb Browser', shape='process')
fig1.node('API',    '200\nAPI Gateway', shape='process')
fig1.node('AUTH',   '210\nAuth Service', shape='process')
fig1.node('ORDER',  '300\nOrder Service', shape='process')
fig1.node('DB',     '400\nDatabase', shape='cylinder')
fig1.node_group(['MOBILE', 'WEB'])
fig1.edge('MOBILE', 'API', label='HTTPS', bidir=True)
fig1.edge('WEB',    'API', label='HTTPS', bidir=True)
fig1.edge('API',    'AUTH',  bidir=True)
fig1.edge('API',    'ORDER', bidir=True)
fig1.edge('ORDER',  'DB',    bidir=True)
fig1.container('client',  ['MOBILE', 'WEB'],       label='010\nClient Layer')
fig1.container('backend', ['AUTH', 'ORDER'],        label='020\nService Layer')
suite.add(fig1, description='System Overview Block Diagram')

# FIG. 2: Login sequence
fig2 = PatentSequence('FIG. 2')
fig2.actor('User',   'user')
fig2.actor('App',    'app')
fig2.actor('Auth',   'auth')
fig2.actor('DB',     'db')
fig2.message('user', 'app',  '200\nenter credentials')
fig2.message('app',  'auth', '202\nPOST /auth/login')
fig2.message('auth', 'db',   '204\nSELECT WHERE email=?')
fig2.message('db',   'auth', '206\nuser record', return_msg=True)
fig2.message('auth', 'app',  '208\n200 OK + JWT', return_msg=True)
fig2.message('app',  'user', '210\nDashboard', return_msg=True)
suite.add(fig2, description='Login Authentication Sequence')

# FIG. 3: Order state machine
fig3 = PatentState('FIG. 3')
fig3.state('PENDING',   '300\nPending',   initial=True)
fig3.state('CONFIRMED', '310\nConfirmed')
fig3.state('SHIPPED',   '320\nShipped')
fig3.state('DELIVERED', '330\nDelivered', final=True)
fig3.state('CANCELLED', '340\nCancelled', final=True)
fig3.transition('PENDING',   'CONFIRMED', label='confirm()')
fig3.transition('PENDING',   'CANCELLED', label='cancel()')
fig3.transition('CONFIRMED', 'SHIPPED',   label='ship()')
fig3.transition('CONFIRMED', 'CANCELLED', label='cancel()')
fig3.transition('SHIPPED',   'DELIVERED', label='receive()')
suite.add(fig3, description='Order State Machine')

# FIG. 4: Software architecture
fig4 = PatentLayered('FIG. 4')
fig4.layer('Presentation',    ['400\nMobile UI', '410\nWeb UI'],  ref='400')
fig4.layer('Business Logic',  ['420\nCart Service', '430\nOrder Engine'], ref='420')
fig4.layer('Data Access',     ['440\nORM', '450\nCache'],         ref='440')
fig4.layer('Infrastructure',  ['460\nPostgreSQL', '470\nRedis'],  ref='460')
fig4.interface('400', '420', label='REST API')
fig4.interface('420', '440', label='Query')
fig4.interface('440', '460', label='SQL/Cache')
suite.add(fig4, description='Software Layered Architecture')

# Render all to output dir
print("Rendering all figures...")
paths = suite.render_all(OUT)
for p in paths:
    print(f"  ✓ {os.path.basename(p)}")

# Export index
idx_path = os.path.join(OUT, 'index.md')
suite.export_index(idx_path)
print(f"\n✓ Index: {idx_path}")

# Export PDF
pdf_path = os.path.join(OUT, 'patent_drawings.pdf')
try:
    suite.export_pdf(pdf_path)
    print(f"✓ PDF: {pdf_path}")
except ImportError as e:
    print(f"  PDF skipped (Pillow not installed): {e}")
except Exception as e:
    print(f"  PDF error: {e}")

# Check ref conflicts
conflicts = suite.check_ref_conflicts()
if conflicts:
    print(f"\n⚠ Ref conflicts: {conflicts}")
else:
    print(f"\n✓ No reference number conflicts")

# Print suite info
print(f"\nSuite info: {suite}")
print(f"\nTotal time: {time.time()-t0:.3f}s")
print("\n=== PatentSuite test complete ===")
