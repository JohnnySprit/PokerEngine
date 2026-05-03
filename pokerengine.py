# pokerengine.py
# - builds a PokerKit heads-up no limit holdem table state
# - runs one hand all the way to the end (deal/burn/board/betting) in play_hand_live()
# - how the bot works with the two algorithms:
#     mc_policy gets monte carlo equity + a little bluff rng
#     expectiminimax_min_policy gets tiny expectiminimax picker (real logic is in expectiminimax_min.py)
# run: python pokerengine.py  (plays one MC hand and prints logs)

import random

from pokerkit import Automation, NoLimitTexasHoldem
from pokerkit.state import State

from expectiminimax_min import decide_expectiminimax_min
from mcequity import decide_with_mc, estimate_hu_equity

#these are kinda the boilerplate automations that pokerkit has, we might not use all of them but its good to just have

_AUTOMATIONS = (
    Automation.ANTE_POSTING,
    Automation.BET_COLLECTION,
    Automation.BLIND_OR_STRADDLE_POSTING,
    Automation.HOLE_CARDS_SHOWING_OR_MUCKING,
    Automation.HAND_KILLING,
    Automation.CHIPS_PUSHING,
    Automation.CHIPS_PULLING,
)


def create_hunl_state(stacks: tuple[int, int] = (500, 500), small_blind: int = 10, big_blind: int = 20, min_bet: int = 20) -> State:
    return NoLimitTexasHoldem.create_state(
        _AUTOMATIONS,
        False, #boolean for ante status
        0, #how much to ante (doesn't matter since we're doing texas holdem)
        (small_blind, big_blind),
        min_bet,
        stacks,
        2, #player count
    )


# --- Monte Carlo bot tuning (MC policy) -------------------------------------

MC_RAISE_EQ = 0.70
MC_BET_TO_CHIPS = 20
MC_RAISE_BY_CHIPS = 20

# simple mixed-strategy bluffing and occasionally does a bet/raise in a marginal equity band.
MC_BLUFF_P = 0.18
MC_BLUFF_EQ_LOW = 0.33
MC_BLUFF_EQ_HIGH = 0.45

# expectiminimax-min raise sizing (must match `expectiminimax_min.decide_expectiminimax_min` default unless changed here).
EXPECTIMINIMAX_MIN_RAISE_BY_CHIPS = 20.0

# added a small speed optimization here for the monte carlo trials
def adaptive_trials_for_street(board_len: int, base_trials: int) -> int:
    # cheap speed hack fewer MC trials early, crank it up as more board cards appear
    # board_len is 0 preflop, 3 flop, 4 turn, 5 river
    if board_len <= 0:
        return max(200, int(base_trials * 0.25))
    if board_len == 3:
        return max(400, int(base_trials * 0.50))
    if board_len == 4:
        return max(600, int(base_trials * 0.80))
    return max(800, int(base_trials * 1.10))


def mc_policy(state: State, bot_index: int = 0, trials: int = 8000) -> str:
    # main bot for demos does sample equity on random villain cards/runouts (monte carlo equity), then act on it
    # when nobody bet into us, we intentionally don't run the pot-odds call helper (that's for facing a bet only, not for checking)

    hero = tuple(state.hole_cards[bot_index])
    board = tuple(state.get_board_cards(0))
    street_trials = adaptive_trials_for_street(len(board), trials)

    bets = list[int](state.bets)
    to_call = max(bets) - bets[bot_index]
    max_bet = max(bets)
    stack = int(state.stacks[bot_index])

    wins, losses, ties, eq = estimate_hu_equity(hero, board, trials=street_trials, seed=None)

    # When facing no bet (to_call == 0): either value-bet or check. Do not use call/fold MC here.
    # if we have enough equity to call, then we can bluff
    if to_call <= 0:
        if (
            (MC_BLUFF_EQ_LOW <= eq <= MC_BLUFF_EQ_HIGH)
            and (random.random() < MC_BLUFF_P)
            and stack > 0
            and state.can_complete_bet_or_raise_to()
        ):
            bet_to = min(stack, MC_BET_TO_CHIPS)
            try:
                state.complete_bet_or_raise_to(bet_to)
                return f"BLUFF_BET_TO {bet_to} eq={eq:.2f} trials={street_trials}"
            except ValueError:
                state.complete_bet_or_raise_to()
                return f"BLUFF_BET_MIN eq={eq:.2f} trials={street_trials}"

        if eq >= MC_RAISE_EQ and stack > 0 and state.can_complete_bet_or_raise_to():
            bet_to = min(stack, MC_BET_TO_CHIPS)
            try:
                state.complete_bet_or_raise_to(bet_to)
                return f"BET_TO {bet_to} eq={eq:.2f} trials={street_trials}"
            except ValueError:
                state.complete_bet_or_raise_to()
                return f"BET_MIN eq={eq:.2f} trials={street_trials}"
        state.check_or_call()
        return f"CHECK eq={eq:.2f} trials={street_trials}"

    r = decide_with_mc(
        hero,
        board,
        pot_chips=float(state.total_pot_amount),
        to_call=float(to_call),
        trials=street_trials,
        seed=None,
    )

    if r["action"] == "FOLD": # if we dont have enough equity to call, then fold
        state.fold()
        return f"FOLD eq={r['equity']:.2f} need={r['breakeven_equity']:.2f} trials={street_trials}"

    # if we are in the marginal equity band, then we can bluff
    if (
        (MC_BLUFF_EQ_LOW <= float(r["equity"]) <= MC_BLUFF_EQ_HIGH)
        and (random.random() < MC_BLUFF_P)
        and stack > 0
        and state.can_complete_bet_or_raise_to()
    ):
        raise_to = max_bet + min(stack, MC_RAISE_BY_CHIPS)
        try:
            state.complete_bet_or_raise_to(raise_to)
            return f"BLUFF_RAISE_TO {int(raise_to)} eq={float(r['equity']):.2f} need={r['breakeven_equity']:.2f} trials={street_trials}"
        except ValueError:
            state.complete_bet_or_raise_to()
            return f"BLUFF_RAISE_MIN eq={float(r['equity']):.2f} need={r['breakeven_equity']:.2f} trials={street_trials}"

    # if we have enough equity to raise, then check if we can legally raise
    if r["equity"] >= MC_RAISE_EQ and stack > 0:
        if state.can_complete_bet_or_raise_to():
            raise_to = max_bet + min(stack, MC_RAISE_BY_CHIPS)
            try:
                state.complete_bet_or_raise_to(raise_to)
                return f"RAISE_TO {int(raise_to)} eq={r['equity']:.2f} need={r['breakeven_equity']:.2f} trials={street_trials}"
            except ValueError:
                state.complete_bet_or_raise_to() # if we can't legally raise, then just do the min legal raise
                return f"RAISE_MIN eq={r['equity']:.2f} need={r['breakeven_equity']:.2f} trials={street_trials}"

    # if all else fails, then just check or call
    state.check_or_call()
    return f"CALL eq={r['equity']:.2f} need={r['breakeven_equity']:.2f} trials={street_trials}"


def expectiminimax_min_policy(state: State, bot_index: int = 0, trials: int = 1500) -> str:
    # read numbers out of PokerKit, call decide_expectiminimax_min(), then apply the chosen PokerKit action
    # the search is only 1 ply and the EV model is simplified

    hero = tuple(state.hole_cards[bot_index])
    board = tuple(state.get_board_cards(0))

    bets = list[int](state.bets)
    to_call = float(max(bets) - bets[bot_index])
    max_bet = float(max(bets))
    stack = float(int(state.stacks[bot_index]))
    can_raise = bool(state.can_complete_bet_or_raise_to())

    # decide the action using the expectiminimax_min algorithm
    r = decide_expectiminimax_min(
        hero,
        board,
        pot_chips=float(state.total_pot_amount),
        to_call=to_call,
        max_bet=max_bet,
        stack=stack,
        can_raise=can_raise,
        trials=trials,
        raise_by=EXPECTIMINIMAX_MIN_RAISE_BY_CHIPS,
    )

    # apply the chosen PokerKit action
    action = str(r["action"])
    amount = int(float(r["amount"]))
    eq = float(r["equity"])
    ev = float(r["best_ev"])
    evs = r.get("action_values", {})
    ev_parts: list[str] = []
    if isinstance(evs, dict):
        for k in ("FOLD", "CALL", "CHECK", "RAISE"):
            if k in evs:
                ev_parts.append(f"{k}={float(evs[k]):.1f}")
    evs_str = (" evs[" + ",".join(ev_parts) + "]") if ev_parts else ""


    if action == "FOLD" and to_call > 0:
        state.fold()
        return f"FOLD eq={eq:.2f} ev={ev:.2f}{evs_str}"

    if action == "RAISE" and can_raise and amount > 0:
        state.complete_bet_or_raise_to(amount)
        if to_call > 0:
            return f"RAISE_TO {amount} eq={eq:.2f} ev={ev:.2f}{evs_str}"
        return f"BET_TO {amount} eq={eq:.2f} ev={ev:.2f}{evs_str}"

    state.check_or_call()
    if to_call > 0:
        return f"CALL eq={eq:.2f} ev={ev:.2f}{evs_str}"
    return f"CHECK eq={eq:.2f} ev={ev:.2f}{evs_str}"


# SUPER SIMPLE VILLAIN THAT JUST CHECKS OR CALLS, want to reach showdowns with villain so we can evaluate the bot
def villain_act(state: State, villain_index: int = 1) -> str:

    bets = list[int](state.bets) #list of bets in front of each player (0 and 1)
    to_call = max(bets) - bets[villain_index] #sees how much villain has to call to match the max bet
    if to_call > 0:
        state.check_or_call()
        return "CALL"

    # If a min bet/raise is legal, do it. otherwise check.
    if state.can_complete_bet_or_raise_to():
        state.complete_bet_or_raise_to()
        return "BET_MIN"
    state.check_or_call()
    return "CHECK"


def play_hand_live(
    state: State,
    bot_index: int = 0,
    trials: int = 8000,
    silent: bool = False,
    bot_policy: str = "mc",
) -> list[str]:
    actions = [] #list that keeps track of each player action
    last_board_len = 0 #keeps track of how many cards are currently on the board, so we know if we need to update
    printed_bot_hand = False
    printed_villain_hand = False

    while state.status: #checks if the game is still ongoing
        if state.can_deal_hole(): #saying if it's still possible to deal a hole to either player, then do it
            state.deal_hole()

            #below functions just help print out each player's hand when they are fully dealt
            hero_cards = ""
            for card in state.hole_cards[0]:
                hero_cards += str(card) + " " #extra space between cards to make it more readable
            if (len(state.hole_cards[0]) == 2) and (not printed_bot_hand): #prints bot hand when it becomes full.
                #had to add the printed_bot_hand part because it would print twice (once after it became full and one more time when the villain was dealt)
                if not silent:
                    print("Bot hand:", hero_cards)
                printed_bot_hand = True

            villain_cards = "" #basically the same thing as bot hand but for the villain
            for card in state.hole_cards[1]: #1 is the villain index
                villain_cards += str(card) + " "
            if (len(state.hole_cards[1]) == 2) and (not printed_villain_hand): #checks if the villain hand is full (double printing hasn't been an issue with villain cards, but wanted to add the logic to both)
                if not silent:
                    print("Villain hand:", villain_cards)
                printed_villain_hand = True

        elif state.can_burn_card():
            state.burn_card() #in poker, always have to burn a card after the flop, turn, and river for randomness
        elif state.can_deal_board(): #saying if it's still possible to deal a board card, then do it
            state.deal_board() #dealing to the board is referring to the community cards like flop, turn, and river
            board = list(state.get_board_cards(0)) #checks how many cards are already on the board, board 0 just means the board that we are playing since pokerkit supports multiple boards
            if len(board) != last_board_len: #if the board got a new card, then we print out the new board
                last_board_len = len(board) #updates length so we can compare again later
                actions.append(f"BOARD {str(board)}")
        elif state.turn_index == bot_index: #if its the bot's turn, then pokerkit deems it legal for it to act
            if bot_policy == "expectiminimax_min":
                a = expectiminimax_min_policy(state, bot_index=bot_index, trials=trials)
            else:
                a = mc_policy(state, bot_index=bot_index, trials=trials)
            actions.append(f"P{bot_index}(BOT) {a}") #logs the action the bot took
        else:
            a = villain_act(state, villain_index=1) #calls villain_act
            actions.append(f"P{1}(VIL) {a}") #logs the action the villain took

    return actions #returns list of actions so we can print later


def main() -> None:

    #loop is basically create a pokerkit heads up no limit texas state, go through play_hand_live and deal/act as pokerkit permits, then print out everything
    #core "game loop" is inside of play_hand_live
    #pokerkit does a lot "grunt" work in tracking, handling, and automating parts of the game
    #things like who's turn it is, what actions are legal, how much either player has bet, etc.


    numtrials = 2000
    state = create_hunl_state() #this is the actual pokerkit state that is tracking everything

    #chance policy to "mc" to use the monte carlo policy
    #change policy here to "expectiminimax_min" to use the expectiminimax_min policy
    actions = play_hand_live(state, bot_index=0, trials=numtrials, bot_policy="expectiminimax_min") #this is the actual loop moving the state forward until the game is over, change bot_policy to "expectiminimax_min" to use the expectiminimax_min policy

    print("\n")
    print("Hand over:", not state.status) #state.status is False when the hand is over, so its a little backwards but makes sense

    print("\n")
    print("Action log:") #prints what each player did during each action
    for line in actions:
        print(line)

    print("\n")
    h, v = int(state.stacks[0]), int(state.stacks[1]) #prints number of chips in each player's stack
    print("Stacks (Bot (seat0), Villain (seat1)):", h, v)

    print("\n")
    board_str = ""
    for card in state.get_board_cards(0):
        board_str += str(card) + " " #extra space between cards
    print("Board:", board_str)


if __name__ == "__main__":
    main()