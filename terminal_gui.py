# terminal_gui.py
# super small "UI" for demos: numbered menu in the terminal (good enough for screen share)
# also supports non-interactive modes via --mode for quick testing
# easiest path for someone grading: python terminal_gui.py

from __future__ import annotations

import argparse
import sys

import analysis
import opencfr_demo
import pokerengine


def print_demo_help() -> None:
    print(
        "\n".join(
            [
                "quick guide (read this once and you're good):",
                "- 1: play one pokerkit hand with the monte carlo bot (pokerengine.mc_policy)",
                "- 2: play one pokerkit hand with the tiny expectiminimax demo (expectiminimax_min.py behind the scenes)",
                "- 3: run the openCFR mccfr external sampling demo (opencfr_demo.py)",
                "- 4: rebuild the graphs (SLOW) -> comparison_outputs/distributions.png (analysis.py)",
            ]
        )
    )


def run_single_hand(trials: int) -> None:
    state = pokerengine.create_hunl_state()
    actions = pokerengine.play_hand_live(
        state,
        bot_index=0,
        trials=trials,
    )

    print("\nHand over:", not state.status)
    print("\nAction log:")
    for line in actions:
        print(line)

    hero_stack, villain_stack = int(state.stacks[0]), int(state.stacks[1])
    print("\nStacks (Bot (seat0), Villain (seat1)):", hero_stack, villain_stack)
    board = " ".join(str(card) for card in state.get_board_cards(0))
    print("Board:", board if board else "(none)")


def run_menu(default_trials: int) -> None:
    print_demo_help()
    while True:
        print("\n=== AI Poker Bot Terminal Menu ===")
        print("1) Play one PokerKit + Monte Carlo hand")
        print("2) Play one PokerKit + Expectiminimax (minimal) hand")
        print("3) Run openCFR demo training")
        print("4) Run analysis and generate plots")
        print("5) Exit")
        choice = input("Select option [1-5]: ").strip()

        if choice == "1":
            raw = input(f"Monte Carlo trials per decision [{default_trials}]: ").strip()
            try:
                trials = default_trials if not raw else int(raw)
                if trials <= 0:
                    raise ValueError("trials must be positive")
            except ValueError:
                print("Invalid trial count. Please enter a positive integer.")
                continue
            run_single_hand(trials)
        elif choice == "2":
            raw = input(f"Expectiminimax MC trials per decision [{default_trials}]: ").strip()
            try:
                trials = default_trials if not raw else int(raw)
                if trials <= 0:
                    raise ValueError("trials must be positive")
            except ValueError:
                print("Invalid trial count. Please enter a positive integer.")
                continue
            state = pokerengine.create_hunl_state()
            actions = pokerengine.play_hand_live(state, bot_index=0, trials=trials, bot_policy="expectiminimax_min")
            print("\nHand over:", not state.status)
            print("\nAction log:")
            for line in actions:
                print(line)
            hero_stack, villain_stack = int(state.stacks[0]), int(state.stacks[1])
            print("\nStacks (Bot (seat0), Villain (seat1)):", hero_stack, villain_stack)
            board = " ".join(str(card) for card in state.get_board_cards(0))
            print("Board:", board if board else "(none)")
        elif choice == "3":
            opencfr_demo.main()
        elif choice == "4":
            analysis.main()
        elif choice == "5":
            print("Exiting.")
            return
        else:
            print("Invalid selection. Please choose 1, 2, 3, 4, or 5.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Terminal GUI for AI Poker Bot demos.")
    parser.add_argument(
        "--mode",
        choices=["menu", "hand", "expectiminimax-min", "cfr", "analysis"],
        default="menu",
        help="Choose which workflow to run.",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=2000,
        help="Monte Carlo trials per decision for hand mode.",
    )
    args = parser.parse_args()

    if args.mode != "menu":
        print_demo_help()

    if args.mode == "menu":
        run_menu(args.trials)
    elif args.mode == "hand":
        run_single_hand(args.trials)
    elif args.mode == "expectiminimax-min":
        state = pokerengine.create_hunl_state()
        actions = pokerengine.play_hand_live(state, bot_index=0, trials=args.trials, bot_policy="expectiminimax_min")
        print("\nHand over:", not state.status)
        print("\nAction log:")
        for line in actions:
            print(line)
        hero_stack, villain_stack = int(state.stacks[0]), int(state.stacks[1])
        print("\nStacks (Bot (seat0), Villain (seat1)):", hero_stack, villain_stack)
        board = " ".join(str(card) for card in state.get_board_cards(0))
        print("Board:", board if board else "(none)")
    elif args.mode == "cfr":
        opencfr_demo.main()
    elif args.mode == "analysis":
        analysis.main()
    else:
        raise ValueError(f"Unsupported mode: {args.mode}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(130)
