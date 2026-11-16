# Reproduction and strategy-transfer audit

Author: 殷明骏

## Current finding

The strongest observed explanation for the predecessor's weak common-protocol
performance is unsuccessful strategy transfer. This does not establish that all
three source reconstructions are exact. Numerical record checks and paper-to-code
fidelity checks answer different questions and must remain separate.

## Evidence by possible cause

| Possible cause | Direct evidence | What it establishes |
| --- | --- | --- |
| Budget or saved-result bookkeeping error | The 7200 common records pass complete matrix, saved-solution, actual-FE and history checks; all methods use the same objective, fixed NP and paired initialization | No detected error in these checked execution properties; not a proof of source-method fidelity |
| Different objective from the paper | A 660-point CEC2014 audit finds discrepancies on F17-F27, F29 and F30; 600 saved reference-evaluator solutions reproduce their recorded values exactly | A confirmed literature-comparison confound; apparent paper gaps on these functions cannot be assigned wholly to algorithm quality |
| DLS-DE reconstruction discrepancy | source/DLSDE_implementation_notes.md maps formulas and Algorithms 4-6; the learning-gate prose and Algorithm 5 disagree, and initialization/repair conventions are not completely specified | A documented, bounded reconstruction with unresolved author-code equivalence; the common fixed-NP control additionally disables native population reduction |
| DSPDE reconstruction discrepancy | Source notes and the local PDF identify a misprinted Eq. 8, undisclosed numeric Linnik parameters and an unresolved Table 7 dimension | Exact paper-table reproduction is unproven; this is the source with the largest outstanding specification uncertainty |
| PEMS-DE reconstruction discrepancy | The retained corrected implementation uses frozen parent generations with immediate archive/success updates; the invalid earlier CEC2017 class-number batch is excluded; 580 corrected native records pass reevaluation | Known earlier execution/numbering issues were corrected, but these checks alone do not certify every source equation or an unavailable author implementation |
| Harmful transfer into PGE-DE | Source potential/elite removal gives 8 full-method wins and 2 losses; in the team backbone, removing the shared potential guide improves 4 functions and worsens none after correction | Source benefit does not survive this defined transfer; the two ablations are different interfaces, not identical operations in different programs |
| Ineffective added complexity | Team two-phase and escape removals show no detected function-level differences after the declared correction | There is no current corrected evidence that these transferred modules improve the predecessor; this does not prove zero effect |
| Wrong choice of all three papers | DLS-DE and PEMS-DE have the two best descriptive ranks in the common five-method comparison | There is no evidence that the whole paper set needs replacing; source strength does not guarantee an extracted module will help another backbone |

## Mechanism correspondence that matters

PEMS-DE combines potential and elite guiding vectors with stage-dependent
mutation, parameter learning and archive/learning operations. The predecessor
transfers only the potential-weighted center and uses fixed CR=0.9; it does not
transfer the complete potential/elite module or its multi-stage context.
Consequently, the source module's favorable ablation cannot be read as a
guarantee for this reduced guide.

DLS-DE's original parameter strategy operates with exponential crossover,
direction learning, an archive and population reduction. The predecessor keeps
the early F rule but fixes the late sampling width and uses another success
weight. Its intervention is explicitly a modification of the source strategy.

DSPDE's escape proposal acts on its own stratified population. The predecessor
uses it to replace ordinary DE trials. The original source comparison favors
escape over its uniform-reset control, while the team removal retains ordinary
DE candidates. These are different alternatives. Their ablation results cannot
be treated as contradictory measurements of one identical effect.

## Consequences for the current revision

1. Preserve the verified common records and original-condition tracks; keep
   benchmark discrepancies explicit instead of merging evaluator results.
2. Do not equate successful result reevaluation with exact source reproduction.
   Retain a formula/pseudocode/implementation mapping and unresolved conventions
   for each source, especially DSPDE.
3. Base the revised combination on destination-backbone evidence. The frozen
   APE-DE revision and its independent sample test a simpler transfer design;
   they do not retroactively validate the source reconstructions.
4. Do not replace papers solely to obtain weaker controls or claim that the
   revised algorithm dominates all methods. Report complete independent wins,
   losses, descriptive ranks and each detected component contribution.

The APE-DE independent validation completed with all 4,800 records verified;
it ranked second, behind DLS-DE. The subsequent DC-DE confirmation runs under
its separately frozen contract in ../improvement_v2/. This audit changes no
source hashes, parameters, seed plans or statistical families.
