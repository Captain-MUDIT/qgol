"""Quantum Game of Life (Ney, Notarnicola, Montangero, Morigi, PRA 104, 062607, 2021).

H = sum_i X_i * P_i, where P_i projects onto "number of alive neighbours of i is in RULE".
Qubit/bit i is site i (little-endian, same as Qiskit). Time is reported as tau = 2t/pi,
so tau = 1 is the time one cell needs to fully flip (one classical generation).
"""
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import expm_multiply

RULE = (2, 3)
SY2 = np.kron([[0, -1j], [1j, 0]], [[0, -1j], [1j, 0]])


def chain(L):
    """Paper geometry: open chain, first and last two sites frozen, neighbours i-2..i+2."""
    return {i: [i - 2, i - 1, i + 1, i + 2] for i in range(2, L - 2)}


def torus(rows, cols, moore=True):
    """2D grid with wrap-around edges; Moore = 8 neighbours, else 4 (von Neumann)."""
    offs = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0) and (moore or a * b == 0)]
    return {r * cols + c: sorted({((r + a) % rows) * cols + (c + b) % cols for a, b in offs})
            for r in range(rows) for c in range(cols)}


def hamiltonian(n, nbrs, rule=RULE):
    x = np.arange(2 ** n, dtype=np.int64)
    rows, cols = [], []
    for i, nb in nbrs.items():
        hit = np.isin(np.bitwise_count(x & sum(1 << j for j in nb)), rule)
        cols.append(x[hit])
        rows.append(x[hit] ^ (1 << i))
    r, c = np.concatenate(rows), np.concatenate(cols)
    return csr_matrix((np.ones(len(r)), (r, c)), shape=(2 ** n, 2 ** n))


def classical(bits, nbrs, steps, rule=RULE):
    """Classical reversible F12-type rule: a cell swaps iff its alive-neighbour count is in RULE."""
    out = [np.array(bits, dtype=np.int8)]
    for _ in range(steps):
        b = out[-1].copy()
        for i, nb in nbrs.items():
            if out[-1][nb].sum() in rule:
                b[i] ^= 1
        out.append(b)
    return np.array(out)


def entropy(p):
    p = p[p > 1e-12]
    return float(-(p * np.log2(p)).sum())


def concurrence(rho):
    lam = np.sqrt(np.abs(np.linalg.eigvals(rho @ SY2 @ rho.conj() @ SY2)))
    lam = np.sort(lam)[::-1]
    return max(0.0, lam[0] - lam[1] - lam[2] - lam[3])


def gram(m):
    """Reduced density matrix of the smaller side of a bipartition (much faster than SVD)."""
    return m @ m.conj().T if m.shape[0] <= m.shape[1] else (m.T @ m.conj()).conj()


def observe(psi, n, pairs=True):
    """All observables of one state: density, single-site/bond entropy, and pair quantities."""
    T = psi.reshape([2] * n).transpose(range(n)[::-1])  # axis i = site i
    rho1 = [(m := np.moveaxis(T, i, 0).reshape(2, -1)) @ m.conj().T for i in range(n)]
    dens = np.array([r[1, 1].real for r in rho1])
    s1 = np.array([entropy(np.linalg.eigvalsh(r)) for r in rho1])
    bond = np.array([entropy(np.linalg.eigvalsh(gram(psi.reshape(2 ** (n - j - 1), 2 ** (j + 1)))))
                     for j in range(n - 1)])
    out = {"n": dens, "S": s1, "bond": bond}
    if pairs:
        mi, conc = np.zeros((n, n)), np.zeros((n, n))
        for i in range(n):
            for j in range(i + 1, n):
                m = np.moveaxis(T, [i, j], [0, 1]).reshape(4, -1)
                r = m @ m.conj().T
                mi[i, j] = mi[j, i] = 0.5 * (s1[i] + s1[j] - entropy(np.linalg.eigvalsh(r)))
                conc[i, j] = conc[j, i] = concurrence(r)
        out["MI"], out["conc"] = mi, conc
    return out


def fock(bits):
    psi = np.zeros(2 ** len(bits), dtype=complex)
    psi[sum(int(b) << i for i, b in enumerate(bits))] = 1
    return psi


def evolve(bits, nbrs, tau_max, frames, rule=RULE, pairs=True):
    """Exact Schrodinger evolution; returns observables stacked over `frames + 1` time points."""
    n = len(bits)
    # keeps every frame in memory, fine up to ~16 qubits
    states = expm_multiply((-1j * np.pi / 2) * hamiltonian(n, nbrs, rule), fock(bits),
                           start=0, stop=tau_max, num=frames + 1, endpoint=True)
    rec = [observe(psi, n, pairs) for psi in states]
    res = {k: np.array([r[k] for r in rec]) for k in rec[0]}
    res["back"] = np.abs(states[:, np.flatnonzero(fock(bits))[0]]) ** 2  # chance the board looks exactly like the start
    res["tau"] = np.linspace(0, tau_max, frames + 1)
    return res


def state_at(bits, nbrs, tau, rule=RULE):
    return expm_multiply((-1j * np.pi / 2 * tau) * hamiltonian(len(bits), nbrs, rule), fock(bits))


def clusters(row):
    """Sizes of the runs of alive cells: [0,1,1,0,1] -> [2, 1]."""
    return [len(s) for s in "".join(str(int(c)) for c in row).split("0") if s]


def pattern(L, *blocks):
    """pattern(11, (4, '101')) -> 11 sites, '101' placed starting at site 4."""
    b = np.zeros(L, dtype=np.int8)
    for start, s in blocks:
        b[start:start + len(s)] = [int(c) for c in s]
    return b
