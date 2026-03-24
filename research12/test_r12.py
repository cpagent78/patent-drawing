"""
Research 12 Test Script
Tests: PatentLayered (layered architecture) + PatentTiming (timing diagrams)
"""
import sys, os
SKILL_DIR = os.path.expanduser('~/.openclaw/skills/patent-drawing/scripts')
sys.path.insert(0, SKILL_DIR)
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

from patent_figure import PatentLayered, PatentTiming

print("=" * 60)
print("Research 12 — Layered Architecture + Timing Diagrams")
print("=" * 60)

# ── Test A: OSI 7-Layer Model ─────────────────────────────────────────────────
print("\n[1/6] OSI 7-Layer Model (layered_a_osi.png)")
fig = PatentLayered('FIG. 2A')
fig.layer('Application Layer',  ['HTTP', 'FTP', 'SMTP'],      ref='700')
fig.layer('Presentation Layer', ['SSL/TLS', 'Encoding'],      ref='600')
fig.layer('Session Layer',      ['Session Manager'],           ref='500')
fig.layer('Transport Layer',    ['TCP', 'UDP'],                ref='400')
fig.layer('Network Layer',      ['IP', 'ICMP', 'Routing'],    ref='300')
fig.layer('Data Link Layer',    ['Ethernet', 'WiFi', 'MAC'],  ref='200')
fig.layer('Physical Layer',     ['Cable', 'Fiber', 'Radio'],  ref='100')
fig.interface('700', '600', label='App Interface')
fig.interface('600', '500', label='Presentation')
fig.interface('500', '400', label='Session')
fig.interface('400', '300', label='Transport')
fig.interface('300', '200', label='Network')
fig.interface('200', '100', label='Physical')
fig.render(os.path.join(OUTPUT_DIR, 'layered_a_osi.png'))
print("  ✓ layered_a_osi.png")

# ── Test B: Microservice Architecture ────────────────────────────────────────
print("\n[2/6] Microservice Architecture (layered_b_microservice.png)")
fig = PatentLayered('FIG. 2B')
fig.layer('API Gateway Layer',
          ['Rate Limiter', 'Auth Filter', 'Load Balancer', 'Router'],
          ref='100')
fig.layer('Service Layer',
          ['User Service', 'Order Service', 'Payment Service', 'Notification'],
          ref='200')
fig.layer('Data Layer',
          ['PostgreSQL', 'Redis Cache', 'S3 Storage', 'Kafka MQ'],
          ref='300')
fig.interface('100', '200', label='REST/gRPC')
fig.interface('200', '300', label='ORM/Query')
fig.render(os.path.join(OUTPUT_DIR, 'layered_b_microservice.png'))
print("  ✓ layered_b_microservice.png")

# ── Test C: Embedded System Software Stack ────────────────────────────────────
print("\n[3/6] Embedded Software Stack (layered_c_embedded.png)")
fig = PatentLayered('FIG. 2C')
fig.layer('Application',    ['Sensor App', 'Control Logic', 'Comm App'], ref='400')
fig.layer('Middleware',     ['RTOS', 'Protocol Stack', 'Driver Manager'], ref='300')
fig.layer('HAL',            ['GPIO HAL', 'UART HAL', 'SPI HAL'],         ref='200')
fig.layer('Hardware',       ['MCU Core', 'Peripherals', 'Memory'],       ref='100')
fig.interface('400', '300', label='System Calls')
fig.interface('300', '200', label='HAL API')
fig.interface('200', '100', label='Register I/O')
fig.render(os.path.join(OUTPUT_DIR, 'layered_c_embedded.png'))
print("  ✓ layered_c_embedded.png")

# ── Test D: SPI Communication Protocol Timing ─────────────────────────────────
print("\n[4/6] SPI Timing (timing_a_spi.png)")
fig = PatentTiming('FIG. 5A')
fig.signal('SCLK',  '100', wave='clock', period=1.0)
fig.signal('CS',    '200', wave=[1,0,0,0,0,0,0,0,0,1])
fig.signal('MOSI',  '300', wave=[0,0,1,0,1,1,0,1,0,0],
           labels=['D7','D6','D5','D4'])
fig.signal('MISO',  '400', wave=[0,0,0,1,1,0,1,0,1,0])
fig.marker(t=1.0, label='CS Assert')
fig.marker(t=9.0, label='CS Release')
fig.render(os.path.join(OUTPUT_DIR, 'timing_a_spi.png'))
print("  ✓ timing_a_spi.png")

# ── Test E: DRAM Read Cycle ───────────────────────────────────────────────────
print("\n[5/6] DRAM Read Cycle (timing_b_dram.png)")
fig = PatentTiming('FIG. 5B')
fig.signal('CLK',     '100', wave='clock', period=1.0)
fig.signal('RAS',     '200', wave=[1,0,0,0,0,1,1,1])
fig.signal('CAS',     '300', wave=[1,1,0,0,1,1,1,1])
fig.signal('WE',      '400', wave=[1,1,1,1,1,1,1,1])  # read: WE=high
fig.signal('DATA',    '500', wave=[0,0,0,'X',0,1,0,0])
fig.marker(t=1.0, label='tRAS')
fig.marker(t=2.0, label='tCAS')
fig.marker(t=3.5, label='tACC')
fig.render(os.path.join(OUTPUT_DIR, 'timing_b_dram.png'))
print("  ✓ timing_b_dram.png")

# ── Test F: I2C Data Transfer ─────────────────────────────────────────────────
print("\n[6/6] I2C Data Transfer (timing_c_i2c.png)")
fig = PatentTiming('FIG. 5C')
fig.signal('SCL', '100', wave='clock', period=1.0)
fig.signal('SDA', '200', wave=[1,0,0,1,0,1,0,1,1,0,0,0,1,1],
           labels=['START','A6','A5','A4','A3','A2','A1','A0'])
fig.signal('ACK', '300', wave=[1,1,1,1,1,1,1,1,0,1,1,1,1,1])
fig.marker(t=1.0,  label='START')
fig.marker(t=9.0,  label='ACK')
fig.marker(t=13.0, label='STOP')
fig.render(os.path.join(OUTPUT_DIR, 'timing_c_i2c.png'))
print("  ✓ timing_c_i2c.png")

print("\n" + "=" * 60)
print("Research 12 COMPLETE — 6 figures generated")
print("=" * 60)
