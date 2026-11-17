"""Thirty measured best-run curves, author 殷明骏, 202483890029."""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ.setdefault('MPLCONFIGDIR', '/tmp/adaptive_de-final-mpl')
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator, ScalarFormatter
import numpy as np
from analyze_adaptive_de import ROOT, OUT, FINAL, DISPLAY, load, csv_write
sys.path.insert(0, str(ROOT/'tools'))
from audit_panel_alignment import require_matplotlib_panel_alignment

COLORS = {'DE': '#0072BD', 'DSPDE': '#D95319', 'DLSDE': '#EDB120', 'PEMSDE': '#7E2F8E', 'TEAM': '#A2142F'}
LINES = {'DE': ':', 'DSPDE': '--', 'DLSDE': '-.', 'PEMSDE': (0, (5, 2, 1, 2)), 'TEAM': '-'}


def main():
    summary = json.loads((OUT/'analysis_summary.json').read_text())
    if summary['final_comparison_runs'] != 3000:
        raise RuntimeError('final matrix not complete')
    rows = load(ROOT/'results/common_benchmark')
    output = OUT/'curves'
    output.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family': 'serif', 'font.serif': ['Liberation Serif', 'DejaVu Serif'],
                         'font.size': 10, 'axes.labelsize': 11, 'axes.titlesize': 12,
                         'xtick.labelsize': 10, 'ytick.labelsize': 10, 'legend.fontsize': 10,
                         'axes.spines.right': False, 'axes.spines.top': False,
                         'pdf.fonttype': 42, 'svg.fonttype': 'none', 'savefig.dpi': 300})
    selection = []
    for fid in range(1, 31):
        fig, ax = plt.subplots(figsize=(7.2, 4.3))
        fig.subplots_adjust(left=.15, right=.97, bottom=.19, top=.74)
        source = []
        observed = []
        for algorithm in FINAL:
            group = [r for r in rows if r['function'] == fid and r['algorithm'] == algorithm]
            assert len(group) == 20
            best = min(group, key=lambda r: (r['fun'], r['run']))
            h = np.array(best['history'], float)
            assert np.all(np.diff(h[:, 0]) > 0)
            assert np.all(np.diff(h[:, 1]) <= 1e-8)
            assert np.all(h[:, 1] > 0)
            observed.extend(h[:, 1])
            ax.step(h[:, 0], h[:, 1], where='post', color=COLORS[algorithm], linestyle=LINES[algorithm],
                    linewidth=1.8 if algorithm == 'TEAM' else 1.1, label=DISPLAY[algorithm])
            selection.append(dict(function=fid, algorithm=algorithm, run=best['run'], seed=best['seed'],
                                  final_fitness=best['fun'], error=best['error']))
            source.extend(dict(algorithm=algorithm, run=best['run'], seed=best['seed'],
                               fes=int(x), best_fitness=float(y)) for x, y in h)
        ax.set_yscale('log')
        if np.log10(max(observed)/min(observed)) < 1:
            low, high = ax.get_ylim()
            ticks = [v for v in MaxNLocator(nbins=5, min_n_ticks=4).tick_values(low, high) if low <= v <= high and v > 0]
            ax.set_yticks(ticks)
            ax.yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
        ax.minorticks_off()
        ax.set_xlim(0, 100000)
        ax.set_xticks([0, 20000, 40000, 60000, 80000, 100000])
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: '0' if x == 0 else f'{x/1000:.0f}k'))
        ax.set_xlabel('Function evaluations (initialization included)', labelpad=8)
        ax.set_ylabel('Best-so-far objective value (log scale)', labelpad=8)
        ax.grid(axis='y', color='#E4E7EA', linewidth=.5)
        fig.suptitle(f'CEC2014 / F{fid:02d} / 10D / fixed NP=100 / 100,000 FEs', x=.52, y=.98, fontsize=12)
        handles, labels = ax.get_legend_handles_labels()
        fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(.55, .91),
                   ncol=3, frameon=False, columnspacing=1.5, handlelength=2.7)
        fig.text(.15, .035, 'Best final run of 20 per algorithm; unsmoothed measured checkpoints.', fontsize=9)
        stem = output/f'F{fid:02d}'
        fig.canvas.draw()
        require_matplotlib_panel_alignment(fig, json_out=str(stem)+'.alignment.json', tolerance_pt=1.5, strict=True)
        fig.savefig(str(stem)+'.pdf', metadata={'Author': '殷明骏', 'Creator': None, 'Producer': None, 'Subject': None, 'Keywords': None, 'CreationDate': None})
        fig.savefig(str(stem)+'.svg', metadata={'Creator': '殷明骏'})
        fig.savefig(str(stem)+'.png', dpi=300, metadata={'Author': '殷明骏', 'Software': None})
        csv_write(str(stem)+'.csv', source)
        plt.close(fig)
    csv_write(OUT/'best_curve_runs.csv', selection)
    print('Exported 30 curves with PDF/SVG/PNG/CSV and 150 best-run identifiers')


if __name__ == '__main__':
    main()
