"""Qiskit version: Trotterised time evolution of the quantum Game of Life Hamiltonian.

exp(-i dt X_i P_i) = "rotate cell i by RX(2 dt) only if its neighbours match an allowed pattern".
The allowed patterns (2 or 3 of the 4 neighbours alive) are mutually exclusive, so each one is a
multi-controlled RX gate and their product is exact for that cell; only the cell ordering is
approximate (Trotter error), which shrinks as the number of steps grows.
"""
from itertools import combinations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import RXGate
from qiskit.quantum_info import Statevector

from .model import RULE


def patterns(k, rule=RULE):
    """Integers whose bit j = 1 means neighbour j alive, for every allowed alive-count."""
    return [sum(1 << j for j in alive) for c in rule for alive in combinations(range(k), c)]


def trotter_circuit(bits, nbrs, tau, steps, rule=RULE, measure=False, order=1):
    """order=1: cells updated left to right each step. order=2: symmetric (half step forward, half back)."""
    n = len(bits)
    qc = QuantumCircuit(n, n if measure else 0)
    qc.x([i for i, b in enumerate(bits) if b])
    theta = 2 * (np.pi / 2) * tau / steps  # RX(theta) = exp(-i theta X / 2)
    sweeps = [(list(nbrs), theta)] if order == 1 else [(list(nbrs), theta / 2), (list(nbrs)[::-1], theta / 2)]
    for _ in range(steps):
        qc.barrier()
        for cells, th in sweeps:
            for i in cells:
                for p in patterns(len(nbrs[i]), rule):
                    qc.append(RXGate(th).control(len(nbrs[i]), ctrl_state=p), list(nbrs[i]) + [i])
    if measure:
        qc.barrier()
        qc.measure(range(n), range(n))
    return qc


def densities(psi, n):
    """Probability each qubit is |1>, from a statevector (little-endian, qubit i = bit i)."""
    p = np.abs(np.asarray(psi)) ** 2
    x = np.arange(len(p))
    return np.array([p[(x >> i) & 1 == 1].sum() for i in range(n)])


def counts_to_density(counts, n):
    shots = sum(counts.values())
    return np.array([sum(v for k, v in counts.items() if k[::-1][i] == "1") for i in range(n)]) / shots


def trotter_state(bits, nbrs, tau, steps, rule=RULE, order=1):
    return Statevector(trotter_circuit(bits, nbrs, tau, steps, rule, order=order)).data
