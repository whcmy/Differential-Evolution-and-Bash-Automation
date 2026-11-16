"""Render the already summarized report as a six-page Chinese PDF (ReportLab)."""
import argparse
from html import escape
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak)


def main():
    root = Path(__file__).parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=root / "output/report_data.json")
    parser.add_argument("--output", type=Path, default=root / "output/pdf/report.pdf")
    parser.add_argument("--font", type=Path, help="Optional Chinese TrueType font (TTF or TTC)")
    args = parser.parse_args()
    data = json.loads(args.input.read_text())
    font_path = args.font or Path("/usr/share/fonts/truetype/arphic/uming.ttc")
    if font_path.exists():
        pdfmetrics.registerFont(TTFont("ReportCJK", str(font_path), subfontIndex=0))
        body_font = "ReportCJK"
    else:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        body_font = "STSong-Light"
    latin_font, latin_bold, math_font = "Helvetica", "Helvetica-Bold", "Times-Roman"
    font_root = Path("/usr/share/fonts/truetype/dejavu")
    if (font_root / "DejaVuSerif.ttf").exists():
        for name, filename in (("ReportLatin", "DejaVuSans.ttf"),
                               ("ReportLatinBold", "DejaVuSans-Bold.ttf"),
                               ("ReportMath", "DejaVuSerif.ttf")):
            pdfmetrics.registerFont(TTFont(name, str(font_root / filename)))
        latin_font, latin_bold, math_font = "ReportLatin", "ReportLatinBold", "ReportMath"
    body = ParagraphStyle("Body", fontName=body_font, fontSize=10.2,
                          leading=16, spaceAfter=9, wordWrap="CJK", textColor=colors.HexColor("#243142"))
    heading = ParagraphStyle("Heading", parent=body, fontSize=16, leading=22,
                             spaceAfter=15, textColor=colors.HexColor("#143B59"))
    small = ParagraphStyle("Small", parent=body, fontSize=9, leading=13, spaceAfter=7)
    formula = ParagraphStyle("Formula", parent=body, fontName=math_font,
                             fontSize=12, leading=19, alignment=TA_CENTER, spaceAfter=11)
    story = []

    def p(text, style=body):
        story.append(Paragraph(escape(text), style))

    def h(text):
        p(text, heading)

    def numeric_table(rows, columns, widths):
        values = [[label for key, label in columns]]
        for row in rows:
            values.append([f"{row[key]:.4e}" if isinstance(row[key], float) else str(row[key])
                           for key, label in columns])
        table = Table(values, colWidths=widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), latin_font),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("LEADING", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (-1, 0), latin_bold),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E7EFF5")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#143B59")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FA")]),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#7291A6")),
            ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#7291A6")),
        ]))
        story.append(table)
        story.append(Spacer(1, 10))

    h("Project1：基础差分进化算法实验报告")
    p("CEC2014 / 10维 / 30个函数 / 每个函数20次独立运行", body)
    p("实验日期：2026-10-26。逐次结果、随机种子与收敛记录随报告保存，可重新生成统计表。", small)
    p("1. 参数与算法", heading)
    param_table = Table([[Paragraph(escape(str(r["parameter"])), small),
                          Paragraph(escape(str(r["value"])), small)] for r in data["parameters"]],
                        colWidths=[173, 338], hAlign="LEFT")
    param_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#F0F4F8"), colors.white]),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    story.append(param_table)
    story.append(Spacer(1, 12))
    p("种群均匀初始化。r1、r2、r3 互不相同，且都不等于目标个体 i；供体均来自上一代。")
    story.append(Paragraph("v<sub>i</sub> = x<sub>r1</sub> + F (x<sub>r2</sub> - x<sub>r3</sub>)", formula))
    p("变异后逐坐标截断边界；二项交叉强制至少一个坐标来自变异向量。试验个体仅在严格更优时替换父代。"
      "初始化100次评价加999个更新代，恰好100000次评价；预算包含初始化，不采用提前停止。")
    story.append(PageBreak())

    h("2. 主要结果：最终绝对误差")
    p("每次运行记录预算内最小目标值 b，统计 e=|b-f*|，其中 f*=100×函数编号。"
      "Best、Median、Mean、Worst 均跨20次独立运行计算；Std 和 Variance 为样本口径（分母19）。", small)
    story.append(Paragraph("mean = sum(e<sub>r</sub>)/20; &nbsp; variance = sum((e<sub>r</sub> - mean)<super>2</super>)/19; &nbsp; std = sqrt(variance)", formula))
    columns = [("function", "F"), ("best", "Best"), ("median", "Median"), ("mean", "Mean"),
               ("worst", "Worst"), ("std", "Std"), ("variance", "Variance")]
    numeric_table(data["errors"], columns, [30] + [80.16] * 6)
    p("表格显示5位有效数字。完整精度见 summary_error.csv；所有逐次结果见 runs.csv 和 results/*.json。", small)
    story.append(PageBreak())

    h("3. 补充结果：原始目标值")
    p("本表统计各次运行的最小目标值 b。它保留函数偏置，便于核对原始输出。"
      "解释优化精度时，应以第2页的误差为准。", small)
    numeric_table(data["fitness"], columns, [30] + [80.16] * 6)
    p("函数最优值依次为100、200、…、3000。原始目标值的方差与误差方差在本实验中相同；"
      "均值和位置统计量则包含相应偏置。完整精度见 summary_fitness.csv。", small)
    story.append(PageBreak())

    h("4. 结果分析与复现检查")
    for paragraph in data["analysis"]:
        p(paragraph)
    p("完整性检查", heading)
    p("实验共600次、累计60000000次评价。每次运行保存种子、评价次数、最优向量和按评价次数采样的收敛轨迹。"
      "验证脚本对全部600个最终向量重新调用 opfunu，核对日志、代码哈希、原始文件哈希与汇总表。")
    p("随机数使用 NumPy PCG64。种子由 SeedSequence([20261026, 函数编号, 运行编号]) 派生，"
      "进程调度顺序不改变每次运行的随机流。断点续算仅补齐缺失记录，并要求配置、代码与环境记录一致。")
    p("操作命令与目录说明见 README.md；机器可读的审计结论见 output/verification.json。"
      "所有原始数据随交付目录保留，可重新生成报告。")
    story.append(PageBreak())

    h("5. 论文背景对照：DE-VCR")
    p("来源：Zhao 等，2026，表20第18页，“Our algorithm”列，CEC2014 10D。"
      "论文列是改进算法 DE-VCR（51次重复），本实验列是基础 DE（20次重复）；"
      "两列均为 Mean / Std。此表不作为基础 DE 复现成功的判据。", small)
    comparison_columns = [("function", "F"), ("basic_de_mean", "DE Mean"), ("basic_de_std", "DE Std"),
                          ("paper_de_vcr_mean", "DE-VCR Mean"), ("paper_de_vcr_std", "DE-VCR Std")]
    numeric_table(data["comparison"], comparison_columns, [35, 119, 119, 119, 119])
    p("相同维度和评价预算不能消除算法、函数实现、边界处理与重复次数的差异。"
      "没有文献逐次数据，未执行跨论文显著性检验。", small)
    story.append(PageBreak())

    h("6. 可比性说明与结论")
    for paragraph in data["limitations"]:
        p(paragraph, small)
    p("结论", heading)
    p(data["conclusion"])
    p("参考材料", heading)
    p("[1] 课程 Project Introduction.pdf，Project description 1 与报告要求。\n"
      "[2] 课程 Test condition.pdf，第1-2页。", small)
    p("[3] Zhao L, Sun L, Song Z, Zhang Q, Matsveichuk N, Sotskov Y. Differential evolution with a variance contribution ratio-based "
      "diversity enhancement mechanism for numerical optimization. Swarm and Evolutionary Computation 104 (2026), 102359. "
      "DOI: 10.1016/j.swevo.2026.102359. 第2节、实验设置与表20。", small)
    p("[4] opfunu 1.0.4: https://pypi.org/project/opfunu/1.0.4/", small)

    def decorate(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#CFD9E3"))
        canvas.line(42, 39, A4[0] - 42, 39)
        canvas.setFont(latin_font, 8)
        canvas.setFillColor(colors.HexColor("#61758A"))
        canvas.drawString(42, 26, "Project1 | Basic DE | CEC2014 10D | 2026-10-26")
        canvas.drawRightString(A4[0] - 42, 26, str(document.page))
        canvas.restoreState()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(str(args.output), pagesize=A4, leftMargin=42, rightMargin=42,
                                 topMargin=40, bottomMargin=51, title="Project1 基础差分进化算法实验报告",
                                 author="Project1 experiment", allowSplitting=1)
    document.build(story, onFirstPage=decorate, onLaterPages=decorate)
    print(args.output)


if __name__ == "__main__":
    main()
