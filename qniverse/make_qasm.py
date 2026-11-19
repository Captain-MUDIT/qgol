"""Writes OpenQASM 2.0 files for Qniverse's editor and checks each against the exact answer.

The 7-cell blinker . . 1 0 1 . . only ever changes the 3 middle cells (the edges stay dead), so it is
exactly a 3-qubit system: each middle cell flips only when the other two are alive.
Gates used: x, h, t, tdg, cx and `rz (pi / n)` (Qniverse's own syntax; it rejected decimals, cu1, cp, comments, measure).  Run: uv run python qniverse/make_qasm.py
"""
from pathlib import Path

import numpy as np
from qiskit import qasm2
from qiskit.quantum_info import Statevector
from scipy.linalg import expm

OUT = Path(__file__).parent
NAMES = {0: "left cell q[0]", 1: "middle cell q[1]", 2: "right cell q[2]"}


def ccrx(theta, a, b, t):
    """Rotate cell t by RX(theta) only if cells a and b are both alive.

    H . exp(-i theta/2 Z_t n_a n_b) . H, with the doubly-controlled RZ written as RZ(+-theta/4) on the parities
    t, t^a, t^a^b, t^b (a Gray-code walk of CNOTs), so only h, rz and cx are needed.
    """
    q = theta / 4

    def rz(angle):
        """Qniverse syntax: `rz (pi / n)`, positive only; X.RZ(a).X = RZ(-a) handles negatives; T/Tdg for pi/4."""
        if abs(abs(angle) - np.pi / 4) < 1e-9:
            return [f"{'t' if angle > 0 else 'tdg'} q[{t}];"]
        n = np.pi / abs(angle)
        assert abs(n - round(n)) < 1e-9, f"angle {angle} is not pi/n"
        line = f"rz (pi / {round(n)}) q[{t}];"
        return [line] if angle > 0 else [f"x q[{t}];", line, f"x q[{t}];"]

    return [f"h q[{t}];", *rz(q), f"cx q[{a}],q[{t}];", *rz(-q), f"cx q[{b}],q[{t}];",
            *rz(q), f"cx q[{a}],q[{t}];", *rz(-q), f"cx q[{b}],q[{t}];", f"h q[{t}];"]


TERMS = {0: (1, 2), 1: (0, 2), 2: (0, 1)}  # cell -> the two cells that must be alive


def sequence(generations, steps, orders=((0, 1, 2), (2, 1, 0))):
    """(cell, RX angle) list: symmetric Trotter steps, cell order alternating, neighbouring half-steps merged."""
    th = np.pi * generations / steps  # exp(-i dt X n n) with dt = (pi/2) * generations / steps  ->  RX(2 dt)
    seq = []
    for s in range(steps):
        a, b, c = orders[s % len(orders)]
        seq += [(a, th / 2), (b, th / 2), (c, th), (b, th / 2), (a, th / 2)]
    merged = [seq[0]]
    for cell, ang in seq[1:]:
        if merged[-1][0] == cell:
            merged[-1] = (cell, merged[-1][1] + ang)
        else:
            merged.append((cell, ang))
    return merged


def blinker(generations, steps, orders=((0, 1, 2), (2, 1, 0))):
    return [line for cell, ang in sequence(generations, steps, orders) for line in ccrx(ang, *TERMS[cell], cell)]


def program(title, prep, body):
    """No comments and no measure lines: Qniverse's editor rejects them; its chart shows probabilities anyway."""
    return "\n".join(["OPENQASM 2.0;", 'include "qelib1.inc";', "qreg q[3];", "creg c[3];", *prep, *body, ""])


def exact(generations, start):
    H = np.zeros((8, 8))
    for x in range(8):
        for t, (a, b) in TERMS.items():
            if (x >> a) & 1 and (x >> b) & 1:
                H[x ^ (1 << t), x] = 1
    psi0 = np.zeros(8)
    psi0[start] = 1
    return expm(-1j * np.pi / 2 * generations * H) @ psi0


FILES = {
    "1_rule_two_alive.qasm": ("Rule check: both neighbours alive, so the middle cell flips (expect 111)",
                              ["x q[0];", "x q[2];"], ccrx(np.pi, 0, 2, 1), None, None),
    "2_rule_one_alive.qasm": ("Rule check: only one neighbour alive, so the middle cell stays dead (expect 001 / 100)",
                              ["x q[0];"], ccrx(np.pi, 0, 2, 1), None, None),
    "3_rule_superposition.qasm": ("Neighbour in superposition: the middle cell flips in one branch only, so it gets entangled",
                                  ["h q[0];", "x q[2];"], ccrx(np.pi, 0, 2, 1), None, None),
    "4_blinker_half_generation.qasm": ("Quantum blinker . . 1 0 1 . . after half a generation",
                                       ["x q[0];", "x q[2];"], blinker(0.5, 1), 0b101, 0.5),
    "5_blinker_one_generation.qasm": ("Quantum blinker . . 1 0 1 . . after one generation",
                                      ["x q[0];", "x q[2];"], blinker(1.0, 2), 0b101, 1.0),
    "6_blinker_comes_back.qasm": ("Quantum blinker after 2.4 generations: the start comes back",
                                  ["x q[0];", "x q[2];"], blinker(2.4, 3, orders=((1, 0, 2), (1, 2, 0))), 0b101, 2.4),  # 2.4 keeps every angle pi/n; full return is at 2.31
}

if __name__ == "__main__":
    for name, (title, prep, body, start, gens) in FILES.items():
        src = program(title, prep, body)
        (OUT / name).write_text(src, encoding="utf-8")
        qc = qasm2.loads(src)
        sv = Statevector(qc)
        probs = {format(i, "03b")[::-1]: round(float(p), 3) for i, p in enumerate(sv.probabilities()) if p > 1e-3}
        fid = "" if start is None else f"fidelity {abs(np.vdot(exact(gens, start), sv.data)) ** 2:.4f}"
        ops = qc.count_ops()
        print(f"{name:34s} gates {sum(ops.values()) - ops.get('barrier', 0):3d}  {fid}  probs (q0 q1 q2) {probs}")
