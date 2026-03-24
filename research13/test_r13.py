"""
Research 13 Test Script
Tests: PatentDFD + PatentER + quality improvements + quick_draw() extensions
"""
import sys, os
SKILL_DIR = os.path.expanduser('~/.openclaw/skills/patent-drawing/scripts')
sys.path.insert(0, SKILL_DIR)
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

from patent_figure import (PatentDFD, PatentER, PatentFigure, PatentSequence,
                             PatentState, PatentLayered, PatentTiming,
                             quick_draw)

print("=" * 60)
print("Research 13 — DFD + ER + Quality Improvements")
print("=" * 60)

# ─────────────────────────────────────────────────────────────────────────────
# Phase 1: PatentDFD
# ─────────────────────────────────────────────────────────────────────────────
print("\n[Phase 1] Data Flow Diagrams")

# Test A: Authentication System DFD
print("[1/3] Auth System DFD (dfd_a_auth.png)")
fig = PatentDFD('FIG. 3A')
fig.external('USER',  '100\nUser')
fig.process( 'AUTH',  '200\nAuthentication')
fig.process( 'PROC',  '300\nData Processing')
fig.store(   'DB',    '400\nUser Database')
fig.store(   'LOG',   '500\nAudit Log')
fig.flow('USER', 'AUTH', label='credentials')
fig.flow('AUTH', 'DB',   label='lookup')
fig.flow('DB',   'AUTH', label='user record')
fig.flow('AUTH', 'PROC', label='token')
fig.flow('AUTH', 'LOG',  label='auth event')
fig.flow('PROC', 'USER', label='response')
fig.render(os.path.join(OUTPUT_DIR, 'dfd_a_auth.png'))
print("  ✓ dfd_a_auth.png")

# Test B: E-commerce Order Processing DFD
print("[2/3] E-commerce Order DFD (dfd_b_order.png)")
fig = PatentDFD('FIG. 3B')
fig.external('CUST',    '100\nCustomer')
fig.external('VENDOR',  '150\nVendor')
fig.process( 'CART',    '200\nCart Manager')
fig.process( 'PAY',     '300\nPayment Engine')
fig.process( 'SHIP',    '400\nShipping Engine')
fig.store(   'CATALOG', '500\nProduct Catalog')
fig.store(   'ORDERS',  '600\nOrder Store')
fig.flow('CUST',    'CART',    label='add item')
fig.flow('CART',    'CATALOG', label='query')
fig.flow('CATALOG', 'CART',    label='product info')
fig.flow('CART',    'PAY',     label='checkout')
fig.flow('PAY',     'ORDERS',  label='save order')
fig.flow('ORDERS',  'SHIP',    label='fulfillment')
fig.flow('SHIP',    'VENDOR',  label='dispatch')
fig.render(os.path.join(OUTPUT_DIR, 'dfd_b_order.png'))
print("  ✓ dfd_b_order.png")

# Test C: IoT Data Pipeline DFD
print("[3/3] IoT Pipeline DFD (dfd_c_iot.png)")
fig = PatentDFD('FIG. 3C')
fig.external('SENSOR',   '100\nSensor Node')
fig.process( 'GATEWAY',  '200\nGateway Processor')
fig.process( 'ANALYTICS','300\nAnalytics Engine')
fig.store(   'TIMESERIES','400\nTime Series DB')
fig.store(   'ALERTS',   '500\nAlert Store')
fig.external('DASHBOARD','600\nDashboard')
fig.flow('SENSOR',    'GATEWAY',   label='raw data')
fig.flow('GATEWAY',   'TIMESERIES',label='store')
fig.flow('GATEWAY',   'ANALYTICS', label='stream')
fig.flow('ANALYTICS', 'ALERTS',    label='anomaly')
fig.flow('ANALYTICS', 'DASHBOARD', label='insights')
fig.flow('ALERTS',    'DASHBOARD', label='alert')
fig.render(os.path.join(OUTPUT_DIR, 'dfd_c_iot.png'))
print("  ✓ dfd_c_iot.png")

# ─────────────────────────────────────────────────────────────────────────────
# Phase 2: PatentER
# ─────────────────────────────────────────────────────────────────────────────
print("\n[Phase 2] ER Diagrams")

# Test A: E-commerce ER
print("[4/6] E-commerce ER (er_a_ecommerce.png)")
fig = PatentER('FIG. 6A')
fig.entity('USER',    '100\nUser',
           attrs=['user_id (PK)', 'username', 'email', 'created_at'])
fig.entity('ORDER',   '200\nOrder',
           attrs=['order_id (PK)', 'date', 'total', 'status'])
fig.entity('PRODUCT', '300\nProduct',
           attrs=['product_id (PK)', 'name', 'price', 'stock'])
fig.relationship('USER',  'ORDER',   '1', 'N', label='places')
fig.relationship('ORDER', 'PRODUCT', 'N', 'M', label='contains')
fig.render(os.path.join(OUTPUT_DIR, 'er_a_ecommerce.png'))
print("  ✓ er_a_ecommerce.png")

# Test B: IoT Device Management ER
print("[5/6] IoT Device ER (er_b_iot.png)")
fig = PatentER('FIG. 6B')
fig.entity('DEVICE',  '400\nIoT Device',
           attrs=['device_id (PK)', 'type', 'location'])
fig.entity('OWNER',   '500\nDevice Owner',
           attrs=['owner_id (PK)', 'name', 'email'])
fig.entity('READING', '600\nSensor Reading',
           attrs=['reading_id (PK)', 'timestamp', 'value', 'unit'])
fig.relationship('OWNER',  'DEVICE',  '1', 'N', label='owns')
fig.relationship('DEVICE', 'READING', '1', 'N', label='generates')
fig.render(os.path.join(OUTPUT_DIR, 'er_b_iot.png'))
print("  ✓ er_b_iot.png")

# Test C: Patent Database ER
print("[6/6] Patent Database ER (er_c_patent.png)")
fig = PatentER('FIG. 6C')
fig.entity('PATENT',   '700\nPatent',
           attrs=['patent_id (PK)', 'title', 'filing_date', 'status'])
fig.entity('INVENTOR', '800\nInventor',
           attrs=['inventor_id (PK)', 'name', 'country'])
fig.entity('CLAIM',    '900\nClaim',
           attrs=['claim_id (PK)', 'claim_num', 'claim_text'])
fig.relationship('PATENT',   'INVENTOR', 'N', 'M', label='invented by')
fig.relationship('PATENT',   'CLAIM',    '1', 'N', label='has')
fig.render(os.path.join(OUTPUT_DIR, 'er_c_patent.png'))
print("  ✓ er_c_patent.png")

# ─────────────────────────────────────────────────────────────────────────────
# Phase 3: Sequence Diagram Message Number Enhancement
# ─────────────────────────────────────────────────────────────────────────────
print("\n[Phase 3] Sequence Diagram with message numbers (seq_numbered.png)")
# Test with existing PatentSequence — now with message numbers
fig = PatentSequence('FIG. 7')
fig.actor('Client', 'c')
fig.actor('Auth Server', 'as')
fig.actor('Resource Server', 'rs')
fig.actor('Database', 'db')
fig.message('c',  'as', '1. login(user, pass)')
fig.message('as', 'db', '2. query user()')
fig.message('db', 'as', '3. user record', return_msg=True)
fig.message('as', 'c',  '4. JWT token', return_msg=True)
fig.message('c',  'rs', '5. request + token')
fig.message('rs', 'as', '6. verify(token)')
fig.message('as', 'rs', '7. valid', return_msg=True)
fig.message('rs', 'c',  '8. resource data', return_msg=True)
fig.render(os.path.join(OUTPUT_DIR, 'seq_numbered.png'))
print("  ✓ seq_numbered.png")

# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: quick_draw() Extensions
# ─────────────────────────────────────────────────────────────────────────────
print("\n[Phase 4] quick_draw() extended types")

# quick_draw with TB direction (standard)
print("[8] quick_draw TB (qd_tb.png)")
spec_tb = """
S100: Receive Payment Request
S200: Validate Input Data
S300: Data valid?
S400: Return Error Response
S500: Process Payment
S600: Payment successful?
S700: Notify Failure
S800: Send Confirmation
S900: End
"""
result = quick_draw(spec_tb, os.path.join(OUTPUT_DIR, 'qd_tb.png'),
                    fig_label='FIG. 8A')
print(f"  ✓ qd_tb.png — {result['node_count']} nodes, {result['elapsed_sec']}s")

# quick_draw with LR direction
print("[9] quick_draw LR pipeline (qd_lr.png)")
spec_lr = """
S100: Data Ingestion
S200: Preprocessing
S300: Feature Extraction
S400: Model Inference
S500: Post-processing
S600: Output Delivery
"""
result = quick_draw(spec_lr, os.path.join(OUTPUT_DIR, 'qd_lr.png'),
                    direction='LR', fig_label='FIG. 8B')
print(f"  ✓ qd_lr.png — {result['node_count']} nodes, {result['elapsed_sec']}s")

# ─────────────────────────────────────────────────────────────────────────────
# Phase 5: Full Regression
# ─────────────────────────────────────────────────────────────────────────────
print("\n[Phase 5] Full regression all diagram types")

# PatentState
fig = PatentState('FIG. R1')
fig.state('S1', '100\nStart', initial=True)
fig.state('S2', '200\nMid')
fig.state('S3', '300\nEnd',   final=True)
fig.transition('S1', 'S2', label='go')
fig.transition('S2', 'S3', label='done')
fig.transition('S2', 'S1', label='retry')
fig.render(os.path.join(OUTPUT_DIR, 'regress_state.png'))
print("  ✓ PatentState regression")

# PatentLayered
fig = PatentLayered('FIG. R2')
fig.layer('Layer A', ['A1', 'A2'], ref='100')
fig.layer('Layer B', ['B1', 'B2', 'B3'], ref='200')
fig.interface('100', '200', label='API')
fig.render(os.path.join(OUTPUT_DIR, 'regress_layered.png'))
print("  ✓ PatentLayered regression")

# PatentTiming
fig = PatentTiming('FIG. R3')
fig.signal('CLK', '100', wave='clock', period=1.0)
fig.signal('DATA', '200', wave=[0,1,1,0,1,0])
fig.marker(t=2.0, label='T1')
fig.render(os.path.join(OUTPUT_DIR, 'regress_timing.png'))
print("  ✓ PatentTiming regression")

# PatentDFD
fig = PatentDFD('FIG. R4')
fig.external('EXT', '100\nExternal')
fig.process('PROC', '200\nProcess')
fig.store('DB', '300\nStore')
fig.flow('EXT', 'PROC', label='in')
fig.flow('PROC', 'DB', label='save')
fig.render(os.path.join(OUTPUT_DIR, 'regress_dfd.png'))
print("  ✓ PatentDFD regression")

# PatentER
fig = PatentER('FIG. R5')
fig.entity('E1', '100\nEntity A', attrs=['id (PK)', 'name'])
fig.entity('E2', '200\nEntity B', attrs=['id (PK)', 'value'])
fig.relationship('E1', 'E2', '1', 'N', label='rel')
fig.render(os.path.join(OUTPUT_DIR, 'regress_er.png'))
print("  ✓ PatentER regression")

# PatentFigure (original)
fig = PatentFigure('FIG. R6')
fig.node('S100', '100\nStart', shape='start')
fig.node('S200', '200\nProcess')
fig.node('S300', '300\nEnd', shape='end')
fig.edge('S100', 'S200')
fig.edge('S200', 'S300')
fig.render(os.path.join(OUTPUT_DIR, 'regress_figure.png'))
print("  ✓ PatentFigure regression")

print("\n" + "=" * 60)
print("Research 13 COMPLETE — all phases done")
print("=" * 60)
