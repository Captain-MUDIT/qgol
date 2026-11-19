"""Self-check against the paper's figures. Run: uv run python check.py [--big]"""
import sys
import numpy as np
from qgol.model import chain, torus, hamiltonian, classical, pattern, state_at, observe, evolve

T100 = 200 / np.pi  # paper's t = 100 in units of tau = 2t/pi

# H is real symmetric (Hermitian) for chain and torus
for n, nb in [(11, chain(11)), (9, torus(3, 3)), (16, torus(4, 4, moore=False))]:
    H = hamiltonian(n, nb)
    assert abs(H - H.T).max() == 0 and H.nnz > 0

# Classical F12: ..0101 0.. -> middle cell has 2 alive neighbours -> 111 (Fig. 1a, first step)
c = classical(pattern(11, (4, "101")), chain(11), 2)
assert "".join(map(str, c[1])) == "00001110000", c[1]

# Fig. 2: L = 11 blinker; Fig. 2b colour scale (max ~0.65) matches S_i in natural log (ln 2 = 0.69)
r = evolve(pattern(11, (4, "101")), chain(11), 64, 320)
print("Fig2  max S_i (ln) =", (r["S"].max() * np.log(2)).round(3), " mean n per site:", r["n"].mean(0).round(2))
assert 0.6 < r["S"].max() * np.log(2) <= 0.7 and r["n"][:, [0, 1, 9, 10]].max() == 0

# Fig. 6b: L = 11 blinker, bond entropy profile at t = 100 peaks ~1.6
o = observe(state_at(pattern(11, (4, "101")), chain(11), T100), 11, pairs=False)
print("Fig6b L=11 bond entropy at t=100:", o["bond"].round(2))
assert 1.3 < o["bond"].max() < 1.9

# Qiskit Trotter circuit converges to the exact evolution
from qgol.circuits import trotter_state
ex = state_at(pattern(7, (2, "101")), chain(7), 1.0)
fid = abs(np.vdot(ex, trotter_state(pattern(7, (2, "101")), chain(7), 1.0, 4, order=2))) ** 2
print("Trotter 2nd order, 4 steps, fidelity =", round(fid, 4))
assert fid > 0.999

if "--big" in sys.argv:
    # Fig. 3b: L = 20 blinker, ODE peak ~4.2 at the centre
    o = observe(state_at(pattern(20, (9, "101")), chain(20), T100), 20, pairs=False)
    print("Fig3b L=20 bond entropy at t=100:", o["bond"].round(2))
    # Fig. 6b: two blinkers, L = 19, peak ~5.7
    o = observe(state_at(pattern(19, (4, "101"), (12, "101")), chain(19), T100), 19, pairs=False)
    print("Fig6b two blinkers L=19:", o["bond"].round(2))

print("all checks passed")
