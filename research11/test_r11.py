"""
Research 11 Test Script
Tests: PatentState (state diagrams) + PatentHardware (hardware block diagrams)
"""
import sys, os
SKILL_DIR = os.path.expanduser('~/.openclaw/skills/patent-drawing/scripts')
sys.path.insert(0, SKILL_DIR)
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

from patent_figure import PatentState, PatentHardware

print("=" * 60)
print("Research 11 — State Diagrams + Hardware Block Diagrams")
print("=" * 60)

# ── Test A: TCP Connection State Machine ─────────────────────────────────────
print("\n[1/6] TCP Connection State Machine (state_a_tcp.png)")
fig = PatentState('FIG. 4A')
fig.state('CLOSED',      '100\nClosed',      initial=True)
fig.state('LISTEN',      '200\nListen')
fig.state('SYN_SENT',    '300\nSYN Sent')
fig.state('ESTABLISHED', '400\nEstablished')
fig.state('CLOSE_WAIT',  '500\nClose Wait',  final=True)
fig.transition('CLOSED',      'LISTEN',      label='passive open')
fig.transition('CLOSED',      'SYN_SENT',    label='active open')
fig.transition('LISTEN',      'SYN_SENT',    label='send SYN')
fig.transition('SYN_SENT',    'ESTABLISHED', label='SYN+ACK rcvd')
fig.transition('SYN_SENT',    'CLOSED',      label='timeout')
fig.transition('ESTABLISHED', 'CLOSE_WAIT',  label='recv FIN')
fig.render(os.path.join(OUTPUT_DIR, 'state_a_tcp.png'))
print("  ✓ state_a_tcp.png")

# ── Test B: Smart Home Device State (IoT) ────────────────────────────────────
print("\n[2/6] Smart Home Device State (state_b_iot.png)")
fig = PatentState('FIG. 4B')
fig.state('INIT',     '100\nInitializing', initial=True)
fig.state('STANDBY',  '200\nStandby')
fig.state('ACTIVE',   '300\nActive')
fig.state('SLEEP',    '400\nSleep Mode')
fig.state('ERROR',    '500\nError')
fig.state('SHUTDOWN', '600\nShutdown',    final=True)
fig.transition('INIT',     'STANDBY',  label='boot complete')
fig.transition('STANDBY',  'ACTIVE',   label='cmd received')
fig.transition('ACTIVE',   'STANDBY',  label='idle timeout')
fig.transition('ACTIVE',   'SLEEP',    label='power save')
fig.transition('SLEEP',    'STANDBY',  label='wake signal')
fig.transition('ACTIVE',   'ERROR',    label='fault detected')
fig.transition('ERROR',    'STANDBY',  label='error cleared')
fig.transition('STANDBY',  'SHUTDOWN', label='power off')
fig.render(os.path.join(OUTPUT_DIR, 'state_b_iot.png'))
print("  ✓ state_b_iot.png")

# ── Test C: Protocol Handshake State (Communication Patent) ──────────────────
print("\n[3/6] Protocol Handshake State (state_c_protocol.png)")
fig = PatentState('FIG. 4C', direction='LR')
fig.state('IDLE',       '100\nIdle',       initial=True)
fig.state('CONNECTING', '200\nConnecting')
fig.state('AUTH',       '300\nAuth')
fig.state('READY',      '400\nReady')
fig.state('CLOSED',     '500\nClosed',     final=True)
fig.transition('IDLE',       'CONNECTING', label='initiate()')
fig.transition('CONNECTING', 'AUTH',       label='hello rcvd')
fig.transition('CONNECTING', 'IDLE',       label='timeout')
fig.transition('AUTH',       'READY',      label='auth OK')
fig.transition('AUTH',       'CLOSED',     label='auth fail')
fig.transition('READY',      'CLOSED',     label='close()')
fig.transition('READY',      'READY',      label='heartbeat')  # self-loop
fig.render(os.path.join(OUTPUT_DIR, 'state_c_protocol.png'))
print("  ✓ state_c_protocol.png")

# ── Test D: CPU Internal Block ────────────────────────────────────────────────
print("\n[4/6] CPU Internal Block (hw_a_cpu.png)")
fig = PatentHardware('FIG. 2A')
cpu  = fig.chip('CPU', '610\nALU Core', cx=2.5, cy=7.5,
                n_pins_left=4, n_pins_right=4)
cache = fig.register('CACHE', '620\nL1 Cache', cx=2.5, cy=5.8, cells=8,
                     cell_w=0.28, cell_h=0.38)
bus   = fig.block('BUS', '630\nBus Interface', cx=2.5, cy=4.2,
                  w=1.80, h=0.55)
reg   = fig.register('REG', '640\nRegisters', cx=5.0, cy=7.5, cells=4,
                     cell_w=0.35, cell_h=0.38)
mux   = fig.mux('MUX', '650\nMUX', cx=5.0, cy=5.8, w=0.80, h=1.0)
mem   = fig.memory_array('MEM', '660\nCache Array', cx=5.0, cy=4.0,
                         rows=4, cols=6, cell_w=0.22, cell_h=0.22)
fig.connect(cpu, cache, label='data')
fig.connect(cache, bus, label='miss')
fig.connect(cpu, reg, bidir=True)
fig.connect(reg, mux, label='sel')
fig.connect(mux, mem, label='addr')
fig.connect(cache, mux, label='tag')
fig.render(os.path.join(OUTPUT_DIR, 'hw_a_cpu.png'))
print("  ✓ hw_a_cpu.png")

# ── Test E: SoC Architecture ─────────────────────────────────────────────────
print("\n[5/6] SoC Architecture (hw_b_soc.png)")
fig = PatentHardware('FIG. 2B')
ap    = fig.chip('AP',  '710\nApp Processor', cx=2.2, cy=8.2,
                 n_pins_left=3, n_pins_right=3)
modem = fig.chip('MDM', '720\nModem', cx=5.8, cy=8.2,
                 n_pins_left=3, n_pins_right=3)
rf    = fig.block('RF', '730\nRF Frontend', cx=5.8, cy=6.5,
                  w=1.50, h=0.55)
dram  = fig.memory_array('DRAM', '740\nLPDDR4', cx=2.2, cy=6.5,
                          rows=3, cols=4, cell_w=0.28, cell_h=0.25)
pmic  = fig.block('PMIC', '750\nPMIC', cx=4.0, cy=4.8,
                  w=1.50, h=0.55)
fig.connect(ap, modem, label='MIPI', bidir=True)
fig.connect(ap, dram, label='LPDDR4')
fig.connect(modem, rf, label='RF signal')
fig.connect(ap, pmic, label='power req')
fig.connect(modem, pmic, label='power req')
fig.render(os.path.join(OUTPUT_DIR, 'hw_b_soc.png'))
print("  ✓ hw_b_soc.png")

# ── Test F: Sensor Interface Circuit ─────────────────────────────────────────
print("\n[6/6] Sensor Interface Circuit (hw_c_sensor.png)")
fig = PatentHardware('FIG. 2C')
sensor = fig.block('SNS', '810\nSensor Array', cx=1.8, cy=8.0,
                   w=1.40, h=0.60)
adc    = fig.chip('ADC', '820\nADC', cx=3.8, cy=8.0,
                  n_pins_left=2, n_pins_right=2)
dsp    = fig.chip('DSP', '830\nDSP Core', cx=5.8, cy=8.0,
                  n_pins_left=2, n_pins_right=2)
mem    = fig.memory_array('BUF', '840\nData Buffer', cx=5.8, cy=6.2,
                          rows=2, cols=6, cell_w=0.24, cell_h=0.24)
mcu    = fig.chip('MCU', '850\nMCU', cx=3.8, cy=6.2,
                  n_pins_left=2, n_pins_right=2)
mux_s  = fig.mux('AMUX', '860\nAnalog MUX', cx=2.8, cy=6.2,
                 w=0.70, h=0.90)
fig.connect(sensor, adc, label='analog')
fig.connect(adc, dsp, label='digital')
fig.connect(dsp, mem, label='DMA')
fig.connect(mem, mcu, label='bus')
fig.connect(sensor, mux_s, label='ch sel')
fig.connect(mux_s, mcu, label='ctrl')
fig.render(os.path.join(OUTPUT_DIR, 'hw_c_sensor.png'))
print("  ✓ hw_c_sensor.png")

print("\n" + "=" * 60)
print("Research 11 COMPLETE — 6 figures generated")
print("=" * 60)
