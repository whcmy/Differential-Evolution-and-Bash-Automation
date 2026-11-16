"""Scientific comparison figures from retained runs. Author: 殷明骏."""
import os
os.environ['MPLCONFIGDIR']='/tmp/report1-figure-config'
from pathlib import Path
import csv,json,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
from plot_report import style,panel,BLUE,ORANGE,GRAY,require_matplotlib_panel_alignment
FIG=ROOT.parent/'output/figures'
def export(fig,name,**options):
    stem=FIG/name
    fig.canvas.draw()
    require_matplotlib_panel_alignment(fig,json_out=str(stem)+'.alignment.json',tolerance_pt=1.5,strict=True,**options)
    fig.savefig(str(stem)+'.pdf',metadata={'Author':'殷明骏','Creator':None,'Producer':None,'Subject':None,'Keywords':None,'CreationDate':None})
    fig.savefig(str(stem)+'.svg',metadata={'Creator':'殷明骏','Date':None})
    fig.savefig(str(stem)+'.png',dpi=400,metadata={'Author':'殷明骏','Software':None})
    plt.close(fig)

def rows(n):
    with (ROOT/n).open() as f:return list(csv.DictReader(f))
def load(n):return [json.loads(p.read_text()) for p in sorted((ROOT/n).glob('F*.json'))]
def main():
    plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['DejaVu Sans'],'font.size':8,'axes.labelsize':8,'xtick.labelsize':7,'ytick.labelsize':7,'svg.fonttype':'none','pdf.fonttype':42,'axes.linewidth':.6,'legend.frameon':False})
    pairs=rows('paired_results.csv');probes=rows('pointwise_validation.csv')
    fig,axs=plt.subplots(2,1,figsize=(6.9,4.1),gridspec_kw={'height_ratios':[1.5,1]})
    fig.subplots_adjust(left=.10,right=.975,bottom=.115,top=.90,hspace=.9)
    ax=axs[0]
    for f in range(1,31):
        data=[r for r in pairs if int(r['function'])==f]
        y=np.array([np.log10((float(r['official_error'])+1e-8)/(float(r['opfunu_error'])+1e-8)) for r in data])
        ax.scatter(f+np.linspace(-.18,.18,20),y,s=7,alpha=.38,color=GRAY,edgecolor='none')
        q=np.quantile(y,[.25,.5,.75]);ax.vlines(f,q[0],q[2],color=BLUE,lw=2);ax.scatter(f,q[1],s=12,color=BLUE,zorder=5)
    ax.axhline(0,color='black',lw=.6,ls='--');ax.set(xlim=(.3,30.7),xticks=range(1,31),ylabel='Paired log ratio',xlabel='CEC2014 function')
    panel(ax,'a','Changing only the evaluator changes final error');style(ax)
    ax=axs[1];x=np.arange(1,31)
    ax.bar(x,[int(r['mismatches']) for r in probes],color=ORANGE,width=.6)
    ax.set(xlim=(.3,30.7),ylim=(0,220),xticks=x,yticks=[0,100,204],ylabel='Mismatched points',xlabel='CEC2014 function');panel(ax,'b','204 fixed input probes for every function');style(ax)
    export(fig,'05_evaluator')
    comp=rows('paper_comparison.csv');x=np.arange(len(comp));ids=[int(r['function']) for r in comp]
    fig,axs=plt.subplots(2,1,figsize=(6.9,4.05))
    fig.subplots_adjust(left=.10,right=.975,bottom=.115,top=.85,hspace=.95)
    ax=axs[0];a=np.array([float(r['mean']) for r in comp]);b=np.array([float(r['paper_mean']) for r in comp])
    ax.plot(x,np.log10(a+1e-8),'-o',ms=3,color=BLUE,lw=1,label='Python control (20 runs)')
    ax.plot(x,np.log10(b+1e-8),'--s',ms=3,mfc='white',color=ORANGE,lw=.9,label='Published basic DE (30 runs)')
    ax.set(xticks=x,xticklabels=ids,xlim=(-.6,len(x)-.4),ylabel='log10(mean error + 1e-8)',xlabel='Non-rotated study function');fig.legend(*ax.get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.54,1.0),ncol=2,fontsize=7)
    panel(ax,'a','The comparison now uses the same basic-DE protocol');style(ax)
    ax=axs[1];scale=np.array([float(r['absolute_gap'])/float(r['descriptive_tolerance']) for r in comp])
    ax.scatter(x,scale,s=20,color=[ORANGE if y>1 else BLUE for y in scale],zorder=4)
    ax.axhline(1,color='black',lw=.7,ls='--');ax.set(xticks=x,xticklabels=ids,xlim=(-.6,len(x)-.4),ylabel='Mean gap / descriptive band',xlabel='Non-rotated study function',ylim=(-.06,2.15))
    j=ids.index(21)
    panel(ax,'b','27 of 28 means fall inside the rounding-aware band');style(ax)
    export(fig,'06_matched_paper')
    data=load('results_paper')
    for block,fs in enumerate([ids[:14],ids[14:]],1):
        fig,axs=plt.subplots(5,3,figsize=(6.9,7.25))
        fig.subplots_adjust(left=.11,right=.98,bottom=.08,top=.96,wspace=.43,hspace=.83)
        for ax,fid in zip(axs.flat,fs):
            rs=[r for r in data if r['function']==fid];h=np.array([r['history'] for r in rs]);fe=h[0,:,0]/1000
            err=np.abs(h[:,:,1]-100*fid);q=np.quantile(err,[.25,.5,.75],axis=0)
            best=min(rs,key=lambda r:r['error']);bh=np.array(best['history']);be=abs(bh[:,1]-100*fid)
            ax.fill_between(fe,np.maximum(q[0],1e-8),np.maximum(q[2],1e-8),color=BLUE,alpha=.16,lw=0)
            ax.plot(fe,np.maximum(q[1],1e-8),color=BLUE,lw=.8)
            ax.plot(bh[:,0]/1000,np.maximum(be,1e-8),color=ORANGE,lw=.7,ls='--')
            ax.set_yscale('log');ax.set(xlim=(0,50),xticks=[0,25,50]);ax.set_title(f'F{fid:02d}',fontsize=8,pad=4);ax.tick_params(labelsize=6.5);limits=ax.get_ylim();ax.set_yticks(np.geomspace(*limits,11)[[1,5,9]]);ax.yaxis.set_major_formatter(FuncFormatter(lambda y,pos:f'{y:.1e}'));ax.yaxis.set_minor_formatter(NullFormatter());style(ax);ax.grid(False)
        axs.flat[-1].axis('off')
        axs.flat[-1].legend(handles=[Line2D([0],[0],color=BLUE,lw=1,label='Median and IQR'),Line2D([0],[0],color=ORANGE,lw=1,ls='--',label='Best final run')],loc='center',fontsize=7)
        fig.text(.5,.018,'Function evaluations (thousands)',ha='center',fontsize=8)
        fig.text(.008,.53,'Absolute error (log scale; display floor 1e-8)',rotation=90,va='center',fontsize=8)
        export(fig,f'paper_curves_{block}',exclude_axes=[axs.flat[-1]])
    print('Exported evaluator, same-algorithm comparison and 28 convergence panels')
if __name__=='__main__':main()
