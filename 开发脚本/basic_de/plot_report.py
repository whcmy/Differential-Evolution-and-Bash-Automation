"""Scientific figures from retained Basic DE observations. Author: 殷明骏."""
from pathlib import Path
import os
os.environ.setdefault('MPLCONFIGDIR', '/tmp/basic_de-report-mpl')
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import csv
import json
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, FancyBboxPatch, FancyArrowPatch, Rectangle
from matplotlib.ticker import ScalarFormatter, MaxNLocator

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output'
FIG = OUT / 'figures'
sys.path.insert(0, str(ROOT / 'tools'))
from audit_panel_alignment import require_matplotlib_panel_alignment
BLUE, TEAL, ORANGE, GRAY = '#0072BD', '#77AC30', '#D95319', '#737373'
BAND, DARK = '#BAD8EB', '#222222'
FLOOR = 1e-12
ROWS = [json.loads(p.read_text()) for p in sorted((ROOT / 'results').glob('F*_run*.json'))]
ROWS.sort(key=lambda r: (r['function'], r['run']))
assert len(ROWS) == 600

def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def group(fid):
    rs = [r for r in ROWS if r['function'] == fid]
    assert len(rs) == 20
    return rs

def export(fig, name, **layout_options):
    stem = FIG / name
    fig.canvas.draw()
    require_matplotlib_panel_alignment(fig, json_out=str(stem)+'.alignment.json', tolerance_pt=1.5, strict=True, **layout_options)
    fig.savefig(str(stem)+'.pdf', metadata={'Author':'殷明骏','Creator':None,'Producer':None,'Subject':None,'Keywords':None,'CreationDate':None})
    fig.savefig(str(stem)+'.svg', metadata={'Creator':'殷明骏','Date':None})
    fig.savefig(str(stem)+'.png', dpi=400, metadata={'Author':'殷明骏','Software':None})
    plt.close(fig)

def panel(ax, letter, title):
    ax.set_title(r'$\mathbf{'+letter+r'}$  '+title, loc='left', fontsize=9.5, pad=12)

def style(ax):
    ax.set_axisbelow(True)
    ax.tick_params(length=2.5,width=.55,direction='in')
    ax.grid(True,which='major',color='#DCDCDC',lw=.35)
    for spine in ax.spines.values():
        spine.set_color('#666666');spine.set_linewidth(.55)


def schematic_axis(height):
    fig,ax=plt.subplots(figsize=(5.72,height))
    fig.subplots_adjust(left=.015,right=.985,bottom=.015,top=.985)
    ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
    return fig,ax

def box(ax,x,y,w,h,title,detail,fill='#C9DFFF'):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.008,rounding_size=0.012',
                              facecolor=fill,edgecolor=BLUE,linewidth=1))
    ax.text(x+w/2,y+h*.69,title,ha='center',va='center',fontsize=9,fontweight='bold')
    ax.text(x+w/2,y+h*.30,detail,ha='center',va='center',fontsize=8.5,linespacing=1.35)

def arrow(ax,a,b):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=11,lw=1.3,color=BLUE,shrinkA=2,shrinkB=2))

def workflow():
    with plt.rc_context({'text.color':'black','axes.labelcolor':'black','xtick.color':'black','ytick.color':'black','axes.linewidth':.65}):
        # The occupancy matrix is derived from the 600 observed function/run pairs.
        from matplotlib.colors import ListedColormap
        fig=plt.figure(figsize=(6.9,2.15))
        gs=fig.add_gridspec(1,3,left=.095,right=.975,bottom=.19,top=.77,wspace=.85)
        ax=fig.add_subplot(gs[0,0])
        occupancy=np.zeros((30,20))
        for r in ROWS:occupancy[r['function']-1,r['run']-1]=1
        assert np.all(occupancy==1)
        ax.pcolormesh(np.arange(21),np.arange(31),occupancy,cmap=ListedColormap(['#EDF1F3',BLUE]),
            vmin=0,vmax=1,edgecolors='white',linewidth=.25,antialiased=False)
        ax.set(xlim=(0,20),ylim=(30,0))
        ax.set_xticks([.5,9.5,19.5],['1','10','20']);ax.set_yticks([.5,14.5,29.5],['F01','F15','F30'])
        ax.set_xlabel('Independent run');panel(ax,'a','30 × 20 runs')
        for spine in ax.spines.values():spine.set_visible(False)
        ax=fig.add_subplot(gs[0,1:])
        ax.set(xlim=(-5000,105000),ylim=(0,1))
        ax.add_patch(Rectangle((100,.45),99900,.18,facecolor='#DCE9EF',edgecolor='none'))
        ax.plot([100,100000],[.54,.54],color=BLUE,lw=1)
        ax.plot([100,100000],[.54,.54],'o',color=BLUE,ms=4)
        ax.annotate('100 initialization FEs',xy=(100,.57),xytext=(2000,.88),ha='left',fontsize=8,
            arrowprops=dict(arrowstyle='-',color=GRAY,lw=.65))
        ax.text(55000,.72,'999 generations × 100 FEs',ha='center',fontsize=8.5)
        ax.text(50000,.12,'Save the solution and full history',ha='center',fontsize=8.5)
        ax.set_xticks([0,50000,100000],['0','50k','100k']);ax.set_yticks([])
        ax.set_xlabel('Function evaluations per run')
        for edge in ['left','top','right']:ax.spines[edge].set_visible(False)
        panel(ax,'b','A common evaluation budget')
        export(fig,'00_workflow')


def mechanism():
    with plt.rc_context({'text.color':'black','axes.labelcolor':'black','xtick.color':'black','ytick.color':'black','axes.linewidth':.65}):
        fig=plt.figure(figsize=(6.9,3.35))
        gs=fig.add_gridspec(2,2,left=.065,right=.975,bottom=.055,top=.89,
                             height_ratios=[1.5,1],wspace=.27,hspace=.61)
        # A schematic projection, with exact difference-vector and clipping relations.
        ax=fig.add_subplot(gs[0,0]);ax.set(xlim=(-.17,1.47),ylim=(-.26,1.45));ax.axis('off')
        ax.add_patch(Rectangle((0,0),1,1,facecolor='#F3F6F7',edgecolor=GRAY,lw=.7))
        r1=np.array([.85,.7]);r2=np.array([.65,.9]);r3=np.array([.05,.1])
        v=r1+.5*(r2-r3);clipped=np.clip(v,0,1)
        assert np.allclose(v,[1.15,1.1])
        ax.scatter([r1[0],r2[0],r3[0]],[r1[1],r2[1],r3[1]],s=17,color=BLUE,zorder=4)
        ax.add_patch(FancyArrowPatch(r3,r2,arrowstyle='-|>',mutation_scale=9,lw=1.0,color=GRAY))
        ax.add_patch(FancyArrowPatch(r1,v,arrowstyle='-|>',mutation_scale=10,lw=1.3,color=TEAL))
        ax.scatter([v[0]],[v[1]],s=26,marker='o',color=ORANGE,zorder=5)
        ax.scatter([clipped[0]],[clipped[1]],s=25,marker='s',color=TEAL,zorder=5)
        ax.plot([v[0],clipped[0]],[v[1],clipped[1]],color=ORANGE,lw=1,ls='--')
        for xy,label,position in [(r3,r'$x_{r3}$',(.04,-.23)),(r2,r'$x_{r2}$',(.05,1.10)),
                                (r1,r'$x_{r1}$',(.72,.45))]:
            ax.annotate(label,xy=xy,xytext=position,fontsize=9,
                        arrowprops=dict(arrowstyle='-',color=GRAY,lw=.55))
        ax.annotate(r'$v_i$',xy=v,xytext=(5,3),textcoords='offset points',fontsize=9)
        ax.text(.05,1.29,r'$v_i=x_{r1}+0.5(x_{r2}-x_{r3})$',fontsize=8.5)
        ax.text(.95,.03,'Allowed box',fontsize=8,ha='right')
        ax.annotate('Clip',xy=(1,1),xytext=(1.20,.25),fontsize=8,ha='left',
            arrowprops=dict(arrowstyle='-',lw=.65,color=GRAY))
        panel(ax,'a','Mutation creates a direction')
        ax=fig.add_subplot(gs[0,1]);ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
        mask=np.array([1,1,1,1,1,0,1,1,1,1],dtype=bool)
        x0=.22;step=.073;cell=.064
        for row,(label,y) in enumerate([(r'$x_i$',.71),(r'$v_i$',.46),(r'$u_i$',.21)]):
            ax.text(.02,y+.035,label,fontsize=10,va='center')
            for j in range(10):
                color='#D8E4EF' if row==0 or (row==2 and not mask[j]) else '#A7D7DD'
                ax.add_patch(Rectangle((x0+j*step,y),cell,.08,facecolor=color,edgecolor='white',lw=.4))
        # Origin indicators explain coordinate ownership rather than adding numeric values.
        for j in [4,5]:
            source=.71 if not mask[j] else .46
            ax.add_patch(FancyArrowPatch((x0+j*step+cell/2,source),
                         (x0+j*step+cell/2,.29),arrowstyle='-|>',mutation_scale=7,
                         lw=.7,color=GRAY))
        ax.add_patch(Rectangle((x0+4*step-.004,.204),cell+.008,.092,fill=False,edgecolor=ORANGE,lw=1.2))
        ax.text(.55,.97,'CR = 0.9',ha='center',fontsize=8.5)
        ax.text(x0+4*step+cell/2,.115,r'$j_{rand}$',ha='center',fontsize=9)
        ax.text(.5,-.035,'Outlined coordinate must be mutant-derived',ha='center',fontsize=8)
        panel(ax,'b','Crossover assembles the trial')
        ax=fig.add_subplot(gs[1,:]);ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
        ax.text(.01,.74,r'One evaluation of $u_i$',fontsize=9)
        ax.text(.01,.48,r'$f(u_i)<f(x_i)$ ?',fontsize=10)
        ax.add_patch(FancyArrowPatch((.31,.52),(.58,.72),arrowstyle='-|>',mutation_scale=9,lw=.8,color=TEAL))
        ax.add_patch(FancyArrowPatch((.31,.47),(.58,.33),arrowstyle='-|>',mutation_scale=9,lw=.8,color=GRAY))
        ax.text(.43,.74,'Yes',fontsize=8,ha='center')
        ax.text(.43,.10,'No',fontsize=8,ha='center')
        ax.text(.62,.70,r'Accept trial $u_i$',fontsize=9)
        ax.text(.62,.27,r'Retain parent $x_i$',fontsize=9)
        ax.text(.01,-.03,'All donors come from X(g); commit X(g + 1) after constructing every trial',fontsize=8)
        panel(ax,'c','Selection preserves strict improvement')
        export(fig,'00_de_update')

def accuracy():
    fig,axs=plt.subplots(2,1,figsize=(6.9,3.2),sharex=True,gridspec_kw={'height_ratios':[2,1]})
    fig.subplots_adjust(left=.16,right=.975,bottom=.17,top=.84,hspace=.64)
    data=np.array([[r['error'] for r in group(f)] for f in range(1,31)])
    q=np.quantile(data,[.25,.5,.75],axis=1);x=np.arange(1,31)
    bands=[(.5,3.5),(3.5,16.5),(16.5,22.5),(22.5,30.5)]
    for ax in axs:
        for i,(a,b) in enumerate(bands):
            if i%2==0:ax.axvspan(a,b,color='#EAF1FF',zorder=0)
        style(ax)
    ax=axs[0]
    ax.vlines(x,np.maximum(q[0],FLOOR),np.maximum(q[2],FLOOR),color=BLUE,lw=2.4)
    ax.scatter(x,np.maximum(q[1],FLOOR),color=BLUE,marker='o',s=22,zorder=3)
    ax.axhline(1e-8,color=ORANGE,lw=1.3,ls='--')
    ax.set_yscale('log');ax.set_ylim(2e-13,5e7)
    ax.set_yticks([1e-12,1e-8,1e-4,1,1e4]);ax.set_ylabel('Final absolute error');ax.minorticks_off()
    panel(ax,'a','Accuracy across the complete benchmark')
    ax=axs[1];ax.grid(False);counts=(data<=1e-8).sum(axis=1)
    ax.bar(x,counts,width=.65,color=BLUE)
    for fid,count in zip(x,counts):
        if count and fid not in [1,3]:
            ax.text(fid,count+.6,str(count),ha='center',va='bottom',fontsize=8)
    ax.set(ylim=(0,28),yticks=[0,10,20],xlim=(.4,30.6),ylabel='Runs at threshold',xlabel='CEC2014 function')
    ax.set_xticks(x,[f'F{f:02d}' for f in x],rotation=90,fontsize=8)
    panel(ax,'b','Repeatability at an error of 10⁻⁸ or less')
    fig.legend([Line2D([0],[0],color=BLUE,marker='o',lw=1.5,ms=4),Line2D([0],[0],color=ORANGE,ls='--',lw=.85)],
               ['Median and IQR','Interpretation threshold'],loc='upper center',bbox_to_anchor=(.56,1),ncol=2,frameon=False)
    export(fig,'01_accuracy')
    write_csv(FIG/'01_accuracy.csv',[dict(function=f'F{f:02d}',q25=q[0,f-1],median=q[1,f-1],q75=q[2,f-1],successes=int(counts[f-1]),runs=20) for f in x])

def swarm_y(ax,values,center):
    """Displace dots only vertically, using rendered coordinates to avoid overlap."""
    ax.figure.canvas.draw()
    occupied=[];ys=[];mindist=3.8*ax.figure.dpi/72
    for value in values:
        xpix,ypix=ax.transData.transform((value,center))
        candidates=[0]+[sign*k*mindist for k in range(1,30) for sign in [1,-1]]
        for offset in candidates:
            if all((xpix-x)**2+(ypix+offset-y)**2>=mindist**2-.01 for x,y in occupied):break
        occupied.append((xpix,ypix+offset));ys.append(ax.transData.inverted().transform((xpix,ypix+offset))[1])
    assert min(ys)>center-.49 and max(ys)<center+.49
    return ys


def distributions():
    fig=plt.figure(figsize=(6.9,4.65))
    gs=fig.add_gridspec(2,2,left=.13,right=.97,bottom=.12,top=.88,
        height_ratios=[1.25,1],hspace=.95,wspace=.55)
    ax=fig.add_subplot(gs[0,:]);ax.set_xscale('log')
    floor_labels=[f'F{fid:02d}\n{sum(r["error"]<=FLOOR for r in group(fid))} at floor' for fid in [4,6]]
    ax.set(xlim=(2e-13,5e2),ylim=(-.6,1.6),yticks=[1,0],yticklabels=floor_labels)
    ax.set_xticks([1e-12,1e-8,1e-4,1,100]);ax.minorticks_off()
    ax.axvline(1e-8,color=ORANGE,lw=.8,ls='--')
    ax.set_xlabel('Final absolute error')
    for fid,y in [(4,1),(6,0)]:
        errors=np.array([r['error'] for r in group(fid)]);display=np.maximum(errors,FLOOR)
        ax.scatter(display,swarm_y(ax,display,y),s=13,color=BLUE,edgecolors='white',linewidths=.25,zorder=4)
        floor_count=int((errors<=FLOOR).sum());success=int((errors<=1e-8).sum())
        ax.text(1e-5,y+.35,f'{success}/20 ≤ 10⁻⁸',ha='left',fontsize=8)
    ax.spines['left'].set_visible(False);ax.tick_params(axis='y',length=0)
    panel(ax,'a','Repeated runs split into distinct outcomes')
    for col,fid,letter in [(0,30,'b'),(1,22,'c')]:
        ax=fig.add_subplot(gs[1,col]);errors=np.sort([r['error'] for r in group(fid)])
        med=float(np.median(errors));mean=float(np.mean(errors))
        ax.plot(np.arange(1,21),errors,'o',ms=4,color=BLUE,lw=0)
        ax.axhline(med,color=TEAL,lw=1.2);ax.axhline(mean,color=ORANGE,lw=1.2,ls='--')
        ax.set(xlim=(0,21),ylim=(0,float(errors[-1])*1.12),xticks=[1,10,20],xlabel='Run ordered by error',ylabel='Final error')
        if fid==30:
            ax.set_yticks([0,20000,40000],['0','20k','40k'])
            ax.annotate(f'Worst / median = {errors[-1]/med:.1f}',xy=(20,errors[-1]),xytext=(.03,.96),
                        textcoords='axes fraction',va='top',fontsize=8,arrowprops=dict(arrowstyle='-',lw=.65,color=GRAY))
        else:ax.set_yticks([0,10,20])
        ax.text(.03,.72,f'Mean {mean:,.1f}\nMedian {med:,.2f}',transform=ax.transAxes,fontsize=8,linespacing=1.5,va='top')
        panel(ax,letter,f'F{fid:02d}: upper-tail sensitivity');style(ax);ax.grid(False)
    fig.legend([Line2D([0],[0],color=TEAL,lw=.8),Line2D([0],[0],color=ORANGE,lw=.8,ls='--')],
        ['Median (b,c)','Mean (b,c)'],loc='upper center',bbox_to_anchor=(.57,1.005),ncol=2,frameon=False)
    export(fig,'02_variability')
    write_csv(FIG/'02_variability.csv',[dict(function=r['function'],run=r['run'],seed=r['seed'],error=r['error']) for r in ROWS if r['function'] in [4,6,22,30]])

def traces(ax, fid, error=False, start_fes=0):
    rs = group(fid)
    histories = [np.array(r['history'], dtype=float) for r in rs]
    x = histories[0][:, 0]
    assert all(np.array_equal(h[:, 0], x) for h in histories)
    assert np.all(np.diff(x) > 0)
    values = np.array([h[:, 1] for h in histories])
    if error:
        values = np.abs(values - rs[0]['optimum'])
    window=x>=start_fes
    x=x[window];values=values[:,window]
    q = np.quantile(values, [.25, .5, .75], axis=0)
    winner = min(range(20), key=lambda i: (rs[i]['best_fitness'], rs[i]['run']))
    display = lambda a: np.maximum(a, FLOOR) if error else a
    ax.fill_between(x, display(q[0]), display(q[2]), step='post', color=BAND, lw=0)
    ax.step(x, display(q[1]), where='post', color=BLUE, lw=.95, marker='o', markersize=1.8, markevery=(0,20))
    ax.step(x, display(values[winner]), where='post', color=ORANGE, lw=.85, ls='--', marker='^', markersize=2, markevery=(10,20))
    ax.set_yscale('log')
    ax.set_xlim(start_fes, 100000)
    ax.set_xticks([0, 20000, 40000, 60000, 80000, 100000], ['0', '20k', '40k', '60k', '80k', '100k'])
    ax.set_xlim(start_fes, 100000)
    ax.set_xlabel('Function evaluations')
    ax.set_ylabel('Best absolute error (log scale)' if error else 'Best objective (log scale)')
    if error and np.min(values) < FLOOR:
        ax.set_ylim(bottom=2e-13)
    elif (np.log10(np.max(values) / np.min(values)) < 1
          or sum(ax.get_ylim()[0] <= t <= ax.get_ylim()[1] for t in ax.get_yticks()) < 2):
        lo, hi = ax.get_ylim()
        ticks = [v for v in MaxNLocator(nbins=5, min_n_ticks=4).tick_values(lo, hi) if lo <= v <= hi and v > 0]
        ax.set_yticks(ticks)
        ax.yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
    ax.minorticks_off()
    style(ax)
    if not error:
        limits=ax.get_ylim()
        if limits[0] <= rs[0]['optimum'] <= limits[1]:
            ax.axhline(rs[0]['optimum'], color=DARK, lw=.6, ls=':')
        ax.set_ylim(limits)
        ax.text(.99,1.02,f"f* {rs[0]['optimum']:g} | error {np.median([r['error'] for r in rs]):.2g}",transform=ax.transAxes,
                ha='right',va='bottom',fontsize=6.6,color=DARK)
    return rs[winner]

def trace_legend(fig):
    fig.legend([Line2D([0],[0],color=BLUE,lw=1.25),Patch(facecolor=BAND),Line2D([0],[0],color=ORANGE,lw=1.1,ls='--')],
               ['Median','Interquartile range','Best final run'],loc='upper center',bbox_to_anchor=(.55,1.005),ncol=3,frameon=False)

def budget_progress():
    rows=[]
    for fid in range(1,31):
        runs=group(fid);t=max(h[0] for h in runs[0]['history'] if h[0]<=50000)
        mid=np.array([abs(next(h[1] for h in r['history'] if h[0]==t)-r['optimum']) for r in runs])
        final=np.array([r['error'] for r in runs]);m50=float(np.median(mid));m100=float(np.median(final))
        assert m50>=m100-1e-12
        rows.append(dict(function=f'F{fid:02d}',midpoint_fes=t,final_fes=100000,
            midpoint_median_error=m50,final_median_error=m100,
            late_gain_orders=float(np.log10(max(m50,FLOOR)/max(m100,FLOOR))),
            relative_reduction=(m50-m100)/m50 if m50 else 0))
    write_csv(FIG/'budget_progress.csv',rows)
    return rows


def convergence():
    rows=budget_progress()
    fig=plt.figure(figsize=(6.9,4.15))
    gs=fig.add_gridspec(2,2,left=.135,right=.975,bottom=.12,top=.84,
        height_ratios=[1.25,1],hspace=.95,wspace=.55)
    ax=fig.add_subplot(gs[0,:]);x=np.arange(1,31);gains=[100*r['relative_reduction'] for r in rows]
    ax.bar(x,gains,color=[ORANGE if i in [11,26] else BLUE for i in x],width=.68)
    ax.set(xlim=(.4,30.6),ylim=(0,106),yticks=[0,25,50,75,100],
           ylabel='Median error removed\nlate in the budget (%)',xlabel='CEC2014 function')
    ax.set_xticks(x,[f'F{i:02d}' for i in x],rotation=90,fontsize=8)
    ax.text(26,5,f'{gains[25]:.3f}%',ha='center',fontsize=8)
    panel(ax,'a','Late progress differs across the benchmark')
    for ax,fid,letter in [(fig.add_subplot(gs[1,0]),11,'b'),(fig.add_subplot(gs[1,1]),26,'c')]:
        traces(ax,fid,error=True,start_fes=49100)
        ax.set_xticks([50000,75000,100000],['50k','75k','100k'])
        assert ax.get_xlim()==(49100,100000)
        ax.set_xlabel('Function evaluations');ax.set_ylabel('Best absolute error')
        q=np.quantile([[abs(h[1]-r['optimum']) for h in r['history'] if h[0]>=49100] for r in group(fid)],[.25,.75])
        # Keep all median/IQR and best-run data visible; no post-hoc y clipping.
        ax.relim();ax.autoscale_view(scalex=False)
        vals=[abs(h[1]-r['optimum']) for r in group(fid) for h in r['history'] if h[0]>=49100]
        lo=min(vals);hi=max(vals);assert lo>0
        factor=np.exp(max(np.log(hi/lo)*.08,1e-9))
        lower,upper=lo/factor,hi*factor
        ax.set_ylim(lower,upper)
        ticks=([100,300,1000] if hi/lo>2 else MaxNLocator(nbins=3).tick_values(lower,upper))
        ax.set_yticks([v for v in ticks if lower<=v<=upper])
        ax.yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
        panel(ax,letter,f'F{fid:02d}: '+('ongoing progress' if fid==11 else 'persistent residual'))
    trace_legend(fig);export(fig,'03_convergence')

def curve_grids():
    selected=[];trace_rows=[]
    for first in range(1,31,15):
        fig,axs=plt.subplots(5,3,figsize=(6.9,6.65))
        fig.subplots_adjust(left=.075,right=.985,bottom=.075,top=.915,hspace=.96,wspace=.47)
        for j,(ax,fid,letter) in enumerate(zip(axs.flat,range(first,first+15),'abcdefghijklmno')):
            best=traces(ax,fid)
            ax.texts[-1].set_text(f"f* = {100*fid}")
            ax.texts[-1].set_fontsize(6.8)
            ax.tick_params(labelsize=7.3)
            ax.set_xticks([0,50000,100000],['0','50','100'])
            ax.set_xlabel('FEs (k)' if j>=12 else '',fontsize=8)
            ax.set_ylabel('Objective' if j%3==0 else '',fontsize=8)
            ax.set_title(r'$\mathbf{'+letter+r'}$  '+f'F{fid:02d}',loc='left',fontsize=8,pad=10)
            if ax.get_ylim()[1]/ax.get_ylim()[0]<10:
                lo,hi=ax.get_ylim();ticks=[t for t in MaxNLocator(nbins=3).tick_values(lo,hi) if lo<=t<=hi and t>0]
                ax.set_yticks(ticks);ax.yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
            else:
                from matplotlib.ticker import LogLocator
                ax.yaxis.set_major_locator(LogLocator(base=10,numticks=3))
            selected.append(dict(function=f'F{fid:02d}',run=best['run'],seed=best['seed'],best_fitness=best['best_fitness'],error=best['error']))
            for r in group(fid):
                trace_rows.extend(dict(function=f'F{fid:02d}',run=r['run'],seed=r['seed'],fes=h[0],objective=h[1],error=abs(h[1]-r['optimum'])) for h in r['history'])
        trace_legend(fig);export(fig,f'curves_{first:02d}_{first+14:02d}')
    write_csv(FIG/'curve_selection.csv',selected);write_csv(FIG/'convergence_source.csv',trace_rows)


def error_histories():
    """All retained histories in function order, without temporal interpolation."""
    x=np.array(group(1)[0]['history'],dtype=float)[:,0]
    assert np.all(np.diff(x)>0)
    values={}
    for fid in range(1,31):
        runs=group(fid)
        assert all(np.array_equal(np.array(r['history'])[:,0],x) for r in runs)
        values[fid]=np.abs(np.array([np.array(r['history'])[:,1] for r in runs])-100*fid)
    return x,values,{f:np.quantile(v,[.25,.5,.75],axis=0) for f,v in values.items()}

def median_curve(ax,fid,x,q):
    low,median,high=np.maximum(q[fid],FLOOR)
    ax.fill_between(x/1000,low,high,color=BAND,step='post',lw=0)
    ax.step(x/1000,median,where='post',color=BLUE,lw=1.25)
    ax.plot(100,median[-1],'o',ms=4.5,color=ORANGE,zorder=4)
    ax.set_yscale('log');ax.minorticks_off()
    ax.set(xlim=(0,103),ylim=(low.min()/2.5,high.max()*3),xticks=[0,50,100],
           xlabel='Evaluations (k)',ylabel='Absolute error')
    from matplotlib.ticker import LogLocator
    ax.yaxis.set_major_locator(LogLocator(base=10,numticks=3))
    ax.grid(axis='y',color='#E4EAF4',lw=.5);style(ax)

def heatmap_overview():
    x,values,q=error_histories()
    fig=plt.figure(figsize=(6.9,2.7))
    gs=fig.add_gridspec(1,2,left=.105,right=.975,bottom=.24,top=.77,wspace=.3)
    z=np.log10(np.maximum(np.array([q[f][1] for f in range(1,31)]),FLOOR))
    for j,first in enumerate([1,16]):
        ax=fig.add_subplot(gs[0,j])
        image=ax.imshow(z[first-1:first+14],aspect='auto',origin='upper',cmap='viridis',vmin=-12,vmax=8,
                        extent=[-.5,len(x)-.5,first+14.5,first-.5],interpolation='nearest')
        ax.set_yticks(range(first,first+15),[f'F{f:02d}' for f in range(first,first+15)],fontsize=6.8)
        ax.set_xticks([0,50,100],[f'{x[i]/1000:g}' for i in [0,50,100]])
        ax.set_xlabel('Recorded FEs (k)');ax.tick_params(axis='y',length=0)
        panel(ax,chr(97+j),f'F{first:02d}–F{first+14:02d}')
    cax=fig.add_axes([.56,.91,.41,.018])
    cb=fig.colorbar(image,cax=cax,orientation='horizontal',ticks=[-12,-8,-4,0,4,8])
    cb.ax.set_xticklabels(['≤10⁻¹²','10⁻⁸','10⁻⁴','1','10⁴','10⁸'])
    cb.ax.xaxis.set_ticks_position('top');cb.ax.tick_params(labelsize=6.8,length=0,pad=2)
    cb.outline.set_linewidth(.4);fig.text(.105,.91,'Median absolute error',fontsize=8,color=DARK)
    export(fig,'04_heatmap',exclude_axes=[cax])
    write_csv(FIG/'heatmap_source.csv',[dict(function=f'F{f:02d}',fes=int(t),q25=q[f][0,k],
        median=q[f][1,k],q75=q[f][2,k]) for f in range(1,31) for k,t in enumerate(x)])


def stage_distributions():
    x,values,q=error_histories()
    inds=[np.flatnonzero(x<=b)[-1] for b in [10000,50000,100000]]
    assert list(x[inds])==[9100,49100,100000]
    fig=plt.figure(figsize=(6.9,4.65))
    gs=fig.add_gridspec(2,4,left=.105,right=.975,bottom=.16,top=.87,
                       height_ratios=[1.65,1],hspace=.78,wspace=.95)
    colors=[GRAY,ORANGE,BLUE];markers=['o','D','o']
    for column,first in enumerate([1,16]):
        ax=fig.add_subplot(gs[0,column*2:column*2+2]);ids=range(first,first+15);y=np.arange(15,0,-1)
        for fid,yy in zip(ids,y):
            vals=np.maximum(q[fid][1,inds],FLOOR)
            ax.plot([vals[-1],vals[0]],[yy,yy],color='#A3B0BB',lw=.7,zorder=1)
        for k,(idx,col,marker) in enumerate(zip(inds,colors,markers)):
            vals=np.maximum([q[f][1,idx] for f in ids],FLOOR)
            ax.scatter(vals,y,s=[20,19,14][k],marker=marker,color=col,
                       edgecolors='white',linewidths=.3,zorder=2+k)
        ax.set_xscale('log');ax.minorticks_off()
        ax.set(xlim=(1e-13,1e8),ylim=(.25,15.75),xlabel='Median absolute error')
        ax.set_xticks([1e-12,1,1e8])
        ax.set_yticks(y,[f'F{f:02d}' for f in ids],fontsize=7)
        ax.tick_params(axis='y',length=0);style(ax)
        panel(ax,chr(97+column),f'F{first:02d}–F{first+14:02d}')
    fig.legend([Line2D([],[],color=c,marker=m,ms=4,lw=0) for c,m in zip(colors,markers)],
        ['9.1k FEs','49.1k FEs','100k FEs'],loc='upper center',bbox_to_anchor=(.56,1.005),ncol=3,frameon=False)
    for j,fid in enumerate([4,11,22,26]):
        ax=fig.add_subplot(gs[1,j]);vals=np.sort([r['error'] for r in group(fid)])
        ax.scatter(np.arange(1,21),vals,s=13,color=BLUE,edgecolors='white',linewidths=.3,zorder=3)
        ax.axhline(np.median(vals),color=ORANGE,lw=1.2,ls=(0,(4,3)))
        ax.set(xlim=(0,21),xticks=[1,10,20]);ax.grid(axis='y',color='#E4EAF4',lw=.5)
        ax.yaxis.set_major_locator(MaxNLocator(3))
        if fid==26:
            from matplotlib.ticker import FormatStrFormatter
            ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f'));ax.tick_params(axis='y',labelsize=6.8)
        else:ax.set_ylim(-.05*max(vals),1.12*max(vals))
        if j==0:ax.set_ylabel('Final absolute error')
        ax.tick_params(axis='x',labelsize=7);panel(ax,chr(99+j),f'F{fid:02d}')
    fig.text(.54,.03,'Final runs ordered by absolute error (1–20)',ha='center',fontsize=8.5)
    export(fig,'05_stages')
    write_csv(FIG/'stage_source.csv',[dict(function=f'F{fid:02d}',fes=int(x[idx]),median_error=q[fid][1,idx])
        for fid in range(1,31) for idx in inds])

def representative_curves():
    x,values,q=error_histories()
    fig=plt.figure(figsize=(6.9,4.65))
    gs=fig.add_gridspec(2,3,left=.11,right=.975,bottom=.12,top=.88,
                       height_ratios=[1.4,1],hspace=.85,wspace=.65)
    ax=fig.add_subplot(gs[0,:]);median_curve(ax,11,x,q)
    panel(ax,'a','F11 | Continued improvement under a fixed budget')
    # This range includes the entire IQR and median in the enlarged example.
    lo,mid,hi=np.maximum(q[11],FLOOR)
    ax.set_ylim(lo.min()/1.1,hi.max()*1.15)
    ax.set_yticks([1000,2000,3000],['1,000','2,000','3,000'])
    ax.set_ylim(min(lo.min()/1.1,950),max(hi.max()*1.15,3100))
    for j,(fid,title) in enumerate([(4,'Split'),(22,'Late gain'),(26,'Plateau')]):
        ax=fig.add_subplot(gs[1,j]);median_curve(ax,fid,x,q)
        panel(ax,chr(98+j),f'F{fid:02d} | {title}')
        if j:ax.set_ylabel('')
        ax.set_xlabel('FEs (k)')
    fig.legend([Line2D([],[],color=BLUE,lw=1.25),Patch(facecolor=BAND)],['Median','Interquartile range'],
               loc='upper center',bbox_to_anchor=(.56,1.005),ncol=2,frameon=False)
    export(fig,'06_representative')

def main():
    FIG.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['DejaVu Sans'],'font.size':8.5,
        'axes.labelsize':8.5,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8.5,
        'axes.spines.top':True,'axes.spines.right':True,'axes.linewidth':.55,'pdf.fonttype':42,'svg.fonttype':'none',
        'text.color':DARK,'axes.labelcolor':DARK,'xtick.color':DARK,'ytick.color':DARK})
    workflow();mechanism();accuracy();distributions();convergence();curve_grids()
    heatmap_overview()
    print('Exported 8 journal-style figure sheets including all 30 function histories')

if __name__=='__main__':main()
