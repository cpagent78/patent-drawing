#!/usr/bin/env python3
"""
patent_draw.py — Command-Line Interface for Patent Drawing (Research 15)

Usage::

    # Single figure from spec file
    python patent_draw.py --spec spec.txt --output fig1.png --preset uspto

    # Specify diagram type
    python patent_draw.py --spec spec.txt --type state --output fig2.png

    # Suite from JSON descriptor
    python patent_draw.py --suite suite.json --output-dir ./figs/

    # Inline spec (quick one-liner)
    python patent_draw.py --inline "S100: Start\nS200: Process\nS100->S200" --output fig.png

suite.json format::

    {
        "title": "My Invention",
        "figures": [
            {"type": "flowchart", "spec": "spec1.txt", "label": "FIG. 1",
             "description": "System Overview", "output": "fig1.png"},
            {"type": "sequence", "spec": "spec2.txt", "label": "FIG. 2",
             "description": "Login Flow", "output": "fig2.png"}
        ],
        "export_pdf": "patent_drawings.pdf",
        "export_index": "index.md"
    }

Supported --type values:
    flowchart   PatentFigure (default)
    state       PatentState
    sequence    PatentSequence
    layered     PatentLayered
    timing      PatentTiming
    dfd         PatentDFD
    er          PatentER
"""

import argparse
import json
import os
import sys
import time

# Add scripts dir to path
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)


def _get_figure_class(diagram_type: str):
    """Return the appropriate figure class for the given diagram type."""
    from patent_figure import (
        PatentFigure, PatentSequence, PatentState,
        PatentLayered, PatentTiming, PatentDFD, PatentER,
        quick_draw,
    )
    type_map = {
        'flowchart': PatentFigure,
        'state':     PatentState,
        'sequence':  PatentSequence,
        'layered':   PatentLayered,
        'timing':    PatentTiming,
        'dfd':       PatentDFD,
        'er':        PatentER,
    }
    dtype = diagram_type.lower().strip()
    if dtype not in type_map:
        raise ValueError(
            f"Unknown diagram type: {dtype!r}. "
            f"Choose from: {', '.join(type_map)}"
        )
    return type_map[dtype]


def cmd_single(args):
    """Handle single-figure generation: --spec or --inline."""
    from patent_figure import quick_draw

    # Read spec
    if args.spec:
        with open(args.spec, 'r', encoding='utf-8') as f:
            spec_text = f.read()
    elif args.inline:
        spec_text = args.inline.replace('\\n', '\n')
    else:
        print("ERROR: Provide --spec <file> or --inline <text>", file=sys.stderr)
        sys.exit(1)

    output = args.output or 'fig1.png'
    preset = args.preset or 'uspto'
    diagram_type = args.type or 'flowchart'
    fig_label = args.label or 'FIG. 1'

    t0 = time.time()
    result = quick_draw(
        spec_text,
        output,
        preset=preset,
        diagram_type=diagram_type,
        fig_label=fig_label,
    )
    elapsed = time.time() - t0

    print(f"✓ Generated: {output}")
    if isinstance(result, dict):
        pages = result.get('pages', [output])
        for p in pages:
            print(f"  Page: {p}")
        if result.get('warnings'):
            print(f"  Warnings: {len(result['warnings'])}")
            for w in result['warnings'][:5]:
                print(f"    · {w}")
    print(f"  Time: {elapsed:.3f}s")


def cmd_suite(args):
    """Handle suite generation from --suite JSON file."""
    from patent_suite import PatentSuite

    with open(args.suite, 'r', encoding='utf-8') as f:
        suite_def = json.load(f)

    title = suite_def.get('title', 'Patent Drawings')
    output_dir = args.output_dir or '.'
    os.makedirs(output_dir, exist_ok=True)

    suite = PatentSuite(title)

    for fig_def in suite_def.get('figures', []):
        diagram_type = fig_def.get('type', 'flowchart')
        fig_label = fig_def.get('label', 'FIG. 1')
        description = fig_def.get('description', '')

        # Load spec
        spec_path = fig_def.get('spec', '')
        spec_text = fig_def.get('spec_inline', '')
        if spec_path:
            spec_file = spec_path if os.path.isabs(spec_path) else os.path.join(
                os.path.dirname(args.suite), spec_path
            )
            if os.path.exists(spec_file):
                with open(spec_file, 'r', encoding='utf-8') as f:
                    spec_text = f.read()
            else:
                print(f"  WARNING: spec file not found: {spec_file}", file=sys.stderr)
                spec_text = ''

        if not spec_text:
            print(f"  WARNING: no spec for {fig_label}, skipping.", file=sys.stderr)
            continue

        from patent_figure import quick_draw

        # For suite, we use quick_draw to create figure object
        # But we need a figure object... use quick_draw to render directly
        output_fname = fig_def.get('output') or PatentSuite._fig_label_to_filename(fig_label)
        output_path = os.path.join(output_dir, output_fname)

        t0 = time.time()
        result = quick_draw(
            spec_text,
            output_path,
            preset=fig_def.get('preset', 'uspto'),
            diagram_type=diagram_type,
            fig_label=fig_label,
        )
        elapsed = time.time() - t0

        # Create a dummy figure with output_path for the suite
        class _DoneEntry:
            def __init__(self, lab, path):
                self.fig_label = lab
                self.output_path = path
            def render(self, p):
                import shutil
                if p != self.output_path:
                    shutil.copy(self.output_path, p)

        dummy = _DoneEntry(fig_label, output_path)
        # Manually add to suite (bypass normal add to avoid re-render)
        from patent_suite import SuiteEntry
        entry = SuiteEntry(
            figure=dummy,
            fig_label=fig_label,
            description=description,
            output_path=output_path,
            ref_range_start=PatentSuite._assign_ref_range(PatentSuite._parse_fig_num(fig_label))[0],
            ref_range_end=PatentSuite._assign_ref_range(PatentSuite._parse_fig_num(fig_label))[1],
        )
        suite._entries.append(entry)

        print(f"✓ {fig_label}: {output_path} ({elapsed:.3f}s)")

    # Export index
    if suite_def.get('export_index'):
        idx_path = os.path.join(output_dir, suite_def['export_index'])
        suite.export_index(idx_path)
        print(f"✓ Index: {idx_path}")

    # Export PDF
    if suite_def.get('export_pdf'):
        pdf_path = os.path.join(output_dir, suite_def['export_pdf'])
        try:
            suite.export_pdf(pdf_path)
            print(f"✓ PDF: {pdf_path}")
        except ImportError as e:
            print(f"  PDF export skipped: {e}", file=sys.stderr)
        except Exception as e:
            print(f"  PDF export failed: {e}", file=sys.stderr)

    print(f"\nSuite '{title}' complete: {len(suite._entries)} figures in {output_dir}/")


def main():
    parser = argparse.ArgumentParser(
        description='Patent Drawing CLI — Generate USPTO-compliant patent figures.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Single-figure mode
    parser.add_argument('--spec', metavar='FILE',
                        help='Spec file path (S100: ... format)')
    parser.add_argument('--inline', metavar='TEXT',
                        help='Inline spec text (use \\\\n for newlines)')
    parser.add_argument('--output', '-o', metavar='FILE',
                        help='Output PNG path (default: fig1.png)')
    parser.add_argument('--type', '-t', metavar='TYPE',
                        default='flowchart',
                        help='Diagram type: flowchart|state|sequence|layered|timing|dfd|er')
    parser.add_argument('--preset', metavar='PRESET',
                        default='uspto',
                        help='Style preset: uspto|draft|presentation (default: uspto)')
    parser.add_argument('--label', metavar='LABEL',
                        help='FIG. label (default: FIG. 1)')

    # Suite mode
    parser.add_argument('--suite', metavar='JSON',
                        help='Suite JSON descriptor file')
    parser.add_argument('--output-dir', metavar='DIR',
                        help='Output directory for suite (default: .)')

    args = parser.parse_args()

    if args.suite:
        cmd_suite(args)
    elif args.spec or args.inline:
        cmd_single(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
