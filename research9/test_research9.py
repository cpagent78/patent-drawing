"""
Research 9 Test Suite
Generates all figures for Phase 1-7 testing.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from patent_figure import PatentFigure, PatentSequence

OUT = os.path.dirname(__file__)

def p(fname):
    return os.path.join(OUT, fname)


# ──────────────────────────────────────────────────────────────────────────────
# Phase 1A: 의료 진단 시스템 from_spec()
# ──────────────────────────────────────────────────────────────────────────────

spec_medical = """
S100: 환자 생체 데이터 수집 (혈압, 맥박, 체온, 혈당)
S200: 데이터 전처리 및 이상치 제거
S300: 기계학습 모델로 1차 진단 수행
S400: 진단 신뢰도 임계값(0.85) 초과 여부 판단
S500: 신뢰도 미달 시 추가 검사 항목 요청 후 S100으로 복귀
S600: 1차 진단 결과를 전문의 검토 시스템에 전송
S700: 전문의 승인 여부 판단
S800: 전문의 거부 시 수동 진단 프로세스로 전환 후 종료
S900: 최종 진단 결과를 전자의무기록(EMR) 시스템에 저장
S1000: 환자 단말로 진단 결과 통지
"""

fig1 = PatentFigure.from_spec('FIG. 1', spec_medical)
warnings = fig1.validate()
print(f"Phase 1A warnings: {warnings}")
fig1.render(p('fig1_medical_spec.png'))
print("✓ fig1_medical_spec.png")


# ──────────────────────────────────────────────────────────────────────────────
# Phase 1B: 블록체인 스마트컨트랙트 from_spec() — 병렬 처리
# ──────────────────────────────────────────────────────────────────────────────

spec_blockchain = """
S100: 트랜잭션 요청 수신
S200: 요청자 디지털 서명 검증
S300: 서명 검증 실패 시 트랜잭션 거부 후 종료
S400: 스마트컨트랙트 실행 조건 확인
S500: 조건 미충족 시 대기 큐에 추가 후 종료
S600a: 토큰 잔액 차감 처리
S600b: 수신자 잔액 증가 처리
S600c: 트랜잭션 로그 기록
S700: S600a, S600b, S600c 완료 후 블록 생성
S800: 네트워크 노드 브로드캐스트
S900: 합의 알고리즘(PoS) 실행
S1000: 블록 확정 및 체인에 추가
"""

fig2 = PatentFigure.from_spec('FIG. 2', spec_blockchain)
warnings2 = fig2.validate()
print(f"Phase 1B warnings: {warnings2}")
fig2.render(p('fig2_blockchain_spec.png'))
print("✓ fig2_blockchain_spec.png")


# ──────────────────────────────────────────────────────────────────────────────
# Phase 2A: 시스템 아키텍처 블록 다이어그램 (LR, 3계층)
# ──────────────────────────────────────────────────────────────────────────────

fig3 = PatentFigure('FIG. 3', direction='LR')
fig3.node('CLI',  '310\nClient\nBrowser / Mobile', shape='process')
fig3.node('LB',   '320\nLoad\nBalancer', shape='process')
fig3.node('APP1', '330\nApp Server\nNode A', shape='process')
fig3.node('APP2', '332\nApp Server\nNode B', shape='process')
fig3.node('DB',   '340\nDatabase\nPostgres', shape='cylinder')
fig3.node('CACHE','342\nCache\nRedis', shape='process')

fig3.node_group(['APP1', 'APP2'])

fig3.edge('CLI',  'LB',   label='HTTPS', label_back='response', bidir=True)
fig3.edge('LB',   'APP1', label='route')
fig3.edge('LB',   'APP2', label='route')
fig3.edge('APP1', 'DB',   bidir=True)
fig3.edge('APP2', 'DB',   bidir=True)
fig3.edge('APP1', 'CACHE', bidir=True)
fig3.edge('APP2', 'CACHE', bidir=True)

fig3.render(p('fig3_architecture_lr.png'))
print("✓ fig3_architecture_lr.png")


# ──────────────────────────────────────────────────────────────────────────────
# Phase 2B: IoT 네트워크 토폴로지
# ──────────────────────────────────────────────────────────────────────────────

fig4 = PatentFigure('FIG. 4', direction='LR')
fig4.node('SENS1', '410\nTemp\nSensor', shape='process')
fig4.node('SENS2', '412\nHumidity\nSensor', shape='process')
fig4.node('SENS3', '414\nMotion\nSensor', shape='process')
fig4.node('GW',    '420\nIoT Gateway\nBLE/WiFi', shape='process')
fig4.node('CLOUD', '430\nCloud\nProcessing', shape='process')
fig4.node('DASH',  '440\nDashboard\nMobile App', shape='process')

fig4.node_group(['SENS1', 'SENS2', 'SENS3'])

fig4.edge('SENS1', 'GW', label='BLE')
fig4.edge('SENS2', 'GW', label='BLE')
fig4.edge('SENS3', 'GW', label='BLE')
fig4.edge('GW',    'CLOUD', label='MQTT', label_back='config', bidir=True)
fig4.edge('CLOUD', 'DASH',  label='WebSocket', bidir=True)

fig4.render(p('fig4_iot_topology.png'))
print("✓ fig4_iot_topology.png")


# ──────────────────────────────────────────────────────────────────────────────
# Phase 2C: AI 파이프라인 (수평, 단계별)
# ──────────────────────────────────────────────────────────────────────────────

fig5 = PatentFigure('FIG. 5', direction='LR')
fig5.node('D',  '510\nRaw\nData', shape='cylinder')
fig5.node('PP', '520\nPre-\nProcessing', shape='process')
fig5.node('FE', '530\nFeature\nExtraction', shape='process')
fig5.node('ML', '540\nML Model\nInference', shape='process')
fig5.node('PO', '550\nPost-\nProcessing', shape='process')
fig5.node('OUT','560\nOutput\nResults', shape='process')

fig5.edge('D',  'PP', label='raw')
fig5.edge('PP', 'FE', label='clean')
fig5.edge('FE', 'ML', label='vectors')
fig5.edge('ML', 'PO', label='scores')
fig5.edge('PO', 'OUT',label='results')

fig5.render(p('fig5_ai_pipeline.png'))
print("✓ fig5_ai_pipeline.png")


# ──────────────────────────────────────────────────────────────────────────────
# Phase 2D: Bus 연결 테스트
# ──────────────────────────────────────────────────────────────────────────────

fig6b = PatentFigure('FIG. 6', direction='LR')
fig6b.node('CPU',    '610\nCPU\nProcessor', shape='process')
fig6b.node('MEM',    '620\nMemory\nDDR5', shape='process')
fig6b.node('GPU',    '630\nGPU\nAccelerator', shape='process')
fig6b.node('STORE',  '640\nNVMe\nStorage', shape='cylinder')

fig6b.node_group(['CPU', 'MEM', 'GPU', 'STORE'])

fig6b.bus('DATA_BUS', ['CPU', 'MEM', 'GPU', 'STORE'], label='810\nSystem Data Bus')

fig6b.render(p('fig6_bus_connection.png'))
print("✓ fig6_bus_connection.png")


# ──────────────────────────────────────────────────────────────────────────────
# Phase 3: 시퀀스 다이어그램
# ──────────────────────────────────────────────────────────────────────────────

seq = PatentSequence('FIG. 7')
seq.actor('User',   'user')
seq.actor('Server', 'server')
seq.actor('DB',     'db')

seq.message('user',   'server', 'login(id, pw)')
seq.message('server', 'db',     'query(id)')
seq.message('db',     'server', 'result',          return_msg=True)
seq.message('server', 'user',   'JWT token',        return_msg=True)
seq.message('user',   'server', 'GET /api/data')
seq.message('server', 'db',     'SELECT * FROM ...')
seq.message('db',     'server', 'rows',             return_msg=True)
seq.message('server', 'user',   'JSON response',    return_msg=True)

seq.render(p('fig7_sequence.png'))
print("✓ fig7_sequence.png")


# ──────────────────────────────────────────────────────────────────────────────
# Phase 5: 에러 복구 테스트
# ──────────────────────────────────────────────────────────────────────────────

import warnings
with warnings.catch_warnings(record=True) as wlist:
    warnings.simplefilter('always')

    fig_err = PatentFigure('FIG. 8')
    fig_err.node('S100', '')                # empty text
    fig_err.node('S100', 'Process A')       # duplicate ID
    fig_err.node('S200', 'Process B')
    fig_err.node('S300', 'Process C' * 70)  # 210+ chars
    fig_err.node('S400', 'End Step', shape='end')

    fig_err.edge('S100', 'S200')
    fig_err.edge('S200', 'S300')
    fig_err.edge('S300', 'S400')

    validate_warns = fig_err.validate()
    print(f"Phase 5 runtime warnings: {len(wlist)}")
    for w in wlist:
        print(f"  - {w.message}")
    print(f"Phase 5 validate warnings: {validate_warns}")

    fig_err.render(p('fig8_error_recovery.png'))
    print("✓ fig8_error_recovery.png")


# ──────────────────────────────────────────────────────────────────────────────
# Phase 7: 회귀 테스트 — FIG.6 from Research 6
# ──────────────────────────────────────────────────────────────────────────────

fig_reg = PatentFigure('FIG. 9')
fig_reg.node('S500', '500\nReceive Order', shape='start')
fig_reg.node('S502', '502\nValidate Input')
fig_reg.node('S504', '504\nCheck Inventory', shape='diamond')
fig_reg.node('S506', '506\nAlert: Out of Stock')
fig_reg.node('S508', '508\nProcess Payment', shape='diamond')
fig_reg.node('S510', '510\nNotify Failure')
fig_reg.node('S512', '512\nCreate Shipment')
fig_reg.node('S514', '514\nEnd', shape='end')

fig_reg.edge('S500', 'S502')
fig_reg.edge('S502', 'S504')
fig_reg.edge('S504', 'S506', label='No')
fig_reg.edge('S504', 'S508', label='Yes')
fig_reg.edge('S506', 'S502')
fig_reg.edge('S508', 'S510', label='No')
fig_reg.edge('S508', 'S512', label='Yes')
fig_reg.edge('S510', 'S508')
fig_reg.edge('S512', 'S514')

fig_reg.render(p('fig9_regression_flowchart.png'))
print("✓ fig9_regression_flowchart.png")


# ──────────────────────────────────────────────────────────────────────────────
# Phase 7: 회귀 — 한글 플로우
# ──────────────────────────────────────────────────────────────────────────────

fig_kor = PatentFigure('FIG. 10')
fig_kor.node('S600', '600\n결제 시작', shape='start')
fig_kor.node('S610', '610\n결제 방법 선택')
fig_kor.node('S620', '620\n카드/계좌 인증', shape='diamond')
fig_kor.node('S630', '630\n인증 실패 알림')
fig_kor.node('S640', '640\n결제 처리')
fig_kor.node('S650', '650\n영수증 발급', shape='end')

fig_kor.edge('S600', 'S610')
fig_kor.edge('S610', 'S620')
fig_kor.edge('S620', 'S630', label='실패')
fig_kor.edge('S620', 'S640', label='성공')
fig_kor.edge('S630', 'S610')
fig_kor.edge('S640', 'S650')

fig_kor.render(p('fig10_korean_regression.png'))
print("✓ fig10_korean_regression.png")


# ──────────────────────────────────────────────────────────────────────────────
# Phase 7: 회귀 — 프리셋 테스트
# ──────────────────────────────────────────────────────────────────────────────

def _make_preset_fig(label):
    f = PatentFigure(label)
    f.node('S100', '100\nStart', shape='start')
    f.node('S200', '200\nProcess Data')
    f.node('S300', '300\nCheck Result', shape='diamond')
    f.node('S400', '400\nRetry')
    f.node('S500', '500\nEnd', shape='end')
    f.edge('S100', 'S200')
    f.edge('S200', 'S300')
    f.edge('S300', 'S400', label='No')
    f.edge('S300', 'S500', label='Yes')
    f.edge('S400', 'S200')
    return f

_make_preset_fig('FIG. 11').preset('uspto').render(p('fig11_preset_uspto.png'))
print("✓ fig11_preset_uspto.png")

_make_preset_fig('FIG. 12').preset('draft').render(p('fig12_preset_draft.png'))
print("✓ fig12_preset_draft.png")

_make_preset_fig('FIG. 13').preset('presentation').render(p('fig13_preset_presentation.png'))
print("✓ fig13_preset_presentation.png")


print("\n=== All figures generated successfully ===")
