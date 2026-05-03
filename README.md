# AI Poker Bot (Heads-Up No-Limit Texas Hold'em)

This project implements and evaluates multiple AI approaches for Heads-Up No-Limit Texas Hold'em:

- A PokerKit-based playable game environment.
- A Monte Carlo equity decision bot.
- A depth-limited Expectiminimax bot.
- A CFR (MCCFR external sampling) training demo with `openCFR`.
- A comparison script that generates analysis plots.
- A terminal menu interface for live demos.

## Quick Start

Make sure you are in the correct folder with correct files when doing ls (pokerengine.py, mcequity.py, expectiminimax_min.py, etc.)

`PokerBot-zheng/PokerBot-zheng`

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run the gui:

```bash
python terminal_gui.py
```

## Proposal Notes

Per discussion with Owen and Soren during our first meeting about the proposal draft, **Expectiminimax is not part of the grading focus** for final evaluation and the project was meant to demonstrate just Monte Carlo and some level of CFR.

This repository still includes a small Expectiminimax implementation partly for fun, but also partly because it still exists in the final project proposal under the algorithms section.

The External Sampling MCCFR used in this project is provided by the `openCFR` python library due to time constraints. We received confirmation from Owen on our meeting from 4/28 that this was okay to do.

The goals we set out for this project are:

- C-range:
  - Implement a working Heads-Up Texas Hold’em game environment (`pokerengine.py` using PokerKit).
  - Implement a basic poker bot that makes decisions based on hand strength (`pokerengine.py` using `mcequity.py` Monte Carlo equity trials).
  - Create a simple evaluation system to measure bot performance (`analysis.py` evaluates and graphs data).

- B-range:
  - Analyze performance differences between algorithms (`analysis.py` compares methods using `comparison_outputs/distributions.png`).
  - Implement some form/level of Counterfactual Regret Minimization (CFR) (done with `openCFR` External Sampling MCCFR due to time constraints).

- A-range:
  - Create a GUI poker interface (terminal menu interface in `terminal_gui.py`).
  - Optimize decision speed and pruning techniques (implemented in `pokerengine.py` via `adaptive_trials_for_street()`).
  - Implement bluffing strategy and mixed strategies (implemented in `pokerengine.py` via `mc_policy()`).

## Repository Structure

- `pokerengine.py`
  - Builds a PokerKit Heads-Up No-Limit state.
  - Runs a full hand loop (deal, betting actions, board progression).
  - Contains the Monte Carlo-driven bot action policy (including simple mixed-strategy bluffing and speed-optimizing adaptive trials by street), an Expectiminimax policy, and a simple villain.

- `mcequity.py`
  - Monte Carlo hand equity simulation in heads-up spots.
  - Pot-odds break-even equity calculations.
  - Call/fold recommendation helper used by the bot.

- `expectiminimax_min.py`
  - Small Expectiminimax implementation.
  - Max node over a small action set, chance node estimated with Monte Carlo equity.

- `opencfr_demo.py`
  - Minimal CFR demonstration using `openCFR`'s MCCFR external sampling.
  - Prints infoset and expected game value training outputs.

- `analysis.py`
  - Generates side-by-side comparison figures:
    - openCFR training metrics (infoset growth, expected value per iteration, training time).
    - PokerKit runtime/performance metrics (MC vs expectiminimax-min policy).
  - Saves output image to `comparison_outputs/distributions.png`.

- `terminal_gui.py`
  - Terminal menu ("GUI") for quick demos:
    - Play one PokerKit + MC hand (`pokerengine.py` MC policy).
    - Play one PokerKit + Expectiminimax(min) hand (`pokerengine.py` expectiminimax-min policy).
    - Run openCFR training demo (`opencfr_demo.py`).
    - Run full analysis plot generation (`analysis.py`).

- `requirements.txt`
  - Python dependencies.

## Requirements

- Python 3.10+ (tested on Python 3.11.9).
- `pip` package manager.

## Install

From the project folder:

```bash
python -m pip install -r requirements.txt
```

If that doesn't work then you can try manually installing the dependencies:

```bash
python -m pip install numpy pokerkit matplotlib fnvhash openCFR
```

## How to Run

### Use terminal menu interface

```bash
python terminal_gui.py
```

## For specific files

### 1) Play one hand (PokerKit + Monte Carlo/Expectiminimax)

```bash
python pokerengine.py
```

### 2) Run CFR demo training

```bash
python opencfr_demo.py
```

### 3) Run comparison analysis and generate graph

```bash
python analysis.py
```

Expected output image:

- `comparison_outputs/distributions.png`


## How Components Work Together

1. `pokerengine.py` can use Monte Carlo (`mcequity.py`) or Expectiminimax (`expectiminimax_min.py`) to choose actions.
2. `opencfr_demo.py` demonstrates a game-theory-based strategy method (External Sampling MCCFR).
3. `analysis.py` gathers metrics from both approaches and saves visual comparisons.
4. `terminal_gui.py` provides one gui entry point to run all demos quickly.
