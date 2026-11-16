"""Confirmation figures from complete recorded observations. Author: 殷明骏."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ.setdefault('MPLCONFIGDIR','/tmp/report2-revision-mpl')
from pathlib import Path
import csv
import json
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyArrowPatch
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools'))
from analyze_project2 import load, csv_write
from audit_panel_alignment import require_matplotlib_panel_alignment
from analyze_validation import MAIN, ABLATION
OUT=ROOT/'improvement/analysis';FIG=ROOT/'output/figures'
COLORS={'DE':'#0072BD','DSPDE':'#D95319','DLSDE':'#EDB120',
        'PEMSDE':'#7E2F8E','TEAM':'#A2142F','APE':'#77AC30',
        'APE_no_potential':'#0072BD','APE_no_control':'#D95319'}
DISPLAY={'DE':'DE','DSPDE':'DSPDE','DLSDE':'DLS-DE','PEMSDE':'PEMS-DE',
         'TEAM':'PGE-DE','APE':'APE-DE','APE_no_potential':'Without potential guidance',
         'APE_no_control':'Without parameter control'}
MARKERS=dict(zip(MAIN,['o','s','^','D','*','v']))
STYLES=dict(zip(MAIN,['--',':','-.','--',':','-']))
plt.rcParams.update({'font.family':'serif','font.serif':['DejaVu Serif','Liberation Serif'],
                     'font.size':8,'axes.labelsize':8,'xtick.labelsize':7.3,
                     'ytick.labelsize':7.3,'axes.spines.top':False,'axes.spines.right':False,
                     'axes.linewidth':.65,'pdf.fonttype':42,'svg.fonttype':'none','legend.frameon':False})


def read(name):
    with (OUT/name).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))


def export(fig,name,exclude_axes=None):
    stem=FIG/name;fig.canvas.draw()
    require_matplotlib_panel_alignment(fig,json_out=str(stem)+'.alignment.json',
                                       tolerance_pt=1.5,strict=True,exclude_axes=exclude_axes or [])
    fig.savefig(str(stem)+'.pdf',metadata={'Author':'殷明骏','Creator':None,'Producer':None,
                                        'Subject':None,'Keywords':None,'CreationDate':None})
    fig.savefig(str(stem)+'.svg',metadata={'Creator':'殷明骏'})
    fig.savefig(str(stem)+'.png',dpi=400,metadata={'Author':'殷明骏','Software':None})
    plt.close(fig)


def title(ax,letter,text):
    ax.set_title(text,loc='left',fontsize=8.5,pad=12)
    ax.annotate(letter,xy=(0,1),xytext=(-10,12),xycoords='axes fraction',
                textcoords='offset points',fontweight='bold',fontsize=9,ha='right',va='bottom')


def mechanism():
    fig,axs=plt.subplots(1,2,figsize=(6.8504,2.9))
    fig.subplots_adjust(left=.06,right=.97,bottom=.10,top=.78,wspace=.28)
    for ax in axs:
        ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
    targets=np.array([[.12,.25],[.45,.12],[.82,.25]])
    def arrow(ax,a,b,color):
        ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=9,lw=1,color=color))
    ax=axs[0];guide=np.array([.48,.72])
    ax.scatter(targets[:,0],targets[:,1],s=28,facecolors='none',edgecolors=COLORS['DE'])
    ax.scatter(*guide,s=40,color=COLORS['TEAM'])
    for point in targets:arrow(ax,point,guide,COLORS['TEAM'])
    ax.text(.48,.85,'One weighted guide',ha='center',fontsize=8)
    ax.text(.5,.00,'Same attraction point for every target',ha='center',fontsize=7.5)
    title(ax,'a','Predecessor: shared attraction')
    ax=axs[1];guides=np.array([[.18,.72],[.50,.84],[.82,.65]])
    ax.scatter(targets[:,0],targets[:,1],s=28,facecolors='none',edgecolors=COLORS['DE'])
    ax.scatter(guides[:,0],guides[:,1],s=30,color=COLORS['APE'],marker='v')
    for point,guide in zip(targets,guides):arrow(ax,point,guide,COLORS['APE'])
    ax.text(.5,.98,'Actual elite or improving members',ha='center',fontsize=7.5)
    ax.text(.5,.00,'Archive differences retain past alternatives',ha='center',fontsize=7.5)
    title(ax,'b','Revision: independent guides')
    export(fig,'revision_mechanism')


def performance():
    ranking=sorted(read('validation_ranks.csv'),key=lambda r:float(r['mean_rank']))
    tests=read('validation_paired_tests.csv');controls=MAIN[:-1]
    matrix=np.empty((len(controls),30));significant=np.zeros(matrix.shape,bool)
    for r in tests:
        if r['comparison'] not in controls:continue
        i=controls.index(r['comparison']);j=int(r['function'])-1
        matrix[i,j]=-float(r['rank_biserial']);significant[i,j]=float(r['p_holm'])<.05
    fig,axs=plt.subplots(1,2,figsize=(6.8504,3.0))
    fig.subplots_adjust(left=.13,right=.88,bottom=.24,top=.78,wspace=.90)
    ax=axs[0]
    for i,r in enumerate(ranking):
        x=float(r['mean_rank']);ax.plot([1,x],[i,i],color='#CCCCCC',lw=1.4)
        ax.scatter(x,i,s=32,color=COLORS[r['algorithm']],zorder=3)
        ax.text(6.1,i,f'{x:.3f}',ha='right',va='center',fontsize=7.5)
    ax.set_yticks(range(6),[DISPLAY[r['algorithm']] for r in ranking]);ax.invert_yaxis()
    ax.set(xlim=(.8,6.3),xticks=[1,2,3,4,5],xlabel='Mean rank');ax.tick_params(axis='y',length=0)
    title(ax,'a','Confirmed ordering')
    ax=axs[1]
    cmap=LinearSegmentedColormap.from_list('paired_effect',['#A2142F','#FFFFFF','#0072BD'])
    im=ax.imshow(matrix,vmin=-1,vmax=1,cmap=cmap,aspect='auto',interpolation='nearest',extent=(.5,30.5,4.5,-.5))
    ys,xs=np.where(significant);ax.scatter(xs+1,ys,s=7,c='black',linewidths=0)
    ax.set_yticks(range(5),[DISPLAY[a] for a in controls]);ax.set_xticks([1,10,20,30])
    ax.set_xlabel('CEC2014 function');ax.tick_params(length=2)
    for x in [3.5,16.5,22.5]:ax.axvline(x,color='#777777',lw=.5)
    title(ax,'b','APE-DE relative to controls')
    cax=fig.add_axes([.92,.24,.012,.50]);cb=fig.colorbar(im,cax=cax,ticks=[-1,0,1])
    cb.set_label('Paired effect; positive favours APE-DE',fontsize=7)
    export(fig,'revision_performance',[cax])
    csv_write(FIG/'revision_performance.csv',[r for r in tests if r['comparison'] in controls])


def ablations():
    ranks=read('validation_ablation_ranks.csv')
    counts=[r for r in read('validation_comparison_counts.csv') if r['family']=='ablation']
    fig,axs=plt.subplots(1,2,figsize=(6.8504,2.75));fig.subplots_adjust(left=.26,right=.97,bottom=.22,top=.76,wspace=.80)
    ax=axs[0]
    for i,r in enumerate(ranks):
        ax.scatter(float(r['mean_rank']),i,s=35,color=COLORS[r['algorithm']],zorder=3)
    ax.set_yticks(range(3),[DISPLAY[r['algorithm']] for r in ranks]);ax.invert_yaxis()
    ax.set(xlim=(1,3),xticks=[1,2,3],xlabel='Mean rank');title(ax,'a','Revision-family ordering')
    ax=axs[1]
    for i,r in enumerate(counts):
        left=0
        for key,color in [('wins','#0072BD'),('not_detected','#D9D9D9'),('losses','#A2142F')]:
            v=int(r[key]);ax.barh(i,v,left=left,color=color,height=.42)
            if v>=3:ax.text(left+v/2,i,str(v),ha='center',va='center',fontsize=7,color='white' if key!='not_detected' else 'black')
            left+=v
    ax.set_yticks(range(2),['Potential','Control']);ax.invert_yaxis();ax.set(xlim=(0,30),xticks=[0,10,20,30],xlabel='Number of functions')
    title(ax,'b','Full method versus removal')
    fig.legend([Line2D([],[],lw=5,color=c) for c in ['#0072BD','#D9D9D9','#A2142F']],
               ['Full wins','Not detected','Full loses'],ncol=3,loc='upper center',bbox_to_anchor=(.61,.99),fontsize=7.4)
    export(fig,'revision_ablation');csv_write(FIG/'revision_ablation.csv',counts)


def distributions(rows):
    algorithms=['DE','TEAM','APE'];data=[]
    fig,axs=plt.subplots(1,2,figsize=(6.8504,3.0));fig.subplots_adjust(left=.11,right=.98,bottom=.20,top=.81,wspace=.42)
    for ax,fid,letter in zip(axs,[11,29],'ab'):
        values=[]
        for algorithm in algorithms:
            group=sorted([r for r in rows if r['algorithm']==algorithm and r['function']==fid],key=lambda r:r['run'])
            assert len(group)==20
            values.append(np.array([r['error'] for r in group]))
            data.extend(dict(function=fid,algorithm=algorithm,run=r['run'],seed=r['seed'],error=r['error']) for r in group)
        for run in range(20):
            ax.plot(range(3),np.maximum(np.array(values)[:,run],1e-8),color='#BBBBBB',lw=.5,alpha=.7,zorder=1)
        for i,algorithm in enumerate(algorithms):
            ax.scatter(np.full(20,i),np.maximum(values[i],1e-8),s=15,facecolors='none',edgecolors=COLORS[algorithm],lw=.7,zorder=3)
        ax.set_yscale('log');ax.set_xticks(range(3),[DISPLAY[a] for a in algorithms]);ax.set_ylabel('Final absolute error')
        ax.set_xlim(-.3,2.3);title(ax,letter,f'F{fid:02d}: all paired seeds')
    export(fig,'revision_distributions');csv_write(FIG/'revision_distributions.csv',data)


def grids(rows):
    selection=[];points=[]
    for first in range(1,31,6):
        fig,axs=plt.subplots(2,3,figsize=(6.8504,4.25))
        fig.subplots_adjust(left=.085,right=.97,bottom=.14,top=.83,hspace=.66,wspace=.43)
        for ax,fid in zip(axs.flat,range(first,first+6)):
            for algorithm in MAIN:
                group=[r for r in rows if r['function']==fid and r['algorithm']==algorithm]
                assert len(group)==20
                best=min(group,key=lambda r:(r['fun'],r['run']))
                h=np.asarray(best['history'],float)
                assert np.all(h[:,1]>0) and np.all(np.diff(h[:,0])>0)
                ax.step(h[:,0],h[:,1],where='post',color=COLORS[algorithm],ls=STYLES[algorithm],
                        lw=1.1 if algorithm=='APE' else .7,marker=MARKERS[algorithm],
                        markevery=15,ms=2.4 if algorithm=='APE' else 1.8,mfc='none',mew=.5,
                        zorder=5 if algorithm=='APE' else 2)
                selection.append(dict(function=fid,algorithm=algorithm,run=best['run'],seed=best['seed'],final_objective=best['fun']))
                points.extend(dict(function=fid,algorithm=algorithm,run=best['run'],seed=best['seed'],fes=int(fes),objective=float(value)) for fes,value in h)
            ax.set_yscale('log');ax.set_xlim(0,100000);ax.set_xticks([0,50000,100000],['0','50k','100k'])
            ax.set_title(f'F{fid:02d}',fontsize=8.5,pad=8);ax.grid(axis='y',alpha=.17,lw=.5)
            ax.minorticks_off()
        for ax in axs[:,0]:ax.set_ylabel('Best-so-far objective')
        for ax in axs[-1,:]:ax.set_xlabel('Function evaluations')
        handles=[Line2D([],[],color=COLORS[a],ls=STYLES[a],marker=MARKERS[a],mfc='none',lw=1,ms=3,label=DISPLAY[a]) for a in MAIN]
        fig.legend(handles=handles,ncol=3,loc='upper center',bbox_to_anchor=(.53,.995),fontsize=7.6,columnspacing=1.5,handlelength=2.2)
        export(fig,f'revision_curves_{first:02d}_{first+5:02d}')
    assert len(selection)==180
    csv_write(FIG/'revision_curve_selection.csv',selection)
    csv_write(FIG/'revision_curve_data.csv',points)


def main():
    summary=json.loads((OUT/'validation_summary.json').read_text());assert summary['formal_records']==4800
    rows=load(ROOT/'improvement/results/validation')
    assert len(rows)==4800
    mechanism();performance();ablations();distributions(rows);grids(rows)


if __name__=='__main__':main()
