# analysis.py
# makes the big comparison png:
# - left column: openCFR training stats over more iterations (infosets, value, time)
# - right column: pokerkit rollout stats comparing mc_policy vs expectiminimax_min_policy
# this can take a little while because it retrains openCFR a bunch AND plays a bunch of pokerkit hands
# run: python analysis.py (writes comparison_outputs/distributions.png)

import os
import sys
import time

import matplotlib.pyplot as plt
import numpy as np

import openCFR.minimizers.MCCFR_External as MCCFR_External
from openCFR.Trainer import Trainer
from openCFR.games.sample_games import TexasHoldEm

from pokerengine import create_hunl_state, play_hand_live

# openCFR trainer metrics
TRAIN_ITERS = 400
SB = 1
BB = 2
STACK = 8
SAMPLE_EVERY = 10  # record metrics every N iterations


# PokerKit evaluation settings
HANDS = 40  # number of PokerKit hands
MC_TRIALS = 400  # trials per bot decision (adaptive trials happen inside bot_act_mc)


OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "comparison_outputs") #folder to hold the graphs


def evaluate_pokerkit_policy(policy_name: str, bot_policy: str, trials: int) -> dict[str, object]:
    # simple evaluation system: play N hands, track chip delta, runtime, and street reached
    changes_in_chips: list[int] = []
    hand_times: list[float] = []
    street_counts = {0: 0, 3: 0, 4: 0, 5: 0}
    bluff_count = 0

    for _ in range(HANDS):
        state = create_hunl_state()
        start = int(state.stacks[0])

        t0 = time.perf_counter()
        actions = play_hand_live(state, 0, trials, silent=True, bot_policy=bot_policy)
        hand_times.append(time.perf_counter() - t0)

        # track how far the hand went
        board_len = len(list(state.get_board_cards(0)))
        if board_len in street_counts:
            street_counts[board_len] += 1

        # count explicit bluff logs (only present in MC policy right now)
        for line in actions:
            if "BLUFF" in line:
                bluff_count += 1

        changes_in_chips.append(int(state.stacks[0]) - start)

    changes_arr = np.asarray(changes_in_chips, dtype=np.float64)
    x_hand = np.arange(1, HANDS + 1)
    running_mean = np.cumsum(changes_arr) / x_hand
    cum_time = np.cumsum(hand_times)

    return {
        "name": policy_name,
        "bot_policy": bot_policy,
        "trials": trials,
        "changes": changes_arr,
        "hand_times": np.asarray(hand_times, dtype=np.float64),
        "running_mean": running_mean,
        "cum_time": cum_time,
        "street_counts": street_counts,
        "bluff_count": bluff_count,
        "avg_delta": float(np.mean(changes_arr)),
        "avg_time": float(np.mean(hand_times)),
    }

def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True) #creates folder to hold the graphs

    # openCFR spams console so mute
    old_out = sys.stdout
    old_err = sys.stderr
    null = open(os.devnull, "w")
    sys.stdout = null
    sys.stderr = null

    try:
        #runs trainer from scratch for k iterations, records results, repeats
        #each iteration is a brand new game.

        iters = [] #storesnumber of iterations [10, 20, 30 etc.]
        infoset_counts = [] #stores number of infosets exist after trainings (100, 200, 300, etc.)
        egv_per_iter = [] #stores expected game value (this is the amount of "chips" openCFR returns after training) per iteration (these are cumulative, so divided by number of iterations, will be chips per iteration)
        training_times = [] #how many seconds it took for training to complete for each iteration

        i = SAMPLE_EVERY #starts at 5
        while i <= TRAIN_ITERS: #runs until 800 or however many iterations we want
            game = TexasHoldEm(small_blind=SB, big_blind=BB, starting_stack=STACK) #creates a new openCFR texas holdemgame
            trainer = Trainer(game=game, minimizer=MCCFR_External) #creates a new openCFR trainer with MCCFR external sampling

            t0 = time.perf_counter() #starts timer
            infosets, expected_game_value = trainer.train(iterations=i, display_results=False, save_results=False) #trains the openCFR trainer for i iterations (so 10, 20, 30, and so on)
            elapsed = time.perf_counter() - t0 #stops timer and stores how many seconds it took for that training

            iters.append(i) #adds the number of iterations to the list
            infoset_counts.append(len(infosets)) #how many infosets exist after training
            egv_per_iter.append(float(expected_game_value) / i) #expected game value per iteration
            training_times.append(elapsed) #how many seconds it took for training to complete

            i += SAMPLE_EVERY #adds 10 to i so it can run the next batch oftraining


        # PokerKit evaluation: compare bot policies (MC vs Expectiminimax-min)
        pk_mc = evaluate_pokerkit_policy("PokerKit+MC", bot_policy="mc", trials=MC_TRIALS)
        pk_expecti = evaluate_pokerkit_policy("PokerKit+Expectiminimax(min)", bot_policy="expectiminimax_min", trials=MC_TRIALS)

        x_hand = np.arange(1, HANDS + 1)
        street_labels = ["0", "3", "4", "5"]

        fig, ax = plt.subplots(3, 2, figsize=(12, 10))

        # Left column: openCFR MCCFR trainer metrics
        ax[0, 0].plot(iters, infoset_counts)
        ax[0, 0].set_title("openCFR: infoset growth vs iterations")
        ax[0, 0].set_ylabel("infosets")
        ax[0, 0].set_xlabel("iterations")
        ax[0, 0].grid(True, alpha=0.3)

        ax[1, 0].plot(iters, egv_per_iter)
        ax[1, 0].set_title("openCFR: expected_game_value / iter vs iterations")
        ax[1, 0].set_ylabel("expected_game_value / iter")
        ax[1, 0].set_xlabel("iterations")
        ax[1, 0].grid(True, alpha=0.3)

        ax[2, 0].plot(iters, training_times)
        ax[2, 0].set_title("openCFR: training time vs iterations")
        ax[2, 0].set_xlabel("iterations")
        ax[2, 0].set_ylabel("seconds")
        ax[2, 0].grid(True, alpha=0.3)


        # Right column: PokerKit bot policy comparison
        ax[0, 1].plot(x_hand, pk_mc["cum_time"], label=f"{pk_mc['name']} (avg {pk_mc['avg_time']:.2f}s/hand)")
        ax[0, 1].plot(x_hand, pk_expecti["cum_time"], label=f"{pk_expecti['name']} (avg {pk_expecti['avg_time']:.2f}s/hand)")
        ax[0, 1].set_title("PokerKit: cumulative runtime vs hands (policy comparison)")
        ax[0, 1].set_ylabel("seconds (total so far)")
        ax[0, 1].set_xlabel("hands")
        ax[0, 1].grid(True, alpha=0.3)
        ax[0, 1].legend(fontsize=8)

        ax[1, 1].plot(x_hand, pk_mc["running_mean"], label=f"{pk_mc['name']} (avg Δ {pk_mc['avg_delta']:.1f})")
        ax[1, 1].plot(x_hand, pk_expecti["running_mean"], label=f"{pk_expecti['name']} (avg Δ {pk_expecti['avg_delta']:.1f})")
        ax[1, 1].set_title("PokerKit: running mean seat0 chip difference (policy comparison)")
        ax[1, 1].set_xlabel("hand #")
        ax[1, 1].set_ylabel("mean chip difference so far")
        ax[1, 1].grid(True, alpha=0.3)
        ax[1, 1].legend(fontsize=8)

        mc_counts = pk_mc["street_counts"]
        ex_counts = pk_expecti["street_counts"]
        mc_vals = [mc_counts[0], mc_counts[3], mc_counts[4], mc_counts[5]]
        ex_vals = [ex_counts[0], ex_counts[3], ex_counts[4], ex_counts[5]]
        x = np.arange(len(street_labels))
        width = 0.38
        ax[2, 1].bar(x - (width / 2), mc_vals, width=width, label=pk_mc["name"], color="#2ecc71")
        ax[2, 1].bar(x + (width / 2), ex_vals, width=width, label=pk_expecti["name"], color="#3498db")
        ax[2, 1].set_xticks(x, street_labels)
        ax[2, 1].set_title("PokerKit: street reached distribution (policy comparison)")
        ax[2, 1].set_ylabel("# hands")
        ax[2, 1].set_xlabel("# board cards dealt at end")
        ax[2, 1].legend(fontsize=8)

        fig.suptitle("openCFR training vs PokerKit bot policy evaluation", fontsize=11)
        fig.tight_layout()

        dist_path = os.path.join(OUTPUT_FOLDER, "distributions.png") #saves the figure to the output folder
        fig.savefig(dist_path, dpi=150)
        plt.close(fig)

    finally:
        #always restore stdout/stderr so we don't lose tracebacks on failure
        sys.stdout = old_out
        sys.stderr = old_err
        null.close()

    print(f"Saved: {dist_path}")
    print(f"PokerKit eval summary: {pk_mc['name']} avg_delta={pk_mc['avg_delta']:.2f} avgTime={pk_mc['avg_time']:.3f}s bluffs={pk_mc['bluff_count']}")
    print(f"PokerKit eval summary: {pk_expecti['name']} avg_delta={pk_expecti['avg_delta']:.2f} avgTime={pk_expecti['avg_time']:.3f}s bluffs={pk_expecti['bluff_count']}")



if __name__ == "__main__":
    main()
