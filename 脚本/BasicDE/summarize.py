"""Validate all run records and build the BasicDE tables and Chinese report."""
import argparse
from collections import Counter
import csv
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import statistics


def statistics_row(values):
    """Across independent runs: sample variance/std (denominator n-1)."""
    return dict(best=min(values), median=statistics.median(values),
                mean=statistics.mean(values), worst=max(values),
                std=statistics.stdev(values) if len(values) > 1 else None,
                variance=statistics.variance(values) if len(values) > 1 else None)


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows, columns):
    header = "| " + " | ".join(label for _, label in columns) + " |"
    lines = [header, "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        cells = []
        for key, _ in columns:
            value = row[key]
            cells.append(f"{value:.6e}" if isinstance(value, float) else str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def load_records(folder):
    manifest = json.loads((folder / "manifest.json").read_text())
    config = manifest["config"]
    if "completed_utc" not in manifest:
        raise ValueError("experiment is not marked complete")
    expected = {(fid, run) for fid in config["functions"] for run in range(1, config["runs"] + 1)}
    rows = [json.loads(p.read_text()) for p in sorted(folder.glob("F*_run*.json"))]
    counts = Counter((r["function"], r["run"]) for r in rows)
    if set(counts) != expected or any(count != 1 for count in counts.values()):
        raise ValueError("missing, duplicate, or extra run records")
    for row in rows:
        if row["nfev"] != config["max_fes"]:
            raise ValueError("incorrect FE budget")
        if not all(math.isfinite(row[key]) for key in ("best_fitness", "error", "optimum")):
            raise ValueError("non-finite result")
        if not math.isclose(row["error"], abs(row["best_fitness"] - row["optimum"]), abs_tol=1e-12):
            raise ValueError("incorrect error")
        if len(row["best_x"]) != config["dimension"] or not all(-100 <= x <= 100 for x in row["best_x"]):
            raise ValueError("invalid decision vector")
        history = row["history"]
        if history[0][0] != config["population_size"] or history[-1][0] != config["max_fes"]:
            raise ValueError("history does not cover the experiment")
        if history[-1][1] != row["best_fitness"]:
            raise ValueError("history does not match final fitness")
        for (fa, va), (fb, vb) in zip(history, history[1:]):
            if fb <= fa or vb > va:
                raise ValueError("invalid convergence history")
    return manifest, sorted(rows, key=lambda r: (r["function"], r["run"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path(__file__).parent / "results")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "output")
    args = parser.parse_args()
    manifest, raw = load_records(args.results)
    config = manifest["config"]
    if config["runs"] < 2:
        parser.error("at least two independent runs are required for sample variance")
    args.output.mkdir(parents=True, exist_ok=True)
    error_rows, fitness_rows = [], []
    for fid in config["functions"]:
        group = [row for row in raw if row["function"] == fid]
        common = dict(function=f"F{fid:02d}", name=group[0]["name"],
                      optimum=group[0]["optimum"], runs=len(group))
        for key, output in (("error", error_rows), ("best_fitness", fitness_rows)):
            output.append(dict(common, **statistics_row([r[key] for r in group])))
    write_csv(args.output / "summary_error.csv", error_rows)
    write_csv(args.output / "summary_fitness.csv", fitness_rows)
    raw_export = [{key: row[key] for key in
                   ("function", "run", "seed", "nfev", "optimum", "best_fitness", "error", "seconds")}
                  for row in raw]
    write_csv(args.output / "runs.csv", raw_export)
    paper = list(csv.DictReader((Path(__file__).parent / "reference/de_vcr_table20.csv").open()))
    comparisons = []
    for row in error_rows:
        p = paper[int(row["function"][1:]) - 1]
        comparisons.append(dict(function=row["function"], basic_de_mean=row["mean"],
                                 basic_de_std=row["std"],
                                 paper_de_vcr_mean=float(p["paper_mean"]),
                                 paper_de_vcr_std=float(p["paper_std"])))
    write_csv(args.output / "paper_context.csv", comparisons)
    columns = [("function", "Function"), ("best", "Best"), ("median", "Median"),
               ("mean", "Mean"), ("worst", "Worst"), ("std", "Std"), ("variance", "Variance")]
    near = [r["function"] for r in error_rows if r["worst"] <= 1e-8]
    # Analysis is tied to measured records, never to a predetermined conclusion.
    largest = sorted(error_rows, key=lambda r: r["mean"], reverse=True)[:3]
    unstable = sorted(error_rows, key=lambda r: r["std"], reverse=True)[:3]
    perfect_runs = sum(row["error"] <= 1e-8 for row in raw)
    total_fes = sum(row["nfev"] for row in raw)
    elapsed = (datetime.fromisoformat(manifest["completed_utc"])
               - datetime.fromisoformat(manifest["started_utc"])).total_seconds()
    params = [dict(parameter=k, value=v) for k, v in [
        ("算法", config["algorithm"]), ("测试集", "opfunu CEC2014 F1-F30"),
        ("维度 D", config["dimension"]), ("边界", "[-100, 100]"),
        ("种群 NP", config["population_size"]), ("缩放因子 F", config["f"]),
        ("交叉率 CR", config["cr"]), ("每次运行评价预算", config["max_fes"]),
        ("每个函数独立运行次数", config["runs"]), ("基础随机种子", config["seed"]),
        ("更新方式", "整代更新；严格贪婪选择"), ("边界处理", "逐坐标截断（clip）"),
        ("离散程度", "样本标准差与样本方差，ddof=1")]]
    analysis = [
        f"本次共完成 {len(raw)} 次独立运行，累计 {total_fes:,} 次目标函数评价。"
        f"其中 {perfect_runs} 次最终绝对误差不超过 1e-8；所有运行均达到该阈值的函数为"
        f" {', '.join(near) if near else '无'}。阈值仅用于结果解读，没有触发提前停止。",
        "均值误差最大的三个函数为 " + "、".join(f"{r['function']} ({r['mean']:.6e})" for r in largest)
        + "。不同函数的尺度和结构不同，这一顺序仅描述本实验的数值大小，不作为跨函数难度排名。",
        "运行间标准差最大的三个函数为 " + "、".join(f"{r['function']} ({r['std']:.6e})" for r in unstable)
        + "。应结合中位数、最差值以及原始运行结果判断是否存在少量较差运行；单次最优结果不能代表稳定性。",
        "基础 DE 依靠种群差分产生搜索方向。种群在局部区域聚集后，差分步长可能缩小，"
        "从而限制后续探索。这能为部分函数残留误差提供算法层面的解释，但本实验没有记录种群多样性，"
        "不能据此确认某个具体函数的失败机制。",
        "F1-F3 属于单峰组，F4-F16 属于简单多峰组，F17-F22 为混合函数，F23-F30 为组合函数。"
        "基础算法在这些结构上的表现差异可作为 AdaptiveDE 的对照基线。不同组内部仍有明显差异，"
        "不应把一个函数的表现推广到整组。",
    ]
    limitations = [
        "文件夹中没有独立的 BasicDE 基础 DE 数值参考表，也没有研究报告模板。"
        "测试要求中的结果示例标为 C-17，不能替代明确指定的 CEC2014。"
        "基础 DE 的文献数值接近程度尚未验证。",
        "参数 F=0.5、CR=0.9、NP=100 取自 Test condition.pdf 第1页的 DE 参数示例表；"
        "10D 和 20 次重复取自研究要求。评价预算使用所附 DE-VCR 论文第4节的 10000D，"
        "在 10D 下为 100000，且包含初始化。边界截断属于本实现明确选择的约定。",
        "表中的论文背景对照来自 Zhao 等（2026）DE-VCR 论文表20（第18页），"
        "比较对象是改进 DE-VCR，其实验为51次重复、MATLAB环境；本实验为基础 DE、20次重复、Python/opfunu。"
        "两者即使预算、测试集和维度一致，也不构成同一算法的复现验证。论文只给出汇总值，"
        "因此没有对它执行显著性检验。",
        "实际调用的是未修改的 opfunu 1.0.4。最优点检查和最终解重算只能校验调用与记录的一致性，"
        "不能证明该库与 CEC 官方 C/MATLAB 实现逐点等价。涉及文献数值差异时，"
        "还需要核对函数实现、旋转/置换顺序、边界规则和停止条件，不能全部归因于算法。",
        "当前环境为 Python " + config["python"] + "、NumPy " + config["versions"]["numpy"]
        + "、opfunu " + config["versions"]["opfunu"] + "。opfunu 1.0.4 的包元数据声明 Python<3.12；"
        "本机在3.12中忽略该安装限制后通过本项目测试并完成实验。新环境建议使用 Python3.11；"
        "要逐值复现已交付结果，请匹配 manifest.json 记录的环境。",
    ]
    conclusion = (f"已实现基础 DE/rand/1/bin 并按研究规定完成 {len(config['functions'])} 个 CEC2014 "
                  f"{config['dimension']}D 函数、每函数 {config['runs']} 次重复实验，给出完整统计量和原始记录。"
                  "实验表明基础 DE 能在部分函数上获得较低误差，但其精度与稳定性依赖函数结构。"
                  "该实现可直接作为后续改进算法的统一预算基线；与文献接近程度需以可比的基础 DE 参考值另行核实。")
    report = ["# BasicDE：基础差分进化算法研究报告", "",
              "实验日期：2026-10-26。结果、随机种子与收敛记录均保存在交付目录中，可重新生成统计表。", "",
              "## 1. 参数设置", "", markdown_table(params, [("parameter", "项目"), ("value", "设置")]), "",
              "## 2. 算法与评价预算", "",
              "均匀随机初始化种群。对每个目标个体 i，从上一代中抽取互不相同且均不等于 i 的 r1、r2、r3。", "",
              "$$v_i = x_{r1} + F(x_{r2}-x_{r3})$$", "",
              "变异向量先截断到搜索边界；二项交叉以概率 CR 采用变异分量，并强制至少一个坐标来自变异向量。"
              "仅当试验个体目标值严格小于父代时替换。整代供体都取自旧种群，不使用代内即时更新。", "",
              "初始化的 NP 次评价计入总预算。最后不足一代时只评价剩余个体，因此每次运行恰好消耗 max_fes 次评价。"
              "当前配置为初始化100次加999个完整更新代，共100000次；不把100000解释为迭代代数。", "",
              "随机数使用 NumPy default_rng（PCG64）；每个函数和运行的种子由 SeedSequence([基础种子, 函数编号, 运行编号]) 派生，"
              "因此调度顺序与并行进程数不会改变该次运行的随机流。", "",
              "## 3. 统计口径", "",
              "每次运行保存预算内发现的最小目标值 b。已知最优值为 f*=100×函数编号；主表统计绝对误差 e=|b-f*|。"
              "因此 Best/Worst 是20次运行各自最终最优误差的最小/最大值，而非种群中最好/最差个体。", "",
              "$$\\bar e=\\frac{1}{n}\\sum_{r=1}^{n}e_r,\\quad s^2=\\frac{1}{n-1}\\sum_{r=1}^{n}(e_r-\\bar e)^2,\\quad s=\\sqrt{s^2}$$", "",
              "中位数为排序后第10和第11个误差的平均值。标准差与方差均按样本口径（ddof=1）计算。"
              "原始目标值另存 summary_fitness.csv；原始逐次结果保存在 runs.csv 和 results/*.json。", "",
              "## 4. 实验结果：绝对误差", "", markdown_table(error_rows, columns), "",
              "## 5. 结果分析", ""]
    for paragraph in analysis:
        report.extend([paragraph, ""])
    report += ["## 6. 论文背景对照与可比性", "",
               "下表仅作背景对照，右侧为改进算法 DE-VCR 的文献结果，不是基础 DE 的目标值。", "",
               markdown_table(comparisons, [("function", "Function"), ("basic_de_mean", "本实验 Mean"),
                                            ("basic_de_std", "本实验 Std"), ("paper_de_vcr_mean", "论文 DE-VCR Mean"),
                                            ("paper_de_vcr_std", "论文 DE-VCR Std")]), ""]
    for paragraph in limitations:
        report.extend([paragraph, ""])
    report += ["## 7. 验证与复现", "",
               "test_basic_de.py 检查供体索引、评价次数、边界、强制交叉、收敛记录单调性与种子复现，"
               "并检查全部30个测试函数声明的最优点及调用计数。verify_results.py 重新计算全部保存解的函数值，"
               "核对完整性、统计结果、日志与代码哈希。验证结果见 verification.json。", "",
               "完整运行、断点续算、生成报告的命令见 README.md。原始JSON同时包含最优解向量与按评价次数记录的收敛轨迹。"
               f"manifest 记录的开始至结束跨度为 {elapsed:.1f} 秒（包含中断间隔），不能视为纯计算时间。", "",
               "## 8. 结论", "", conclusion, "",
               "## 参考材料", "",
               "1. 研究 Study Introduction.pdf，Study description 1 与 Report Requirement。",
               "2. 研究 Test condition.pdf，第1-2页（测试集、参数示例、统计字段）。",
               "3. Zhao L, Sun L, Song Z, Zhang Q, Matsveichuk N, Sotskov Y. Differential evolution with a variance contribution ratio-based "
               "diversity enhancement mechanism for numerical optimization. Swarm and Evolutionary Computation 104 (2026), 102359. "
               "https://doi.org/10.1016/j.swevo.2026.102359 。第2节、实验设置与表20。",
               "4. opfunu 1.0.4：https://pypi.org/pypi/opfunu/1.0.4/json 。", ""]
    (args.output / "report.md").write_text("\n".join(report), encoding="utf-8")
    payload = dict(parameters=params, errors=error_rows, fitness=fitness_rows,
                   comparison=comparisons, analysis=analysis, limitations=limitations,
                   conclusion=conclusion, config=config,
                   count=len(raw), total_fes=total_fes, elapsed_seconds=elapsed)
    (args.output / "report_data.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(args.results.glob("F*_run*.json"))}
    (args.output / "raw_sha256.json").write_text(json.dumps(hashes, indent=2))
    print(f"Validated {len(raw)} runs; wrote tables and report to {args.output}")


if __name__ == "__main__":
    main()
