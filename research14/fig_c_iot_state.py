"""
Research 14 - Phase 1C: IoT Smart Home - State Diagram
States: OFF, STANDBY, ACTIVE, UPDATING, ERROR, FACTORY_RESET
"""
import sys
sys.path.insert(0, '/Users/cpagent/.openclaw/skills/patent-drawing/scripts')
from patent_figure import PatentState

fig = PatentState('FIG. 4')

fig.state('OFF',           '400\nOFF',           initial=True)
fig.state('STANDBY',       '410\nSTANDBY')
fig.state('ACTIVE',        '420\nACTIVE')
fig.state('UPDATING',      '430\nUPDATING')
fig.state('ERROR',         '440\nERROR')
fig.state('FACTORY_RESET', '450\nFACTORY RESET',  final=True)

# Transitions
fig.transition('OFF',           'STANDBY',       label='power on')
fig.transition('STANDBY',       'OFF',           label='power off')
fig.transition('STANDBY',       'ACTIVE',        label='paired')
fig.transition('ACTIVE',        'STANDBY',       label='unpaired')
fig.transition('ACTIVE',        'UPDATING',      label='update available')
fig.transition('UPDATING',      'ACTIVE',        label='update success')
fig.transition('UPDATING',      'ERROR',         label='update failed')
fig.transition('ACTIVE',        'ERROR',         label='fault detected')
fig.transition('ERROR',         'ACTIVE',        label='reset error')
fig.transition('ERROR',         'FACTORY_RESET', label='factory reset')
fig.transition('FACTORY_RESET', 'OFF',           label='complete')

out = '/Users/cpagent/.openclaw/skills/patent-drawing/research14/fig_c_iot_state.png'
fig.render(out)
print(f"Saved: {out}")
