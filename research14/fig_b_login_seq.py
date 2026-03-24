"""
Research 14 - Phase 1B: Login Authentication System - Sequence Diagram
Actors: User, Browser, Auth Server, Database
"""
import sys
sys.path.insert(0, '/Users/cpagent/.openclaw/skills/patent-drawing/scripts')
from patent_figure import PatentSequence

fig = PatentSequence('FIG. 2')

fig.actor('User',        'user')
fig.actor('Browser',     'browser')
fig.actor('Auth Server', 'auth')
fig.actor('Database',    'db')

fig.message('user',    'browser', '300\nenter credentials')
fig.message('browser', 'auth',    '302\nPOST /login')
fig.message('auth',    'db',      '304\nSELECT user WHERE email=?')
fig.message('db',      'auth',    '306\nuser record', return_msg=True)
fig.message('auth',    'auth',    '308\nverify password hash')
fig.message('auth',    'browser', '310\n200 OK + JWT token', return_msg=True)
fig.message('browser', 'user',    '312\nredirect to dashboard', return_msg=True)

out = '/Users/cpagent/.openclaw/skills/patent-drawing/research14/fig_b_login_seq.png'
fig.render(out)
print(f"Saved: {out}")
