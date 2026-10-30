#!/usr/bin/env python3
"""Plot the output of step_iv.py: IV curve and current settling per step

    python3 plot_step_iv.py iv_u300_20261028_213012.json [-o iv.png] [--compare older.json ...]
"""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('data', type=Path, help='JSON written by step_iv.py')
p.add_argument('-o', '--output', type=Path, help='output prefix (default: input without .json)')
p.add_argument('--unit', choices=['nA', 'uA'], default='nA', help='current unit on the axes')
p.add_argument('--logy', action='store_true', help='log scale for current (positive currents only)')
p.add_argument('--compare', type=Path, nargs='*', default=[], help='more step_iv.py JSON files to overlay on the IV')
args = p.parse_args()
scale = {'nA': 1e9, 'uA': 1e6}[args.unit]

d = json.loads(args.data.read_text())
steps = d['steps']
prefix = args.output or args.data.with_suffix('')
fig_iv, ax_iv = plt.subplots(figsize=(7, 5))

for f, color in [(args.data, 'C0')] + [(c, f'C{i + 2}') for i, c in enumerate(args.compare)]:
    s = json.loads(Path(f).read_text())['steps']
    ax_iv.errorbar([x['v_mean'] for x in s], [x['i_mean'] * scale for x in s],
                   yerr=[x['i_std'] * scale for x in s], fmt='o-', color=color, capsize=3,
                   label=Path(f).stem)
    for x in s:
        if x.get('interrupted'):
            ax_iv.annotate('aborted', (x['v_mean'], x['i_mean'] * scale), fontsize=8, color='C3')
        elif not x['stable']:
            ax_iv.annotate('not stable', (x['v_mean'], x['i_mean'] * scale), fontsize=8, color='C3')
ax_iv.set_xlabel('terminal voltage [V]')
ax_iv.set_ylabel(f'current [{args.unit}]')
ax_iv.set_title(f'{d["channel"]} IV, limit {d["args"]["ilimit"]:.0e} A')
if args.logy:
    ax_iv.set_yscale('log')
    ax_iv.set_ylim(bottom=0.1 * scale / 1e9)
ax_iv.grid(alpha=.3, which='both')
ax_iv.legend(fontsize=8)
fig_iv.tight_layout()
fig_iv.savefig(f'{prefix}-iv.png', dpi=130)
print(f'wrote {prefix}-iv.png')

fig_t, ax_t = plt.subplots(figsize=(8, 5))

t0 = steps[0]['history'][0]['t'] if steps[0]['history'] else steps[0]['samples'][0]['t']
colors = plt.cm.viridis([k / max(1, len(steps) - 1) * 0.9 for k in range(len(steps))])
for k, x in enumerate(steps):
    c = colors[k]
    h, s = x['history'], x['samples']
    ax_t.plot([r['t'] - t0 for r in h], [r['i'] * scale for r in h], '.', ms=3, color=c, alpha=.5)
    ax_t.plot([r['t'] - t0 for r in s], [r['i'] * scale for r in s], '.', ms=5, color=c,
              label=f'{x["v_set"]:g} V: {x["i_mean"] * scale:.3f} {args.unit}'
                    + (' (aborted)' if x.get('interrupted') else '' if x['stable'] else ' (not stable)'))
    if h:
        ax_t.axvline(h[-1]['t'] - t0, color=c, ls=':', lw=1)
# robust range, single switch-on spikes would hide everything else
all_i = sorted(r['i'] * scale for x in steps for r in x['history'] + x['samples'])
if len(all_i) > 20:
    lo, hi = all_i[len(all_i) // 100], all_i[-len(all_i) // 100 - 1]
    pad = 0.2 * (hi - lo) or 0.1 * scale / 1e9
    ax_t.set_ylim(lo - pad, hi + pad)
ax_t.set_xlabel('time since first step [s]')
ax_t.set_ylabel(f'current [{args.unit}]')
ax_t.set_title(f'{d["channel"]} settling (faint) and recorded samples (bold), dotted = stable')
ax_t.grid(alpha=.3)
ax_t.legend(fontsize=8)

fig_t.tight_layout()
fig_t.savefig(f'{prefix}-settling.png', dpi=130)
print(f'wrote {prefix}-settling.png')
