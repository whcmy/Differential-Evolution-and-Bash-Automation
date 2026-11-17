"""Executed experimental and PGE-DE flow diagrams. Author: 殷明骏."""
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from plot_report_revision import FIG, require_matplotlib_panel_alignment
from plot_adaptive_de import COLORS

def export(fig,name):
    stem=FIG/name
    fig.canvas.draw()
    require_matplotlib_panel_alignment(fig,json_out=str(stem)+'.alignment.json',tolerance_pt=1.5,strict=True)
    fig.savefig(str(stem)+'.pdf',metadata={'Author':'殷明骏','Creator':None,'Producer':None,'Subject':None,'Keywords':None,'CreationDate':None})
    fig.savefig(str(stem)+'.svg',metadata={'Creator':'殷明骏'})
    fig.savefig(str(stem)+'.png',dpi=400,metadata={'Author':'殷明骏','Software':None})
    plt.close(fig)

def box(ax,x,y,w,h,text,color,solid=False,size=9):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.25,rounding_size=1.1',
        facecolor=color if solid else '#FFFFFF',edgecolor=color,linewidth=1.5))
    ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=size,
            color='white' if solid else '#17212E',linespacing=1.5)

def arrow(ax,x1,y1,x2,y2,color='#364152'):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',mutation_scale=11,
                              linewidth=1.4,color=color,shrinkA=2,shrinkB=3))

def experiment():
    fig,ax=plt.subplots(figsize=(5.72,4.45));fig.subplots_adjust(left=.025,right=.975,bottom=.03,top=.97)
    ax.set(xlim=(0,100),ylim=(0,100));ax.axis('off')
    specs=[(2,'DSPDE','CEC2022 · 10D\nNP 50 · 75,000 FEs','4 source controls'),
           (35,'DLSDE','CEC2014 · 10D\nNP 182 → 4 · 100,000 FEs','5 source controls'),
           (68,'PEMSDE','CEC2017 · 10D\nNP 60 · 100,000 FEs','4 source controls')]
    for x,key,details,control in specs:
        label={'DSPDE':'DSPDE','DLSDE':'DLS-DE','PEMSDE':'PEMS-DE'}[key]
        box(ax,x,85,30,12,label,COLORS[key],True,11)
        box(ax,x,63,30,18,details,COLORS[key],size=8.1)
        arrow(ax,x+15,85,x+15,81,COLORS[key])
        ax.text(x+15,57,control,ha='center',va='center',fontsize=8.7,fontweight='bold')
    ax.plot([17,17,83,83],[53,49,49,53],color='#364152',lw=1.2)
    ax.plot([50,50],[53,49],color='#364152',lw=1.2)
    arrow(ax,50,49,50,44)
    box(ax,2,29,96,15,'Common comparison: DE + three reconstructions + PGE-DE\nCEC2014 · 30 functions · 10D · fixed NP 100 · 100,000 FEs',COLORS['TEAM'],True,9)
    arrow(ax,50,29,50,24)
    box(ax,2,11,96,13,'20 runs per function and condition\nFull statistics · paired tests · all 30 convergence curves','#0057D9',size=9)
    ax.text(50,4,'Source controls retain their recorded protocols; native and common tracks remain separate.',
            ha='center',va='center',fontsize=7.2)
    export(fig,'00_experiment_flow')

def algorithm():
    fig,ax=plt.subplots(figsize=(5.72,5.0));fig.subplots_adjust(left=.025,right=.975,bottom=.025,top=.975)
    ax.set(xlim=(0,100),ylim=(0,100));ax.axis('off')
    box(ax,22,89,66,9,'Initialize 100 solutions · evaluate · F memory = 0.5','#364152',True,9)
    box(ax,2,66,29,13,'PEMS-DE\nPotential-weighted guide',COLORS['PEMSDE'],True,8.6)
    box(ax,35,66,29,13,'DLS-DE\nTwo-phase F sampler',COLORS['DLSDE'],True,8.6)
    box(ax,68,66,30,13,'DSPDE\nProbabilistic escape',COLORS['DSPDE'],True,8.6)
    arrow(ax,55,89,55,84)
    ax.plot([16.5,83],[84,84],color='#364152',lw=1.2)
    for x in [16.5,49.5,83]:
        arrow(ax,x,84,x,80)
    arrow(ax,16.5,66,32,59,COLORS['PEMSDE']);arrow(ax,49.5,66,49.5,59,COLORS['DLSDE'])
    box(ax,22,48,44,11,'Current-to-guide mutation\nBinomial crossover · CR 0.9',COLORS['TEAM'],True,9)
    arrow(ax,83,66,83,43,COLORS['DSPDE']);arrow(ax,44,48,44,43)
    box(ax,22,31,76,12,'Eligible inferior target? Replace its ordinary trial\nwith one escape candidate; otherwise retain the trial',COLORS['DSPDE'],size=8.8)
    arrow(ax,60,31,60,26)
    box(ax,22,15,76,11,'Clip · evaluate within remaining FEs · accept strict improvements\nUpdate F memory from ordinary successes only',COLORS['TEAM'],size=8.5)
    arrow(ax,60,15,60,10)
    box(ax,22,1,76,9,'Stop at 100,000 FEs; otherwise repeat the generation','#364152',True,8.6)
    ax.plot([22,.5,.5],[5.5,5.5,84],color='#364152',lw=1.2)
    arrow(ax,.5,84,16.5,84)
    ax.text(5,38,'Repeat',rotation=90,ha='center',va='center',fontsize=8.5)
    export(fig,'00_algorithm_flow')

if __name__=='__main__':
    plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['DejaVu Sans'],'pdf.fonttype':42,'svg.fonttype':'none'})
    experiment();algorithm()
