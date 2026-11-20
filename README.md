# Quantum Game of Life

Reproduction and 2D extension of *Entanglement in the Quantum Game of Life*,
Ney, Notarnicola, Montangero & Morigi, Phys. Rev. A 104, 062607 (2021) · [arXiv:2104.14924](https://arxiv.org/abs/2104.14924).

Each cell is a qubit. The Hamiltonian `H = Σ X_i · P_i` flips cell *i* only when exactly 2 or 3 of its
neighbours are alive. Evolving it exactly (NumPy/SciPy) and as Trotter circuits (Qiskit) shows a
"quantum blinker", entanglement growth, and how the result differs from classical Life.

## Why the Game of Life

Conway's Game of Life (1970, made popular by Martin Gardner's column in *Scientific American*) is a grid of
cells that live or die by one simple rule about their neighbours. It became famous because such a simple rule
produces surprisingly complex behaviour: still patterns, oscillators ("blinkers"), patterns that move across
the board ("gliders") and patterns that create other patterns. It is even Turing complete, so in principle it
can run any computer program.

That makes it the standard example of *emergence*: complex global behaviour from simple local rules.
Cellular automata like it are used to model traffic flow, crystal growth, forest fires, epidemics and pattern
formation in biology, and to study parallel computing.

The quantum version asks what happens to that complexity when cells follow quantum mechanics. Quantum cellular
automata are a model of quantum computation in their own right, and rules of this "flip only when the
neighbours allow it" kind arise naturally in Rydberg-atom quantum simulators.

## Aims

**1D (the paper's setting).** A single row of 13 cells, simulated exactly.
- Reproduce the paper's main results: the quantum blinker and the growth of entanglement.
- Recompute its key figures (Figs. 1, 2, 7/8 and 11) and check the numbers against it (`check.py`).
- Turn the blinker into a 3-qubit circuit in Qiskit and run it on C-DAC's Qniverse.

**2D (our extension, not in the paper).** A 3 × 4 board (12 qubits) that wraps around at the edges.
- Check whether the quantum blinker survives in two dimensions.
- Compare 4 neighbours (up, down, left, right) with Conway's 8. With 4 the start returns at 99%; with 8 it never
  returns above 24% and every cell ends up almost fully entangled.

## Theory

**Classical rule.** The paper uses a one-row version of Conway's Game of Life. Each cell looks at four
neighbours, two on each side, and *flips* (dead ↔ alive) when exactly 2 or 3 of them are alive. The two cells
at each end never change. The rule flips cells instead of creating or killing them, so every step can be
undone. Quantum evolution has to be reversible, which is why this rule is used instead of Conway's own.

**Cells as qubits.** Cell *i* is a qubit: |0⟩ is dead, |1⟩ is alive. The rule becomes a Hamiltonian

$$H = \sum_i X_i \left(N_i^{(2)} + N_i^{(3)}\right)$$

where $X_i$ flips cell *i*, and $N_i^{(2)}$, $N_i^{(3)}$ are projectors that are 1 when exactly 2 or 3 of its
neighbours are alive and 0 otherwise. The board evolves by the Schrödinger equation,
$|\psi(t)\rangle = e^{-iHt}|\psi(0)\rangle$. A cell whose rule is "on" fully flips after $t = \pi/2$, so we
measure time in generations, $\tau = 2t/\pi$.

**Classical vs quantum.** If every cell were measured after each $\pi/2$, the board would follow classical Life
exactly. Without measurement, cells go into superposition (partly alive), and different histories of the board
interfere. Interference is what produces the **quantum blinker**: the pattern `101` keeps coming back to its
starting state, which never happens classically.

**Entanglement.** Because a cell flips only when its neighbours allow it, cells become entangled. We measure:
- *single-site entropy* $S_i$: how entangled cell *i* is with the rest (max 1 bit),
- *bond entropy*: entanglement between the left and right part of the row,
- *mutual information* and *concurrence*: how strongly two particular cells are linked.

**Circuits.** $e^{-iHt}$ is split into small Trotter steps. Each term $e^{-i X_i P_i \Delta t}$ is an RX rotation
on cell *i* controlled by its neighbours, so one step of the rule is one multi-controlled RX gate per cell.
For the blinker only three cells ever change, and each middle cell can flip only when the other two are alive,
so it reduces to a 3-qubit circuit of doubly-controlled RX gates. Qniverse has no such gate, so
`make_qasm.py` writes each one using H, RZ, X and CNOT.

## Run

```
uv sync
uv run streamlit run app.py          # presentation
uv run python check.py               # checks against the paper's figures (~20 s)
uv run python check.py --big         # also L = 19 and 20 chains (~6 min)
```

The presentation is a slide deck: arrow keys change slides, `?s=N` opens slide N and `?notes=1` shows speaker notes.

## Files

| File | What it does |
|---|---|
| `qgol/model.py` | Hamiltonian, exact evolution, classical rule, observables (density, entropies, mutual information, concurrence) |
| `qgol/circuits.py` | Qiskit Trotter circuits (multi-controlled RX gates), 1st and 2nd order |
| `app.py` | The slide deck: 20 slides + 4 backup, including the paper's Figs. 1, 2, 7/8 and 11 recomputed |
| `qgol/board.html` | Animated Go-board view used by the app (stones = alive, faint stones = partly alive, blue = entangled) |
| `check.py` | Asserts results match the paper's Fig. 2, 3b, 6b and that Trotter circuits converge |
| `qniverse/*.qasm` | OpenQASM 2.0 circuits to paste into Qniverse's editor (3-qubit blinker); `make_qasm.py` regenerates and checks them |
| `screenshots/` | Results of the QASM files on Qniverse, named after the files |
| `assets/` | Qniverse charts shown in the deck, and saved results of the two slow slides (`assets/cache`) |

## Matches with the paper

| Figure | Paper | This code |
|---|---|---|
| Fig. 6b, bond entropy peak, L = 11 blinker, t = 100 | ≈ 1.6 | 1.61 |
| Fig. 3b, bond entropy peak, L = 20 blinker, t = 100 | ≈ 4.2 | 4.28 |
| Fig. 6b, two blinkers, L = 19, t = 100 | ≈ 5.7 | 5.70 |
| Fig. 2b, max single-site entropy, L = 11 | ≈ 0.65 | 0.69 (natural log) |

Time is shown as τ = 2t/π, so τ = 1 is one classical generation.
