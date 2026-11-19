"""Quantum Game of Life, presented as a slide deck. Run: uv run streamlit run app.py

Arrow keys / PageUp / PageDown (or a clicker) change slides. ?s=N opens slide N, ?notes=1 shows speaker notes.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from qgol.model import chain, classical, evolve, observe, pattern, state_at, torus

st.set_page_config(page_title="Quantum Game of Life", page_icon="⚫", layout="wide", initial_sidebar_state="collapsed")

INK, GREY, BLUE, WOOD = "#1e2328", "#9a948a", "#2e43c9", "#e7d3ae"
STONE = [[0, WOOD], [1, "#1c1a17"]]
ROOT = Path(__file__).parent
BOARD_HTML = (ROOT / "qgol" / "board.html").read_text(encoding="utf-8")
ASSETS = ROOT / "assets" / "qniverse"
L = 13  # cells in the 1D chain
WALLS = (0, 1, L - 2, L - 1)
BLINKER = "0000010100000"
COMES_BACK = 7.5  # generation of the strongest revival of the 13-cell blinker (61%)

st.markdown("""<style>
html, body, p, li, label, .stMarkdown, h1, h2, h3, h4 {font-family: Calibri, Carlito, Arial, sans-serif !important;}
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stSidebar"],
[data-testid="collapsedControl"] {display: none !important;}
.block-container {padding: 1.4rem 3rem 4.2rem; max-width: 100%;}
h1.claim {font-weight: 700; font-size: 2.5rem; line-height: 1.15; color: #1f3864; margin: 0 0 1rem; padding: 0 0 .45rem;
  border-bottom: 3px solid #1f3864;}
ul.pts {font-size: 1.3rem; line-height: 1.4; color: #222; margin: 0 0 .9rem; padding-left: 1.5rem;}
ul.pts li {margin-bottom: .2rem;}
.title-slide {text-align: center; padding-top: 3vh;}
.title-slide .inst {font-size: 1.6rem; font-weight: 700; color: #222; margin: 0;}
.title-slide .dept {font-size: 1.25rem; color: #444; margin: .2rem 0 2.2rem;}
.title-slide h1 {font-size: 3.6rem; font-weight: 700; color: #1f3864; line-height: 1.1; margin: 0 0 .8rem; padding: 0;}
.title-slide .lede {font-size: 1.4rem; color: #333; margin: 0 0 2rem;}
.title-slide .course {font-size: 1.25rem; color: #444; margin: 0 0 1.6rem;}
.title-slide .by {font-size: 1.2rem; color: #444; line-height: 1.6; margin: 0 0 1.6rem;}
.title-slide .by b {color: #222; font-size: 1.35rem; font-weight: 700;}
.prose h3 {font-size: 1.7rem; font-weight: 700; color: #1f3864; margin: .2rem 0 .7rem; padding: 0;}
.prose p, .prose li {font-size: 1.4rem; line-height: 1.5; color: #222; max-width: 52ch;}
.prose.wide li {max-width: none; font-size: 1.6rem; margin-bottom: 1.1rem;}
.prose li {margin-bottom: .8rem;}
.tools {font-size: 1.3rem !important; color: #444; margin-top: 1.2rem;}
.refs {font-size: 1.3rem; line-height: 1.45; padding-left: 1.8rem; margin-top: .4rem;}
.refs li {margin-bottom: 1rem; padding-left: .4rem;}
.key {display: flex; gap: 1.4rem; flex-wrap: wrap; font-size: 1.05rem; color: #333; margin: 0 0 .4rem;}
.key span {display: inline-flex; align-items: center; gap: .5rem;}
.sw {width: 16px; height: 16px; border-radius: 50%; display: inline-block;}
.rules {display: grid; grid-template-columns: 1fr 1fr; gap: .2rem 3rem; margin-top: .6rem;}
.rule {display: grid; grid-template-columns: auto 1fr; align-items: center; gap: 1rem; padding: .7rem 0; border-top: 1px solid #ccc; font-size: 1.2rem;}
.rule .strip {display: inline-flex; gap: 7px; background: #dcb878; padding: 7px 9px; border-radius: 4px;}
.spot {width: 30px; height: 30px; border-radius: 50%; display: inline-block; border: 1px dashed rgba(80,50,15,.4); box-sizing: border-box;}
.spot.alive {background: #1c1a17; border: 0;}
.spot.centre {outline: 2.5px solid #2e43c9; outline-offset: 2px;}
.rule .res {font-weight: 700; display: flex; align-items: center; gap: .8rem;}
.rule .why {display: block; color: #555; font-weight: 400; font-size: 1.05rem;}
.cap {font-size: 1.1rem; color: #333; margin: .1rem 0 .3rem;}
.cap b {color: #111;}
.footer {position: fixed; left: 0; right: 0; bottom: 0; height: 44px; display: flex; align-items: center; justify-content: space-between;
  padding: 0 3rem; background: #fff; border-top: 1px solid #1f3864; z-index: 99; font-size: 1rem; color: #444;}
.footer .count {margin-right: 7.5rem; font-variant-numeric: tabular-nums;}
.st-key-nav {position: fixed; right: 2.2rem; bottom: 4px; z-index: 100; width: auto !important;}
.st-key-nav button {min-height: 34px; padding: 0 14px; font-size: 1.1rem; border-radius: 4px;}
.st-key-keys {position: absolute; width: 0; height: 0; overflow: hidden;}
</style>""", unsafe_allow_html=True)

KEY = ('<div class="key"><span><i class="sw" style="background:#1c1a17"></i>alive</span>'
       '<span><i class="sw" style="background:#1c1a17;opacity:.3"></i>partly alive</span>'
       '<span><i class="sw" style="border:3px solid #2e43c9"></i>entangled</span></div>')


# ---------- data ----------
@st.cache_data(show_spinner=False, max_entries=16)
def run_chain(start, tau_max=40.0, frames=240):
    bits = np.array([int(c) for c in start], dtype=np.int8)
    r = evolve(bits, chain(len(bits)), tau_max, frames)
    r["classical"] = classical(bits, chain(len(bits)), int(tau_max))
    return r


@st.cache_data(show_spinner=False, max_entries=16)
def run_grid(R, C, moore, start, tau_max=16.0, frames=96):
    bits = np.array(start, dtype=np.int8)
    nb = torus(R, C, moore)
    r = evolve(bits, nb, tau_max, frames, pairs=False)
    r["classical"] = classical(bits, nb, int(tau_max))
    return r


def board(r, boards, rows, cols, height, walls=(), rings=False, threads=False, rate=1.2, moments=()):
    """Animated Go-board view (canvas, see qgol/board.html)."""
    n = rows * cols
    data = dict(rows=rows, cols=cols, tau=np.round(r["tau"], 4).tolist(), q=np.round(r["n"], 3).tolist(),
                s=np.round(r["S"], 3).tolist(), c=r["classical"].tolist(), walls=list(walls), rings=rings,
                threads=threads, rate=rate, height=height, layout="stack" if rows == 1 else "side",
                boards=[dict(title=t, kind=k) for t, k in boards], moments=list(moments))
    if threads and "MI" in r:
        pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        data.update(pairs=pairs, mi=np.round([[m[i, j] for i, j in pairs] for m in r["MI"]], 4).tolist(),
                    mimax=float(r["MI"].max()) or 1.0)
    st.iframe(BOARD_HTML.replace("__DATA__", json.dumps(data)), height=height + 56)


def style(fig, h=320, title=None):
    fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=h,
                      margin=dict(l=8, r=8, t=58 if title else 16, b=8), font=dict(family="Calibri, Arial, sans-serif", color=INK, size=15),
                      legend=dict(orientation="h", x=0, y=1.0, yanchor="bottom", bgcolor="rgba(0,0,0,0)"),
                      hoverlabel=dict(bgcolor="white", font_color=INK))
    if title:
        fig.update_layout(title=dict(text=title, x=0, xanchor="left", yref="container", y=0.97, yanchor="top",
                                     font=dict(family="Calibri, Arial, sans-serif", size=19)))
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#c4cad0", color="#3d454c")
    fig.update_yaxes(gridcolor="#d9dee3", zeroline=False, color="#3d454c")
    return fig


def show(fig, where=st):
    where.plotly_chart(fig, width="stretch", theme=None, config={"displayModeBar": False})


def head(title, *points):
    st.markdown(f'<h1 class="claim">{title}</h1>' + ('<ul class="pts">' + "".join(f"<li>{x}</li>" for x in points) + "</ul>" if points else ""),
                unsafe_allow_html=True)


def spot(alive, centre=False):
    return f'<i class="spot{" alive" if alive else ""}{" centre" if centre else ""}"></i>'


# ---------- circuits ----------
CIRCUIT_STYLE = {"name": "clifford", "backgroundcolor": "#ffffff", "textcolor": INK, "linecolor": INK, "fontsize": 14,
                 "subfontsize": 11, "displaycolor": {
                     "rx": [BLUE, "#ffffff"], "ccrx": [BLUE, "#ffffff"], "x": ["#1c1a17", "#ffffff"], "h": ["#e6c48a", INK],
                     "rz": ["#c9d1ff", INK], "t": ["#c9d1ff", INK], "tdg": ["#c9d1ff", INK]}}
CELLS = ("left", "middle", "right")
RUNS = {"½ generation": (0.5, 1, ((0, 1, 2), (2, 1, 0))), "1 generation": (1.0, 2, ((0, 1, 2), (2, 1, 0))),
        "2.4 generations": (2.4, 3, ((1, 0, 2), (1, 2, 0)))}  # the exact settings of Qniverse files 4, 5, 6


def png(qc, scale=0.9):
    import io
    import matplotlib
    matplotlib.use("Agg")
    fig = qc.draw("mpl", style=CIRCUIT_STYLE, fold=-1, scale=scale)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    return buf.getvalue()


@st.cache_data(show_spinner=False)
def compact_png(run):
    """The blinker circuit with one gate per rule: RX on a cell, controlled by the other two cells being alive."""
    from qiskit import QuantumCircuit, QuantumRegister
    from qiskit.circuit.library import RXGate
    from qniverse.make_qasm import TERMS, sequence
    qc = QuantumCircuit(*[QuantumRegister(1, c) for c in CELLS])
    qc.x([0, 2])
    qc.barrier(label="start: 1 0 1")
    for cell, ang in sequence(*RUNS[run]):
        qc.append(RXGate(ang).control(2), [*TERMS[cell], cell])
    return png(qc), len(sequence(*RUNS[run]))


@st.cache_data(show_spinner=False)
def expanded_png():
    """One rule gate written in the basic gates Qniverse accepts (h, rz, x, cx)."""
    from qiskit import QuantumCircuit, QuantumRegister, qasm2
    from qniverse.make_qasm import ccrx, program
    basic = qasm2.loads(program("", [], ccrx(np.pi / 2, 0, 2, 1)).replace("creg c[3];", ""))
    qc = QuantumCircuit(*[QuantumRegister(1, c) for c in CELLS])
    qc.compose(basic, inplace=True)
    return png(qc, 0.75)


@st.cache_data(show_spinner=False)
def one_gate_png():
    from qiskit import QuantumCircuit, QuantumRegister
    from qiskit.circuit.library import RXGate
    qc = QuantumCircuit(*[QuantumRegister(1, c) for c in CELLS])
    qc.append(RXGate(np.pi / 2).control(2), [0, 2, 1])
    return png(qc, 0.75)


@st.cache_data(show_spinner=False)
def qniverse_results():
    """Probabilities of Qniverse files 4-6 (same QASM, simulated here) next to the exact physics."""
    from qiskit import qasm2
    from qiskit.quantum_info import Statevector
    from qniverse.make_qasm import exact
    out = []
    for f, gens in (("4_blinker_half_generation.qasm", 0.5), ("5_blinker_one_generation.qasm", 1.0),
                    ("6_blinker_comes_back.qasm", 2.4)):
        circ = Statevector(qasm2.loads((ROOT / "qniverse" / f).read_text(encoding="utf-8"))).probabilities()
        out.append((gens, circ, np.abs(exact(gens, 0b101)) ** 2))
    return out


@st.cache_data(show_spinner=False)
def steps_study(max_steps=6):
    """Accuracy vs size for one generation: fidelity with the exact answer and Qniverse gate count."""
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import RXGate
    from qiskit.quantum_info import Statevector
    from qniverse.make_qasm import TERMS, blinker, exact, sequence
    ex, rows = exact(1.0, 0b101), []
    for n in range(1, max_steps + 1):
        qc = QuantumCircuit(3)
        qc.x([0, 2])
        for cell, ang in sequence(1.0, n):
            qc.append(RXGate(ang).control(2), [*TERMS[cell], cell])
        rows.append((n, abs(np.vdot(ex, Statevector(qc).data)) ** 2, len(blinker(1.0, n)) + 2))
    return rows


# ---------- slides ----------
TEAM = ["Mudit Jain (231070021)", "Aadit Pujari (231070046)"]
INSTITUTE = "Veermata Jijabai Technological Institute, Mumbai"
DEPT = "Department of Computer Engineering"
COURSE = "Quantum Computing Lab Mini Project, LY B.Tech CE"


def s_title():
    st.markdown(f"""<div class="title-slide"><p class="inst">{INSTITUTE}</p><p class="dept">{DEPT}</p>
<h1>Quantum Game of Life</h1>
<p class="lede">Simulation of a quantum cellular automaton using exact evolution, Qiskit circuits and Qniverse</p>
<p class="course">{COURSE}</p>
<p class="by">Presented by<br><b>{"<br>".join(TEAM)}</b></p></div>""", unsafe_allow_html=True)
    return "- Introduce yourselves and the one-line topic."


def s_objectives():
    head("Problem Statement and Objectives")
    left, right = st.columns([0.45, 0.55], gap="large")
    left.markdown("""<div class="prose"><h3>Problem statement</h3>
<p>In Conway's Game of Life every cell is either alive or dead, and the board follows a fixed rule.</p>
<p>What happens when every cell is a <b>qubit</b>, so cells can be partly alive (superposition) and linked to
each other (entanglement)? Does the board still behave like Life?</p></div>""", unsafe_allow_html=True)
    right.markdown("""<div class="prose"><h3>Objectives</h3><ol>
<li>Implement the quantum Game of Life model from Ney et al. (2021) and simulate it exactly.</li>
<li>Reproduce the paper's results: the quantum blinker and the growth of entanglement.</li>
<li>Build the model as quantum circuits in Qiskit and run them on Qniverse.</li>
<li>Extend the model from a single row of cells to a 2D board.</li></ol></div>""", unsafe_allow_html=True)
    return "- Objective 4 is our own addition; the paper only studies a single row."


def s_paper():
    head("Literature Review: Base Paper",
         "P.-M. Ney, S. Notarnicola, S. Montangero and G. Morigi, “Entanglement in the Quantum Game of Life”, "
         "Phys. Rev. A 104, 062607 (2021), arXiv:2104.14924")
    left, right = st.columns([0.5, 0.5], gap="large")
    left.markdown("""<div class="prose"><h3>What the paper does</h3><ul>
<li>A row of qubits, one per cell, evolving in continuous time under a Hamiltonian.</li>
<li>A cell flips only when exactly 2 or 3 of its 4 nearest neighbours are alive.</li>
<li>Simulated exactly for up to 20 cells, and with tensor networks for 32.</li>
<li>Finds a <b>quantum blinker</b>, a pattern that keeps reviving with no classical counterpart, and entanglement that
grows with system size.</li></ul></div>""", unsafe_allow_html=True)
    with right:
        st.markdown('<div class="prose"><h3>The model</h3></div>', unsafe_allow_html=True)
        st.latex(r"\hat H=\sum_{i} \hat X_i\,\big(\hat N^{(2)}_i+\hat N^{(3)}_i\big)")
        st.markdown("""<div class="prose"><ul>
<li><b>X<sub>i</sub></b> flips cell i between dead |0⟩ and alive |1⟩.</li>
<li><b>N<sup>(2)</sup>, N<sup>(3)</sup></b> are 1 only when exactly 2 or 3 neighbours are alive, else 0.</li>
<li>Time is shown in generations: one generation is the time a lone cell takes to flip completely.</li></ul></div>""",
                    unsafe_allow_html=True)
    return ("- The Hamiltonian first appeared in Bleh, Calarco and Montangero (2012); this paper adds the entanglement analysis.\n"
            "- The rule must flip cells (not just create or kill them) because quantum evolution is reversible.")


def s_method():
    head("Methodology")
    steps = [("Build the Hamiltonian", "A sparse 2ⁿ × 2ⁿ matrix for n cells, one entry for every allowed flip (NumPy, SciPy)."),
             ("Evolve exactly", "Solve the Schrödinger equation for all 2ⁿ board patterns at once (SciPy expm_multiply)."),
             ("Measure", "Chance each cell is alive, entanglement entropy, mutual information and concurrence."),
             ("Turn it into circuits", "Split time into small Trotter steps; each rule becomes a controlled-RX gate (Qiskit)."),
             ("Run on Qniverse", "Export the circuits as OpenQASM 2.0 and run them on C-DAC's Qniverse platform.")]
    st.markdown('<div class="prose wide"><ol>' + "".join(f"<li><b>{a}:</b> {b}</li>" for a, b in steps) + "</ol></div>"
                '<p class="tools"><b>Tools used:</b> Python 3.11, NumPy, SciPy, Qiskit 2.6, Plotly, Streamlit, Qniverse</p>',
                unsafe_allow_html=True)
    return "- Every result in this deck comes from this pipeline; check.py re-runs the comparison with the paper."


def s_conclusion():
    head("Conclusion and Future Scope")
    left, right = st.columns([0.55, 0.45], gap="large")
    left.markdown("""<div class="prose"><h3>Conclusion</h3><ul>
<li>Quantum Life behaves differently from classical Life: patterns stay localised and keep reviving instead of spreading.</li>
<li>Cells become strongly entangled, which is what makes large boards hard to simulate classically.</li>
<li>Our simulation matches the paper's figures, and the same circuits give the same answers on Qniverse.</li>
<li>In 2D the neighbourhood decides the outcome: 4 neighbours still blink, Conway's 8 scramble.</li></ul></div>""",
                  unsafe_allow_html=True)
    right.markdown("""<div class="prose"><h3>Future scope</h3><ul>
<li>Run the circuits on real IBM hardware through Qniverse and study the effect of noise.</li>
<li>Larger 2D boards with tensor-network methods.</li>
<li>Search for other quantum patterns, such as quantum gliders.</li></ul></div>""", unsafe_allow_html=True)
    return "- No speedup is claimed; the value is behaviour that classical Life cannot show."


def s_references():
    head("References")
    refs = ["P.-M. Ney, S. Notarnicola, S. Montangero and G. Morigi, “Entanglement in the Quantum Game of Life”, "
            "Phys. Rev. A 104, 062607 (2021).",
            "D. Bleh, T. Calarco and S. Montangero, “Quantum Game of Life”, EPL 97, 20012 (2012).",
            "M. Gardner, “Mathematical Games: The fantastic combinations of John Conway's new solitaire game ‘life’”, "
            "Scientific American 223, 120 (1970).",
            "M. Suzuki, “Generalized Trotter's formula and systematic approximants of exponential operators”, "
            "Commun. Math. Phys. 51, 183 (1976).",
            "Qiskit documentation, IBM Quantum, docs.quantum.ibm.com",
            "Qniverse quantum computing platform, C-DAC Bengaluru, qniverse.in"]
    st.markdown('<ol class="refs">' + "".join(f"<li>{r}</li>" for r in refs) + "</ol>", unsafe_allow_html=True)
    return ""


def s_thanks():
    st.markdown(f"""<div class="title-slide" style="padding-top:26vh"><h1>Thank You</h1><p class="lede">Questions?</p></div>""", unsafe_allow_html=True)
    return ""


def s_rule():
    head("Introduction: Conway's Game of Life",
         "Each spot is a cell: a stone means alive, an empty spot means dead.",
         "One-row version used by the paper: a cell flips when exactly 2 or 3 of its 4 neighbours (two on each side) are alive.")
    board(run_chain(BLINKER), [("Classical Life, one generation at a time", "classical")], 1, L, 150, walls=WALLS, rate=1.0)
    rows = [("01010", "flips: becomes alive", "2 neighbours alive", 1), ("11110", "flips: dies", "3 neighbours alive", 0),
            ("00010", "stays dead", "1 neighbour alive", 0), ("11011", "stays dead", "4 neighbours alive", 0)]
    html = ['<div class="rules">']
    for s, result, why, after in rows:
        cells = "".join(spot(c == "1", i == 2) for i, c in enumerate(s))
        html.append(f'<div class="rule"><span class="strip">{cells}</span>'
                    f'<span class="res">{spot(after, True)}<span>{result}<span class="why">{why}</span></span></span></div>')
    st.markdown("".join(html) + "</div>", unsafe_allow_html=True)
    return ("- A version of Conway's Game of Life on one row, as in the paper.\n"
            "- It flips cells instead of creating or killing them, so it can always be run backwards. Quantum physics "
            "needs that: it never destroys information.\n"
            "- The two cells at each end are a fixed edge.")


def s_quantum():
    head("Classical vs Quantum Evolution",
         "Same starting pattern and same rule for both boards.",
         "Classical Life fills the board; quantum Life stays near its start.",
         "A faint stone is partly alive: the percentage is the probability of finding that cell alive.")
    st.markdown(KEY, unsafe_allow_html=True)
    board(run_chain(BLINKER), [("Classical Life", "classical"), ("Quantum Life", "quantum")], 1, L, 330, walls=WALLS,
          moments=[["Start", 0], ["1 generation", 1.0], ["It comes back", COMES_BACK]])
    return ("- Same start, same rule. Classical Life jumps between patterns and fills the board.\n"
            "- Quantum Life flows smoothly and stays near the middle.\n"
            "- The rule is a Hamiltonian, H = Σ X_i · P_i: X flips cell i, P_i only allows it when 2 or 3 neighbours are alive. "
            "We solve the Schrödinger equation exactly for all 2¹³ = 8,192 boards at once.\n"
            f"- Click 'It comes back' to jump to generation {COMES_BACK}.")


def s_blinker():
    head("Results: Quantum Blinker",
         "The quantum pattern keeps returning to its start, which classical Life never does.",
         "Cause: interference between different histories of the board (like H then H giving back |0⟩ in Lab 2).")
    r = run_chain(BLINKER)
    left, right = st.columns([0.47, 0.53], gap="large")
    tau, steps = r["tau"], np.arange(len(r["classical"]))
    fig = make_subplots(1, 2, subplot_titles=("Classical history", "Quantum history"), horizontal_spacing=0.1)
    hov = "cell %{x}<br>generation %{y:.1f}<br>alive %{z:.2f}<extra></extra>"
    fig.add_trace(go.Heatmap(z=r["classical"], x=np.arange(1, L + 1), y=steps, colorscale=STONE, zmin=0, zmax=1,
                             showscale=False, xgap=1, hovertemplate=hov), 1, 1)
    fig.add_trace(go.Heatmap(z=r["n"], x=np.arange(1, L + 1), y=tau, colorscale=STONE, zmin=0, zmax=1, showscale=False,
                             hovertemplate=hov), 1, 2)
    fig.update_yaxes(autorange="reversed", title="generation", row=1, col=1)
    fig.update_yaxes(autorange="reversed", row=1, col=2)
    fig.update_xaxes(title="cell")
    style(fig, 520).update_layout(margin_t=44)
    fig.update_annotations(font=dict(family="Calibri, Arial, sans-serif", size=18, color=INK))
    show(fig, left)
    back_c = (r["classical"] == r["classical"][0]).all(1).astype(float)
    f = go.Figure()
    f.add_trace(go.Scatter(x=steps, y=back_c, name="classical", mode="lines", line=dict(color=GREY, width=2.5, shape="hv", dash="dot")))
    f.add_trace(go.Scatter(x=tau, y=r["back"], name="quantum", mode="lines", line=dict(color=INK, width=2.5),
                           hovertemplate="generation %{x:.1f}: %{y:.0%}<extra></extra>"))
    k = int(np.argmin(np.abs(tau - COMES_BACK)))
    f.add_annotation(x=tau[k], y=r["back"][k], text="back to the start: 61%", showarrow=True, arrowhead=0, ax=60, ay=-40,
                     font=dict(color=INK, size=15))
    f.update_xaxes(title="generation")
    f.update_yaxes(title="chance", tickformat=".0%", range=[0, 1.05])
    f.update_layout(hovermode="x unified")
    show(style(f, 520, "Chance the board looks exactly like the start"), right)
    return ("- Left: every moment stacked as a row, top to bottom. Classical never returns; quantum keeps returning.\n"
            "- Right: the spikes are the revivals. Classical drops to 0 after the first step and stays there.\n"
            "- The paper calls this a quantum blinker.")


def s_entangle():
    head("Results: Entanglement Between Cells",
         "Cells become entangled; entanglement is lowest when the blinker returns.",
         "Blue ring: how entangled a cell is with the rest. Blue threads: which pairs of cells are linked.")
    r = run_chain(BLINKER)
    left, right = st.columns([0.6, 0.4], gap="large")
    with left:
        st.markdown(KEY, unsafe_allow_html=True)
        board(r, [("Quantum Life", "quantum")], 1, L, 330, walls=WALLS, rings=True, threads=True,
              moments=[["Start", 0], ["Tangled", 2.0], ["It comes back", COMES_BACK]])
    tau = r["tau"]
    f = make_subplots(2, 1, shared_xaxes=True, vertical_spacing=0.14,
                      subplot_titles=("Chance the board looks like the start", "Entanglement between the two halves"))
    f.add_trace(go.Scatter(x=tau, y=r["back"], mode="lines", line=dict(color=INK, width=2.5), hovertemplate="%{y:.0%}<extra></extra>"), 1, 1)
    f.add_trace(go.Scatter(x=tau, y=r["bond"][:, L // 2 - 1], mode="lines", line=dict(color=BLUE, width=2.5),
                           hovertemplate="%{y:.2f} bits<extra></extra>"), 2, 1)
    f.add_trace(go.Scatter(x=tau, y=np.zeros_like(tau), mode="lines", line=dict(color=GREY, width=2, dash="dot"), hoverinfo="skip"), 2, 1)
    f.update_yaxes(tickformat=".0%", row=1, col=1)
    f.update_yaxes(title="bits", row=2, col=1)
    f.update_xaxes(title="generation", row=2, col=1)
    f.update_layout(hovermode="x unified", showlegend=False)
    style(f, 470).update_layout(margin_t=40)
    f.update_annotations(font=dict(family="Calibri, Arial, sans-serif", size=17, color=INK))
    f.add_annotation(x=tau[-1], y=0, text="classical: always 0", showarrow=False, xanchor="right", yshift=12, row=2, col=1,
                     font=dict(color="#5b636b", size=13))
    show(f, right)
    return ("- Entanglement: no cell has a state of its own any more. We measure it with von Neumann entropy; "
            "1 bit is the maximum for one qubit.\n"
            "- Threads are mutual information between two cells.\n"
            "- The dips in the blue line line up with the spikes in the black one.\n"
            "- This entanglement is why big boards are hard for normal computers: the numbers to track double with every cell.")


def s_circuit():
    head("Implementation: Quantum Circuit",
         "The edge cells of the blinker never change, so it is exactly a 3-qubit circuit: left, middle and right cells.",
         "Each blue gate rotates one cell only if the other two are alive (doubly-controlled RX).")
    img, gates = compact_png("1 generation")
    st.image(img, width=900, caption=f"One generation of the quantum blinker: {gates} rule gates, in small symmetric time steps.")
    st.markdown('<p class="cap"><b>Qniverse has no button for this gate</b>, so each one is built from H, RZ, X and CNOT:</p>',
                unsafe_allow_html=True)
    a, eq, b, _ = st.columns([0.13, 0.03, 0.6, 0.24], vertical_alignment="center")
    a.image(one_gate_png())
    eq.markdown("<div style='font-size:2.4rem;text-align:center'>=</div>", unsafe_allow_html=True)
    b.image(expanded_png())
    return ("- Why 3 qubits: with dead edges, a middle cell has 2 or 3 live neighbours only when the other two middle cells "
            "are alive. So the rule is a doubly-controlled RX gate.\n"
            "- Splitting time into small steps is Trotterisation; symmetric steps (half forward, half back) are far more "
            "accurate. Backup slide 2 shows accuracy against circuit size.\n"
            "- The full simulation (13 qubits in 1D, 16 in 2D) runs in NumPy; the 3-qubit circuit is the hardware demo.")


def s_qniverse():
    head("Results: Circuits on Qniverse",
         "On C-DAC's Qniverse platform the board spreads out, then returns to its start, matching the exact simulation.",
         "Bar labels follow Qniverse's bit order: right, middle, left cell.")
    labels = ["011", "101", "110", "111"]
    idx = [int(s, 2) for s in labels]
    names = {0.5: "After ½ generation", 1.0: "After 1 generation", 2.4: "After 2.4 generations"}
    for col, (gens, circ, ex), shot in zip(st.columns(3, gap="large"), qniverse_results(), ("chart4", "chart5", "chart6")):
        f = go.Figure()
        f.add_trace(go.Bar(x=labels, y=[ex[i] for i in idx], name="exact physics", marker=dict(color=INK, cornerradius=3),
                           hovertemplate="%{x}: %{y:.0%}<extra>exact</extra>"))
        f.add_trace(go.Bar(x=labels, y=[circ[i] for i in idx], name="circuit", marker=dict(color=BLUE, cornerradius=3),
                           hovertemplate="%{x}: %{y:.0%}<extra>circuit</extra>"))
        f.update_layout(barmode="group", bargap=0.3, bargroupgap=0.08)
        f.update_yaxes(tickformat=".0%", range=[0, 1.05])
        style(f, 330, names[gens])
        show(f, col)
        col.image(str(ASSETS / f"{shot}.png"), caption="The same circuit, run on Qniverse")
    return ("- Bars are the same QASM we pasted into Qniverse; the screenshots underneath are Qniverse's own charts.\n"
            "- After 1 generation classical Life always gives 111; the quantum board is spread over four patterns.\n"
            "- At 2.4 generations the start is back with 99%. The exact return is at 2.31; 2.4 keeps every angle a simple "
            "fraction of π, which is what Qniverse's editor accepts.\n"
            "- Ideal simulator, no noise; we didn't spend credits on Run.")


def s_2d():
    head("Extension: 2D Board",
         "Not in the paper: a 3 × 4 board (12 qubits) that wraps around at the edges, starting from a row of three.",
         "With 4 neighbours it still blinks; with Conway's 8 neighbours it scrambles.")
    g = np.zeros((3, 4), dtype=np.int8)
    g[1, :3] = 1
    runs = {m: run_grid(3, 4, m, tuple(g.ravel()), 16.0, 160) for m in (False, True)}
    a, b, c = st.columns([0.27, 0.27, 0.46], gap="large")
    with a:
        board(runs[False], [("4 neighbours", "quantum")], 3, 4, 250, rings=True, rate=0.8)
    with b:
        board(runs[True], [("8 neighbours, like Conway", "quantum")], 3, 4, 250, rings=True, rate=0.8)
    f = go.Figure()
    for m, col, nm in ((False, INK, "4 neighbours"), (True, BLUE, "8 neighbours")):
        f.add_trace(go.Scatter(x=runs[m]["tau"], y=runs[m]["back"], name=nm, mode="lines", line=dict(color=col, width=2.5),
                               hovertemplate=f"{nm}<br>generation %{{x:.1f}}: %{{y:.0%}}<extra></extra>"))
    f.update_xaxes(title="generation")
    f.update_yaxes(title="chance", tickformat=".0%", range=[0, 1.05])
    show(style(f, 330, "Chance the board looks like the start"), c)
    c.markdown('<p class="cap">With 8 neighbours the start never comes back above <b>24%</b>, and each cell ends up '
               '<b>0.93 of 1 bit</b> entangled. With 4 neighbours it returns at <b>99%</b>.</p>', unsafe_allow_html=True)
    return ("- The paper only studies a single row; this is our own extension.\n"
            "- More neighbours means more cells can trigger each flip, so the board scrambles into a highly entangled state "
            "instead of blinking.\n"
            "- Half-board entanglement reaches 4.33 of a possible 6 bits with 8 neighbours, only 1.48 with 4.")


def s_close():
    head("Validation Against the Base Paper",
         "Values read from the paper's figures compared with our exact simulation.",
         "Paper time t = 100 is about 64 generations.")
    left, right = st.columns([0.5, 0.5], gap="large")
    o = observe(state_at(pattern(11, (4, "101")), chain(11), 200 / np.pi), 11, pairs=False)
    rows = [["Fig. 6b", "11 cells, one blinker", "1.6", f"{o['bond'].max():.2f}"],
            ["Fig. 3b", "20 cells, one blinker", "4.2", "4.28"],
            ["Fig. 6b", "19 cells, two blinkers", "5.7", "5.70"],
            ["Fig. 2b", "most entangled single cell", "0.65", "0.69"]]
    left.markdown("".join(['<table style="font-size:1.15rem;width:100%;border-collapse:collapse">',
                           '<tr style="text-align:left;border-bottom:2px solid #1e2328"><th>Figure</th><th>Setup</th><th>Paper</th><th>Ours</th></tr>',
                           *[f'<tr style="border-bottom:1px solid #d5dadf"><td style="padding:.6rem 0">{a}</td><td>{b}</td><td>{c}</td>'
                             f'<td><b>{d}</b></td></tr>' for a, b, c, d in rows], "</table>"]), unsafe_allow_html=True)
    left.markdown('<p class="cap" style="margin-top:1.4rem">Entanglement in bits; the last row only matches if that figure uses '
                  'the natural log.</p>', unsafe_allow_html=True)
    f = go.Figure(go.Scatter(x=np.arange(1, 11), y=o["bond"], mode="lines+markers", line=dict(color=BLUE, width=2.5),
                             marker=dict(size=10, color=BLUE), hovertemplate="cut after cell %{x}: %{y:.2f} bits<extra></extra>"))
    f.add_hline(y=1.6, line=dict(color=GREY, dash="dot"), annotation_text="paper: about 1.6", annotation_position="top left")
    f.update_xaxes(title="where the chain is cut")
    f.update_yaxes(title="entanglement (bits)")
    show(style(f, 420, "Fig. 6b reproduced"), right)
    return ("- 19 and 20-cell runs take a few minutes, so they're in check.py --big.\n"
            "- Likely questions: quantum advantage (no speedup claimed; the point is behaviour classical Life can't show, "
            "and why it's hard to simulate classically); why not Conway's exact rule (quantum evolution must be reversible); "
            "real hardware (not yet, ideal simulator).")


QNIVERSE_RULE = [("chart1", "Both neighbours alive", "The middle cell flips: 111 at 100%."),
                 ("chart2", "Only one neighbour alive", "It stays dead: 001 at 100%."),
                 ("chart3", "Neighbour in superposition", "Flips in one branch only: 100 and 111 at 50%. Now entangled.")]


def b_rule():
    head("Backup: Rule Gate Verified on Qniverse")
    for col, (f, title, cap) in zip(st.columns(3, gap="large"), QNIVERSE_RULE):
        col.markdown(f'<p class="cap"><b>{title}</b></p>', unsafe_allow_html=True)
        col.image(str(ASSETS / f"{f}.png"), caption=cap)
    return "- The third chart is the smallest example of entanglement in this project: a superposed neighbour."


def b_accuracy():
    head("Backup: Accuracy vs Circuit Size",
         "One generation of the blinker: more Trotter steps are more accurate but need a bigger circuit.",
         "Same accuracy-versus-size trade-off as counting qubits in QPE (Lab 5).")
    rows = steps_study()
    f = go.Figure(go.Scatter(x=[g for _, _, g in rows], y=[fd for _, fd, _ in rows], mode="lines+markers+text",
                             text=[f"{n} step{'s' * (n > 1)}" for n, _, _ in rows],
                             textposition=["bottom right"] * (len(rows) - 1) + ["bottom left"],
                             line=dict(color=BLUE, width=2.5), marker=dict(size=11, color=BLUE),
                             hovertemplate="%{text}<br>%{x} gates on Qniverse<br>match %{y:.2%}<extra></extra>"))
    f.update_xaxes(title="gates in the Qniverse circuit")
    f.update_yaxes(title="match with exact answer", tickformat=".0%", range=[0.85, 1.01])
    show(style(f, 480))
    return "- We used 2 steps for one generation: 99.8% match with 142 basic gates."


PATTERNS = {"Blinker": BLINKER, "Two blinkers": "0010100010100", "Block": "0011111111100", "Mixed": "0010110010100"}


def b_explore():
    head("Backup: Other Starting Patterns")
    p = st.pills("Starting pattern", list(PATTERNS), default="Blinker", label_visibility="collapsed") or "Blinker"
    st.markdown(KEY, unsafe_allow_html=True)
    board(run_chain(PATTERNS[p]), [("Classical Life", "classical"), ("Quantum Life", "quantum")], 1, L, 330, walls=WALLS, rings=True)
    return "- For questions: any pattern of the 9 middle cells works."


MAIN = [s_title, s_rule, s_objectives, s_paper, s_method, s_quantum, s_blinker, s_entangle, s_circuit, s_qniverse, s_2d,
        s_close, s_conclusion, s_references, s_thanks]
BACKUP = [b_rule, b_accuracy, b_explore]
SLIDES = MAIN + BACKUP

# ---------- page ----------
if "slide" not in st.session_state:
    q = st.query_params.get("s", "1")
    st.session_state.slide = int(q) - 1 if q.isdigit() and 1 <= int(q) <= len(SLIDES) else 0
i = st.session_state.slide
st.query_params["s"] = str(i + 1)

with st.spinner("Computing…"):
    notes = SLIDES[i]()
if st.query_params.get("notes") == "1":
    with st.expander("Speaker notes", expanded=True):
        st.markdown(notes)


def move(d):
    st.session_state.slide = min(max(st.session_state.slide + d, 0), len(SLIDES) - 1)


count = f"{i + 1}" if i < len(MAIN) else f"Backup {i - len(MAIN) + 1}"
st.markdown(f'<div class="footer"><span>Quantum Game of Life</span><span>{COURSE}</span>'
            f'<span class="count">{count}</span></div>', unsafe_allow_html=True)
with st.container(key="nav", horizontal=True):
    st.button("←", key="prev", on_click=move, args=(-1,), disabled=i == 0)
    st.button("→", key="next", on_click=move, args=(1,), disabled=i == len(SLIDES) - 1)
with st.container(key="keys"):
    st.iframe("""<script>
const P = window.parent;
P.__qgolNav = d => { const b = P.document.querySelector(d > 0 ? '.st-key-next button' : '.st-key-prev button'); if (b && !b.disabled) b.click(); };
if (!P.__qgolKeys) {
  P.__qgolKeys = true;
  P.document.addEventListener('keydown', e => {
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;
    if (['ArrowRight', 'PageDown'].includes(e.key)) { e.preventDefault(); P.__qgolNav(1); }
    if (['ArrowLeft', 'PageUp'].includes(e.key)) { e.preventDefault(); P.__qgolNav(-1); }
  });
}
</script>""", height=1)
