from pokerkit import Automation, NoLimitTexasHoldem
from pokerkit.state import State

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


def bot_act_mc(state: State, bot_index: int = 0, trials: int = 8000) -> str:

    hero = tuple(state.hole_cards[bot_index]) #the bot's hole cards
    board = tuple(state.get_board_cards(0)) #gets the board gardss

    bets = list[int](state.bets) # list of bets in front of each player (0 and 1)
    to_call = max(bets) - bets[bot_index] # difference between max bet and bot's bet (so would be 0 if bot has put up the max bet)
    max_bet = max(bets) # max bet on the table (helps know how much to raise to)
    stack = int(state.stacks[bot_index]) # how many chips the bot has left in their stack


    #CHANGE THESE VALUES IF WANT TO CHANGE THE BOT'S RAISE BEHAVIOR/AGGRESSION
    RAISE_EQ = 0.70 #just saying how much equity is required by monte carlo to raise

    # BET_TO and RAISE_BY only happens RAISE_EQ is met and stack is greater than 0
    BET_TO = 20 #bets 20 if to_call is 0 (villain bot does a check)
    RAISE_BY = 20 #raise by 20 when to_call is greater than 0 (villain bot does a bet)


    wins, losses, ties, eq = estimate_hu_equity(hero, board, trials=trials, seed=None) #estimate_hu_equity is imported in from mcequity.py

    # When facing no bet (to_call == 0): either value-bet or check. Do not use call/fold MC here.
    if to_call <= 0:
        #starts the street off with a bet if equity is high enough
        if eq >= RAISE_EQ and stack > 0 and state.can_complete_bet_or_raise_to(): #if we have high enough equity to raise, as well as having the chips and approval from pokerkit, then we bet to BET_TO
            bet_to = min(stack, BET_TO) #go all in if we have enough chips to cover the bet
            state.complete_bet_or_raise_to(bet_to) #pokerkit function handles the bet
            return f"BET_TO {bet_to} eq={eq:.2f} need=0.00"
        state.check_or_call() #if we don't have high enough equity to raise, then we just check
        return f"CHECK eq={eq:.2f} need=0.00"


    # this block only matters if the villain bot does a bet (like when to_call is greater than 0)

    r = decide_with_mc(hero, board, pot_chips=float(state.total_pot_amount), to_call=float(to_call), trials=trials, seed=None) #calls decide_with_mc which is imported in from mcequity.py
    if r["action"] == "FOLD":
        state.fold()
        return f"FOLD eq={r['equity']:.2f} need={r['breakeven_equity']:.2f}"

    #if fold doesnt happen, then we see if we can raise
    # basically if the bot has enough equity to raise, raise to RAISE_BY (which is 6)
    if r["equity"] >= RAISE_EQ and stack > 0: #same idea as above here
        if state.can_complete_bet_or_raise_to(): #asks pokerkit if legal
            raise_to = max_bet + min(stack, RAISE_BY) #looks at how much the max bet currently is and then raises
            state.complete_bet_or_raise_to(raise_to) #pokerkit function handles the bet or raise to the amount of raise_to
            return f"RAISE_TO {int(raise_to)} eq={r['equity']:.2f} need={r['breakeven_equity']:.2f}"
    else:
        state.check_or_call() # does a regular check orcall if equity is not high enough to raise
        return f"CALL eq={r['equity']:.2f} need={r['breakeven_equity']:.2f}"

# SUPER SIMPLE VILLAIN THAT JUST CHECKS OR CALLS
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


def play_hand_live(state: State, bot_index: int = 0, trials: int = 8000, silent: bool = False) -> list[str]:
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
            a = bot_act_mc(state, bot_index=bot_index, trials=trials) #calls bot_act_mc which helps it make decisions. the # of trials is how many times it runs the monte carlo simulation
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
    actions = play_hand_live(state, bot_index=0, trials=numtrials) #this is the actual loop moving the state forward until the game is over

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