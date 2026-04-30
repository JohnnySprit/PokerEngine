
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
SEED = 1
SB = 1
BB = 2
STACK = 8
SAMPLE_EVERY = 10  # record metrics every N iterations


#PokerKit and monte carlo
HANDS = 40  # number of PokerKit hands
MC_TRIALS = 400  #monte carlo trials per bot decision


OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "comparison_outputs") #folder to hold the graphs

def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True) #creates folder to hold the graphs

    # openCFR spams console so mute
    old_out = sys.stdout
    old_err = sys.stderr
    null = open(os.devnull, "w")
    sys.stdout = null
    sys.stderr = null



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




    # PokerKit + Monte Carlo evaluation (simple metrics)
    changes_in_chips = []  # seat0 chip change per hand
    hand_times = []  # seconds per hand (PokerKit+MC runtime)
    street_counts = {0: 0, 3: 0, 4: 0, 5: 0}  # board cards dealt at end

    for hand in range(HANDS):
        state = create_hunl_state() #creates a new pokerkit state for the bot
        start = int(state.stacks[0]) #keeps track of how many chips the bot starts with

        t_hand0 = time.perf_counter()
        play_hand_live(state, 0, MC_TRIALS, silent=True) #plays the hand
        hand_times.append(time.perf_counter() - t_hand0)

        # how far the hand went: 0 (preflop end), 3 (flop), 4 (turn), 5 (river)
        board_len = len(list(state.get_board_cards(0))) #gets the number of cards on the board
        if board_len in street_counts: #if the number of cards on the board is in the dictionary, then add 1 to the count (this is always 0, 3, 4, or 5)
            street_counts[board_len] += 1 #adds 1 to the count for the number of cards on the board

        changes_in_chips.append(int(state.stacks[0]) - start) #adds the change in chips for the bot to the list

    #matplotlib wants it to be a numpy array
    changes_in_chips = np.asarray(changes_in_chips, dtype=np.float64)





    x_hand = np.arange(1, HANDS + 1) #gets number of hands from 1 to HANDS + 1

    pk_running_mean = np.cumsum(changes_in_chips) / x_hand #running mean is the average of the changes in chips so far (this is going to be like [c1, (c1+c2)/2, (c1+c2+c3)/3, ... until (c1+c2+c3)/40 ])

    pk_cum_time = np.cumsum(hand_times) #cumulative time is the total time so far (this is going to be like [t1, t1+t2, t1+t2+t3, etc.])

    # street reached distribution (0, 3, 4, 5 board cards)
    street_labels = ["0", "3", "4", "5"]
    street_counts = [street_counts[0], street_counts[3], street_counts[4], street_counts[5]]

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


    # Right column: PokerKit+montecarlo  metrics
    ax[0, 1].plot(x_hand, pk_cum_time)
    ax[0, 1].set_title("PokerKit+MC: cumulative runtime vs hands")
    ax[0, 1].set_ylabel("seconds (total so far)")
    ax[0, 1].set_xlabel("hands")
    ax[0, 1].grid(True, alpha=0.3)

    ax[1, 1].bar(street_labels, street_counts, color="#2ecc71")
    ax[1, 1].set_title("PokerKit+MC: street reached (board cards dealt)")
    ax[1, 1].set_ylabel("# hands")
    ax[1, 1].set_xlabel("# board cards dealt")

    ax[2, 1].plot(x_hand, pk_running_mean)
    ax[2, 1].set_title("PokerKit+MC: running mean seat0 chip difference")
    ax[2, 1].set_xlabel("hand #")
    ax[2, 1].set_ylabel("mean difference chips so far")
    ax[2, 1].grid(True, alpha=0.3)

    fig.suptitle("openCFR vs PokerKit+MC comparison", fontsize=11)
    fig.tight_layout()

    dist_path = os.path.join(OUTPUT_FOLDER, "distributions.png") #saves the figure to the output folder
    fig.savefig(dist_path, dpi=150)
    plt.close(fig)

    sys.stdout = old_out
    sys.stderr = old_err
    null.close()
    print(f"Saved: {dist_path}")



if __name__ == "__main__":
    main()
