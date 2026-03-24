"""
Research 16 - Phase 3: AI-Based Personalized Health Monitoring System
Patent Application Simulation

Figures:
FIG.1: System block diagram (PatentLayered)
FIG.2: Data collection flowchart (PatentFigure)
FIG.3: Server-client sequence (PatentSequence)
FIG.4: Device state machine (PatentState)
FIG.5: Data flow diagram (PatentDFD)
FIG.6: Database ER diagram (PatentER)
FIG.7: Signal processing timing (PatentTiming)
"""
import sys, os, time
sys.path.insert(0, '/Users/cpagent/.openclaw/skills/patent-drawing/scripts')

from patent_figure import (
    PatentFigure, PatentSequence, PatentState,
    PatentLayered, PatentDFD, PatentER, PatentTiming
)
from patent_suite import PatentSuite

OUT = '/Users/cpagent/.openclaw/skills/patent-drawing/research16'
os.makedirs(OUT, exist_ok=True)

print("=== Research 16: AI Health Monitoring Patent Simulation ===\n")
t0 = time.time()

suite = PatentSuite('AI-Based Personalized Health Monitoring System')

# ── FIG. 1: System Architecture (PatentLayered) ──────────────────────────────
fig1 = PatentLayered('FIG. 1')
fig1.layer('User Interface',     ['100\nMobile App', '110\nWeb Dashboard'],     ref='100')
fig1.layer('AI Processing',      ['200\nML Inference Engine', '210\nAlert Manager'], ref='200')
fig1.layer('Data Services',      ['300\nHealth Data API', '310\nUser Auth'],    ref='300')
fig1.layer('Sensor Integration', ['400\nBLE Gateway', '410\nIoT Controller'],   ref='400')
fig1.layer('Storage',            ['500\nTime-Series DB', '510\nUser Profile DB'], ref='500')
fig1.interface('100', '200', label='HTTPS/WSS')
fig1.interface('200', '300', label='Internal API')
fig1.interface('300', '400', label='MQTT/BLE')
fig1.interface('300', '500', label='SQL/NoSQL')
suite.add(fig1, description='System Architecture Overview')

# ── FIG. 2: Data Collection Flow (PatentFigure) ──────────────────────────────
fig2 = PatentFigure('FIG. 2')
fig2.node('S200', '600\nStart', shape='start')
fig2.node('S202', '602\nInitialize Sensors')
fig2.node('S204', '604\nSensor Available?', shape='diamond')
fig2.node('S206', '606\nCollect Bio Signals')
fig2.node('S208', '608\nNoise Filtering')
fig2.node('S210', '610\nSignal Valid?', shape='diamond')
fig2.node('S212', '612\nFeature Extraction')
fig2.node('S214', '614\nML Inference')
fig2.node('S216', '616\nAnomaly Detected?', shape='diamond')
fig2.node('S218', '618\nSend Alert')
fig2.node('S220', '620\nStore to DB')
fig2.node('S222', '622\nEnd', shape='end')
fig2.node('SERR', '699\nLog Error', shape='end')

fig2.edge('S200', 'S202')
fig2.edge('S202', 'S204')
fig2.edge('S204', 'S206', label='Yes')
fig2.edge('S204', 'SERR', label='No')
fig2.edge('S206', 'S208')
fig2.edge('S208', 'S210')
fig2.edge('S210', 'S212', label='Yes')
fig2.edge('S210', 'S206', label='No')  # retry
fig2.edge('S212', 'S214')
fig2.edge('S214', 'S216')
fig2.edge('S216', 'S218', label='Yes')
fig2.edge('S216', 'S220', label='No')
fig2.edge('S218', 'S220')
fig2.edge('S220', 'S222')
fig2.preset('uspto')
suite.add(fig2, description='Data Collection and Processing Flow')

# ── FIG. 3: Server-Client Sequence (PatentSequence) ──────────────────────────
fig3 = PatentSequence('FIG. 3')
fig3.actor('Wearable',  'wearable')
fig3.actor('Mobile',    'mobile')
fig3.actor('API Server','api')
fig3.actor('ML Engine', 'ml')
fig3.actor('Database',  'db')

fig3.message('wearable', 'mobile',  '800\nBLE sensor data')
fig3.message('mobile',   'api',     '802\nPOST /health/data')
fig3.message('api',      'db',      '804\nINSERT measurement')
fig3.message('db',       'api',     '806\nrecord id', return_msg=True)
fig3.message('api',      'ml',      '808\nanalyze(data)')
fig3.message('ml',       'api',     '810\nanomaly score', return_msg=True)
fig3.message('api',      'mobile',  '812\n200 OK + score', return_msg=True)
fig3.message('mobile',   'wearable','814\nvibrate alert',  return_msg=True)
suite.add(fig3, description='Server-Client Data Flow Sequence')

# ── FIG. 4: Device State Machine (PatentState) ──────────────────────────────
fig4 = PatentState('FIG. 4')
fig4.state('BOOTING',      '900\nBooting',     initial=True)
fig4.state('CALIBRATING',  '902\nCalibrating')
fig4.state('MONITORING',   '904\nMonitoring')
fig4.state('TRANSMITTING', '906\nTransmitting')
fig4.state('LOW_POWER',    '908\nLow Power')
fig4.state('FIRMWARE_UPD', '910\nFirmware Update')
fig4.state('ERROR',        '912\nError')
fig4.state('OFF',          '914\nOff',         final=True)

fig4.transition('BOOTING',      'CALIBRATING',  label='boot OK')
fig4.transition('CALIBRATING',  'MONITORING',   label='calibrated')
fig4.transition('MONITORING',   'TRANSMITTING', label='data ready')
fig4.transition('TRANSMITTING', 'MONITORING',   label='sent')
fig4.transition('MONITORING',   'LOW_POWER',    label='idle 60s')
fig4.transition('LOW_POWER',    'MONITORING',   label='motion detected')
fig4.transition('MONITORING',   'FIRMWARE_UPD', label='update available')
fig4.transition('FIRMWARE_UPD', 'BOOTING',      label='update done')
fig4.transition('MONITORING',   'ERROR',        label='sensor fault')
fig4.transition('ERROR',        'BOOTING',      label='reset')
fig4.transition('LOW_POWER',    'OFF',          label='power button')
suite.add(fig4, description='Wearable Device State Machine')

# ── FIG. 5: Data Flow Diagram (PatentDFD) ─────────────────────────────────
fig5 = PatentDFD('FIG. 5')
fig5.external('USER',    '1000\nUser',           cx=1.5, cy=8.0)
fig5.external('ALERT',   '1010\nAlert System',   cx=7.0, cy=8.0)
fig5.process( 'COLLECT', '1020\nData Collection', cx=4.25, cy=8.0)
fig5.process( 'ANALYZE', '1030\nML Analysis',     cx=4.25, cy=6.0)
fig5.store(   'TIMESERIES','1040\nTime-Series DB', cx=4.25, cy=4.0)
fig5.store(   'PROFILE',  '1050\nUser Profile',   cx=2.0, cy=6.0)

fig5.flow('USER',    'COLLECT',   label='sensor data')
fig5.flow('COLLECT', 'TIMESERIES',label='store')
fig5.flow('COLLECT', 'ANALYZE',   label='raw data')
fig5.flow('PROFILE', 'ANALYZE',   label='user baseline')
fig5.flow('TIMESERIES', 'ANALYZE',label='history')
fig5.flow('ANALYZE', 'ALERT',     label='anomaly event')
suite.add(fig5, description='Data Flow Diagram')

# ── FIG. 6: ER Diagram (PatentER) ───────────────────────────────────────────
fig6 = PatentER('FIG. 6')
fig6.entity('USER_ENT',     '1100\nUser',
            attrs=['user_id (PK)', 'name', 'age', 'email'])
fig6.entity('DEVICE_ENT',   '1110\nDevice',
            attrs=['device_id (PK)', 'model', 'firmware'])
fig6.entity('MEASUREMENT',  '1120\nMeasurement',
            attrs=['meas_id (PK)', 'timestamp', 'hr_bpm', 'spo2'])
fig6.entity('ALERT_ENT',    '1130\nAlert',
            attrs=['alert_id (PK)', 'type', 'severity', 'ts'])

fig6.relationship('USER_ENT',   'DEVICE_ENT',  '1', 'N', label='owns')
fig6.relationship('DEVICE_ENT', 'MEASUREMENT', '1', 'N', label='generates')
fig6.relationship('USER_ENT',   'ALERT_ENT',   '1', 'N', label='receives')
suite.add(fig6, description='Database ER Diagram')

# ── FIG. 7: Timing Diagram (PatentTiming) ────────────────────────────────────
fig7 = PatentTiming('FIG. 7')
fig7.signal('SENSOR_CLK', '1200', wave='clock', period=0.5)
fig7.signal('HR_DATA',    '1210', wave=[0,0,1,1,1,0,0,1,1,0])
fig7.signal('SPO2_DATA',  '1220', wave=[0,0,0,1,1,1,0,0,1,1])
fig7.signal('BLE_TX',     '1230', wave=[0,0,0,0,1,0,0,0,0,0])
fig7.signal('VALID',      '1240', wave=[0,0,1,1,1,1,0,0,1,1])
fig7.marker(t=2.0, label='T_sample')
fig7.marker(t=4.0, label='T_process')
fig7.marker(t=8.0, label='T_next')
suite.add(fig7, description='Sensor Signal Timing Diagram')

# ── Render all ───────────────────────────────────────────────────────────────
print("Rendering 7 figures...")
paths = suite.render_all(OUT)
for p in paths:
    print(f"  ✓ {os.path.basename(p)}")

# Export index
idx_path = os.path.join(OUT, 'health_index.md')
suite.export_index(idx_path)
print(f"\n✓ Index: {idx_path}")

# Export PDF
pdf_path = os.path.join(OUT, 'health_patent_drawings.pdf')
try:
    suite.export_pdf(pdf_path)
    size_kb = os.path.getsize(pdf_path) // 1024
    print(f"✓ PDF: {pdf_path} ({size_kb} KB)")
except Exception as e:
    print(f"  PDF: {e}")

elapsed = time.time() - t0
print(f"\nTotal time: {elapsed:.3f}s")
print("=== Health Patent Simulation complete ===")
