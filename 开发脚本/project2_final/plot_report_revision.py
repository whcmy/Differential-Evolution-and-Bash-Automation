"""Evidence-led report figures. Author: 殷明骏, 202483890029."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ.setdefault('MPLCONFIGDIR','/tmp/project2-revision-mpl')
from pathlib import Path
import csv
import json
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import to_rgba
from matplotlib.ticker import FuncFormatter, MaxNLocator, ScalarFormatter
import numpy as np
from analyze_project2 import load, FINAL, DISPLAY, csv_write
from plot_project2 import COLORS, LINES

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'
FIG=OUT/'figures'
sys.path.insert(0,str(ROOT/'tools'))
from audit_panel_alignment import require_matplotlib_panel_alignment

def read(name):
    with (OUT/name).open(encoding='utf-8-sig') as f: return list(csv.DictReader(f))

def export(fig,name):
    stem=FIG/name
    fig.canvas.draw()
    require_matplotlib_panel_alignment(fig,json_out=str(stem)+'.alignment.json',tolerance_pt=1.5,strict=True)
    meta={'Author':'殷明骏','Creator':None,'Producer':None,'Subject':None,'Keywords':None,'CreationDate':None}
    fig.savefig(str(stem)+'.pdf',metadata=meta)
    fig.savefig(str(stem)+'.svg',metadata={'Creator':'殷明骏'})
    fig.savefig(str(stem)+'.png',dpi=400,metadata={'Author':'殷明骏','Software':None})
    plt.close(fig)

def panel(ax,letter,title):
    ax.set_title(title,loc='left',fontsize=10,pad=11)
    ax.text(-.02,1.07,letter,transform=ax.transAxes,fontsize=11,fontweight='bold',ha='right',va='bottom')

def result_overview():
    rows=sorted(read('final_ranks.csv'),key=lambda r:float(r['mean_rank']))
    fig,axs=plt.subplots(1,2,figsize=(5.72,3.4),gridspec_kw={'width_ratios':[1,1]})
    fig.subplots_adjust(left=.22,right=.98,bottom=.19,top=.79,wspace=1.05)
    ax=axs[0]
    y=np.arange(5)
    ax.hlines(y,1,[float(r['mean_rank']) for r in rows],color='#E1E7EA',lw=3)
    ax.scatter([float(r['mean_rank']) for r in rows],y,s=45,c=[COLORS[r['algorithm']] for r in rows],zorder=3)
    for i,r in enumerate(rows): ax.text(float(r['mean_rank'])+.27,i,f"{float(r['mean_rank']):.3f}",va='center',fontsize=8.5)
    ax.set_yticks(y,[DISPLAY[r['algorithm']].replace(' (fixed NP)','\n(fixed NP)') for r in rows])
    ax.invert_yaxis(); ax.set_xlim(1,5.5); ax.set_xticks([1,2,3,4,5]); ax.set_xlabel('Mean rank (lower is better)')
    ax.spines['left'].set_visible(False); ax.tick_params(axis='y',length=0)
    panel(ax,'a','Overall ordering')
    counts=read('final_comparison_counts.csv'); ax=axs[1]
    wins=np.array([int(r['reference_wins']) for r in counts]); nd=np.array([int(r['no_difference_detected']) for r in counts]); losses=np.array([int(r['reference_losses']) for r in counts])
    for values,left,c in [(wins,np.zeros(4),'#0057D9'),(nd,wins,'#BCC7D4'),(losses,wins+nd,'#EF6C00')]:
        ax.barh(np.arange(4),values,left=left,color=c,height=.58)
        for j,(v,l) in enumerate(zip(values,left)):
            if v: ax.text(l+v/2,j,str(v),ha='center',va='center',fontsize=8,color='white' if c!='#BCC7D4' else '#17212E')
    ax.set_yticks(range(4),[DISPLAY[r['comparison']].replace(' (fixed NP)','\n(fixed NP)') for r in counts])
    ax.invert_yaxis(); ax.set_xlim(0,30); ax.set_xticks([0,10,20,30]); ax.set_xlabel('Number of functions')
    ax.spines['left'].set_visible(False); ax.tick_params(axis='y',length=0)
    panel(ax,'b','Paired outcomes')
    fig.legend([Line2D([0],[0],color=c,lw=6) for c in ['#0057D9','#BCC7D4','#EF6C00']],['PGE-DE win','ND','PGE-DE loss'],loc='upper center',bbox_to_anchor=(.56,.97),ncol=3,frameon=False,fontsize=8.5)
    export(fig,'01_performance')

def evaluator():
    rows=read('diagnostics/dls_evaluator_comparison.csv'); tau=1e-8
    fig,ax=plt.subplots(figsize=(5.72,2.8)); fig.subplots_adjust(left=.14,right=.98,bottom=.25,top=.81)
    f=np.array([int(r['function']) for r in rows])
    ax.axvspan(16.5,22.5,color='#EDF3F6',zorder=0)
    ax.axvspan(22.5,30.5,color='#F6F1E9',zorder=0)
    for key,offset,c,label,marker in [('opfunu_mean',-.13,'#EF6C00','opfunu 1.0.4','o'),('cpp_mean',.13,'#0057D9','C++ reference','D')]:
        values=np.log10((np.array([float(r[key]) for r in rows])+tau)/(np.array([float(r['paper_mean']) for r in rows])+tau))
        ax.scatter(f+offset,values,color=c,s=22,marker=marker,label=label,zorder=3)
    ax.axhline(0,c='#84929A',lw=.7,zorder=1)
    ax.set_xlim(.3,30.7); ax.set_xticks(range(1,31)); ax.tick_params(axis='x',labelsize=7)
    ax.set_xlabel('CEC2014 function'); ax.set_ylabel('Log10 mean error ratio\nto published mean')
    ax.grid(axis='y',color='#E4E9EB',lw=.6)
    ax.legend(loc='upper center',bbox_to_anchor=(.5,1.34),ncol=2,frameon=False)
    export(fig,'02_evaluator')

def transfer():
    source=[]; team=[]
    for stem,key,teamkey in [('pems','PEMS_no_peg','TEAM_no_peg'),('dls','no_two_phase','TEAM_no_phase'),('dsp','without_escape','TEAM_no_escape')]:
        source.append(next(r for r in read(stem+'_ablation_comparison_counts.csv') if r['comparison']==key))
        team.append(next(r for r in read('team_ablation_comparison_counts.csv') if r['comparison']==teamkey))
    fig,axs=plt.subplots(1,2,figsize=(5.72,2.8));fig.subplots_adjust(left=.22,right=.98,bottom=.21,top=.70,wspace=.85)
    for ax,rows,letter,title in zip(axs,[source,team],['a','b'],['Source backbone','PGE-DE backbone']):
        starts=np.zeros(3)
        for key,c in [('reference_wins','#0057D9'),('no_difference_detected','#BCC7D4'),('reference_losses','#EF6C00')]:
            values=np.array([int(r[key]) for r in rows]);ax.barh(range(3),values,left=starts,height=.55,color=c)
            for j,(v,l) in enumerate(zip(values,starts)):
                if v: ax.text(l+v/2,j,str(v),ha='center',va='center',fontsize=8,color='#17212E' if c=='#BCC7D4' else 'white')
            starts+=values
        first_label='Potential–elite\nmodule' if title=='Source backbone' else 'Weighted\nguide'
        ax.set_yticks(range(3),[first_label,'Two-phase\nsampling','Probabilistic\nescape'])
        ax.invert_yaxis();ax.set_xlim(0,30);ax.set_xticks([0,10,20,30]);ax.set_xlabel('Number of functions')
        ax.tick_params(axis='y',length=0);ax.spines['left'].set_visible(False);panel(ax,letter,title)
    fig.legend([Line2D([0],[0],color=c,lw=6) for c in ['#0057D9','#BCC7D4','#EF6C00']],['Full method win','ND','Full method loss'],loc='upper center',bbox_to_anchor=(.56,.98),ncol=3,frameon=False,fontsize=8.5)
    export(fig,'03_transfer')

def distributions(rows):
    algorithms=FINAL+['TEAM_no_peg'];colors=dict(COLORS,TEAM_no_peg='#C53918')
    fig,axs=plt.subplots(1,2,figsize=(5.72,3.7),sharey=True);fig.subplots_adjust(left=.23,right=.97,bottom=.20,top=.86,wspace=.25)
    source=[]
    for ax,fid,letter in zip(axs,[11,29],['a','b']):
        for j,a in enumerate(algorithms):
            group=sorted([r for r in rows if r['function']==fid and r['algorithm']==a],key=lambda r:r['run'])
            xs=np.array([r['error'] for r in group]); assert len(xs)==20 and min(xs)>0
            bp=ax.boxplot([xs],positions=[j],orientation='horizontal',widths=.53,patch_artist=True,showfliers=False,
                          boxprops={'facecolor':to_rgba(colors[a],.28),'edgecolor':colors[a],'linewidth':1.1},medianprops={'color':colors[a],'lw':1.8},
                          whiskerprops={'color':colors[a]},capprops={'color':colors[a]})
            jitter=(np.arange(20)%5-2)*.055
            ax.scatter(xs,j+jitter,s=13,c=colors[a],alpha=1,zorder=3,edgecolors='none')
            source.extend(dict(function=fid,algorithm=a,run=r['run'],error=r['error']) for r in group)
        ax.set_xscale('log');ax.grid(axis='x',color='#E4E9EB',lw=.5);ax.set_xlabel('Final error (log scale)');ax.minorticks_off()
        if fid==29:ax.set_xticks([5e6,7e6,1e7],['5e6','7e6','1e7'])
        ax.set_yticks(range(6),['DE','DSPDE','DLS-DE\n(fixed NP)','PEMS-DE','PGE-DE','PGE-DE\nwithout guidance'])
        ax.tick_params(axis='y',length=0);ax.spines['left'].set_visible(False)
        panel(ax,letter,f'F{fid:02d}')
    axs[0].invert_yaxis();export(fig,'04_distributions');csv_write(FIG/'04_distributions.csv',source)

def telemetry():
    with (OUT/'diagnostics/team_telemetry.csv').open(encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
    fig,axs=plt.subplots(2,2,figsize=(5.72,4.6));fig.subplots_adjust(left=.14,right=.95,bottom=.13,top=.82,wspace=.39,hspace=.65)
    checkpoints=np.arange(10000,100001,10000);summary=[]
    for col,fid in enumerate([11,29]):
        for row,key,title in [(0,'normalized_rms_diversity','Normalized diversity'),(1,'boundary_fraction','Coordinates on bounds (%)')]:
            ax=axs[row,col]
            for a,c,ls,label in [('TEAM',COLORS['TEAM'],'-','PGE-DE'),('TEAM_no_peg','#C53918','--','Without guidance')]:
                values=np.array([[float(r[key]) for r in rows if int(r['function'])==fid and r['algorithm']==a and int(r['fes'])==n] for n in checkpoints])
                assert values.shape==(10,20)
                if row==1:values*=100
                q=np.quantile(values,[.25,.5,.75],axis=1)
                ax.fill_between(checkpoints,q[0],q[2],color=c,alpha=.24,lw=0)
                ax.plot(checkpoints,q[1],color=c,ls=ls,lw=2.0,label=label)
                summary.append(dict(function=fid,algorithm=a,metric=key,median_final=float(q[1,-1]),q25_final=float(q[0,-1]),q75_final=float(q[2,-1])))
            ax.set_xlim(10000,100000);ax.set_xticks([20000,60000,100000],['20k','60k','100k']);ax.grid(axis='y',color='#E4E9EB',lw=.5)
            if row==1:ax.set_xlabel('Function evaluations')
            if col==0:ax.set_ylabel(title,fontsize=8)
            if row==0 and col==1:ax.yaxis.set_major_formatter(FuncFormatter(lambda x,pos:f'{x*1e4:.2f}'))
            title=(f'F{fid:02d}' if col==0 else 'F29 (×10⁻⁴)') if row==0 else 'Boundary occupancy'
            panel(ax,'abcd'[row*2+col],title)
    fig.legend(*axs[0,0].get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.56,.99),ncol=2,frameon=False)
    export(fig,'05_telemetry');csv_write(OUT/'diagnostics/team_telemetry_summary.csv',summary)

def curve_pairs(rows):
    selected=[]
    for first in range(1,31,2):
        fig,axs=plt.subplots(2,1,figsize=(5.72,8.0));fig.subplots_adjust(left=.15,right=.95,bottom=.08,top=.88,hspace=.45)
        for ax,fid,letter in zip(axs,[first,first+1],['a','b']):
            observed=[]
            for a in FINAL:
                group=[r for r in rows if r['function']==fid and r['algorithm']==a]
                best=min(group,key=lambda r:(r['fun'],r['run']));h=np.asarray(best['history'])
                assert len(group)==20 and np.all(h[:,1]>0) and np.all(np.diff(h[:,0])>0)
                ax.step(h[:,0],h[:,1],where='post',color=COLORS[a],linestyle=LINES[a],lw=2.1 if a=='TEAM' else 1.5,label=DISPLAY[a]);observed.extend(h[:,1])
                selected.append(dict(function=fid,algorithm=a,run=best['run'],seed=best['seed']))
            ax.set_yscale('log');ax.set_xlim(0,100000);ax.set_xticks([0,20000,40000,60000,80000,100000],['0','20k','40k','60k','80k','100k'])
            if np.log10(max(observed)/min(observed))<1:
                low,high=ax.get_ylim();ticks=[v for v in MaxNLocator(nbins=5,min_n_ticks=4).tick_values(low,high) if low<=v<=high and v>0]
                ax.set_yticks(ticks);ax.yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
            ax.minorticks_off();ax.set_xlabel('Function evaluations');ax.set_ylabel('Best objective (log scale)');ax.grid(axis='y',color='#E4E9EB',lw=.5)
            panel(ax,letter,f'CEC2014 F{fid:02d}')
        fig.legend(*axs[0].get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.56,.99),ncol=3,frameon=False,fontsize=8.5,columnspacing=1.25)
        export(fig,f'curves_{first:02d}_{first+1:02d}')
    csv_write(FIG/'curve_pair_selection.csv',selected)

def main(only=None):
    FIG.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['DejaVu Sans'],'font.size':8.5,'axes.labelsize':8.5,
                         'xtick.labelsize':8,'ytick.labelsize':8.5,'axes.spines.right':False,'axes.spines.top':False,
                         'axes.linewidth':.65,'xtick.major.width':.6,'ytick.major.width':.6,'pdf.fonttype':42,'svg.fonttype':'none'})
    if only=='telemetry':
        telemetry();print('Updated telemetry figure');return
    rows=load(ROOT/'results/coursework')
    result_overview();evaluator();transfer();distributions(rows);telemetry();curve_pairs(rows)
    print('Exported five analytical figures and fifteen full-size convergence pairs')

if __name__=='__main__':main('telemetry' if '--only-telemetry' in sys.argv else None)
