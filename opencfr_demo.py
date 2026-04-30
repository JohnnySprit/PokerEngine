import random
import openCFR.minimizers.MCCFR_External as MCCFR_External
from openCFR.Trainer import Trainer
from openCFR.games.sample_games import TexasHoldEm


# CHANGE THESE VALUES TO CHANGE THE TRAINING SETTINGS
TRAIN_ITERS = 800
SEED = random.randint(0, 1000000)
SB = 1
BB = 2
STACK = 8


#Libratus and Pluribus (created by CMU researchers and beat some of the best professionals) use the same algorithm with different implementations.
#can't use vanilla cfr since its almost impossible to train given the massive game trees in no limit texas holdem (anyone can bet any amount of money)


#each iteration of training in openCFR will sample one random chance outcome whenever it's needed and one opponent action whenever its needed.
#whenever it's the bot's (traverser's) turn, it will evaluate all of its options and computes how much better each option would have been in comparison to other options in that state.
#computes regret (how much better a different option would have been compared to the current option)
#the regret-matching will push the bot strategy towards a strategy that prioritizes choices with the highest positive regret (the actions that worked out the most in that game state).


#this moves the bot towards the nash equilibrum which basically just means the bot will play the best it can given the other player's actions.


def main():
    game = TexasHoldEm(small_blind=SB, big_blind=BB, starting_stack=STACK)
    trainer = Trainer(game=game, minimizer=MCCFR_External)
    infosets, expected_game_value = trainer.train(iterations=TRAIN_ITERS, display_results=False, save_results=False)

    print("openCFR's TexasHoldEm External Sampling MCCFR ")
    print(f"train_iters: {TRAIN_ITERS}")
    print(f"infosets: {len(infosets)}")
    print(f"expected_game_value (cumulative): {float(expected_game_value):.4f}")

if __name__ == "__main__":
    main()