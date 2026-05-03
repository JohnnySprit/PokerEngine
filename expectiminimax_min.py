# expectiminimax_min.py
# "expectiminimax" in the loose student project sense:
# - you get a MAX node over a tiny action set (fold/call/raise-ish)
# - the messy hidden info / future cards part is approximated by monte carlo equity from mcequity.py
# - depth is literally 1 ply -- no real tree expansion into later streets
# pokerengine.py imports this and actually clicks the buttons in PokerKit


from pokerkit.utilities import Card

from mcequity import estimate_hu_equity


def decide_expectiminimax_min(hero: tuple[Card, Card], board: tuple[Card, ...], pot_chips: float, to_call: float, max_bet: float, stack: float, can_raise: bool, trials: int = 1500, raise_by: float = 20.0) -> dict[str, float | str | dict[str, float]]:
    # returns the "best" action under a small EV model

    #returns the best action at that point by expected chip value (depth-limited expectiminimax)

    wins, losses, ties, equity = estimate_hu_equity(hero, board, trials=trials, seed=None)  #calling estimate_hu_equity from mcequity.py to get the equity of the hand

    evs: dict[str, float] = {}  # this is the max node action to expected value table
    if to_call > 0:  #if facing a bet
        evs["FOLD"] = 0.0  # fold  (no further investment)
        evs["CALL"] = (equity * (pot_chips + to_call)) - ((1.0 - equity) * to_call)  #expected value of calling via (equity * reward - (1-equity) * risk)
    else:  #else we aren't facing a bet
        evs["CHECK"] = equity * pot_chips  # expected value of checking using equity against current pot in this simplified model

    if can_raise and stack > to_call:  #this runs only if raising is legal and possible to do with current stack
        rb = min(raise_by, stack - to_call)  #choose how much to raise by, basically all in if less than the raise_by
        if rb > 0:  #ensure raise is nonzero or else it will error
            invest = to_call + rb  #total chips invested if we raise now
            evs["RAISE"] = (equity * (pot_chips + invest)) - ((1.0 - equity) * invest)  # expected value of raising under same payoff model

    action = max(evs, key=evs.get)  #this is the max step where we pick the action with highest expected value
    amount = 0.0  #default amount (used for call or raise sizing, if we call or raise)
    if action == "CALL":  #if best action is call
        amount = to_call  #set call amount
    elif action == "RAISE":  #if best action is raise
        amount = max_bet + min(raise_by, stack - to_call)  #then set the raise-to amount

    return {  #outputs for logging and pokerengine.py to use
        "action": action,
        "amount": amount,
        "equity": equity,
        "best_ev": evs[action],
        "action_values": evs,
    }
