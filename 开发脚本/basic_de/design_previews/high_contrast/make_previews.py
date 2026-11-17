"""Basic DE figure-direction studies. Author: 殷明骏."""
from pathlib import Path
import os
os.environ.setdefault('MPLCONFIGDIR', '/tmp/basic_de-direction-mpl')
import csv
import hashlib
import json
import sys
import numpy as np
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import LogLocator, LogFormatterMathtext, NullLocator

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from audit_panel_alignment import require_matplotlib_panel_alignment

NAVY, TEAL, ORANGE = '#174BEB', '#174BEB', '#FF7200'
GRAY, INK, PALE = '#465F8C', '#111D35', '#8BC6FF'
FLOOR = 1e-12
WIDTH, HEIGHT = 7.2, 8.4
mpl.rcParams.update({
    'font.family': 'sans-serif', 'font.sans-serif': ['DejaVu Sans'],
    'font.size': 8, 'axes.labelsize': 8.5, 'axes.titlesize': 9,
    'xtick.labelsize': 7.5, 'ytick.labelsize': 7.5,
    'text.color': INK, 'axes.labelcolor': INK,
    'xtick.color': INK, 'ytick.color': INK,
    'axes.spines.top': False, 'axes.spines.right': False,
    'axes.edgecolor': '#52627C', 'axes.linewidth': .8,
    'xtick.major.width': .6, 'ytick.major.width': .6,
    'xtick.major.size': 2.5, 'ytick.major.size': 2.5,
    'legend.frameon': False, 'legend.fontsize': 8,
    'svg.fonttype': 'none', 'pdf.fonttype': 42,
    'savefig.facecolor': 'white', 'figure.facecolor': 'white',
})
ROWS = [json.loads(p.read_text()) for p in sorted((ROOT / 'results').glob('F*_run*.json'))]
assert len(ROWS) == 600
GROUPS = {fid: sorted([r for r in ROWS if r['function'] == fid], key=lambda r:r['run'])
          for fid in range(1, 31)}
assert all(len(rs) == 20 for rs in GROUPS.values())
X = np.array(GROUPS[1][0]['history'])[:, 0]
assert np.all(np.diff(X) > 0) and X[-1] == 100000
E = {}
for fid, rs in GROUPS.items():
    assert all(np.array_equal(np.array(r['history'])[:, 0], X) for r in rs)
    E[fid] = np.abs(np.array([np.array(r['history'])[:, 1] for r in rs]) - 100 * fid)
    assert np.all(np.diff(E[fid], axis=1) <= 1e-7)
Q = {f: np.quantile(e, [.25, .5, .75], axis=0) for f,e in E.items()}
FINAL = {f: np.array([r['error'] for r in rs]) for f,rs in GROUPS.items()}
for f in GROUPS:
    assert np.allclose(FINAL[f], E[f][:,-1], atol=1e-10, rtol=1e-12)

def panel(ax, letter, title):
    ax.set_title(f'{letter}   {title}', loc='left', fontweight='bold', pad=11)
    ax.set_axisbelow(True)

def header(fig, tag, title, subtitle):
    fig.add_artist(Line2D([.09,.97],[.982,.982],transform=fig.transFigure,color=NAVY,lw=2.8))
    fig.text(.09,.96,tag, fontsize=8.5, color=TEAL, fontweight='bold')
    fig.text(.09,.922,title, fontsize=16, fontweight='bold')
    fig.text(.09,.894,subtitle, fontsize=8.5, color='#40516E')

def footer(fig, text):
    fig.text(.09,.035,text, fontsize=7.5, color='#40516E', linespacing=1.55)

def logaxis(ax):
    ax.set_yscale('log')
    ax.yaxis.set_major_locator(LogLocator(base=10, numticks=4))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.grid(axis='y', color='#E8EDEF', lw=.55)

def curve(ax, f, small=False):
    lo, mid, hi = np.maximum(Q[f], FLOOR)
    ax.fill_between(X/1000, lo, hi, color=PALE, step='post', linewidth=0)
    ax.step(X/1000, mid, where='post', color=NAVY, lw=2.4 if not small else 1.9)
    ax.plot(100, mid[-1], 'o', ms=5, color=ORANGE, clip_on=False, zorder=4)
    logaxis(ax)
    ax.set_xlim(0, 103)
    ymin, ymax = max(FLOOR, lo.min()), hi.max()
    ax.set_ylim(ymin/2.5, ymax*3)
    ax.set_xticks([0,50,100])
    ax.set_xlabel('Evaluations (k)')
    ax.set_ylabel('Absolute error')

def save(fig, name, **kwargs):
    fig.canvas.draw()
    require_matplotlib_panel_alignment(fig, json_out=OUT/f'{name}.alignment.json',
                                      strict=True, tolerance_pt=1.5, **kwargs)
    fig.savefig(OUT/f'{name}.pdf', metadata={'Author':'殷明骏','Creator':None,
        'Producer':None,'CreationDate':None,'Subject':None,'Keywords':None})
    fig.savefig(OUT/f'{name}.svg', metadata={'Creator':'殷明骏','Date':None})
    fig.savefig(OUT/f'{name}.png', dpi=300, metadata={'Author':'殷明骏','Software':None})
    plt.close(fig)

def direction_a():
    fig=plt.figure(figsize=(WIDTH,HEIGHT))
    header(fig, 'A  /  CURVES FIRST', 'Convergence trajectories',
           'A large representative trajectory with three supporting cases.')
    gs=fig.add_gridspec(2,3,left=.10,right=.97,bottom=.19,top=.815,
                       height_ratios=[1.55,1],hspace=.58,wspace=.58)
    ax=fig.add_subplot(gs[0,:]);curve(ax,11)
    panel(ax,'a','F11 | Improvement continues into the late budget')
    ax.set_ylim(850,3500)
    ax.set_yticks([1000,2000,3000],['1,000','2,000','3,000'])
    for j,(f,title) in enumerate([(4,'Split'),(22,'Late gain'),(26,'Plateau')]):
        ax=fig.add_subplot(gs[1,j]);curve(ax,f,True)
        panel(ax,chr(98+j),f'F{f:02d} | {title}')
        if j: ax.set_ylabel('')
    fig.legend(handles=[Line2D([],[],color=NAVY,lw=2.4,label='Median'),
                        Patch(facecolor=PALE,label='Interquartile range')],
               loc='lower left',bbox_to_anchor=(.085,.092),ncol=2,columnspacing=2)
    footer(fig,'20 independent runs per function. Four illustrative functions; full atlas supplied separately.\n'
               'Unsmoothed logged histories; absolute errors ≤10⁻¹² share the display floor. Panel scales differ.')
    save(fig,'A_curves')

def direction_b():
    fig=plt.figure(figsize=(WIDTH,HEIGHT))
    header(fig, 'B  /  OVERVIEW TO EXAMPLES', 'Convergence across the benchmark',
           'Thirty functions in one map; two larger curves explain contrasting behaviour.')
    gs=fig.add_gridspec(2,2,left=.10,right=.97,bottom=.18,top=.815,
                       height_ratios=[2.25,1],hspace=.51,wspace=.35)
    ax=fig.add_subplot(gs[0,:])
    # Per-column values are recorded budgets, not interpolated observations.
    Z=np.log10(np.maximum(np.array([Q[f][1] for f in range(1,31)]),FLOOR))
    # Uniform display columns identify the logged observations. Exact FE labels are retained.
    cmap=plt.get_cmap('magma')
    mesh=ax.imshow(Z, aspect='auto', origin='upper', cmap=cmap, vmin=-12,vmax=8,
                   extent=[-.5,len(X)-.5,30.5,.5],interpolation='nearest')
    ax.set_yticks(np.arange(1,31),[f'F{f:02d}' for f in range(1,31)],fontsize=6.8)
    idx=[0,25,50,75,100]
    ax.set_xticks(idx,[f'{X[i]/1000:g}' for i in idx])
    ax.set_xlabel('Recorded evaluations (×1,000)')
    ax.tick_params(axis='y',length=0)
    ax.spines['left'].set_visible(False);ax.spines['bottom'].set_visible(False)
    panel(ax,'a','Median absolute error across all 30 functions')
    # Colorbar is an explanatory key, not a comparable quantitative panel.
    cax=fig.add_axes([.55,.853,.42,.011])
    cb=fig.colorbar(mesh,cax=cax,orientation='horizontal',ticks=[-12,-8,-4,0,4,8])
    cb.ax.set_xticklabels(['≤10⁻¹²','10⁻⁸','10⁻⁴','1','10⁴','10⁸'])
    cb.ax.xaxis.set_ticks_position('top')
    cb.ax.tick_params(labelsize=6.8,length=0,pad=3);cb.outline.set_visible(False)
    fig.text(.10,.856,'Residual error  /  brighter is higher',fontsize=7.5,color='#40516E')
    for j,(f,title) in enumerate([(11,'Continued improvement'),(26,'Residual plateau')]):
        ax=fig.add_subplot(gs[1,j]);curve(ax,f)
        panel(ax,chr(98+j),f'F{f:02d} | {title}')
        if j: ax.set_ylabel('')
    footer(fig,'Each heatmap row summarizes all 20 runs; a single absolute-error colour scale is shared.\n'
               'Curves show the median and interquartile range. Values ≤10⁻¹² share the display floor.\n'
               'Heatmap cells are recorded observations; no temporal interpolation or curve smoothing.')
    save(fig,'B_heatmap',exclude_axes=[cax])

def direction_c():
    fig=plt.figure(figsize=(WIDTH,HEIGHT))
    header(fig, 'C  /  STAGES AND DISTRIBUTIONS', 'Budget response and final variability',
           'A compact budget comparison replaces most curves; every final run stays visible.')
    gs=fig.add_gridspec(2,4,left=.10,right=.97,bottom=.175,top=.815,
                       height_ratios=[2.5,1],hspace=.38,wspace=.7)
    ax=fig.add_subplot(gs[0,:])
    targets=[10000,50000,100000]
    inds=[np.flatnonzero(X<=v)[-1] for v in targets]
    colors=[GRAY,ORANGE,TEAL]; markers=['o','D','o']
    y=np.arange(30,0,-1)
    for f,yy in zip(range(1,31),y):
        vals=np.maximum(Q[f][1,inds],FLOOR)
        ax.plot([vals[-1],vals[0]],[yy,yy],color='#91A8D0',lw=1.1,zorder=1)
    for k,(ix,col,mark) in enumerate(zip(inds,colors,markers)):
        vals=np.maximum(np.array([Q[f][1,ix] for f in range(1,31)]),FLOOR)
        ax.scatter(vals,y, s=[37,34,26][k],marker=mark,c=col,
                   edgecolor='white',linewidth=.45,zorder=2+k)
    ax.set_xscale('log');ax.xaxis.set_minor_locator(NullLocator())
    ax.set_xlim(1e-13,1e8);ax.set_ylim(.25,30.75)
    ax.set_xticks([1e-12,1e-8,1e-4,1,1e4,1e8])
    ax.set_yticks(y,[f'F{f:02d}' for f in range(1,31)],fontsize=6.8)
    ax.tick_params(axis='y',length=0);ax.spines['left'].set_visible(False)
    ax.grid(axis='x',color='#E8EDEF',lw=.55)
    ax.set_xlabel('Median absolute error at each recorded budget')
    panel(ax,'a','Budget snapshots | all 30 functions')
    handles=[Line2D([],[],color=c,marker=m,ms=5.5,lw=0,label=f'{X[i]/1000:g}k FEs')
             for c,m,i in zip(colors,markers,inds)]
    fig.legend(handles=handles,loc='upper right',bbox_to_anchor=(.98,.87),ncol=3,
               handletextpad=.4,columnspacing=1.5)
    for j,(f,title) in enumerate([(4,'Split outcomes'),(11,'Run spread'),(22,'Upper tail'),(26,'Tight plateau')]):
        ax=fig.add_subplot(gs[1,j]); vals=np.sort(FINAL[f]);rank=np.arange(1,21)
        ax.scatter(rank,vals,s=22,color=TEAL,edgecolor='white',lw=.45,zorder=3)
        med=np.median(vals)
        ax.axhline(med,color=ORANGE,lw=1.2,ls=(0,(4,3)),zorder=2)
        ax.set_xlim(0,21);ax.set_xticks([1,10,20]);ax.set_xlabel('')
        if j==0: ax.set_ylabel('Final absolute error')
        ax.grid(axis='y',color='#E8EDEF',lw=.55)
        ax.yaxis.set_major_locator(mpl.ticker.MaxNLocator(4))
        if f==26:
            ax.ticklabel_format(axis='y',style='plain',useOffset=False)
            ax.yaxis.set_major_formatter(mpl.ticker.FormatStrFormatter('%.2f'))
            ax.tick_params(axis='y',labelsize=6.5)
        else: ax.set_ylim(-.05*max(vals),1.12*max(vals))
        panel(ax,chr(98+j),f'F{f:02d}')
    fig.text(.535,.122,'Final runs ordered by absolute error (1–20)',ha='center',fontsize=8.5)
    footer(fig,'Snapshot medians use 9,100, 49,100 and 100,000 FEs (last logged point within each budget).\n'
               'Lower panels show all 20 final runs; orange dashed lines mark medians. Linear scales differ.\n'
               'No density estimation; values ≤10⁻¹² share the display floor in the logarithmic top panel.')
    save(fig,'C_stage_dots')

def atlas():
    fig,axs=plt.subplots(6,5,figsize=(WIDTH,9.5))
    fig.subplots_adjust(left=.08,right=.98,bottom=.07,top=.91,wspace=.48,hspace=.78)
    fig.text(.08,.957,'A / Complete convergence atlas',fontsize=14,fontweight='bold')
    fig.text(.08,.932,'All 30 functions · median and interquartile range · 20 runs per function',fontsize=8)
    for f,ax in enumerate(axs.flat,1):
        curve(ax,f,True)
        ax.set_title(f'F{f:02d}',loc='left',fontweight='bold',fontsize=8,pad=5)
        ax.set_xlabel('');ax.set_ylabel('');ax.tick_params(labelsize=7.2)
        ax.yaxis.set_major_locator(LogLocator(base=10,numticks=2))
        ax.set_xticks([0,100]);ax.set_xlim(0,103)
    fig.text(.08,.022,'Horizontal: evaluations (×1,000). Vertical: absolute error (log scale; panels differ). Display floor: 10⁻¹².',fontsize=7)
    save(fig,'A_complete_atlas')

def source():
    with (OUT/'source_medians.csv').open('w',newline='') as out:
        w=csv.writer(out);w.writerow(['function','evaluations','q25_error','median_error','q75_error'])
        for f in range(1,31):
            w.writerows([f,int(x),*q] for x,q in zip(X,Q[f].T))
    with (OUT/'source_final_runs.csv').open('w',newline='') as out:
        w=csv.writer(out);w.writerow(['function','run','seed','absolute_error'])
        w.writerows([r['function'],r['run'],r['seed'],r['error']] for r in ROWS)
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'results').glob('F*_run*.json'))}
    (OUT/'data_integrity.json').write_text(json.dumps({'author':'殷明骏','records':600,
        'functions':30,'runs_per_function':20,'raw_sha256':hashes},ensure_ascii=False,indent=2))

def comparison():
    fig,axs=plt.subplots(1,3,figsize=(16.2,6.3))
    fig.subplots_adjust(left=0,right=1,bottom=0,top=1,wspace=0)
    for ax,name in zip(axs,['A_curves','B_heatmap','C_stage_dots']):
        ax.imshow(plt.imread(OUT/f'{name}.png'))
        ax.axis('off')
    require_matplotlib_panel_alignment(fig,json_out=OUT/'comparison.alignment.json',strict=True)
    fig.savefig(OUT/'comparison.png',dpi=300,metadata={'Author':'殷明骏','Software':None})
    plt.close(fig)

if __name__=='__main__':
    source();direction_a();direction_b();direction_c();atlas();comparison()
    print('Rendered three alternatives and the full curve atlas from 600 retained observations.')
