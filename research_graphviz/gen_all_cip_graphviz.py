"""
gen_all_cip_graphviz.py
GraphvizLayout으로 CIP 특허 도면 11장 생성.
"AI-Based Intelligent Content Generation and Distribution System"

FIG.1  - 시스템 아키텍처 블록 다이어그램
FIG.2  - AI 오케스트레이션 흐름 (8노드 + 피드백 2개)
FIG.3  - 콘텐츠 파이프라인 플로우 (10노드)
FIG.4  - 사용자 개인화 모듈 (6노드 + 피드백 1개)
FIG.5  - 품질 검증 서브시스템 (7노드)
FIG.6  - 분산 스토리지 레이어 (5노드)
FIG.7  - API 게이트웨이 라우팅 (8노드 + 피드백 1개)
FIG.8  - 실시간 모니터링 (6노드)
FIG.9  - 배치 처리 파이프라인 (9노드)
FIG.10 - 보안 인증 흐름 (7노드 + 피드백 1개)
FIG.11 - 종합 시스템 아키텍처 (10노드 + 피드백 2개)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from graphviz_layout import GraphvizLayout

OUT_DIR = os.path.dirname(__file__)
warnings_total = []
pass_count = 0
fail_count = 0


def report(fig_label, out_path, warnings):
    global pass_count, fail_count
    rel = os.path.basename(out_path)
    issues = [w for w in (warnings or []) if isinstance(w, str) and
              any(kw in w for kw in ['overlap', 'Diagonal', 'Dangling', 'dangling'])]
    if issues:
        fail_count += 1
        print(f'  ⚠ {fig_label}: {len(issues)} issues')
        for w in issues[:3]:
            print(f'    - {w[:80]}')
    else:
        pass_count += 1
        print(f'  ✓ {fig_label}: OK → {rel}')
    warnings_total.extend(warnings or [])


# ── FIG.1: 시스템 아키텍처 블록 다이어그램 ───────────────────────────────────
def gen_fig1():
    lay = GraphvizLayout('FIG. 1', orientation='portrait')
    lay.node('100', '100\nUser Layer')
    lay.node('110', '110\nMobile Client')
    lay.node('115', '115\nWeb Client')
    lay.node('120', '120\nAPI Gateway')
    lay.node('130', '130\nAI Processing Core')
    lay.node('140', '140\nContent Engine')
    lay.node('150', '150\nStorage Layer')
    lay.node('160', '160\nMonitoring')

    lay.rank_hint('100', 0)
    lay.rank_hint('110', 1)
    lay.rank_hint('115', 1)
    lay.rank_hint('120', 2)
    lay.rank_hint('130', 3)
    lay.rank_hint('140', 3)
    lay.rank_hint('150', 4)
    lay.rank_hint('160', 5)

    lay.edge('100', '110')
    lay.edge('100', '115')
    lay.edge('110', '120')
    lay.edge('115', '120')
    lay.edge('120', '130')
    lay.edge('120', '140')
    lay.edge('130', '150')
    lay.edge('140', '150')
    lay.edge('150', '160')

    out = os.path.join(OUT_DIR, 'FIG1.png')
    w = lay.render(out)
    report('FIG. 1', out, w)


# ── FIG.2: AI 오케스트레이션 흐름 ─────────────────────────────────────────────
def gen_fig2():
    lay = GraphvizLayout('FIG. 2', orientation='portrait')
    lay.node('200', '200\nUser Interface\n& Input Handler')
    lay.node('210', '210\nContext Analysis Unit')
    lay.node('220', '220\nKnowledge Retrieval Unit')
    lay.node('230', '230\nAI Orchestration Engine')
    lay.node('240', '240\nResponse Generator A')
    lay.node('245', '245\nResponse Generator B')
    lay.node('250', '250\nQuality Evaluator')
    lay.node('260', '260\nOutput Formatter')

    lay.rank_hint('200', 0)
    lay.rank_hint('210', 1)
    lay.rank_hint('220', 1)
    lay.rank_hint('230', 2)
    lay.rank_hint('240', 3)
    lay.rank_hint('245', 3)
    lay.rank_hint('250', 4)
    lay.rank_hint('260', 5)

    lay.edge('200', '210', label='context req.')
    lay.edge('200', '220', label='knowledge req.')
    lay.edge('210', '230', label='context data')
    lay.edge('220', '230', label='knowledge data')
    lay.edge('230', '240', label='task A')
    lay.edge('230', '245', label='task B')
    lay.edge('240', '250', label='response A')
    lay.edge('245', '250', label='response B')
    lay.edge('250', '260', label='approved')
    lay.edge('250', '230', label='retry', feedback=True)
    lay.edge('260', '200', label='loop', feedback=True)

    out = os.path.join(OUT_DIR, 'FIG2.png')
    w = lay.render(out)
    report('FIG. 2', out, w)


# ── FIG.3: 콘텐츠 파이프라인 플로우 ──────────────────────────────────────────
def gen_fig3():
    lay = GraphvizLayout('FIG. 3', orientation='portrait')
    lay.node('300', '300\nContent Ingestion')
    lay.node('310', '310\nPreprocessor')
    lay.node('320', '320\nMetadata Extractor')
    lay.node('330', '330\nContent Classifier')
    lay.node('340', '340\nAI Enrichment')
    lay.node('350', '350\nDeduplication Unit')
    lay.node('360', '360\nQuality Filter')
    lay.node('370', '370\nIndex Builder')
    lay.node('380', '380\nContent Distributor')
    lay.node('390', '390\nDelivery Cache')

    lay.rank_hint('300', 0)
    lay.rank_hint('310', 1)
    lay.rank_hint('320', 2)
    lay.rank_hint('330', 2)
    lay.rank_hint('340', 3)
    lay.rank_hint('350', 4)
    lay.rank_hint('360', 4)
    lay.rank_hint('370', 5)
    lay.rank_hint('380', 6)
    lay.rank_hint('390', 7)

    lay.edge('300', '310')
    lay.edge('310', '320')
    lay.edge('310', '330')
    lay.edge('320', '340')
    lay.edge('330', '340')
    lay.edge('340', '350')
    lay.edge('340', '360')
    lay.edge('350', '370')
    lay.edge('360', '370')
    lay.edge('370', '380')
    lay.edge('380', '390')

    out = os.path.join(OUT_DIR, 'FIG3.png')
    w = lay.render(out)
    report('FIG. 3', out, w)


# ── FIG.4: 사용자 개인화 모듈 ───────────────────────────────────────────────
def gen_fig4():
    lay = GraphvizLayout('FIG. 4', orientation='portrait')
    lay.node('400', '400\nUser Profile Store')
    lay.node('410', '410\nBehavior Tracker')
    lay.node('420', '420\nPreference Learner')
    lay.node('430', '430\nPersonalization Engine')
    lay.node('440', '440\nRecommendation Generator')
    lay.node('450', '450\nFeedback Collector')

    lay.rank_hint('400', 0)
    lay.rank_hint('410', 1)
    lay.rank_hint('420', 2)
    lay.rank_hint('430', 3)
    lay.rank_hint('440', 4)
    lay.rank_hint('450', 5)

    lay.edge('400', '410')
    lay.edge('410', '420')
    lay.edge('420', '430')
    lay.edge('430', '440')
    lay.edge('440', '450')
    lay.edge('450', '420', label='update', feedback=True)

    out = os.path.join(OUT_DIR, 'FIG4.png')
    w = lay.render(out)
    report('FIG. 4', out, w)


# ── FIG.5: 품질 검증 서브시스템 ──────────────────────────────────────────────
def gen_fig5():
    lay = GraphvizLayout('FIG. 5', orientation='portrait')
    lay.node('500', '500\nContent Input')
    lay.node('510', '510\nSyntax Validator')
    lay.node('520', '520\nSemantic Checker')
    lay.node('530', '530\nFactual Verifier')
    lay.node('540', '540\nBias Detector')
    lay.node('550', '550\nQuality Scorer')
    lay.node('560', '560\nApproval Gate')

    lay.rank_hint('500', 0)
    lay.rank_hint('510', 1)
    lay.rank_hint('520', 2)
    lay.rank_hint('530', 2)
    lay.rank_hint('540', 3)
    lay.rank_hint('550', 4)
    lay.rank_hint('560', 5)

    lay.edge('500', '510')
    lay.edge('510', '520')
    lay.edge('510', '530')
    lay.edge('520', '540')
    lay.edge('530', '540')
    lay.edge('540', '550')
    lay.edge('550', '560')

    out = os.path.join(OUT_DIR, 'FIG5.png')
    w = lay.render(out)
    report('FIG. 5', out, w)


# ── FIG.6: 분산 스토리지 레이어 ──────────────────────────────────────────────
def gen_fig6():
    lay = GraphvizLayout('FIG. 6', orientation='portrait')
    lay.node('600', '600\nStorage Controller')
    lay.node('610', '610\nPrimary Database')
    lay.node('620', '620\nReplica Store')
    lay.node('630', '630\nCache Layer')
    lay.node('640', '640\nArchive Storage')

    lay.rank_hint('600', 0)
    lay.rank_hint('610', 1)
    lay.rank_hint('620', 1)
    lay.rank_hint('630', 2)
    lay.rank_hint('640', 2)

    lay.edge('600', '610')
    lay.edge('600', '620')
    lay.edge('610', '630')
    lay.edge('620', '640')
    lay.edge('630', '640', label='sync')

    out = os.path.join(OUT_DIR, 'FIG6.png')
    w = lay.render(out)
    report('FIG. 6', out, w)


# ── FIG.7: API 게이트웨이 라우팅 ─────────────────────────────────────────────
def gen_fig7():
    lay = GraphvizLayout('FIG. 7', orientation='portrait')
    lay.node('700', '700\nClient Request')
    lay.node('710', '710\nLoad Balancer')
    lay.node('720', '720\nRate Limiter')
    lay.node('730', '730\nAuth Validator')
    lay.node('740', '740\nRequest Router')
    lay.node('750', '750\nService A')
    lay.node('755', '755\nService B')
    lay.node('760', '760\nResponse Aggregator')

    lay.rank_hint('700', 0)
    lay.rank_hint('710', 1)
    lay.rank_hint('720', 2)
    lay.rank_hint('730', 3)
    lay.rank_hint('740', 4)
    lay.rank_hint('750', 5)
    lay.rank_hint('755', 5)
    lay.rank_hint('760', 6)

    lay.edge('700', '710')
    lay.edge('710', '720')
    lay.edge('720', '730')
    lay.edge('730', '740')
    lay.edge('740', '750', label='route A')
    lay.edge('740', '755', label='route B')
    lay.edge('750', '760')
    lay.edge('755', '760')
    lay.edge('730', '710', label='throttle', feedback=True)

    out = os.path.join(OUT_DIR, 'FIG7.png')
    w = lay.render(out)
    report('FIG. 7', out, w)


# ── FIG.8: 실시간 모니터링 ────────────────────────────────────────────────────
def gen_fig8():
    lay = GraphvizLayout('FIG. 8', orientation='portrait')
    lay.node('800', '800\nMetrics Collector')
    lay.node('810', '810\nStream Processor')
    lay.node('820', '820\nAnomaly Detector')
    lay.node('830', '830\nAlert Manager')
    lay.node('840', '840\nDashboard')
    lay.node('850', '850\nLog Aggregator')

    lay.rank_hint('800', 0)
    lay.rank_hint('810', 1)
    lay.rank_hint('820', 2)
    lay.rank_hint('830', 3)
    lay.rank_hint('840', 3)
    lay.rank_hint('850', 4)

    lay.edge('800', '810')
    lay.edge('810', '820')
    lay.edge('820', '830')
    lay.edge('820', '840')
    lay.edge('830', '850')
    lay.edge('840', '850')

    out = os.path.join(OUT_DIR, 'FIG8.png')
    w = lay.render(out)
    report('FIG. 8', out, w)


# ── FIG.9: 배치 처리 파이프라인 ──────────────────────────────────────────────
def gen_fig9():
    lay = GraphvizLayout('FIG. 9', orientation='portrait')
    lay.node('900', '900\nJob Scheduler')
    lay.node('910', '910\nTask Queue')
    lay.node('920', '920\nWorker Pool A')
    lay.node('925', '925\nWorker Pool B')
    lay.node('930', '930\nData Partitioner')
    lay.node('940', '940\nBatch Processor')
    lay.node('950', '950\nResult Aggregator')
    lay.node('960', '960\nPost-Processor')
    lay.node('970', '970\nOutput Writer')

    lay.rank_hint('900', 0)
    lay.rank_hint('910', 1)
    lay.rank_hint('920', 2)
    lay.rank_hint('925', 2)
    lay.rank_hint('930', 3)
    lay.rank_hint('940', 4)
    lay.rank_hint('950', 5)
    lay.rank_hint('960', 6)
    lay.rank_hint('970', 7)

    lay.edge('900', '910')
    lay.edge('910', '920')
    lay.edge('910', '925')
    lay.edge('920', '930')
    lay.edge('925', '930')
    lay.edge('930', '940')
    lay.edge('940', '950')
    lay.edge('950', '960')
    lay.edge('960', '970')

    out = os.path.join(OUT_DIR, 'FIG9.png')
    w = lay.render(out)
    report('FIG. 9', out, w)


# ── FIG.10: 보안 인증 흐름 ────────────────────────────────────────────────────
def gen_fig10():
    lay = GraphvizLayout('FIG. 10', orientation='portrait')
    lay.node('1000', '1000\nLogin Request')
    lay.node('1010', '1010\nCredential Validator')
    lay.node('1020', '1020\nMFA Handler')
    lay.node('1030', '1030\nToken Generator')
    lay.node('1040', '1040\nSession Manager')
    lay.node('1050', '1050\nAccess Controller')
    lay.node('1060', '1060\nAudit Logger')

    lay.rank_hint('1000', 0)
    lay.rank_hint('1010', 1)
    lay.rank_hint('1020', 2)
    lay.rank_hint('1030', 3)
    lay.rank_hint('1040', 4)
    lay.rank_hint('1050', 5)
    lay.rank_hint('1060', 6)

    lay.edge('1000', '1010')
    lay.edge('1010', '1020', label='2FA req.')
    lay.edge('1020', '1030', label='verified')
    lay.edge('1030', '1040')
    lay.edge('1040', '1050')
    lay.edge('1050', '1060')
    lay.edge('1010', '1060', label='fail log', feedback=True)

    out = os.path.join(OUT_DIR, 'FIG10.png')
    w = lay.render(out)
    report('FIG. 10', out, w)


# ── FIG.11: 종합 시스템 아키텍처 ─────────────────────────────────────────────
def gen_fig11():
    lay = GraphvizLayout('FIG. 11', orientation='landscape')
    lay.node('1100', '1100\nClient Apps')
    lay.node('1110', '1110\nAPI Gateway')
    lay.node('1120', '1120\nAuth Service')
    lay.node('1130', '1130\nAI Orchestrator')
    lay.node('1140', '1140\nContent Engine')
    lay.node('1150', '1150\nPersonalization')
    lay.node('1160', '1160\nQuality Control')
    lay.node('1170', '1170\nStorage Manager')
    lay.node('1180', '1180\nMonitoring Hub')
    lay.node('1190', '1190\nOutput Delivery')

    lay.rank_hint('1100', 0)
    lay.rank_hint('1110', 1)
    lay.rank_hint('1120', 2)
    lay.rank_hint('1130', 3)
    lay.rank_hint('1140', 3)
    lay.rank_hint('1150', 3)
    lay.rank_hint('1160', 4)
    lay.rank_hint('1170', 5)
    lay.rank_hint('1180', 5)
    lay.rank_hint('1190', 6)

    lay.edge('1100', '1110')
    lay.edge('1110', '1120')
    lay.edge('1120', '1130')
    lay.edge('1120', '1140')
    lay.edge('1120', '1150')
    lay.edge('1130', '1160')
    lay.edge('1140', '1160')
    lay.edge('1150', '1160')
    lay.edge('1160', '1170')
    lay.edge('1160', '1180')
    lay.edge('1170', '1190')
    lay.edge('1180', '1190')
    lay.edge('1160', '1130', label='retry', feedback=True)
    lay.edge('1190', '1100', label='loop', feedback=True)

    out = os.path.join(OUT_DIR, 'FIG11.png')
    w = lay.render(out)
    report('FIG. 11', out, w)


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=== GraphvizLayout: CIP 도면 11장 생성 ===\n")
    import time
    t0 = time.time()

    gen_fig1()
    gen_fig2()
    gen_fig3()
    gen_fig4()
    gen_fig5()
    gen_fig6()
    gen_fig7()
    gen_fig8()
    gen_fig9()
    gen_fig10()
    gen_fig11()

    elapsed = time.time() - t0
    print(f"\n{'='*50}")
    print(f"총 11장 생성 완료: {elapsed:.2f}s")
    print(f"PASS: {pass_count}, FAIL: {fail_count}")
    print(f"총 경고 수: {len(warnings_total)}")
    if fail_count > 0:
        print("\n⚠ 주요 문제:")
        for w in warnings_total:
            if isinstance(w, str) and any(kw in w for kw in ['overlap', 'Diagonal', 'dangling']):
                print(f"  - {w[:100]}")
    print(f"{'='*50}")
