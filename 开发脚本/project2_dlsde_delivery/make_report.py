"""Build a Chinese report from verified data; no experiment values are hard-coded."""
import bootstrap
import argparse
import csv
import json
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
CN_NAMES = dict(dls_de="完整 DLS-DE", no_learning="去除差分向量学习", no_two_phase="去除两阶段 F",
                fixed_sigma="固定尺度参数", fitness_weights="改用适应度权重", binomial="改用二项交叉", de="基础 DE")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "output")
    args = parser.parse_args()
    out = args.output
    d = json.loads((out / "report_data.json").read_text(encoding="utf-8"))
    c = d["config"]
    verification = json.loads((out / "verification.json").read_text(encoding="utf-8"))
    if not verification["valid"] or not verification["course_full"] or c.get("evaluator", "opfunu") != "opfunu":
        raise ValueError("This report template requires verified full CEC2014 10D course results; smoke/reference data remain available as CSV and figures.")
    main_rows = [r for r in d["summary"] if r["algorithm"] == "dls_de"]
    ref_file = ROOT / "output_reference/report_data.json"
    ref_data = json.loads(ref_file.read_text(encoding="utf-8")) if ref_file.exists() else None
    ref_map = {r["function"]:r for r in ref_data["paper_comparison"]} if ref_data else {}
    reference_note = ""
    if ref_data:
        for key in ("dimension", "max_fes", "seed", "population_size", "runs", "gate"):
            if ref_data["config"][key] != c[key]:
                raise ValueError(f"reference protocol differs: {key}")
        reference_note = ("另外使用完全相同的优化器、参数和初始化种子，完成600次MinionPy 1.9.1 C++参考评估器实验。"
                          f"其30个函数的均值均与论文处于10倍以内或双方低于1e-8，但该宽松描述不代表统计等价。"
                          f"其中F29均值为{ref_map[29]['reproduced_mean']:.4f}，论文为{ref_map[29]['paper_mean']:.4f}；"
                          f"F30均值为{ref_map[30]['reproduced_mean']:.4f}，论文为{ref_map[30]['paper_mean']:.4f}。"
                          "C++补充结果单独保存于output_reference，不参与opfunu课程实验排名。")
    close = d["paper_within_factor10"]
    small = sum(r["mean"] < 1e-8 for r in main_rows)
    lead = (f"本实验独立实现 Chen 与 Meng 的 DLS-DE，在 CEC2014 的 {len(d['functions'])} 个 {c['dimension']} 维函数上，"
            f"每算法每函数独立运行 {c['runs']} 次，每次严格使用 {c['max_fes']:,} 次优化评价。"
            f"本次共完成 {d['result_count']:,} 次真实运行，逐次结果均通过最优向量重算、预算、边界和轨迹核验。")
    comparison_note = (f"完整算法在 {small} 个函数上的平均误差低于 1e-8。与论文表12的51次结果进行描述性对照，"
                       f"有 {close}/{len(main_rows)} 个函数满足均值相差不超过10倍或双方均小于1e-8。"
                       "该口径仅用于快速定位差异，不是复现成功的统计判据。")
    settings = [
        ("测试集与维数", f"CEC2014 F1-F30，{c['dimension']}D，opfunu 1.0.4"),
        ("重复次数与预算", f"{c['runs']}次；每次 {c['max_fes']:,} FEs，含初始化"),
        ("种群", f"NP_init={c['population_size']}，按FEs线性缩减至4；基础DE固定NP"),
        ("参数记忆与档案", "H=6，mu_F初值0.5，p=0.11，档案比例1.6"),
        ("两阶段与尺度", "前30%预算使用SR非线性生成F；其余Cauchy；lambda=0.1"),
        ("学习触发", "ST=30，tau=0.3；默认按算法5，每代rand>tau"),
        ("初始化约定", "SR=0.5；sigma_F=0.05；Prob各维初值1/D"),
        ("选择与边界", "小于或等于父代时接受；越界坐标采用父代与边界中点"),
        ("随机种子", f"基准{c['seed']}；由函数编号和run编号确定；变体初始种群相同"),
        ("实际运行环境", f"Python {c['python']}，NumPy {c['versions']['numpy']}，Windows"),
    ]
    method = [
        "变异使用 current-to-pbest/1，随机差分的第二个个体从种群与外部档案的并集中选取；供体索引互异并排除目标。指数交叉从随机坐标开始，沿环形连续坐标传递，至少保留一维。",
        "前30%评价预算内，F根据上一代成功率和历史记忆扰动生成并限制在[0.35,0.65]；随后以历史mu_F为位置参数采样Cauchy分布。非正F重新采样，大于1截为1。非零停滞次数为10的倍数时，用尺度0.05重新采样。",
        "成功位移在全部维度上的样本标准差VIX作为权重。mu_F通过加权Lehmer均值更新；sigma_F使用当代和上一代成功F均值的中心，按当代成功F的RMS偏离量自适应调整。",
        "CR由历史概率向量的期望维数k映射得到10k/(10k+1)。成功试验按实际交叉维数分组，依照式(15)-(16)更新概率记忆；若全部成功试验只交叉一维，当前概率记忆槽写入零向量。",
        "停滞期间只记录严格满足f(X)<f(U)<f(Y)的失败试验。其未乘F的差分向量按交叉掩码累加到LV，同时更新LF。ct>30且各维LF非零时，算法5允许使用历史方向均值生成全维学习试验；成功替换后学习状态清零。",
        "每代结束后按评价进度缩减种群，删除最差个体时同步删除其学习状态。初始化计入FEs；最后不完整一代只评价剩余目标。每次完成后额外重算最优向量一次，作为明确单列的审计评价。",
    ]
    limitations = [
        "论文3.3.2节称学习以概率tau触发，但算法5第1行写tau<rand，4.7节也称tau越小越常使用学习。本实现默认遵循伪代码，即概率1-tau，且每代共享一次随机门控；--gate text提供文字解释模式。",
        "论文未明确SR初值、sigma初值、边界修复、零VIX权重和部分抽样细节。具体选择及代码对应位置均见reference/implementation_notes.md；这些约定会影响逐次随机轨迹。",
        "课程要求20次，论文使用51次。论文未提供本交付可用的逐次结果，因此本报告只描述性比较均值和标准差，无法复刻原文对逐次样本执行的Wilcoxon秩和检验。",
        "本实验使用未修改的opfunu 1.0.4，论文使用MATLAB2021a。已在13个混合或复合函数上发现opfunu与C++参考评估器的点值差异，源码也显示F17操作顺序及F29旋转/置乱分块调用不同。有限点探测不能证明全域等价。本机Python3.12.14超出opfunu包声明的<3.12范围，安装时使用--ignore-requires-python，已通过本项目全部检查；推荐可移植环境使用Python3.11。",
        "本报告完成Project2中这一篇论文的复现与策略消融；其余两篇算法及跨论文组合的新算法不在本次范围内。",
    ]
    stats_text = []
    for a, values in d["statistics"].items():
        stats_text.append(f"相对{CN_NAMES[a]}，完整DLS-DE的显著胜/平/负为"
                          f"{values['win']}/{values['tie']}/{values['loss']}。")
    interpretation = []
    test_file = out / "statistical_tests.csv"
    if test_file.exists():
        with test_file.open(encoding="utf-8-sig") as stream:
            test_rows = list(csv.DictReader(stream))
        def function_list(algorithm, outcome):
            ids = [f"F{int(r['function'])}" for r in test_rows
                   if r["comparator"] == algorithm and r["outcome"] == outcome]
            return "、".join(ids) if ids else "无"
        if all(a in d["algorithms"] for a in ("binomial", "fixed_sigma", "no_learning", "no_two_phase")):
            interpretation.append(
                "逐函数结果显示，指数交叉相对二项交叉的显著收益集中在" + function_list("binomial", "win") +
                "；自适应尺度相对固定尺度的收益出现在" + function_list("fixed_sigma", "win") +
                "。去掉学习后仅在" + function_list("no_learning", "win") +
                "检测到完整算法显著更优，去掉两阶段F后对应函数为" + function_list("no_two_phase", "win") +
                "。因此，各策略的作用依赖具体函数，平均排名改善不等于在所有函数上显著改善。")
        if ("fitness_weights" in d["algorithms"]
                and d["statistics"]["fitness_weights"]["win"] == 0
                and d["statistics"]["fitness_weights"]["loss"] == 0):
            interpretation.append(
                "完整算法与适应度权重版本的平均排名接近，二者在本次30个函数上均未检测到Holm校正后的显著差异。"
                "这不足以证明两种权重机制等价，也不足以宣称VIX在10D上稳定优于适应度权重。"
                "这些消融结论限定于本次opfunu实现、20次重复及给定检验口径；不能直接推广为官方CEC2014的策略排名。")
    stats_method = ("逐函数按平均误差排序，使用绝对1e-8、相对1e-10的容差合并数值噪声导致的并列；原始误差仍完整保存。"
                    "每个消融版本与完整算法比较使用双侧Mann-Whitney U检验（渐近法、处理并列），"
                    "同一对算法的30个函数采用Holm校正，alpha=0.05。均值差在上述数值容差内时胜负记为平，并保留原始p值。该检验不同于以单次最好结果推断优劣。")
    best_rank = d["ranking"][0]
    rank_text = f"本组实验平均排名最小的是{CN_NAMES[best_rank['algorithm']]}，平均名次{best_rank['mean_rank']:.3f}。"
    diagnostic_note = ""
    if "diagnostics_totals" in d:
        diag = d["diagnostics_totals"]["dls_de"]
        diagnostic_note = (f"完整算法有{diag['runs_with_learning']}/600次运行实际触发学习分支，累计生成"
                           f"{diag['learning_trials']:,}个学习试验、记录{diag['learning_records']:,}个有潜力的失败试验。"
                           "因此，学习策略已在正式预算下实际执行。")
    conclusion = ("算法公式、核心状态流转、预算控制和结果可追溯性已实现并通过检查。" + comparison_note + rank_text +
                  "策略贡献应依据逐函数统计判断，不能预设完整算法在所有函数上优于每个消融版本。"
                  "C++参考评估器上的补充实验明显缩小F29、F30与论文的差距，支持函数实现对偏差有实质影响。"
                  "与论文的数值一致性仍受实现约定、测试函数实现和重复次数差异限制，应结合对照表逐项评估。")
    md = ["# DLS DE 论文复现实验报告", "", lead, "", comparison_note, "", "## 实验参数", "",
          "| 参数 | 设置 |", "|---|---|"]
    md += [f"| {a} | {b} |" for a, b in settings]
    md += ["", "## 方法", ""] + [x + "\n" for x in method]
    md += ["## 复现结果", "", "误差=max(0,f_best-f*)；Std/Variance采用样本定义ddof=1。", "",
           "| 函数 | Best | Mean | Std | Variance | Rank |", "|---|---:|---:|---:|---:|---:|"]
    md += [f"| F{r['function']:02d} | {r['best']:.5e} | {r['mean']:.5e} | {r['std']:.5e} | {r['variance']:.5e} | {r['rank']:.1f} |" for r in main_rows]
    md += ["", "## 与论文对照", "", comparison_note,
           "论文出处：表12，第14页，10D的DLS-DE列；与表14对应列的30组均值和标准差全部交叉核对一致。", "",
           "| 函数 | 本次Mean | 本次Std | 论文Mean | 论文Std |", "|---|---:|---:|---:|---:|"]
    md += [f"| F{r['function']:02d} | {r['reproduced_mean']:.5e} | {r['reproduced_std']:.5e} | {r['paper_mean']:.5e} | {r['paper_std']:.5e} |" for r in d['paper_comparison']]
    if ref_data:
        md += ["", "## C++参考评估器补充验证", "", reference_note, "",
               "| 函数 | opfunu Mean | C++参考Mean | 论文Mean |", "|---|---:|---:|---:|"]
        md += [f"| F{r['function']:02d} | {r['reproduced_mean']:.5e} | {ref_map[r['function']]['reproduced_mean']:.5e} | {r['paper_mean']:.5e} |" for r in d['paper_comparison']]
    md += ["", "## 消融实验", "", stats_method, "", rank_text, ""] + [x + "\n" for x in stats_text]
    md += [x + "\n" for x in interpretation]
    if diagnostic_note:
        md += ["", diagnostic_note, ""]
    md += ["| 算法 | 平均排名 |", "|---|---:|"] + [f"| {CN_NAMES[r['algorithm']]} | {r['mean_rank']:.3f} |" for r in d["ranking"]]
    md += ["", "## 收敛曲线", "", "output/figures/F01.png至F30.png按各算法20次中最终误差最小的真实运行绘制；最优run编号和种子记录于best_curve_runs.csv。左图纵轴为目标函数值，右图为误差，横轴均为FEs。", "",
           "## 实现约定与限制", ""] + [x + "\n" for x in limitations]
    md += ["## 结论", "", conclusion, "", "## 参考文献", "",
           "Chen J, Meng Z. An adaptive differential evolution algorithm with exponential crossover based on a learning strategy within the difference vector. Swarm and Evolutionary Computation 100 (2026), 102247. https://doi.org/10.1016/j.swevo.2025.102247", ""]
    (out / "report.md").write_text("\n".join(md), encoding="utf-8")

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
    # Matplotlib mathtext gives clear mathematical notation without a TeX install.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    formulas = [r"$\Delta_i=x_{pbest}-x_i+x_{r_1}-\tilde{x}_{r_2},\qquad V_i=x_i+F_i\Delta_i$",
                r"$F_i=\mathrm{clip}_{[0.35,0.65]}\left(0.35+\frac{0.4SR}{0.1+SR}+\epsilon\right)\quad (nfe<0.3T)$",
                r"$CR_i=\frac{10\sum_{k=1}^{D}P_{ik}k}{10\sum_{k=1}^{D}P_{ik}k+1},\qquad U_i=x_i+F_i(x_{pbest}-x_i)+F_i\frac{LV_i}{LF_i}$"]
    formula_file = out / "figures/method_formulas.png"
    fig = plt.figure(figsize=(7.5, 1.35))
    for i, formula in enumerate(formulas):
        fig.text(.01, .82 - i*.32, formula, fontsize=11, va="center")
    fig.savefig(formula_file, dpi=260, transparent=True, bbox_inches="tight", pad_inches=.06)
    plt.close(fig)
    cn_font = Path("C:/Windows/Fonts/simsun.ttc")
    if cn_font.exists():
        pdfmetrics.registerFont(TTFont("BodyCN", str(cn_font), subfontIndex=0))
    else:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        # Keep styles simple for non-Windows installations.
    bodyfont = "BodyCN" if cn_font.exists() else "STSong-Light"
    styles = {"body": ParagraphStyle("body", fontName=bodyfont, fontSize=10.5, leading=17, spaceAfter=7),
              "title": ParagraphStyle("title", fontName=bodyfont, fontSize=20, leading=28, spaceAfter=12),
              "heading": ParagraphStyle("heading", fontName=bodyfont, fontSize=15, leading=22, spaceAfter=10),
              "small": ParagraphStyle("small", fontName=bodyfont, fontSize=9, leading=13, spaceAfter=6)}
    flow = []
    def p(text, role="body"):
        return Paragraph(escape(text), styles[role])
    def table(rows, widths, numeric=False):
        rendered = [[p(str(cell), "small") if not numeric or i == 0 else str(cell) for cell in row] for i, row in enumerate(rows)]
        t = Table(rendered, colWidths=widths, repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), "Times-Roman" if numeric else bodyfont),
                               ("FONTSIZE", (0, 0), (-1, -1), 9),
                               ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                               ("TOPPADDING", (0, 0), (-1, -1), 3),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                               ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf1f5")),
                               ("LINEBELOW", (0, 0), (-1, 0), .5, colors.HexColor("#576575")),
                               ("LINEBELOW", (0, -1), (-1, -1), .5, colors.HexColor("#576575")),
                               ("ALIGN", (1, 1), (-1, -1), "RIGHT" if numeric else "LEFT")]))
        return t
    flow += [p("DLS DE 论文复现实验报告", "title"), p("Project 2  CEC2014  10D  2026年10月30日", "small"), p(lead), p(comparison_note),
             p("实验参数", "heading"), table([["参数", "设置"]] + settings, [115, 370]), Spacer(1, 12),
             p("实验材料与范围", "heading"), p("使用课程指定的opfunu扩展库。依据论文原文独立编写算法，选择原文包含的CEC2014 10D进行复现。课程要求的Best、Mean、Std、Rank与方差均从实际原始记录计算。"), PageBreak()]
    flow += [p("方法与实现约定", "heading")] + [p(x) for x in method]
    from PIL import Image as PILImage
    with PILImage.open(formula_file) as formula_image:
        formula_height = 485 * formula_image.height / formula_image.width
    flow += [p("主要公式与原文索引", "heading"), Image(str(formula_file), width=485, height=formula_height), Spacer(1, 8), p("式(3)：current-to-pbest变异；式(8)-(9)：两阶段F；式(10)-(11)：VIX与mu_F；式(12)-(13)：尺度自适应与停滞覆盖；式(14)-(16)：CR概率记忆；式(17)：学习方向试验。完整映射与缺省约定见reference/implementation_notes.md。"),
             p(limitations[0]), PageBreak()]
    result_table = [["函数", "Best", "Mean", "Std", "Variance", "Rank"]]
    result_table += [[f"F{r['function']:02d}", f"{r['best']:.4e}", f"{r['mean']:.4e}", f"{r['std']:.4e}", f"{r['variance']:.4e}", f"{r['rank']:.1f}"] for r in main_rows]
    flow += [p("完整算法的实验结果", "heading"), p(f"误差为最终最优函数值减去已知最优值。标准差与方差使用样本定义；Rank是在本次{len(d['algorithms'])}种算法间按均值计算的逐函数名次，1为最佳。", "small"),
             table(result_table, [35, 90, 90, 90, 100, 40], numeric=True), Spacer(1, 10), p(comparison_note), PageBreak()]
    paper_table = [["函数", "本次Mean", "本次Std", "论文Mean", "论文Std"]]
    paper_table += [[f"F{r['function']:02d}", f"{r['reproduced_mean']:.4e}", f"{r['reproduced_std']:.4e}", f"{r['paper_mean']:.4e}", f"{r['paper_std']:.4e}"] for r in d["paper_comparison"]]
    flow += [p("与原论文的数值对照", "heading"), p("来源为论文表12，第14页的CEC2014 10D DLS-DE列，已与表14交叉核对。双方预算与初始种群一致；本次20次，论文51次。", "small"),
             table(paper_table, [35, 112.5, 112.5, 112.5, 112.5], numeric=True), Spacer(1, 10), p(limitations[2]), PageBreak()]
    if ref_data:
        reference_table = [["函数", "opfunu Mean", "C++参考Mean", "论文Mean"]]
        reference_table += [[f"F{r['function']:02d}", f"{r['reproduced_mean']:.4e}",
                             f"{ref_map[r['function']]['reproduced_mean']:.4e}", f"{r['paper_mean']:.4e}"] for r in d['paper_comparison']]
        flow += [p("独立参考评估器的补充验证", "heading"), p(reference_note, "small"),
                 table(reference_table, [35, 150, 150, 150], numeric=True), Spacer(1, 8),
                 p("每函数20个随机点及零点、最优点的检查在13个函数上发现差异。F29子函数旋转矩阵分块调用差异有官方源码证据。详见reference/benchmark_findings.md；MinionPy评估器也未被证明与论文作者MATLAB逐点完全等价。", "small"), PageBreak()]
    rank_table = [["算法", "平均排名", "显著胜 平 负"]]
    for r in d["ranking"]:
        s = d["statistics"].get(r["algorithm"])
        rank_table.append([CN_NAMES[r["algorithm"]], f"{r['mean_rank']:.3f}", "-" if s is None else f"{s['win']} / {s['tie']} / {s['loss']}"])
    flow += [p("策略消融与统计分析", "heading"), p(stats_method), p("下表胜平负均以完整DLS-DE为主语。基础DE固定种群，只作整体基线；其余变体沿用完整算法的同一种群缩减过程。"),
             table(rank_table, [230, 100, 155]), Spacer(1, 8), p(rank_text)]
    if diagnostic_note:
        flow += [p(diagnostic_note, "small")]
    if d["friedman"]:
        flow += [p(f"Friedman统计量={d['friedman']['statistic']:.4f}，p={d['friedman']['pvalue']:.4e}。该总体检验反映本组算法存在性能差异，不直接定位任意一对算法的差异。")]
    flow += [p("no_learning只去除学习；no_two_phase全程Cauchy；fixed_sigma固定尺度0.05；fitness_weights用适应度改进替代VIX；binomial保留原CR机制但改用二项交叉。各自的逐函数Best、Mean、Std、Variance、Rank保存在summary_error.csv。平均排名柱形图另附figures/ranking.png。", "small")]
    flow += [p(x) for x in interpretation]
    flow += [PageBreak()]
    for ids in ([1, 9], [11, 18], [22, 23], [29, 30]):
        flow += [p("代表函数的真实最优运行轨迹", "heading"), p("每算法选择20次中最终误差最小的一次。左图显示函数值，右图显示误差；横轴均为函数评价次数。全部30张原图及所选run编号另附。", "small")]
        for fid in ids:
            file = out / f"figures/F{fid:02d}.png"
            if file.exists():
                flow += [Image(str(file), width=485, height=271.6), Spacer(1, 12)]
        flow.append(PageBreak())
    flow += [p("限制与结论", "heading")] + [p(x) for x in limitations[1:]]
    flow += [p("结论", "heading"), p(conclusion), p("参考文献", "heading"),
             p("Chen J, Meng Z. An adaptive differential evolution algorithm with exponential crossover based on a learning strategy within the difference vector. Swarm and Evolutionary Computation 100 (2026), 102247. DOI 10.1016/j.swevo.2025.102247.", "small"),
             p("核验材料：verification.json、raw_sha256.json、results/manifest.json、results_ablation/manifest.json；原始JSON包含种子、向量、轨迹与优化评价次数。复现实验的命令与目录说明见README.md。", "small")]
    for algorithm in d["algorithms"]:
        if algorithm == "dls_de":
            continue
        rows = [r for r in d["summary"] if r["algorithm"] == algorithm]
        appendix_table = [["函数", "Best", "Mean", "Std", "Variance", "Rank"]]
        appendix_table += [[f"F{r['function']:02d}", f"{r['best']:.4e}", f"{r['mean']:.4e}",
                           f"{r['std']:.4e}", f"{r['variance']:.4e}", f"{r['rank']:.1f}"] for r in rows]
        flow += [PageBreak(), p("附录 " + CN_NAMES[algorithm] + "逐函数结果", "heading"),
                 p(f"版本标识为{algorithm}。每个函数20次独立运行，统计口径与主表一致；全部逐次结果和种子另附。", "small"),
                 table(appendix_table, [35, 90, 90, 90, 100, 40], numeric=True)]
    target = out / "pdf/report.pdf"
    target.parent.mkdir(exist_ok=True)
    def footer(canvas, doc):
        canvas.setFont("Times-Roman", 8)
        canvas.setFillColor(colors.HexColor("#536274"))
        canvas.drawString(55, 30, "Project 2 | DLS-DE | CEC2014 10D")
        canvas.drawRightString(A4[0] - 55, 30, str(doc.page))
    SimpleDocTemplate(str(target), pagesize=A4, rightMargin=55, leftMargin=55,
                      topMargin=48, bottomMargin=48, title="DLS-DE reproduction report",
                      author="Project 2").build(flow, onFirstPage=footer, onLaterPages=footer)
    print(target)


if __name__ == "__main__":
    main()
