from pathlib import Path
p=Path('project1/plot_report.py');s=p.read_text()
s=s.replace("BLUE, TEAL, ORANGE, GRAY = '#174BEB', '#009FC7', '#FF7200', '#445B7C'", "BLUE, TEAL, ORANGE, GRAY = '#0072BD', '#77AC30', '#D95319', '#737373'")
s=s.replace("BAND, DARK = '#8BC6FF', '#13223D'", "BAND, DARK = '#BAD8EB', '#222222'")
s=s.replace("    BLUE, TEAL, ORANGE, GRAY = '#31688A', '#28877F', '#C47E43', '#83939D'\n",'')
s=s.replace("'#9CCAC4'","'#A7D7DD'").replace("'#DDE5E9'","'#D8E4EF'")
s=s.replace("color=BLUE,lw=2)","color=BLUE,lw=1.25)")
s=s.replace("color=ORANGE,lw=1.6, ls='--'","color=ORANGE,lw=1.1, ls='--'")
s=s.replace("color=ORANGE,lw=1.6,ls='--'","color=ORANGE,lw=1.1,ls='--'")
s=s.replace("color=BLUE,lw=2),Patch", "color=BLUE,lw=1.25),Patch")
s=s.replace("color=BLUE,lw=2)\n", "color=BLUE,lw=1.25)\n")
s=s.replace("color=BLUE, lw=2)","color=BLUE, lw=1.25, marker='o', markersize=2.1, markevery=(0,20))")
s=s.replace("color=ORANGE, lw=1.6, ls='--')", "color=ORANGE, lw=1.1, ls='--', marker='^', markersize=2.3, markevery=(10,20))")
s=s.replace("color=DARK, lw=.9, ls=':'", "color=DARK, lw=.6, ls=':'")
s=s.replace("ha='right',va='bottom',fontsize=8,color=DARK", "ha='right',va='bottom',fontsize=6.6,color=DARK")
s=s.replace("'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.8", "'axes.spines.top':True,'axes.spines.right':True,'axes.linewidth':.55")
start=s.index('def style(ax):');end=s.index('\ndef schematic_axis',start)
s=s[:start]+'''def style(ax):
    ax.set_axisbelow(True)
    ax.tick_params(length=2.5,width=.55,direction='in')
    ax.grid(True,which='major',color='#DCDCDC',lw=.35)
    for spine in ax.spines.values():
        spine.set_color('#666666');spine.set_linewidth(.55)

'''+s[end:]
start=s.index('def curve_grids():');end=s.index('\ndef error_histories',start)
s=s[:start]+'''def curve_grids():
    selected=[];trace_rows=[]
    for first in range(1,31,10):
        fig,axs=plt.subplots(5,2,figsize=(5.72,7.35))
        fig.subplots_adjust(left=.13,right=.98,bottom=.07,top=.915,hspace=.85,wspace=.43)
        for j,(ax,fid,letter) in enumerate(zip(axs.flat,range(first,first+10),'abcdefghij')):
            best=traces(ax,fid)
            ax.tick_params(labelsize=7.3)
            ax.set_xticks([0,50000,100000],['0','50','100'])
            ax.set_xlabel('FEs (k)' if j>=8 else '',fontsize=8)
            ax.set_ylabel('Objective' if j%2==0 else '',fontsize=8)
            ax.set_title(r'$\\mathbf{'+letter+r'}$  '+f'F{fid:02d}',loc='left',fontsize=8,pad=10)
            if ax.get_ylim()[1]/ax.get_ylim()[0]<10:
                lo,hi=ax.get_ylim();ticks=[t for t in MaxNLocator(nbins=3).tick_values(lo,hi) if lo<=t<=hi and t>0]
                ax.set_yticks(ticks);ax.yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
            else:
                from matplotlib.ticker import LogLocator
                ax.yaxis.set_major_locator(LogLocator(base=10,numticks=3))
            selected.append(dict(function=f'F{fid:02d}',run=best['run'],seed=best['seed'],best_fitness=best['best_fitness'],error=best['error']))
            for r in group(fid):
                trace_rows.extend(dict(function=f'F{fid:02d}',run=r['run'],seed=r['seed'],fes=h[0],objective=h[1],error=abs(h[1]-r['optimum'])) for h in r['history'])
        trace_legend(fig);export(fig,f'curves_{first:02d}_{first+9:02d}')
    write_csv(FIG/'curve_selection.csv',selected);write_csv(FIG/'convergence_source.csv',trace_rows)

'''+s[end:]
s=s.replace("figsize=(5.72,4.9)","figsize=(5.72,4.15)")
s=s.replace("figsize=(5.72,4.5)","figsize=(5.72,3.8)")
s=s.replace("figsize=(5.72,4.65)","figsize=(5.72,4.1)")
s=s.replace("print('Exported 13 figure sheets with the original process diagrams and high-contrast result plots')", "print('Exported 11 paper-style figure sheets including all 30 function histories')")
p.write_text(s)
