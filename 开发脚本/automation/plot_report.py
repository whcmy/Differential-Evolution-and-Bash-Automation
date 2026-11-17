"""Paper-style displays of the retained Automation evidence. Author: 殷明骏."""
from pathlib import Path
from datetime import datetime
import csv,hashlib,json,math,sys
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.ticker import FuncFormatter,MaxNLocator
ROOT=Path(__file__).resolve().parent; OUT=ROOT/'output/figures'
sys.path.insert(0,'/home/yinwhcmy/.codex/skills/nature-figure/scripts')
from audit_panel_alignment import require_matplotlib_panel_alignment
COLORS=['#0072BD','#D95319','#7E2F8E']; MARKERS=['o','s','^']; LINES=['-','--','-.']
WIDTH=6.8504
mpl.rcParams.update({'font.family':'serif','font.serif':['Times New Roman','DejaVu Serif'],
 'font.size':8.5,'axes.labelsize':8.5,'axes.titlesize':9,'xtick.labelsize':8,'ytick.labelsize':8,
 'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':True,'axes.spines.right':True,
 'axes.linewidth':.65,'axes.edgecolor':'#444444','legend.frameon':False,'lines.linewidth':1.0,
 'xtick.direction':'in','ytick.direction':'in','savefig.dpi':400})

def save(fig,name):
    stem=OUT/name
    require_matplotlib_panel_alignment(fig,json_out=str(stem)+'.alignment.json',tolerance_pt=1.5,strict=True)
    fig.savefig(str(stem)+'.pdf',metadata={'Author':'殷明骏','Creator':None,'Producer':None,'CreationDate':None,'ModDate':None})
    fig.savefig(str(stem)+'.svg',metadata={'Creator':None,'Date':None,'Description':None})
    fig.savefig(str(stem)+'.png',dpi=400,metadata={'Author':'殷明骏','Software':None})
    plt.close(fig)

def panel(ax,label,title):
    ax.text(-.12,1.14,label,transform=ax.transAxes,fontsize=10,fontweight='bold',va='bottom')
    ax.set_title(title,loc='left',pad=12)
    ax.tick_params(width=.65,length=3);ax.set_axisbelow(True)

def scientific_figures(rows,data,means):
    populations=[50,100,150]
    contribution=[];remaining=[]
    for pop in populations:
        selected=[r for r in rows if int(r['population'])==pop]
        contribution.append([math.fsum(float(r['absolute_error']) for r in selected if int(r['function'])==29),
                             math.fsum(float(r['absolute_error']) for r in selected if int(r['function'])==30),
                             math.fsum(float(r['absolute_error']) for r in selected if int(r['function']) not in [29,30])])
        remaining.append([math.fsum(float(r['absolute_error']) for r in selected if int(r['execution'])==seed and int(r['function'])!=29)/29 for seed in [1,2,3]])
    fig,axes=plt.subplots(1,2,figsize=(WIDTH,3.15),gridspec_kw={'left':.105,'right':.975,'bottom':.22,'top':.77,'wspace':.52})
    for j,(pop,color,marker) in enumerate(zip(populations,COLORS,MARKERS)):
        assert min(contribution[j])>1
        axes[0].bar(np.arange(3)+(j-1)*.23,np.asarray(contribution[j])-1,bottom=1,width=.21,color=color,edgecolor='#444444',lw=.4)
        a=np.asarray(remaining[j]);axes[1].errorbar(pop,a.mean(),yerr=a.std(ddof=1),color=color,marker=marker,mfc='white',ms=5,capsize=3,lw=1.1,zorder=3)
    for seed,line in zip(range(3),LINES):
        axes[1].plot(populations,[r[seed] for r in remaining],color='#A5A5A5',ls=line,lw=.7,marker='.',ms=4,zorder=1)
    axes[0].set_yscale('log');axes[0].set(xticks=range(3),xticklabels=['F29','F30','Other 28'],ylabel='Pooled absolute error',ylim=(1,1e8))
    axes[0].yaxis.set_major_formatter(FuncFormatter(lambda x,pos:f'1e{int(round(math.log10(x)))}' if x>0 else ''))
    lower=min(0,min(np.mean(r)-np.std(r,ddof=1) for r in remaining)*1.15)
    axes[1].set(xlabel='Population size',ylabel='Mean error on remaining 29 functions',xticks=populations,ylim=(lower,max(max(r) for r in remaining)*1.3))
    handles=[plt.Line2D([],[],color=color,marker=marker,lw=1,mfc='white',label=f'NP {pop}') for pop,color,marker in zip(populations,COLORS,MARKERS)]
    fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.51,.995),ncol=3,fontsize=8)
    for ax,l,title in zip(axes,['a','b'],['Error contribution by function','Diagnostic with F29 removed']):
        panel(ax,l,title);ax.yaxis.grid(True,color='#DFDFDF',lw=.4)
    save(fig,'04_error_decomposition')
    (OUT/'decomposition_source.json').write_text(json.dumps(dict(author='殷明骏',populations=populations,pooled_components_F29_F30_other28=contribution,mean_error_without_F29_by_seed=remaining,remaining_function_count=29,diagnostic_only=True),ensure_ascii=False,indent=2)+'\n')

    history_sources=[];history_groups={};curve_rows=[]
    for r in rows:
        path=ROOT/r['source'];record=json.loads(path.read_text())
        assert hashlib.sha256(path.read_bytes()).hexdigest()==r['sha256']
        history=np.asarray(record['history'],dtype=float)
        assert np.all(np.diff(history[:,0])>0) and history[-1,0]==100000
        assert history[-1,1]==record['fun']
        assert math.isclose(abs(record['fun']-record['optimum']),float(r['absolute_error']),rel_tol=1e-12,abs_tol=1e-12)
        key=(int(r['function']),int(r['population']))
        history_groups.setdefault(key,[]).append((history[:,0],np.abs(history[:,1]-record['optimum'])))
        history_sources.append(dict(source=r['source'],sha256=r['sha256'],checkpoints=len(history),function=key[0],population=key[1],execution=int(r['execution'])))
    assert len(history_sources)==270 and len(history_groups)==90
    for first in [1,11,21]:
        fig,axes=plt.subplots(5,2,figsize=(WIDTH,7.6),sharex=True,gridspec_kw={'left':.115,'right':.98,'bottom':.075,'top':.93,'wspace':.30,'hspace':.47})
        for ax,fid in zip(axes.flat,range(first,first+10)):
            grid=np.unique(np.concatenate([h[0] for pop in populations for h in history_groups[(fid,pop)]]))
            all_values=[]
            for pop,color,marker,line in zip(populations,COLORS,MARKERS,LINES):
                histories=history_groups[(fid,pop)];assert len(histories)==3
                valid_grid=grid[grid>=max(x[0] for x,y in histories)]
                samples=[]
                for x,y in histories:
                    idx=np.searchsorted(x,valid_grid,side='right')-1;assert np.all(idx>=0)
                    samples.append(y[idx])
                a=np.asarray(samples);median=np.median(a,axis=0);lo=a.min(axis=0);hi=a.max(axis=0)
                all_values.extend(lo.tolist()+hi.tolist())
                for x,mn,l,h in zip(valid_grid,median,lo,hi):curve_rows.append([fid,pop,float(x),float(mn),float(l),float(h)])
                ax.fill_between(valid_grid/1e4,np.maximum(lo,1e-8),np.maximum(hi,1e-8),step='post',color=color,alpha=.12,lw=0)
                ax.plot(valid_grid/1e4,np.maximum(median,1e-8),color=color,ls=line,drawstyle='steps-post',marker=marker,markevery=max(1,len(valid_grid)//8),ms=2.5,mfc='white',mew=.6,lw=.9)
            floor=max(1e-8/1.3,min(all_values)/3);upper=max(all_values)*2
            if upper<=floor:upper=floor*10
            ax.set_yscale('log');ax.set(xlim=(0,10),ylim=(floor,upper),xticks=[0,5,10])
            from matplotlib.ticker import LogLocator
            ax.yaxis.set_major_locator(LogLocator(base=10,subs=[1,2,5] if math.log10(upper/floor)<1.8 else [1],numticks=4))
            def log_label(x,pos):
                if x<=0:return ''
                base,exponent=f'{x:.0e}'.split('e')
                return base+'e'+str(int(exponent))
            ax.yaxis.set_major_formatter(FuncFormatter(log_label))
            ax.minorticks_off();ax.tick_params(labelsize=8,width=.55,length=2.5)
            ax.set_title(f'({chr(97+fid-first)}) F{fid:02d}',fontsize=8.5,pad=4)
            ax.grid(True,color='#E3E3E3',lw=.4);ax.set_axisbelow(True)
        fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.54,.99),ncol=3,fontsize=8)
        fig.supxlabel('Objective evaluations (×10⁴)',x=.54,y=.025,fontsize=8.5)
        fig.supylabel('Absolute best-so-far error (median and min–max of 3 seeds)',x=.015,fontsize=8.5)
        save(fig,f'05_convergence_{first:02d}_{first+9:02d}')
    with (OUT/'convergence_source.csv').open('w') as stream:
        writer=csv.writer(stream);writer.writerow(['function','population','evaluations','median_absolute_error','minimum_absolute_error','maximum_absolute_error']);writer.writerows(curve_rows)
    (OUT/'convergence_sources.json').write_text(json.dumps(dict(author='殷明骏',records=270,functions=30,curves=90,aggregation='Median and min–max across three DC-DE rerun master seeds',alignment='Union of original checkpoints; previous-observation hold; no pre-initialization extrapolation',display_floor=1e-8,sources=history_sources),ensure_ascii=False,indent=2)+'\n')

def main():
    OUT.mkdir(exist_ok=True)
    src=ROOT/'output/analysis/records.csv'
    with src.open() as f: rows=list(csv.DictReader(f))
    assert len(rows)==270 and len({(r['execution'],r['population'],r['function']) for r in rows})==270
    populations=[50,100,150]; data=json.loads((ROOT/'output/analysis/results.json').read_text())
    scores={str(i):[math.fsum(float(r['absolute_error']) for r in rows if int(r['execution'])==i and int(r['population'])==p)/30 for p in populations] for i in [1,2,3]}
    means={str(f):[math.fsum(float(r['absolute_error']) for r in rows if int(r['function'])==f and int(r['population'])==p)/3 for p in populations] for f in range(1,31)}
    winners={f:[p for p,v in zip(populations,vals) if math.isclose(v,min(vals),abs_tol=1e-8,rel_tol=1e-10)] for f,vals in means.items()}
    counts={str(p):sum(p in g for g in winners.values()) for p in populations}
    assert sum(len(v) for v in winners.values()) == sum(counts.values())
    assert all(s['score']==scores[str(s['execution'])][populations.index(s['population'])] for s in data['suites'])
    comparison=dict(author='殷明骏',records=270,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),populations=populations,suite_scores=scores,function_mean_errors=means,function_winners=winners,function_best_counts=counts,tie_rule='math.isclose(abs_tol=1e-8,rel_tol=1e-10); count every tied population')
    (OUT/'comparison_data.json').write_text(json.dumps(comparison,ensure_ascii=False,indent=2)+'\n')
    with (OUT/'comparison_source.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['function','np50_mean','np100_mean','np150_mean','lowest_populations'])
        for fid,vals in means.items():w.writerow([fid,*vals,' '.join(map(str,winners[fid]))])

    fig=plt.figure(figsize=(WIDTH,2.55));ax=fig.add_axes([.01,.03,.98,.94]);ax.set(xlim=(0,10),ylim=(0,4));ax.axis('off')
    boxes=[(1.6,3.25,'System cron','Hourly launch + exclusive lock',COLORS[0]),(5,3.25,'Bash parameter loop','NP = 50, 100, 150',COLORS[0]),(8.4,3.25,'DC-DE optimizer','30 functions per configuration',COLORS[0]),(8.4,1.8,'Saved solutions + log','90 JSON records per execution',COLORS[1]),(5,1.8,'Independent verification','Fitness, budget, coverage, hashes',COLORS[1]),(1.6,1.8,'grep | awk extraction','Exact SUITE_RESULT tokens',COLORS[1])]
    for x,y,title,sub,color in boxes:
        ax.add_patch(FancyBboxPatch((x-1.4,y-.43),2.8,.86,boxstyle='round,pad=0.035,rounding_size=0.06',facecolor='#F1F7FB' if color==COLORS[0] else '#FCF3ED',edgecolor=color,lw=.85))
        ax.text(x,y+.12,title,ha='center',va='center',fontsize=9,fontweight='bold')
        ax.text(x,y-.18,sub,ha='center',va='center',fontsize=7.5)
    for a,b in [((3.05,3.25),(3.55,3.25)),((6.45,3.25),(6.95,3.25)),((8.4,2.77),(8.4,2.28)),((6.95,1.8),(6.45,1.8)),((3.55,1.8),(3.05,1.8)),((1.6,1.32),(1.6,.91))]:
        ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=9,lw=.85,color='#303030'))
    ax.add_patch(FancyBboxPatch((.2,.13),9.6,.72,boxstyle='round,pad=.02,rounding_size=.05',facecolor='#F7F7F7',edgecolor='#555555',lw=.7))
    ax.text(5,.49,'Verified summary + BATCH_SUCCESS  →  3 executions / 270 records / 9 scores',ha='center',va='center',fontsize=9)
    save(fig,'00_automation_workflow')

    fig,axes=plt.subplots(1,2,figsize=(WIDTH,2.85),gridspec_kw={'left':.10,'right':.97,'bottom':.23,'top':.76,'wspace':.46})
    origin=datetime.fromisoformat('2026-11-16T20:00:00+08:00');durations=[];delays=[]
    for i,r in enumerate(data['receipts']):
        start=datetime.fromisoformat(r['started_at']);end=datetime.fromisoformat(r['completed_at'])
        minutes=(start-origin).total_seconds()/60;duration=(end-start).total_seconds()/60;planned=20+60*i
        durations.append(duration);delays.append((minutes-planned)*60)
        axes[0].plot([planned,minutes],[i,i],color='#888888',lw=.8,linestyle='--')
        axes[0].scatter(planned,i,marker='|',s=95,color='#202020',zorder=3)
        axes[0].plot([minutes,minutes+duration],[i,i],color=COLORS[0],lw=4,solid_capstyle='butt')
        axes[0].scatter(minutes,i,s=20,marker='o',color=COLORS[0],zorder=4)
        axes[1].bar(i,duration,color=COLORS[0],width=.48)
        axes[1].text(i,duration+.13,f'{duration:.2f}',ha='center',va='bottom',fontsize=8.5)
    axes[0].set(yticks=[0,1,2],yticklabels=['Run 1','Run 2','Run 3'],xticks=[0,60,120,180],xticklabels=['20:00','21:00','22:00','23:00'],ylim=(2.55,-.55),xlim=(-7,185),xlabel='Local time (Asia/Shanghai)')
    axes[0].plot([],[],color='#222222',marker='|',ls='',label='Planned launch')
    axes[0].plot([],[],color=COLORS[0],marker='o',lw=2,label='Actual execution')
    axes[0].legend(loc='lower left',bbox_to_anchor=(-.02,1.13),ncol=2,fontsize=7.5,handlelength=1,columnspacing=.9)
    axes[1].set(xticks=[0,1,2],xticklabels=['Run 1','Run 2','Run 3'],ylim=(0,5),ylabel='Elapsed time (min)');axes[1].yaxis.grid(True,color='#E2E2E2',lw=.4)
    panel(axes[0],'a','Planned and actual launches');panel(axes[1],'b','Batch duration')
    axes[1].yaxis.grid(False)
    save(fig,'02_scheduled_execution')
    (OUT/'timing_source.json').write_text(json.dumps(dict(author='殷明骏',date='2026-11-16',duration_minutes=durations,launch_delays_seconds=delays,receipts=data['receipts']),ensure_ascii=False,indent=2)+'\n')

    fig,axes=plt.subplots(1,2,figsize=(WIDTH,3.15),gridspec_kw={'left':.11,'right':.98,'bottom':.20,'top':.76,'wspace':.50})
    for i,line in zip([1,2,3],LINES):
        axes[0].plot(populations,[v/1e5 for v in scores[str(i)]],marker='.',color='#A5A5A5',ls=line,ms=4,lw=.7,zorder=1)
    for j,(pop,color,marker) in enumerate(zip(populations,COLORS,MARKERS)):
        values=np.array([scores[str(i)][j] for i in [1,2,3]])/1e5
        axes[0].errorbar(pop,values.mean(),yerr=values.std(ddof=1),color=color,marker=marker,mfc='white',mec=color,ms=5,capsize=3,lw=1.1,label=f'NP {pop}',zorder=3)
    axes[0].set(xlabel='Population size',ylabel='Suite mean error (×10⁵)',xticks=populations,ylim=(1.4,2.4))
    axes[0].yaxis.set_major_formatter(FuncFormatter(lambda v,p:f'{v:.1f}'))
    fig.legend(*axes[0].get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.50,.995),ncol=3,fontsize=8,columnspacing=1.8)
    axes[1].bar(range(3),[counts[str(p)] for p in populations],color=COLORS,width=.52,edgecolor='#333333',linewidth=.4)
    axes[1].set(xlabel='Population size',ylabel='Functions with lowest mean error',xticks=range(3),xticklabels=populations,ylim=(0,19))
    axes[1].yaxis.set_major_locator(MaxNLocator(integer=True,nbins=5))
    for x,p in enumerate(populations):axes[1].text(x,counts[str(p)]+.4,str(counts[str(p)]),ha='center',va='bottom')
    for a,l,t in zip(axes,['a','b'],['All scores and mean ± SD','Functionwise coverage']):panel(a,l,t);a.yaxis.grid(True,color='#E2E2E2',lw=.4)
    axes[1].yaxis.grid(False)
    save(fig,'01_population_comparison')

    fig,axes=plt.subplots(1,3,figsize=(WIDTH,3.65),gridspec_kw={'left':.075,'right':.985,'bottom':.20,'top':.78,'wspace':.34})
    for k,ax in enumerate(axes):
        fids=list(range(1+10*k,11+10*k))
        for j,(p,col,marker) in enumerate(zip(populations,COLORS,MARKERS)):
            vals=np.array([means[str(f)][j] for f in fids]);ys=np.arange(10)+(j-1)*.19
            positive=vals>1e-8
            ax.scatter(np.maximum(vals[positive],1e-8),ys[positive],c=col,marker=marker,s=19,linewidths=.5,label=f'NP {p}')
            ax.scatter(np.full((~positive).sum(),1e-8),ys[~positive],facecolors='white',edgecolors=col,marker=marker,s=19,linewidths=.8)
        ax.set_xscale('log');ax.set(xlim=(3e-9,2e7),ylim=(9.6,-.6),yticks=range(10),yticklabels=[f'F{f:02d}' for f in fids],xticks=[1e-8,1e-4,1,1e4],xticklabels=['≤10⁻⁸','10⁻⁴','1','10⁴'],xlabel='Mean absolute error')
        ax.xaxis.grid(True,color='#DDDDDD',lw=.45);ax.tick_params(axis='x',labelsize=7.5)
        panel(ax,chr(97+k),f'F{fids[0]:02d}–F{fids[-1]:02d}')
    handles=[plt.Line2D([],[],color=c,marker=m,lw=0,markersize=4,label=f'NP {p}') for p,c,m in zip(populations,COLORS,MARKERS)]
    fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.52,.995),ncol=3,fontsize=8)
    save(fig,'03_function_profile')
    scientific_figures(rows,data,means)
    print('Exported 8 paper-style figure sheets from 270 original records and histories')
if __name__=='__main__':main()
