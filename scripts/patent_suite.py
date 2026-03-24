"""
patent_suite.py — Multi-Figure Patent Drawing Suite (Research 15)

PatentSuite manages a set of related patent figures (FIG. 1 through FIG. N),
provides auto reference-number range assignment, cross-figure reference tracking,
batch rendering, PDF export, and a Markdown index.

Usage::

    from patent_suite import PatentSuite
    from patent_figure import PatentFigure, PatentSequence, PatentState, PatentLayered

    suite = PatentSuite('My Invention')
    suite.add(PatentFigure('FIG. 1'), description='System Overview')
    suite.add(PatentSequence('FIG. 2'), description='Login Flow')
    suite.add(PatentState('FIG. 3'), description='Device States')
    suite.add(PatentLayered('FIG. 4'), description='Software Architecture')

    # Batch render
    paths = suite.render_all('output/')      # → ['output/FIG1.png', ...]

    # Export Markdown index
    suite.export_index('output/index.md')

    # Export PDF (all figures in one PDF)
    suite.export_pdf('output/patent_drawings.pdf')

Auto reference-number allocation:
    FIG. 1 → 100-series (100, 102, 104, ...)
    FIG. 2 → 200-series (200, 202, 204, ...)
    FIG. N → N00-series (up to FIG. 9; FIG. 10+ uses 1000-series: 1000, 1010, ...)

Cross-reference detection:
    suite.find_cross_refs() → dict mapping (fig_label, ref_num) → fig_label
"""

import os
import re
import sys
from typing import Optional, Union
from dataclasses import dataclass, field

# Ensure scripts dir on path
_SKILL_DIR = os.path.dirname(__file__)
sys.path.insert(0, _SKILL_DIR)


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class SuiteEntry:
    """One figure in the suite."""
    figure: object              # PatentFigure / PatentSequence / PatentState / etc.
    fig_label: str              # 'FIG. 1', 'FIG. 2', etc.
    description: str = ''       # Short description for index
    output_path: str = ''       # Set after render
    ref_range_start: int = 0    # e.g. 100 for FIG. 1
    ref_range_end: int = 0      # e.g. 199 for FIG. 1


# ── PatentSuite ───────────────────────────────────────────────────────────────

class PatentSuite:
    """
    Container for a complete set of patent drawings.

    Parameters
    ----------
    title : str
        Invention title (used in PDF cover page and index).
    """

    def __init__(self, title: str = 'Patent Drawings'):
        self.title = title
        self._entries: list[SuiteEntry] = []
        # Tracks all reference numbers used across all figures: ref_num → [fig_label]
        self._ref_registry: dict[int, list[str]] = {}

    # ── Figure management ─────────────────────────────────────────────────────

    def add(self, figure, description: str = '') -> 'PatentSuite':
        """
        Add a figure to the suite.

        Parameters
        ----------
        figure : PatentFigure | PatentSequence | PatentState | ...
            The figure object. Must have a `fig_label` attribute and `render()` method.
        description : str
            Short description for the index.

        Returns self for chaining.
        """
        fig_label = getattr(figure, 'fig_label', 'FIG. ?')
        fig_num = self._parse_fig_num(fig_label)

        # Assign ref number range
        ref_start, ref_end = self._assign_ref_range(fig_num)

        entry = SuiteEntry(
            figure=figure,
            fig_label=fig_label,
            description=description,
            ref_range_start=ref_start,
            ref_range_end=ref_end,
        )
        self._entries.append(entry)
        return self

    def __len__(self) -> int:
        return len(self._entries)

    # ── Reference number management ───────────────────────────────────────────

    @staticmethod
    def _parse_fig_num(fig_label: str) -> int:
        """Extract integer from 'FIG. 3' → 3. Returns 0 if not found."""
        m = re.search(r'(\d+)', fig_label)
        return int(m.group(1)) if m else 0

    @staticmethod
    def _assign_ref_range(fig_num: int) -> tuple[int, int]:
        """
        Assign 100-series ref range per figure number.

        FIG. 1 → 100–199
        FIG. 2 → 200–299
        ...
        FIG. 9 → 900–999
        FIG. 10 → 1000–1099
        FIG. 11 → 1100–1199
        """
        if fig_num == 0:
            return (0, 99)
        if fig_num <= 9:
            return (fig_num * 100, fig_num * 100 + 99)
        else:
            return (fig_num * 100, fig_num * 100 + 99)

    def register_ref(self, ref_num: int, fig_label: str):
        """Register a reference number as used in the given figure."""
        self._ref_registry.setdefault(ref_num, [])
        if fig_label not in self._ref_registry[ref_num]:
            self._ref_registry[ref_num].append(fig_label)

    def check_ref_conflicts(self) -> list[dict]:
        """
        Check for reference number conflicts within the suite.

        Returns list of conflicts: [{'ref': 200, 'used_in': ['FIG. 1', 'FIG. 2']}]
        """
        conflicts = []
        for ref_num, figs in self._ref_registry.items():
            if len(figs) > 1:
                conflicts.append({'ref': ref_num, 'used_in': figs})
        return conflicts

    def find_cross_refs(self) -> dict:
        """
        Find reference numbers that appear in the wrong figure's range.

        Returns dict: {(fig_label, ref_num): expected_fig_label}
        For example, if ref 210 appears in FIG. 1, it should be in FIG. 2.
        """
        cross_refs = {}
        for ref_num, figs in self._ref_registry.items():
            expected_fig = self._ref_to_fig(ref_num)
            for fig_label in figs:
                if expected_fig and fig_label != expected_fig:
                    cross_refs[(fig_label, ref_num)] = expected_fig
        return cross_refs

    def _ref_to_fig(self, ref_num: int) -> Optional[str]:
        """Return the expected fig_label for a given ref number (by range)."""
        for entry in self._entries:
            if entry.ref_range_start <= ref_num <= entry.ref_range_end:
                return entry.fig_label
        return None

    # ── Batch rendering ───────────────────────────────────────────────────────

    def render_all(self, output_dir: str = '.') -> list[str]:
        """
        Render all figures to PNG files in output_dir.

        File names are derived from the figure label:
            'FIG. 1' → 'FIG1.png'
            'FIG. 1A' → 'FIG1A.png'

        Returns list of output paths (one per figure, may be more if auto-split).
        """
        os.makedirs(output_dir, exist_ok=True)
        paths = []
        for entry in self._entries:
            fname = self._fig_label_to_filename(entry.fig_label)
            out_path = os.path.join(output_dir, fname)
            entry.figure.render(out_path)
            entry.output_path = out_path
            paths.append(out_path)
        return paths

    @staticmethod
    def _fig_label_to_filename(fig_label: str) -> str:
        """'FIG. 1' → 'FIG1.png', 'FIG. 2A' → 'FIG2A.png'"""
        clean = re.sub(r'[^A-Za-z0-9]', '', fig_label.upper())  # 'FIG1', 'FIG2A'
        return clean + '.png'

    # ── Markdown index export ─────────────────────────────────────────────────

    def export_index(self, output_path: str) -> str:
        """
        Export a Markdown index of all figures.

        Format::

            # Patent Drawing Suite: My Invention

            | # | Figure | Description | File | Ref Range |
            |---|--------|-------------|------|-----------|
            | 1 | FIG. 1 | System Overview | FIG1.png | 100–199 |
            ...

        Returns output_path.
        """
        lines = [
            f'# Patent Drawing Suite: {self.title}\n',
            '',
            '| # | Figure | Description | File | Ref Range |',
            '|---|--------|-------------|------|-----------|',
        ]
        for i, entry in enumerate(self._entries, start=1):
            fname = os.path.basename(entry.output_path) if entry.output_path else 'N/A'
            ref_range = f'{entry.ref_range_start}–{entry.ref_range_end}'
            lines.append(
                f'| {i} | {entry.fig_label} | {entry.description} | {fname} | {ref_range} |'
            )

        lines.extend([
            '',
            '## Reference Number Ranges',
            '',
        ])
        for entry in self._entries:
            lines.append(
                f'- **{entry.fig_label}** ({entry.description}): '
                f'refs {entry.ref_range_start}–{entry.ref_range_end}'
            )

        # Cross-reference conflicts
        conflicts = self.check_ref_conflicts()
        if conflicts:
            lines.extend(['', '## ⚠ Reference Number Conflicts', ''])
            for c in conflicts:
                lines.append(f'- Ref **{c["ref"]}** used in: {", ".join(c["used_in"])}')

        content = '\n'.join(lines) + '\n'
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return output_path

    # ── PDF export ────────────────────────────────────────────────────────────

    def export_pdf(self, output_path: str) -> str:
        """
        Export all rendered figures as a single PDF file.

        Requires PIL (Pillow) installed. Each figure becomes one page.
        Pages are ordered by figure order in the suite.

        Returns output_path.

        Raises:
            RuntimeError: If no figures have been rendered yet.
            ImportError: If PIL is not installed.
        """
        rendered = [e for e in self._entries if e.output_path and os.path.exists(e.output_path)]
        if not rendered:
            raise RuntimeError("No figures have been rendered. Call render_all() first.")

        try:
            from PIL import Image
        except ImportError:
            raise ImportError(
                "Pillow is required for PDF export. Install with: pip install Pillow"
            )

        pages = []
        for entry in rendered:
            img = Image.open(entry.output_path).convert('RGB')
            pages.append(img)

        if not pages:
            raise RuntimeError("No valid images to export.")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        pages[0].save(
            output_path,
            save_all=True,
            append_images=pages[1:],
            resolution=150,
            title=self.title,
        )
        return output_path

    # ── Repr ──────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f'PatentSuite(title={self.title!r}, '
            f'figures={[e.fig_label for e in self._entries]})'
        )
