#!/usr/bin/env python3
"""Step-and-settle IV measurement on one MPOD HV channel

    python3 step_iv.py u303 --voltages 1 2 3            # real run
    python3 step_iv.py u303 --voltages 1 2 3 --dry-run  # read only, print plan

"""

import argparse
import json
import os
import signal
import statistics
import subprocess
import sys
import time

IP = os.environ.get('MPOD_CRATE_IP', '192.168.10.50')
SNMP = os.environ.get('NET_SNMP_INSTALL', '/u1/ldmx/net-snmp-5.9.4/install') + '/bin/snmp'
FAIL_WORDS = ('Failure', 'Kill', 'EmergencyOff', 'Trip', 'BoundsExceeded', 'Inhibit')

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('channel', help='MPOD channel, e.g. u303')
p.add_argument('--voltages', type=float, nargs='+', default=[1, 2, 3], help='set points in V, in order')
p.add_argument('--ilimit', type=float, default=10e-6, help='current limit in A (default 10 uA)')
p.add_argument('--rate', type=float, default=0.5, help='rise and fall rate in V/s (default 0.5)')
p.add_argument('--poll', type=float, default=2.0, help='seconds between readings')
p.add_argument('--window', type=float, default=60.0, help='stability window in s')
p.add_argument('--abs-tol', type=float, default=0.2e-9, help='absolute current drift tolerance in A')
p.add_argument('--rel-tol', type=float, default=0.02, help='relative current drift tolerance')
p.add_argument('--timeout', type=float, default=900.0, help='max seconds to wait for stability per step')
p.add_argument('--v-tol', type=float, default=0.25, help='max |V_meas - V_set| in V')
p.add_argument('--v-flat', type=float, default=0.01, help='max terminal voltage spread over the window in V')
p.add_argument('--samples', type=int, default=5, help='readings recorded once stable (at least 2)')
p.add_argument('--output', default=None, help='JSON output (default iv_<channel>_<time>.json)')
p.add_argument('--vmax', type=float, default=10.0, help='refuse set points above this (default 10 V, hard cap 200 V)')
p.add_argument('--hold', type=float, default=0.0, help='keep the last voltage this many seconds (still watched) before ramping down')
p.add_argument('--dry-run', action='store_true', help='only read, print what would be set')
args = p.parse_args()
ch = args.channel


def run(kind, *a, community='public'):
    cmd = [SNMP + kind, '-v', '2c', '-m', '+WIENER-CRATE-MIB', '-c', community] + list(a)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        raise RuntimeError(f'{" ".join(cmd)}: {r.stderr.strip()}')
    return r.stdout.strip()


def get(param):
    """float value with full precision"""
    return float(run('get', '-Oqv', '-Op', '+.12', IP, f'{param}.{ch}').split()[0])


def get_str(param):
    return run('get', '-Oqv', IP, f'{param}.{ch}')


def status_flags():
    out = run('get', '-Oq', IP, f'outputStatus.{ch}')
    return [w for w in out.split() if '(' in w]


def put(param, value, kind='F'):
    if args.dry_run:
        print(f'  [dry-run] would set {param}.{ch} = {value}')
        return
    run('set', IP, f'{param}.{ch}', kind, str(value), community='guru')


def read():
    return dict(t=time.time(), v=get('outputMeasurementTerminalVoltage'), i=get('outputMeasurementCurrent'))


def check(r):
    bad = [f for f in status_flags() if any(w in f for w in FAIL_WORDS)]
    if bad:
        raise RuntimeError(f'channel status {bad}')
    if abs(r['i']) > 0.8 * args.ilimit:
        raise RuntimeError(f'current {r["i"]:.3e} A above 80% of the {args.ilimit:.1e} A limit')


def shutdown(switched_on):
    if args.dry_run or not switched_on:
        return
    print('ramping to 0 V')
    try:
        put('outputVoltage', 0.0)
        t0 = time.time()
        v_now = get('outputMeasurementTerminalVoltage')
        while time.time() - t0 < abs(v_now) / args.rate + 60:
            r = read()
            print(f'  V={r["v"]:.4f} V  I={r["i"]:.3e} A')
            if abs(r['v']) < 0.2:
                break
            time.sleep(args.poll)
    finally:
        put('outputSwitch', 0, kind='i')
        print('switched off:', get_str('outputSwitch'))


# --- pre-checks (read only)
state = dict(switch=get_str('outputSwitch'), vset=get('outputVoltage'), ilim=get('outputCurrent'),
             rise=get('outputVoltageRiseRate'), vmeas=get('outputMeasurementTerminalVoltage'),
             imeas=get('outputMeasurementCurrent'), status=status_flags())
print(f'{ch} now: {json.dumps(state)}')
if 'on' in state['switch'] or state['vset'] != 0.0:
    sys.exit(f'{ch} is not off at 0 V, refusing to start')
if args.vmax > 200:
    sys.exit('--vmax above 200 V is not allowed by this script')
if max(args.voltages) > args.vmax:
    sys.exit(f'set points above --vmax {args.vmax:g} V are not allowed')
print(f'plan: limit {args.ilimit:.1e} A, rate {args.rate} V/s, steps {args.voltages} V, '
      f'stable over {args.window:.0f} s (drift < max({args.abs_tol:.1e} A, {args.rel_tol:.0%})), '
      f'{args.samples} samples per step, timeout {args.timeout:.0f} s per step')



def on_signal(signum, frame):
    # a closed terminal (SIGHUP) or kill (SIGTERM) must still ramp down
    raise KeyboardInterrupt


signal.signal(signal.SIGHUP, on_signal)
signal.signal(signal.SIGTERM, on_signal)
steps, switched_on, cur = [], False, None
try:
    put('outputCurrent', args.ilimit)
    put('outputVoltageRiseRate', args.rate)
    put('outputVoltageFallRate', args.rate)
    put('outputVoltage', 0.0)
    if args.dry_run:
        for v in args.voltages:
            put('outputVoltage', v)
        print('dry run done, nothing was changed')
        sys.exit(0)
    put('outputSwitch', 1, kind='i')
    switched_on = True
    print('switched on:', get_str('outputSwitch'))

    for vset in args.voltages:
        print(f'--- {vset} V')
        put('outputVoltage', vset)
        t0, hist, stable = time.time(), [], False
        cur = dict(v_set=vset, stable=False, history=hist, samples=[])
        v_tol = max(args.v_tol, 0.02 * vset)
        while time.time() - t0 < args.timeout:
            time.sleep(args.poll)
            r = read()
            check(r)
            hist.append(r)
            win = [h for h in hist if h['t'] >= r['t'] - args.window and abs(h['v'] - vset) <= v_tol]
            msg = f'  {r["t"] - t0:6.0f} s  V={r["v"]:.4f} V  I={r["i"]:.4e} A'
            v_spread = max(h['v'] for h in win) - min(h['v'] for h in win) if win else 0
            if (len(win) >= 6 and win[-1]['t'] - win[0]['t'] >= 0.9 * args.window
                    and v_spread <= args.v_flat):
                half = len(win) // 2
                a = statistics.mean(h['i'] for h in win[:half])
                b = statistics.mean(h['i'] for h in win[half:])
                tol = max(args.abs_tol, args.rel_tol * abs(b))
                msg += f'  drift {b - a:+.2e} A (tol {tol:.1e})'
                if abs(b - a) < tol:
                    stable = True
                    print(msg + '  stable')
                    break
            print(msg)
        if not stable:
            print(f'  not stable after {args.timeout:.0f} s, recording anyway')
        samples = []
        cur['samples'] = samples
        for k in range(args.samples):
            time.sleep(args.poll)
            r = read()
            check(r)
            samples.append(r)
            print(f'  sample {k + 1:2d}/{args.samples}  V={r["v"]:.4f} V  I={r["i"]:.4e} A')
        i = [s['i'] for s in samples]
        v = [s['v'] for s in samples]
        step = dict(v_set=vset, stable=stable, settle_s=round(hist[-1]['t'] - t0, 1),
                    v_mean=statistics.mean(v), i_mean=statistics.mean(i), i_std=statistics.stdev(i),
                    history=hist, samples=samples)
        steps.append(step)
        cur = None
        print(f'  RESULT {vset} V: V={step["v_mean"]:.4f} V  I={step["i_mean"]:.4e} +- {step["i_std"]:.1e} A')
    if args.hold > 0:
        print(f'holding {args.voltages[-1]:g} V for {args.hold:.0f} s', flush=True)
        t0 = time.time()
        while time.time() - t0 < args.hold:
            time.sleep(args.poll)
            r = read()
            check(r)
            if int(r['t'] - t0) % 20 < args.poll:
                print(f'  hold {r["t"] - t0:5.0f} s  V={r["v"]:.4f} V  I={r["i"]:.4e} A', flush=True)
        print('hold done', flush=True)
except KeyboardInterrupt:
    print('\ninterrupted, shutting down')
finally:
    shutdown(switched_on)
    if cur is not None and cur['history']:
        # interrupted step, keep what was read
        h = cur['history']
        cur.update(settle_s=round(h[-1]['t'] - h[0]['t'], 1), v_mean=h[-1]['v'], i_mean=h[-1]['i'],
                   i_std=0.0, interrupted=True)
        steps.append(cur)
    if steps:
        out = args.output or time.strftime(f'iv_{ch}_%Y%m%d_%H%M%S.json')
        with open(out, 'w') as f:
            json.dump(dict(channel=ch, args=vars(args), steps=steps), f, indent=1)
        print(f'saved {out}')
        for s in steps:
            print(f'  {s["v_set"]:5.2f} V  {s["v_mean"]:.4f} V  {s["i_mean"]:.4e} A  +- {s["i_std"]:.1e}'
                  f'  {"stable" if s["stable"] else "NOT stable"} after {s["settle_s"]:.0f} s')
