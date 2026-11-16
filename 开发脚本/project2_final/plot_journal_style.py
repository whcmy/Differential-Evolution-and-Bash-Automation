"""Scientific composites adapted from the supplied papers. Author: 殷明骏."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ.setdefault('MPLCONFIGDIR','/tmp/project2-journal-mpl')
from pathlib import Path
import csv,json,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap,to_rgba
from matplotlib.patches import Rectangle,FancyArrowPatch
from matplotlib.ticker import MaxNLocator,ScalarFormatter
import numpy as np
from analyze_project2 import load,FINAL,DISPLAY,csv_write
from plot_project2 import LINES
import plot_report_revision as prior

# Exact MATLAB-style curve colours measured from the supplied DE-VCR figure.
COLORS={'DE':'#0072BD','DSPDE':'#D95319','DLSDE':'#EDB120','PEMSDE':'#7E2F8E','TEAM':'#A2142F'}
MARKERS={'DE':'o','DSPDE':'s','DLSDE':'^','PEMSDE':'D','TEAM':'*'}
prior.COLORS=COLORS

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output';FIG=OUT/'figures'
sys.path.insert(0,str(ROOT/'tools'))
from audit_panel_alignment import require_matplotlib_panel_alignment

plt.rcParams.update({'font.family':'serif','font.serif':['DejaVu Serif','Liberation Serif'],
    'font.size':8,'axes.labelsize':8,'xtick.labelsize':7.5,'ytick.labelsize':7.5,
    'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.65,
    'pdf.fonttype':42,'svg.fonttype':'none','legend.frameon':False})

def read(name):
    with (OUT/name).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))

def export(fig,name,exclude_axes=None):
    stem=FIG/name;fig.canvas.draw()
    require_matplotlib_panel_alignment(fig,json_out=str(stem)+'.alignment.json',tolerance_pt=1.5,strict=True,exclude_axes=exclude_axes or [])
    fig.savefig(str(stem)+'.pdf',metadata={'Author':'殷明骏','Creator':None,'Producer':None,'Subject':None,'Keywords':None,'CreationDate':None})
    fig.savefig(str(stem)+'.svg',metadata={'Creator':'殷明骏'})
    fig.savefig(str(stem)+'.png',dpi=400,metadata={'Author':'殷明骏','Software':None})
    plt.close(fig)

def label(ax,letter,title):
    ax.set_title(title,loc='left',fontsize=8.5,pad=9)
    ax.annotate(letter,xy=(0,1),xytext=(-9,8),xycoords='axes fraction',textcoords='offset points',fontweight='bold',fontsize=9,ha='right',va='bottom')

def arrow(ax,a,b,color='#333333'):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=9,lw=1.1,color=color,shrinkA=2,shrinkB=2))

def workflow():
    fig,ax=plt.subplots(figsize=(6.85,2.65));fig.subplots_adjust(left=.02,right=.98,bottom=.03,top=.97);ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
    ax.text(.01,.98,'Original-condition reconstruction and source controls',fontsize=9,fontweight='bold',va='top')
    for x,key,details in [(.02,'DSPDE','CEC2022 · NP 50 · 75,000 FEs'),(.35,'DLSDE','CEC2014 · NP 182 → 4 · 100,000 FEs'),(.68,'PEMSDE','CEC2017 · NP 60 · 100,000 FEs')]:
        ax.add_patch(Rectangle((x,.57),.30,.28,facecolor='white',edgecolor=COLORS[key],lw=1.2))
        ax.text(x+.15,.77,DISPLAY[key].replace(' (fixed NP)',''),ha='center',fontsize=9,fontweight='bold',color=COLORS[key])
        ax.text(x+.15,.65,details.replace(' · ', '\n',1),ha='center',va='center',fontsize=7.7)
        arrow(ax,(x+.15,.57),(x+.15,.44),COLORS[key])
    ax.plot([.17,.83],[.44,.44],color='#555555',lw=.8)
    arrow(ax,(.5,.44),(.5,.35))
    ax.text(.5,.29,'Controlled CEC2014 comparison',ha='center',fontsize=9,fontweight='bold')
    ax.text(.5,.18,'DE / DSPDE / DLS-DE (fixed NP) / PEMS-DE / PGE-DE',ha='center',fontsize=9)
    ax.text(.5,.07,'30 functions · 10D · NP 100 · 100,000 FEs · 20 paired seeds',ha='center',fontsize=8.8)
    export(fig,'journal_workflow')

def mechanisms():
    fig,axs=plt.subplots(1,3,figsize=(6.85,2.65));fig.subplots_adjust(left=.045,right=.99,bottom=.06,top=.83,wspace=.28)
    for ax in axs:ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
    ax=axs[0];label(ax,'a','Potential-guided mutation')
    xi=np.array([.12,.15]);c=np.array([.30,.77]);r2=np.array([.65,.26]);r1=np.array([.86,.60]);v=xi+.5*(c-xi+r1-r2)
    arrow(ax,xi,c,COLORS['PEMSDE']);arrow(ax,r2,r1,COLORS['DLSDE']);arrow(ax,xi,v,COLORS['TEAM'])
    for xy,t,col,off in [(xi,'xᵢ','#222222',(-.01,-.10)),(c,'c',COLORS['PEMSDE'],(-.03,.06)),(r1,'xᵣ₁',COLORS['DLSDE'],(-.02,.07)),(r2,'xᵣ₂',COLORS['DLSDE'],(.03,-.09)),(v,'vᵢ',COLORS['TEAM'],(.04,0))]:
        ax.scatter(*xy,s=22,color=col,zorder=3);ax.text(xy[0]+off[0],xy[1]+off[1],t,fontsize=9)
    ax.text(.5,.96,'Symbolic vector geometry',ha='center',fontsize=7.3)
    ax=axs[1];label(ax,'b','Two-phase F sampling')
    ax.plot([.04,.96],[.58,.58],color='#333333',lw=.8)
    for x,t in [(.04,'0'),(.32,'0.3'),(.96,'1')]:ax.plot([x,x],[.55,.61],color='black',lw=.8);ax.text(x,.46,t,ha='center',fontsize=8)
    ax.plot([.04,.32],[.66,.66],color=COLORS['DLSDE'],lw=3)
    ax.plot([.32,.96],[.66,.66],color=COLORS['TEAM'],lw=3)
    ax.text(.18,.82,'Success-rate\n+ sine',ha='center',fontsize=8.3)
    ax.text(.65,.82,'Cauchy\n+ memory',ha='center',fontsize=8.3)
    ax.text(.5,.30,'Consumed FEs / budget',ha='center',fontsize=7.5)
    ax.text(.5,.08,'Ordinary successes\nupdate the F memory',ha='center',fontsize=8.2)
    ax=axs[2];label(ax,'c','Probabilistic escape')
    for y,h,t in [(.69,.23,'Inferior target and\ndensity below threshold?'),(.31,.23,'0.7: gradient + noise\n0.3: mirrored proposal')]:
        ax.add_patch(Rectangle((.03,y),.94,h,fc='white',ec=COLORS['DSPDE'],lw=1))
        ax.text(.5,y+h/2,t,ha='center',va='center',fontsize=8.1)
    arrow(ax,(.5,.69),(.5,.54),COLORS['DSPDE']);ax.text(.56,.605,'Yes',fontsize=7.5)
    arrow(ax,(.5,.31),(.5,.21),COLORS['DSPDE'])
    ax.text(.5,.11,'Clip → evaluate → select',ha='center',fontsize=8.1)
    ax.text(.5,.00,'Otherwise retain ordinary trial',ha='center',fontsize=7.2)
    export(fig,'journal_mechanisms')

def performance():
    ranks=sorted(read('final_ranks.csv'),key=lambda x:float(x['mean_rank']))
    tests=read('final_paired_tests.csv');control=['DE','DSPDE','DLSDE','PEMSDE'];mat=np.zeros((4,30));sig=np.zeros_like(mat,dtype=bool)
    for r in tests:
        i=control.index(r['comparison']);j=int(r['function'])-1;mat[i,j]=-float(r['rank_biserial']);sig[i,j]=float(r['p_holm'])<.05
    fig,axs=plt.subplots(1,2,figsize=(6.85,2.75),gridspec_kw={'width_ratios':[1,2.4]});fig.subplots_adjust(left=.13,right=.87,bottom=.23,top=.82,wspace=.50)
    ax=axs[0]
    for i,r in enumerate(ranks):
        ax.plot([1,float(r['mean_rank'])],[i,i],color='#CCCCCC',lw=1.5);ax.scatter(float(r['mean_rank']),i,s=26,color=COLORS[r['algorithm']]);ax.text(5.0,i,f"{float(r['mean_rank']):.3f}",ha='left',va='center',fontsize=7.8)
    ax.set_yticks(range(5),[DISPLAY[r['algorithm']].replace(' (fixed NP)','\n(fixed NP)') for r in ranks]);ax.invert_yaxis();ax.set(xlim=(1,6.3),xticks=[1,2,3,4],xlabel='Mean rank');ax.tick_params(axis='y',length=0);label(ax,'a','Overall ordering')
    ax=axs[1];cmap=LinearSegmentedColormap.from_list('paired_effect',['#A2142F','#FFFFFF','#0072BD'])
    im=ax.imshow(mat,vmin=-1,vmax=1,cmap=cmap,aspect='auto',extent=(.5,30.5,3.5,-.5),interpolation='nearest')
    ys,xs=np.where(sig);ax.scatter(xs+1,ys,s=8,c='black',marker='o',linewidths=0)
    for x in [3.5,16.5,22.5]:ax.axvline(x,color='#666666',lw=.8)
    ax.set_yticks(range(4),['DE','DSPDE','DLS-DE','PEMS-DE']);ax.set_xticks([1,5,10,15,20,25,30]);ax.set_xlabel('CEC2014 function');ax.tick_params(axis='both',length=2);label(ax,'b','PGE-DE relative to each control')
    cax=fig.add_axes([.90,.24,.012,.55]);cb=fig.colorbar(im,cax=cax,ticks=[-1,0,1]);cb.ax.tick_params(labelsize=7);cb.set_label('Paired rank effect',fontsize=7.5)
    export(fig,'journal_performance',exclude_axes=[cax]);csv_write(FIG/'journal_performance.csv',tests)

def grids(rows):
    selection=[]
    for first in range(1,31,6):
        fig,axs=plt.subplots(2,3,figsize=(6.85,4.0));fig.subplots_adjust(left=.075,right=.965,bottom=.14,top=.84,hspace=.57,wspace=.34)
        for ax,fid in zip(axs.flat,range(first,first+6)):
            observed=[]
            for a in FINAL:
                group=[r for r in rows if r['function']==fid and r['algorithm']==a];assert len(group)==20
                best=min(group,key=lambda r:(r['fun'],r['run']));h=np.asarray(best['history']);assert np.all(h[:,1]>0) and np.all(np.diff(h[:,0])>0)
                ax.step(h[:,0],h[:,1],where='post',color=COLORS[a],ls=LINES[a],lw=1.2 if a=='TEAM' else .85,
                        marker=MARKERS[a],markersize=2.4 if a=='TEAM' else 1.8,markevery=max(1,len(h)//9))
                selection.append({'function':fid,'algorithm':a,'run':best['run'],'seed':best['seed']});observed.extend(h[:,1])
            ax.set_yscale('log');ax.set_xlim(0,100000);ax.set_xticks([0,50000,100000],['0','50k','100k']);ax.minorticks_off();ax.grid(axis='y',lw=.4,color='#E2E2E2')
            if np.log10(max(observed)/min(observed))<1:
                lo,hi=ax.get_ylim();ticks=[v for v in MaxNLocator(nbins=3,min_n_ticks=3).tick_values(lo,hi) if lo<=v<=hi and v>0];ax.set_yticks(ticks);ax.yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
            ax.set_title(f'F{fid:02d}',fontsize=8.2,pad=4);ax.tick_params(labelsize=7.5)
        fig.legend([Line2D([0],[0],color=COLORS[a],ls=LINES[a],lw=1.4) for a in FINAL],[DISPLAY[a] for a in FINAL],loc='upper center',bbox_to_anchor=(.53,.99),ncol=5,fontsize=7.4,handlelength=2.2,columnspacing=1)
        fig.text(.53,.035,'Function evaluations',ha='center',fontsize=8);fig.text(.012,.48,'Best objective (log scale)',rotation=90,ha='center',va='center',fontsize=8,rotation_mode='anchor')
        export(fig,f'journal_curves_{first:02d}_{first+5:02d}')
    csv_write(FIG/'journal_curve_selection.csv',selection)

def adapt_existing():
    original=prior.export
    def wider(fig,name):
        replacements={'#0057D9':'#0072BD','#EF6C00':'#A2142F','#BCC7D4':'#C0C0C0','#C53918':'#77AC30'}
        import matplotlib.colors as mc
        for artist in fig.findobj():
            for getter,setter in [('get_color','set_color'),('get_facecolor','set_facecolor'),('get_edgecolor','set_edgecolor')]:
                if not hasattr(artist,getter) or not hasattr(artist,setter):continue
                try:
                    value=getattr(artist,getter)();arr=mc.to_rgba_array(value)
                    changed=False
                    for old,new in replacements.items():
                        mask=np.all(np.isclose(arr[:,:3],mc.to_rgb(old)),axis=1)
                        if np.any(mask):arr[mask,:3]=mc.to_rgb(new);changed=True
                    if changed:getattr(artist,setter)(arr[0] if len(arr)==1 else arr)
                except (TypeError,ValueError):pass
        fig.set_size_inches(6.85,fig.get_figheight());export(fig,'journal_'+name)
    prior.export=wider
    prior.evaluator();prior.transfer();prior.distributions(ROWS);prior.telemetry()
    prior.export=original

if __name__=='__main__':
    FIG.mkdir(exist_ok=True);ROWS=load(ROOT/'results/coursework')
    workflow();mechanisms();performance();adapt_existing();grids(ROWS)
    print('Exported 12 journal-style figure sheets including all 30 measured functions')
