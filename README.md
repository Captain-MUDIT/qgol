# Quantum Game of Life

Reproduction and 2D extension of *Entanglement in the Quantum Game of Life*,
Ney, Notarnicola, Montangero & Morigi, Phys. Rev. A 104, 062607 (2021) · [arXiv:2104.14924](https://arxiv.org/abs/2104.14924).

Each cell is a qubit. The Hamiltonian `H = Σ X_i · P_i` flips cell *i* only when exactly 2 or 3 of its
neighbours are alive. Evolving it exactly (NumPy/SciPy) and as Trotter circuits (Qiskit) shows a
"quantum blinker", entanglement growth, and how the result differs from classical Life.

## Run

```
uv sync
uv run streamlit run app.py          # interactive app
uv run python check.py               # checks against the paper's figures (~20 s)
uv run python check.py --big         # also L = 19 and 20 chains (~6 min)
```

## Files

| File | What it does |
|---|---|
| `qgol/model.py` | Hamiltonian, exact evolution, classical rule, observables (density, entropies, mutual information, concurrence) |
| `qgol/circuits.py` | Qiskit Trotter circuits (multi-controlled RX gates), 1st and 2nd order |
| `app.py` | Streamlit app: a 7-step guided walkthrough (rule → quantum → blinker → entanglement → circuit → 2D → paper check), each with speaker notes. `?step=N` opens step N |
| `qgol/board.html` | Animated Go-board view used by the app (stones = alive, faint stones = partly alive, blue = entangled) |
| `check.py` | Asserts results match the paper's Fig. 2, 3b, 6b and that Trotter circuits converge |
| `qniverse/*.qasm` | OpenQASM 2.0 circuits to paste into Qniverse's editor (3-qubit blinker); `make_qasm.py` regenerates and checks them |

## Matches with the paper

| Figure | Paper | This code |
|---|---|---|
| Fig. 6b, bond entropy peak, L = 11 blinker, t = 100 | ≈ 1.6 | 1.61 |
| Fig. 3b, bond entropy peak, L = 20 blinker, t = 100 | ≈ 4.2 | 4.28 |
| Fig. 6b, two blinkers, L = 19, t = 100 | ≈ 5.7 | 5.70 |
| Fig. 2b, max single-site entropy, L = 11 | ≈ 0.65 | 0.69 (natural log) |

Time is shown as τ = 2t/π, so τ = 1 is one classical generation.
