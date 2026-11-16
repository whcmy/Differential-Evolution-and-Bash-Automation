from pathlib import Path
p=Path('project1/plot_report.py');s=p.read_text();start=s.index('def heatmap_overview():');end=s.index('\ndef stage_distributions():',start)
s=s[:start]+'''def heatmap_overview():
    x,values,q=error_histories()
    fig=plt.figure(figsize=(5.72,4.6))
    gs=fig.add_gridspec(2,2,left=.105,right=.975,bottom=.12,top=.85,
                       height_ratios=[1.65,1],hspace=.78,wspace=.5)
    z=np.log10(np.maximum(np.array([q[f][1] for f in range(1,31)]),FLOOR))
    for j,first in enumerate([1,16]):
        ax=fig.add_subplot(gs[0,j])
        image=ax.imshow(z[first-1:first+14],aspect='auto',origin='upper',cmap='viridis',vmin=-12,vmax=8,
                        extent=[-.5,len(x)-.5,first+14.5,first-.5],interpolation='nearest')
        ax.set_yticks(range(first,first+15),[f'F{f:02d}' for f in range(first,first+15)],fontsize=7)
        ax.set_xticks([0,50,100],[f'{x[i]/1000:g}' for i in [0,50,100]])
        ax.set_xlabel('Recorded FEs (k)');ax.tick_params(axis='y',length=0)
        panel(ax,chr(97+j),f'F{first:02d}–F{first+14:02d}')
    cax=fig.add_axes([.56,.95,.41,.015])
    cb=fig.colorbar(image,cax=cax,orientation='horizontal',ticks=[-12,-8,-4,0,4,8])
    cb.ax.set_xticklabels(['≤10⁻¹²','10⁻⁸','10⁻⁴','1','10⁴','10⁸'])
    cb.ax.xaxis.set_ticks_position('top');cb.ax.tick_params(labelsize=6.8,length=0,pad=2)
    cb.outline.set_linewidth(.4);fig.text(.105,.951,'Median absolute error',fontsize=8,color=DARK)
    for j,(fid,title) in enumerate([(11,'Continued progress'),(26,'Residual plateau')]):
        ax=fig.add_subplot(gs[1,j]);median_curve(ax,fid,x,q)
        panel(ax,chr(99+j),f'F{fid:02d} | {title}')
        if j:ax.set_ylabel('')
    export(fig,'04_heatmap',exclude_axes=[cax])
    write_csv(FIG/'heatmap_source.csv',[dict(function=f'F{f:02d}',fes=int(t),q25=q[f][0,k],
        median=q[f][1,k],q75=q[f][2,k]) for f in range(1,31) for k,t in enumerate(x)])

'''+s[end:]
start=s.index('def stage_distributions():');end=s.index('\ndef representative_curves():',start)
old=s[start:end]
# Reuse the final-run panels and source export; compact the all-suite snapshots into two blocks.
bottom=old[old.index('    for j,fid in enumerate([4,11,22,26]):'):]
bottom=bottom.replace('gs[1,j]','gs[1,j]').replace("chr(98+j)","chr(99+j)")
s=s[:start]+'''def stage_distributions():
    x,values,q=error_histories()
    inds=[np.flatnonzero(x<=b)[-1] for b in [10000,50000,100000]]
    assert list(x[inds])==[9100,49100,100000]
    fig=plt.figure(figsize=(5.72,4.65))
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
'''+bottom+s[end:]
s=s.replace("fig.text(.54,.025,'Final runs", "fig.text(.54,.03,'Final runs")
p.write_text(s)
