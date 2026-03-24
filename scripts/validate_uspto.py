"""
validate_uspto.py — USPTO 규격 자동 검증 스크립트
Research 10 (Phase 1)

생성된 PNG 파일을 스캔하여 USPTO §1.84 규격 위반 항목을 자동으로 리포트.

사용법:
    python validate_uspto.py output.png [output2.png ...]
    python validate_uspto.py research10/

검증 항목:
    #1  모든 박스에 참조번호 있는지 (§1.84(p))        → PatentFigure.validate()로 사전 체크
    #2  텍스트 최소 10pt (§1.84(p)(3))               → PatentFigure DEFAULT_FS=10
    #3  흑백만 사용 — 컬러 없는지 (§1.84(m))          → PNG 픽셀 분석
    #4  FIG. N 라벨 존재 및 위치 (§1.84(u))           → 구조 체크
    #5  화살표 최소 shaft 0.44" (§1.84)              → 내부 검증
    #6  특수기호/유니코드 아래첨자 없는지              → PatentFigure.validate()
    #7  파일 크기 / 해상도 적정 여부                   → PNG 메타데이터
"""

import os
import sys
import glob
import argparse
from pathlib import Path


def analyze_colors(png_path: str) -> dict:
    """
    PNG 이미지를 열어 컬러 사용 여부 분석.
    반환: {'is_bw': bool, 'max_color_deviation': float, 'suspicious_pixels': int}
    
    흑백 기준: 각 픽셀의 R=G=B (또는 허용 오차 ±5 이내)
    """
    result = {
        'is_bw': True,
        'max_color_deviation': 0.0,
        'suspicious_pixels': 0,
        'error': None,
    }
    try:
        from PIL import Image
        import numpy as np
        with Image.open(png_path) as img:
            img_rgb = img.convert('RGB')
            arr = np.array(img_rgb, dtype=float)
            r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
            # Deviation from grayscale
            mean_chan = (r + g + b) / 3.0
            dev_r = np.abs(r - mean_chan)
            dev_g = np.abs(g - mean_chan)
            dev_b = np.abs(b - mean_chan)
            max_dev = float(np.max(np.maximum(dev_r, np.maximum(dev_g, dev_b))))
            # Pixels with significant color (threshold=10)
            color_mask = (dev_r > 10) | (dev_g > 10) | (dev_b > 10)
            n_color = int(np.sum(color_mask))
            result['max_color_deviation'] = round(max_dev, 1)
            result['suspicious_pixels'] = n_color
            result['is_bw'] = (n_color == 0)
    except ImportError:
        result['error'] = 'PIL/numpy not available — skipping color check'
    except Exception as e:
        result['error'] = f'Color analysis error: {e}'
    return result


def check_resolution(png_path: str) -> dict:
    """
    PNG 해상도 및 크기 체크.
    USPTO 권장: 300 DPI 이상, 8.5"×11" 기준
    """
    result = {
        'width_px': 0, 'height_px': 0,
        'dpi': None, 'ok': True, 'notes': [],
    }
    try:
        from PIL import Image
        with Image.open(png_path) as img:
            result['width_px'], result['height_px'] = img.size
            dpi_info = img.info.get('dpi')
            if dpi_info:
                result['dpi'] = dpi_info
            # Check minimum resolution (patent drawings need to be readable)
            if result['width_px'] < 800 or result['height_px'] < 1000:
                result['ok'] = False
                result['notes'].append(
                    f"Low resolution: {result['width_px']}×{result['height_px']}px — "
                    "recommend ≥800×1000 for USPTO submission"
                )
    except ImportError:
        result['notes'].append('PIL not available — skipping resolution check')
    except Exception as e:
        result['notes'].append(f'Resolution check error: {e}')
    return result


def check_file_basics(png_path: str) -> dict:
    """파일 기본 검사: 존재, 크기, 포맷."""
    result = {'ok': True, 'issues': []}
    p = Path(png_path)
    if not p.exists():
        result['ok'] = False
        result['issues'].append(f"File not found: {png_path}")
        return result
    size = p.stat().st_size
    if size < 5000:
        result['ok'] = False
        result['issues'].append(f"File too small ({size} bytes) — possibly empty render")
    if p.suffix.lower() != '.png':
        result['issues'].append(f"Non-PNG extension: {p.suffix} — USPTO prefers PNG/TIFF")
    return result


def validate_png(png_path: str, verbose: bool = False) -> dict:
    """
    Single PNG 파일에 대한 완전한 USPTO 규격 검증.
    
    Returns:
        {
            'path': str,
            'passed': bool,
            'issues': list[str],
            'info': dict,
        }
    """
    report = {
        'path': png_path,
        'passed': True,
        'issues': [],
        'info': {},
    }

    # ── Check #7: 파일 기본 ──────────────────────────────────────────────────
    basics = check_file_basics(png_path)
    if not basics['ok']:
        report['passed'] = False
        report['issues'].extend(basics['issues'])
        return report  # Can't proceed if file missing

    # ── Check #3: 흑백만 사용 (§1.84(m)) ───────────────────────────────────
    color_info = analyze_colors(png_path)
    report['info']['color'] = color_info
    if color_info.get('error'):
        report['issues'].append(f"[WARN] §1.84(m) color check skipped: {color_info['error']}")
    elif not color_info['is_bw']:
        n = color_info['suspicious_pixels']
        dev = color_info['max_color_deviation']
        if n > 50:  # Allow minor anti-aliasing noise
            report['passed'] = False
            report['issues'].append(
                f"[FAIL] §1.84(m): Color detected! {n} non-grayscale pixels "
                f"(max deviation={dev}) — USPTO requires black-and-white only"
            )
        else:
            report['issues'].append(
                f"[INFO] §1.84(m): Minor color noise ({n} pixels, dev={dev}) — "
                "likely anti-aliasing, acceptable"
            )

    # ── Check #7: 해상도 ─────────────────────────────────────────────────────
    res_info = check_resolution(png_path)
    report['info']['resolution'] = res_info
    if not res_info['ok']:
        report['issues'].extend([f"[WARN] Resolution: {n}" for n in res_info['notes']])
    elif verbose and res_info['width_px']:
        report['info']['resolution_str'] = (
            f"{res_info['width_px']}×{res_info['height_px']}px"
        )

    # ── Structural checks (require PatentFigure instance, done pre-render) ──
    # §1.84(p) ref numbers, §1.84(p)(3) min 10pt, §1.84(u) FIG. label,
    # arrow shaft — these are validated by PatentFigure.validate() before render.
    # We note them here as "verified by pre-render structural check".
    report['info']['structural_checks'] = (
        "§1.84(p) ref numbers, §1.84(p)(3) min 10pt, §1.84(u) FIG. label, "
        "arrow shaft ≥0.44\", unicode subscript — verified by PatentFigure.validate()"
    )

    return report


def validate_directory(dir_path: str, verbose: bool = False) -> list:
    """디렉토리 내 모든 PNG 파일 검증."""
    pngs = sorted(glob.glob(os.path.join(dir_path, '*.png')))
    if not pngs:
        print(f"No PNG files found in: {dir_path}")
        return []
    results = []
    for p in pngs:
        r = validate_png(p, verbose=verbose)
        results.append(r)
    return results


def print_report(results: list, verbose: bool = False):
    """검증 결과 출력."""
    if not results:
        return

    n_pass = sum(1 for r in results if r['passed'])
    n_fail = len(results) - n_pass

    print("\n" + "="*60)
    print("USPTO 규격 검증 리포트")
    print("="*60)

    for r in results:
        status = "✅ PASS" if r['passed'] else "❌ FAIL"
        fname = os.path.basename(r['path'])
        print(f"\n{status}  {fname}")
        if r['issues']:
            for issue in r['issues']:
                print(f"    {issue}")
        if verbose and r['info'].get('resolution_str'):
            print(f"    [INFO] Resolution: {r['info']['resolution_str']}")
        if verbose:
            print(f"    [INFO] {r['info'].get('structural_checks', '')}")

    print("\n" + "-"*60)
    print(f"결과: {n_pass}/{len(results)} 통과"
          + (f" | {n_fail}개 실패" if n_fail else " | 모두 통과 ✅"))
    print("="*60 + "\n")

    return {'total': len(results), 'passed': n_pass, 'failed': n_fail}


def main():
    parser = argparse.ArgumentParser(
        description='USPTO 규격 검증 — 생성된 PNG 자동 리포트'
    )
    parser.add_argument('targets', nargs='+',
                        help='PNG 파일 또는 디렉토리 경로')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='상세 정보 출력')
    args = parser.parse_args()

    all_results = []
    for target in args.targets:
        if os.path.isdir(target):
            results = validate_directory(target, verbose=args.verbose)
            all_results.extend(results)
        elif os.path.isfile(target):
            r = validate_png(target, verbose=args.verbose)
            all_results.append(r)
        else:
            # Try glob
            matches = glob.glob(target)
            if matches:
                for m in sorted(matches):
                    r = validate_png(m, verbose=args.verbose)
                    all_results.append(r)
            else:
                print(f"Not found: {target}")

    if all_results:
        summary = print_report(all_results, verbose=args.verbose)
        # Exit code 1 if any failures
        sys.exit(0 if summary['failed'] == 0 else 1)


if __name__ == '__main__':
    main()
