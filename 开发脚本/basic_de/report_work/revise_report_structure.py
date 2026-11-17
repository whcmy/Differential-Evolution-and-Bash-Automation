from pathlib import Path
p=Path('basic_de/build_report.py');s=p.read_text()
s=s.replace("r.h('2.3 Outcome measures',2,newpage=True,toc=False)","r.h('2.3 Outcome measures',2,toc=False)")
# Exact numerical statements stay in the text; captions focus on how to read the graphics.
a=s.index("    r.fig('04_heatmap'");b=s.index("    r.p('The common colour scale",a)
s=s[:a]+'''    r.fig('04_heatmap','Figure 4. Convergence across the benchmark. '
        'a,b Median absolute errors for F01–F15 and F16–F30 share one logarithmic colour scale; brighter cells indicate higher errors. '
        'c,d F11 and F26 show medians and IQRs over 20 runs, with orange final-median markers. '
        'Axes are independently scaled. Recorded checkpoints are not interpolated; errors ≤10⁻¹² share a display floor.')
'''+s[b:]
a=s.index("    r.fig('05_stages'");b=s.index("    r.p('The snapshots",a)
s=s[:a]+'''    r.fig('05_stages','Figure 6. Budget response and final variability. '
        'a,b Median errors over 20 runs at 9,100, 49,100 and 100,000 FEs for F01–F15 and F16–F30. '
        'c–f All 20 final errors for F04, F11, F22 and F26, sorted within function; dashed orange lines mark medians. '
        'Snapshots use a logarithmic axis with a 10⁻¹² floor. Final-run panels use separate linear scales.')
'''+s[b:]
a=s.index("    notes=[");b=s.index("    r.h('3.6 Benchmark and literature comparison'",a)
s=s[:a]+'''    notes=[
        'F01 to F03 approach their declared optima. F04 to F10 retain multimodal residuals; on F04 and F06 the best final run separates from the median. The IQR shows how much of this contrast is shared across runs.',
        'F11 to F16 complete the basic multimodal group, followed by hybrid functions F17 to F20. F11 continues to improve late in the budget; the narrow bands on several other functions indicate similar trajectories across seeds.',
        'F21 and F22 complete the hybrid group; F23 to F30 are composition functions. F23 and F26 retain stable nonzero residuals, while F27 and F30 separate typical from favorable trajectories. A flat objective trace does not by itself establish convergence to the declared optimum.'
    ]
    for i,first in enumerate(range(1,31,10)):
        title='3.5 Complete convergence curves' if i==0 else f'Convergence curves F{first:02d} to F{first+9:02d}'
        r.h(title,2,newpage=True)
        r.fig(f'curves_{first:02d}_{first+9:02d}',f'Figure {9+i}. Objective histories for F{first:02d}–F{first+9:02d}. '
            'Blue lines and bands show medians and IQRs across all 20 runs; orange dashed lines show the best final run. '
            'Every panel uses its own logarithmic scale and reports the optimum f* and final median error. '
            'Markers identify recorded checkpoints; all logged points contribute to the traces. Visible optima are dotted.')
        r.p(notes[i])
'''+s[b:]
p.write_text(s)
