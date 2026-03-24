"""
detect_type.py — Patent diagram type auto-detector for Momo (patent-drawing skill).

Usage:
    from detect_type import detect_diagram_type

    result = detect_diagram_type(spec_text)
    # result = {
    #   'type': 'flowchart' | 'sequence' | 'state' | 'layered' |
    #           'timing' | 'dfd' | 'er' | 'hardware',
    #   'confidence': 0.0~1.0,
    #   'reason': '판단 근거 한 줄 설명',
    #   'class': 'PatentFigure' | 'PatentSequence' | ...
    # }
"""

import re


# ── 타입별 클래스 매핑 ─────────────────────────────────────────────────────────
_TYPE_CLASS_MAP = {
    'flowchart': 'PatentFigure',
    'sequence':  'PatentSequence',
    'state':     'PatentStateDiagram',
    'layered':   'PatentLayered',
    'timing':    'PatentTiming',
    'dfd':       'PatentDFD',
    'er':        'PatentER',
    'hardware':  'PatentHardware',
}


def detect_diagram_type(text: str) -> dict:
    """
    명세서 텍스트를 분석해서 최적 도면 타입을 반환.

    우선순위:
      1. 시퀀스  (0.9)
      2. 상태    (0.9)
      3. ER      (0.9)
      4. 타이밍  (0.9)
      5. 계층    (0.85)
      6. DFD     (0.85)
      7. 하드웨어 (0.85)
      8. 플로우차트 (0.7, default)

    Returns:
        {
            'type': str,
            'confidence': float,
            'reason': str,
            'class': str,
        }
    """
    t = text  # 원본 텍스트 (대소문자 유지)
    tl = text.lower()  # 소문자 비교용

    candidates: list[dict] = []

    # ── 1. 시퀀스 다이어그램 ──────────────────────────────────────────────────
    seq_score = 0
    seq_reasons = []

    # HTTP 메서드 / 프로토콜
    if re.search(r'\b(POST|GET|PUT|DELETE|PATCH)\s+/', t):
        seq_score += 3
        seq_reasons.append('HTTP 메서드 패턴')
    if re.search(r'\bHTTP\b', t, re.IGNORECASE):
        seq_score += 2
        seq_reasons.append('HTTP 언급')

    # Actor → Actor 패턴  (예: User → Server, Client → DB)
    arrow_actors = re.findall(
        r'[A-Z가-힣][A-Za-z가-힣\s]*\s*(?:→|->|→)\s*[A-Z가-힣][A-Za-z가-힣\s]*',
        t
    )
    if len(arrow_actors) >= 2:
        seq_score += 3
        seq_reasons.append(f'Actor 간 화살표 패턴 {len(arrow_actors)}개')

    # 요청/응답/전송/수신 동사 (한글)
    kr_msg_count = len(re.findall(r'(요청|응답|전송|수신|송신|반환|조회)', t))
    if kr_msg_count >= 2:
        seq_score += min(kr_msg_count, 4)
        seq_reasons.append(f'메시지 동사 {kr_msg_count}회')

    # sends/responds/returns/requests (영어)
    en_msg_count = len(re.findall(
        r'\b(sends?|responds?|returns?|requests?|replies?|forwards?)\b', tl
    ))
    if en_msg_count >= 2:
        seq_score += min(en_msg_count, 3)
        seq_reasons.append(f'영어 메시지 동사 {en_msg_count}회')

    if seq_score >= 5:
        candidates.append({
            'type': 'sequence',
            'confidence': min(0.95, 0.7 + seq_score * 0.03),
            'reason': '시퀀스: ' + ', '.join(seq_reasons),
            'class': _TYPE_CLASS_MAP['sequence'],
        })

    # ── 2. 상태 다이어그램 ────────────────────────────────────────────────────
    state_score = 0
    state_reasons = []

    # 상태 전이 키워드 (한글)
    kr_state_count = len(re.findall(r'(상태|전이|상태\s*변경|전환)', t))
    if kr_state_count >= 2:
        state_score += min(kr_state_count, 4)
        state_reasons.append(f'상태/전이 키워드 {kr_state_count}회')

    # state/transition (영어)
    en_state_count = len(re.findall(r'\b(state|transition|transitions?)\b', tl))
    if en_state_count >= 2:
        state_score += min(en_state_count, 3)
        state_reasons.append(f'영어 state 키워드 {en_state_count}회')

    # 대문자 상태명 (IDLE, ACTIVE, ERROR, STANDBY, etc.)
    upper_states = re.findall(r'\b(IDLE|ACTIVE|ERROR|STANDBY|READY|SLEEP|RUNNING|STOPPED|PAUSED|INIT|OFF|ON)\b', t)
    if len(upper_states) >= 2:
        state_score += len(upper_states)
        state_reasons.append(f'대문자 상태명 {len(upper_states)}개: {set(upper_states)}')

    # 이벤트 조건 패턴
    event_count = len(re.findall(r'(이벤트\s*발생|on event|when .+전이|→\s*[A-Z가-힣].*상태)', t))
    if event_count >= 1:
        state_score += 2
        state_reasons.append(f'이벤트 조건 {event_count}개')

    # 전이 화살표 + 상태 패턴  "→ XX 상태"
    if re.search(r'→\s*\S+\s*상태', t):
        state_score += 2
        state_reasons.append('→ XX 상태 패턴')

    if state_score >= 4:
        candidates.append({
            'type': 'state',
            'confidence': min(0.95, 0.7 + state_score * 0.04),
            'reason': '상태: ' + ', '.join(state_reasons),
            'class': _TYPE_CLASS_MAP['state'],
        })

    # ── 3. ER 다이어그램 ──────────────────────────────────────────────────────
    er_score = 0
    er_reasons = []

    # 엔티티 키워드
    er_entity = len(re.findall(r'\b(엔티티|entity|entities)\b', tl))
    if er_entity >= 1:
        er_score += er_entity * 2
        er_reasons.append(f'엔티티 키워드 {er_entity}회')

    # PK/FK
    pk_fk = len(re.findall(r'\b(PK|FK|primary key|foreign key)\b', t, re.IGNORECASE))
    if pk_fk >= 1:
        er_score += pk_fk * 2
        er_reasons.append(f'PK/FK {pk_fk}회')

    # 관계/relationship
    er_rel = len(re.findall(r'\b(관계|relationship|1:N|N:M|1:1|one-to-many|many-to-many)\b', t, re.IGNORECASE))
    if er_rel >= 1:
        er_score += er_rel * 2
        er_reasons.append(f'관계 키워드 {er_rel}회')

    # 속성
    er_attr = len(re.findall(r'\b(속성|attribute)\b', tl))
    if er_attr >= 1:
        er_score += er_attr
        er_reasons.append(f'속성 키워드 {er_attr}회')

    if er_score >= 4:
        candidates.append({
            'type': 'er',
            'confidence': min(0.95, 0.7 + er_score * 0.04),
            'reason': 'ER: ' + ', '.join(er_reasons),
            'class': _TYPE_CLASS_MAP['er'],
        })

    # ── 4. 타이밍 다이어그램 ─────────────────────────────────────────────────
    timing_score = 0
    timing_reasons = []

    # CLK/클록
    clk_count = len(re.findall(r'\b(CLK|클록|clock)\b', t, re.IGNORECASE))
    if clk_count >= 1:
        timing_score += clk_count * 3
        timing_reasons.append(f'CLK/클록 {clk_count}회')

    # 신호/HIGH/LOW
    sig_count = len(re.findall(r'\b(신호|signal|HIGH|LOW|H|L)\b', t))
    if sig_count >= 2:
        timing_score += min(sig_count, 4)
        timing_reasons.append(f'신호/HIGH/LOW {sig_count}회')

    # edge/timing 용어
    edge_count = len(re.findall(
        r'\b(rising edge|falling edge|setup time|hold time|타이밍|timing|주기|period|펄스|pulse)\b',
        tl
    ))
    if edge_count >= 1:
        timing_score += edge_count * 2
        timing_reasons.append(f'타이밍 용어 {edge_count}회')

    if timing_score >= 4:
        candidates.append({
            'type': 'timing',
            'confidence': min(0.95, 0.7 + timing_score * 0.04),
            'reason': '타이밍: ' + ', '.join(timing_reasons),
            'class': _TYPE_CLASS_MAP['timing'],
        })

    # ── 5. 계층 아키텍처 ──────────────────────────────────────────────────────
    layer_score = 0
    layer_reasons = []

    layer_kw = len(re.findall(
        r'\b(레이어|layer|계층|tier|상위\s*계층|하위\s*계층|스택|stack)\b', tl
    ))
    if layer_kw >= 2:
        layer_score += min(layer_kw, 5)
        layer_reasons.append(f'계층 키워드 {layer_kw}회')

    named_layer = len(re.findall(
        r'\b(application layer|service layer|data layer|presentation layer|'
        r'business layer|infrastructure layer|transport layer|network layer)\b',
        tl
    ))
    if named_layer >= 1:
        layer_score += named_layer * 3
        layer_reasons.append(f'명명된 레이어 {named_layer}개')

    if layer_score >= 4:
        candidates.append({
            'type': 'layered',
            'confidence': min(0.92, 0.65 + layer_score * 0.04),
            'reason': '계층: ' + ', '.join(layer_reasons),
            'class': _TYPE_CLASS_MAP['layered'],
        })

    # ── 6. DFD (데이터 플로우) ────────────────────────────────────────────────
    dfd_score = 0
    dfd_reasons = []

    dfd_kw = len(re.findall(
        r'\b(데이터\s*흐름|data flow|저장소|datastore|외부\s*엔티티|external entity|'
        r'입력\s*데이터|출력\s*데이터|처리\s*모듈|process)\b', tl
    ))
    if dfd_kw >= 2:
        dfd_score += min(dfd_kw, 5)
        dfd_reasons.append(f'DFD 키워드 {dfd_kw}회')

    # 처리/저장소/외부엔티티 3요소 동시 존재
    has_process = bool(re.search(r'(처리|process|프로세스)', tl))
    has_store   = bool(re.search(r'(저장소|datastore|데이터\s*저장)', tl))
    has_ext     = bool(re.search(r'(외부\s*엔티티|external entity|외부\s*시스템)', tl))
    if has_process and has_store:
        dfd_score += 3
        dfd_reasons.append('처리+저장소 동시 존재')
    if has_ext:
        dfd_score += 2
        dfd_reasons.append('외부 엔티티 존재')

    if dfd_score >= 4:
        candidates.append({
            'type': 'dfd',
            'confidence': min(0.92, 0.65 + dfd_score * 0.04),
            'reason': 'DFD: ' + ', '.join(dfd_reasons),
            'class': _TYPE_CLASS_MAP['dfd'],
        })

    # ── 7. 하드웨어 블록 ──────────────────────────────────────────────────────
    hw_score = 0
    hw_reasons = []

    hw_chips = len(re.findall(
        r'\b(회로|circuit|칩|chip|MCU|CPU|ALU|GPU|SoC|MPU|FPGA)\b', t, re.IGNORECASE
    ))
    if hw_chips >= 1:
        hw_score += hw_chips * 2
        hw_reasons.append(f'칩/CPU/MCU {hw_chips}회')

    hw_comp = len(re.findall(
        r'\b(레지스터|register|메모리|memory|버스|bus|핀|pin|ADC|DAC|GPIO|UART|SPI|I2C|PWM|DMA)\b',
        t, re.IGNORECASE
    ))
    if hw_comp >= 2:
        hw_score += min(hw_comp, 5)
        hw_reasons.append(f'하드웨어 컴포넌트 {hw_comp}회')

    if hw_score >= 4:
        candidates.append({
            'type': 'hardware',
            'confidence': min(0.92, 0.65 + hw_score * 0.04),
            'reason': '하드웨어: ' + ', '.join(hw_reasons),
            'class': _TYPE_CLASS_MAP['hardware'],
        })

    # ── 8. 플로우차트 (명시적 S100... 패턴 or default) ────────────────────────
    flow_score = 0
    flow_reasons = []

    step_pattern = re.findall(r'\bS\d{3,}\b', t)
    if len(step_pattern) >= 2:
        flow_score += len(step_pattern) * 2
        flow_reasons.append(f'S100 형식 단계 {len(step_pattern)}개')

    step_kw = len(re.findall(r'\b(단계|step|절차|프로세스|과정)\b', tl))
    if step_kw >= 2:
        flow_score += min(step_kw, 3)
        flow_reasons.append(f'단계/절차 키워드 {step_kw}회')

    if flow_score >= 4:
        flow_conf = min(0.92, 0.7 + flow_score * 0.03)
        candidates.append({
            'type': 'flowchart',
            'confidence': flow_conf,
            'reason': '플로우차트: ' + ', '.join(flow_reasons),
            'class': _TYPE_CLASS_MAP['flowchart'],
        })

    # ── 최종 선택: confidence 최고값 ──────────────────────────────────────────
    if not candidates:
        # 아무것도 안 걸리면 flowchart default (confidence 낮게)
        return {
            'type': 'flowchart',
            'confidence': 0.6,
            'reason': '패턴 미감지 — 기본값 플로우차트 사용',
            'class': _TYPE_CLASS_MAP['flowchart'],
        }

    # 최고 confidence 선택 (동점 시 flowchart 우선)
    candidates.sort(key=lambda x: (-x['confidence'], x['type'] != 'flowchart'))
    return candidates[0]


# ── 간편 CLI 테스트 ────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import json

    TEST_CASES = [
        {
            'label': '케이스 1: 플로우차트',
            'text': """
S100: 사용자 로그인 요청
S200: 자격증명 검증
S300: 실패 시 S200으로 복귀
S400: 성공 시 토큰 발급
            """,
            'expected_type': 'flowchart',
            'expected_min_conf': 0.85,
        },
        {
            'label': '케이스 2: 시퀀스',
            'text': """
사용자가 브라우저에 ID/PW를 입력한다.
브라우저는 Auth Server로 POST /login 요청을 전송한다.
Auth Server는 Database에서 사용자 정보를 조회한다.
Database가 사용자 레코드를 반환한다.
Auth Server가 JWT 토큰을 생성하여 브라우저로 응답한다.
            """,
            'expected_type': 'sequence',
            'expected_min_conf': 0.9,
        },
        {
            'label': '케이스 3: 상태',
            'text': """
디바이스는 초기에 OFF 상태에 있다.
전원 버튼을 누르면 STANDBY 상태로 전이한다.
페어링 완료 시 ACTIVE 상태로 전이한다.
에러 발생 시 ERROR 상태로 전이하고, 리셋 시 OFF로 돌아간다.
            """,
            'expected_type': 'state',
            'expected_min_conf': 0.9,
        },
        {
            'label': '케이스 4: 혼합 (애매한 경우)',
            'text': """
시스템은 데이터를 수집하고 처리하여 결과를 저장한다.
사용자는 결과를 조회할 수 있다.
            """,
            'expected_type': 'flowchart',
            'expected_max_conf': 0.75,
        },
        {
            'label': '케이스 5: ER',
            'text': """
User 엔티티는 user_id(PK), name, email 속성을 가진다.
Order 엔티티는 order_id(PK), date, user_id(FK) 속성을 가진다.
User와 Order는 1:N 관계이다.
            """,
            'expected_type': 'er',
            'expected_min_conf': 0.9,
        },
    ]

    all_passed = True
    for case in TEST_CASES:
        result = detect_diagram_type(case['text'])
        type_ok = result['type'] == case['expected_type']
        conf_ok = True
        if 'expected_min_conf' in case:
            conf_ok = result['confidence'] >= case['expected_min_conf']
        if 'expected_max_conf' in case:
            conf_ok = result['confidence'] < case['expected_max_conf']

        status = '✅ PASS' if (type_ok and conf_ok) else '❌ FAIL'
        if not (type_ok and conf_ok):
            all_passed = False

        print(f"{status} {case['label']}")
        print(f"       타입: {result['type']} (예상: {case['expected_type']})")
        print(f"       confidence: {result['confidence']:.2f}")
        print(f"       근거: {result['reason']}")
        print()

    print('=' * 50)
    print('전체 결과:', '✅ 모두 통과' if all_passed else '❌ 실패 있음')
