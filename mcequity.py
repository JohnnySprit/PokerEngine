import random

from pokerkit import StandardHighHand
from pokerkit.utilities import Card, Deck


def estimate_hu_equity(hero: tuple[Card, Card], board: tuple[Card, ...] = (), trials: int = 10_000, seed: int | None = None) -> tuple[int, int, int, float]:

    #starts with 0 wins, losses, and ties everytime its called
    wins = losses = ties = 0

    used = set(hero) | set(board)
    remaining = []
    for card in Deck.STANDARD: #Deck.STANDARD is the standard 52 card deck
        if card not in used:
            remaining.append(card)  #goes through pokerkit's deck and appends any cards that haven't been used yet
    draw_count = 2 + (5 - len(board))  # villain hole + board runout

    rnd = random.Random(seed) #random number generator

    for trial in range(trials):
        draw = rnd.sample(remaining, draw_count) #samples draw_count number of cards from remaining without replacement
        villain_hole = (draw[0], draw[1]) #for each trial/simulation, we sample 2 cards for the villain first
        full_board = board + tuple(draw[2:]) #thenafter that we sample the rest of the cards for the board

        hero_best = StandardHighHand.from_game(hero, full_board) #pokerkit function that evaluates the best 5-card hand for the hero from the hole and the community
        villain_best = StandardHighHand.from_game(villain_hole, full_board) #same thing for the villain
        if hero_best > villain_best: #if hero hand is better, then we add a win
            wins += 1
        elif villain_best > hero_best: #if villain hand is better, then we add a loss
            losses += 1
        else: #if both hands are equal, then we add a tie
            ties += 1

    equity = (wins + (0.5 * ties)) / trials #equity is basically win percentage
    return wins, losses, ties, equity #returns the number of wins, losses, ties, and the equity


#breakeven equity basically helps determine if calling is worth it or not. the definition of it is risk/(risk+reward)
#function is used later by comparing the equity to the breakeven equity to determine if calling is worth it
def breakeven_equity_for_call(pot_chips: float, to_call: float) -> float:
    if to_call <= 0: #if the call is free, then the breakeven equity is 0 because you're not risking anything
        return 0.0
    return to_call / (pot_chips + to_call) #otherwise, do the breakeven equity formula


def call_or_fold_advice(equity: float, pot_chips: float, to_call: float) -> tuple[str, float]:
    need = breakeven_equity_for_call(pot_chips=pot_chips, to_call=to_call) #now uses the breakeven equity formula to see how much equity is "needed" before its worth it to call (or even raise)
    if equity >= need: #if the equity is greater than the breakeven equity, then its worth it to call
        return "CALL", need
    else: #if the equity is less than the breakeven equity, then its not worth it to call and just tell bot to fold
        return "FOLD", need


def decide_with_mc(hero: tuple[Card, Card], board: tuple[Card, ...] = (), *, pot_chips: float, to_call: float, trials: int = 10_000, seed: int | None = None) -> dict[str, float | int | str]:
    wins, losses, ties, equity = estimate_hu_equity(hero, board, trials=trials, seed=seed)
    action, need = call_or_fold_advice(equity=equity, pot_chips=pot_chips, to_call=to_call)
    #returns a dictionary with all of the outcomes of everything, makes it easier to read and then call
    return {
        "action": action,
        "equity": equity,
        "breakeven_equity": need,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "trials": trials,
    }