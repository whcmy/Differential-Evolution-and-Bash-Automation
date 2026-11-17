# Development toward first overall rank

Author: 殷明骏

The requested success criterion is the lowest mean within-function rank over
all 30 CEC2014 functions at dimension 10, fixed NP 100, exactly 100000 objective
evaluations including initialization and all auxiliary proposals, and 20 runs
per function. Final comparison retains DE, DSPDE, fixed-NP DLS-DE and PEMS-DE,
with the original PGE-DE retained as a predecessor control. A first descriptive
rank is distinct from statistically significant superiority to every control.

The first APE-DE revision and its independent experiment remain frozen and
continue unchanged. They may inform a later design only when labelled as
development evidence for that design. No confirmation sample is reused to
confirm a subsequently modified algorithm.

## Bounded candidate set

The DLS-DE reconstruction is the strongest current common-protocol baseline.
Rather than discarding its functioning interfaces, two separate additions are
tested, retaining its fixed-NP archive, parameter control, exponential crossover
and direction-learning conventions where applicable.

1. DLC: add PEMS-inspired complementary learning for a strictly stagnant
   non-elite individual. At most one extra objective call per generation is
   charged to the same budget. The best fifth is protected; the historical
   best is stored separately. The guide blends a sampled elite and the
   historical best with the PEMS elite schedule; the complementary point may
   replace the stagnant member even if worse. This is an explicit guarded
   transfer, not exact PEMS-DE CLS identity.
2. DUAL: combine DLS exponential crossover with a PEMS-inspired adaptive
   binomial crossover branch. Successful branch rates adapt the mixture,
   bounded to [0.1,0.9]; successful realized crossover fractions update the
   binomial CR mean. Direction-learning override trials do not train the
   crossover selector. Each target still receives one evaluated trial.

Both candidates are general optimizers: no benchmark ID, optimum, shift vector,
reference result, per-function setting, ensemble best-of-several full budgets,
or uncharged objective call is available inside the optimizer.

Development uses all 30 functions and the first five historical development
seeds (master 20261109). Complete older records provide matched controls.
All candidate outcomes are retained. If either candidate merits confirmation,
its source/settings and the complete test families are locked before a fresh
20-run sample begins, using a new master seed (20261118 or a later explicitly
recorded unused seed). No final first-place claim is made from development.
