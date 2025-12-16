"""
main.py

This file orchestrates the entire tournament.
It handles:
    1. Importing core components (constants, PlayerState, helper functions) from engine_core.py.
    2. Importing strategies (participant strategies or dummy fallbacks) from dummy_strategies.py.
    3. The main play_match() loop that runs the games, manages state, and calls strategy methods.
"""

# Import necessary components from the core engine file
# This gives us access to configuration, classes, and poker math functions.
from engine_core import (
    NUM_GAMES, STARTING_STACK, BUY_IN, PLAYER_NAMES, PlayerState,
    create_deck, calculate_multiplayer_equity, evaluate_hand,
)

# Import the pre-loaded strategy objects from the strategy file.
# These variables (strategyA, strategyB, etc.) are instances of the strategy classes.
from dummy_strategies import (
    strategyA, strategyB, strategyC, strategyD, strategyE
)

# Import standard library components needed for the game loop
import random
import copy
import sys
import itertools


# ============================================================
# 1. STRATEGY INSTANCES
# ============================================================
# List of strategy objects that will play in each game.
# These were already loaded/replaced by the logic in dummy_strategies.py.
PLAYERS = [strategyA, strategyB, strategyC, strategyD, strategyE]


# ============================================================
# 2. MAIN GAME LOOP: play_match()
# ============================================================

def play_match():
    """
    Runs the entire tournament simulation across NUM_GAMES.
    """
    # Create PlayerState objects, one for each strategy, binding them to a name and index.
    players = [PlayerState(name, strat, i) for i, (name, strat) in enumerate(zip(PLAYER_NAMES, PLAYERS))]
    
    # CRITICAL SETUP: Assign each strategy its index (0-4) for internal reference.
    # This is how strategies identify their own data in lists (stacks, bets).
    for p in players:
        p.strategy.my_index = p.index
        
    # match_history stores a full log of every completed game.
    # This is passed to strategies at the start of each new game.
    match_history = []

    # Tracks wins (fractional for ties) across the whole tournament.
    no_of_wins = [0] * len(players)

    # Current number of players actively participating in the match.
    current_num_players = len(players)

    # --- Start Game Loop ---
    for game_num in range(1, NUM_GAMES + 1):
        print(f"\n--- Starting Game {game_num} ---")

        # Call the external initialization hook for each strategy.
        # This allows strategies to update their internal opponent models 
        # based on the history of previous games.
        for p in players:
            p.strategy.initialize_game(match_history, game_num)
        
        # ------------------------------------------------------------
        # ROUND 0: Setup and Buy-in
        # ------------------------------------------------------------
        print("\n", "\n", "Round 0 starting: Buy-ins and Dealing")
        pot = 0
        deck = create_deck()
        random.shuffle(deck)
        community_cards = []
        active_players_indices = []

        for p in players:
            # Reset all per-game state (cards, bets, fold status)
            p.reset_round()
            
            # Skip players who were previously eliminated.
            if p.is_lost_match:
                continue

            # Check if player can afford the BUY_IN.
            if p.stack < BUY_IN:
                # Elimination: Player cannot afford the buy-in.
                print(f"{p.name} eliminated! Stack ({p.stack:.2f}) < {BUY_IN}.")
                pot += p.stack # Any remaining stack is added to the pot for logging (but stack becomes 0)
                p.stack = 0
                p.is_lost_match = True
            else:
                # Player is active this game: pay buy-in and receive cards.
                p.stack -= BUY_IN
                pot += BUY_IN
                p.hole_cards = [deck.pop(), deck.pop()]
                print(f"{p.name} is dealt: {p.hole_cards}")
                active_players_indices.append(p.index)

        # Deal the conceptual 5 community cards now (to be revealed later).
        community_cards = [deck.pop() for _ in range(5)]
        print(f"The community cards are: {community_cards}")

        # Safety Check: Stop if not enough competitors remain.
        if len(active_players_indices) < 2:
            print("Not enough players to continue match.")
            break

        # ------------------------------------------------------------
        # ROUND 1: FLOP BETTING (3 community cards shown)
        # ------------------------------------------------------------
        visible_community = community_cards[:3]
        print("\n", "\n", "Round 1 starting: Flop Betting")
        print(f"Visible Community Cards for Round 1 (Flop): {visible_community}")
        
        # Determine who is eligible to bet in R1 (must afford minimum bet of 100).
        round1_active_indices = []
        current_stacks = [p.stack for p in players] # Snapshot of stacks before betting.

        for idx in active_players_indices:
            p = players[idx]
            if p.stack < 100:
                 # Elimination: Player cannot afford the R1 minimum bet.
                 print(f"{p.name} eliminated! Stack ({p.stack:.2f}) < 100.")
                 pot += p.stack
                 p.stack = 0
                 p.is_lost_match = True
            else:
                 round1_active_indices.append(idx)

        # r1_bets tracks the amount bet in R1 by each player (0 if folded/inactive).
        r1_bets = {idx: 0 for idx in range(len(players))}

        # Each active player makes a decision.
        for idx in round1_active_indices:
            p = players[idx]

            # Calculate Hero's win probability on the current board (Flop).
            # The calculation considers all players active at the start of the game (current_num_players).
            win_prob = calculate_multiplayer_equity(p.hole_cards, visible_community, num_players=len(round1_active_indices))

            print(f"Equity: {win_prob*100:.2f}%, {p.name}", end=' ')

            # STRATEGY CALL: Get the Round 1 decision.
            action, val = p.strategy.round1(p.hole_cards, visible_community, current_stacks, pot, win_prob)

            if action == "fold":
                p.has_folded = True
                print(" chose to fold.")
            else:
                # Engine enforces bet range: [100, 300].
                price = max(100.0, min(300.0, float(val)))
                
                # Cannot bet more than current stack.
                price = min(price, p.stack)

                p.current_bet_r1 = price
                r1_bets[idx] = price
                p.stack -= price
                pot += price
                print(f" chose to bet ${price:.2f}.")
            
            # Log the equity for history.
            p.round_equities.append(win_prob)

        # After Round 1, check how many players are still in.
        round1_post_fold_indices = [i for i in round1_active_indices if not players[i].has_folded]
        
        # EARLY WIN CONDITION: If only one player remains, they win the pot immediately.
        if len(round1_post_fold_indices) == 1:
            winner_idx = round1_post_fold_indices[0]
            winner = players[winner_idx]
            
            # Winning Cap calculation uses R1 bet as the base for early termination.
            winner_bet = winner.current_bet_r1 
            winning_cap = 4 * (BUY_IN + winner_bet)
            actual_win = min(winning_cap, pot)
            
            # Pay winner and log.
            winner.stack += actual_win
            no_of_wins[winner.index] += 1
            
            print("\n*** EARLY WINNER (Fold Equity) ***")
            print(f"{winner.name} wins by fold! Pot: ${pot:.2f}. Payout: ${actual_win:.2f}")

            # Prepare truncated history log.
            round_history = {}
            for p in players:
                # Note: final_score is dummy and final_bet is 0 if no showdown.
                round_history[p.index] = {
                    "hole_cards": p.hole_cards,
                    "final_score": 7463, 
                    "folded": p.has_folded,
                    "final_bet": 0, 
                    "equities": p.round_equities,
                    "stack": p.stack
                }
            round_history["community_cards"] = community_cards[:3] # Log only visible cards.
            round_history["pot_final"] = pot
            match_history.append(round_history)

            # Print end-of-game stacks and move to next game.
            for p in players:
                print(f"{p.name}: ${p.stack:.2f}")
            continue

        # ------------------------------------------------------------
        # ROUND 2: TURN BETTING (4 community cards visible)
        # ------------------------------------------------------------
        visible_community = community_cards[:4]
        print("\n", "\n", "Round 2 starting: Turn Betting")
        print(f"Visible Community Cards for Round 2 (Turn): {visible_community}")
        
        # Only players who *did not fold* in Round 1 can proceed.
        round2_active_indices = round1_post_fold_indices

        # r2_bets tracks the amount bet in R2.
        r2_bets = {idx: 0 for idx in range(len(players))}
        
        # Number of players currently in the hand (used for equity calculation).
        num_r2_players = len(round2_active_indices)
        if num_r2_players == 0:
            print("No players remain in Round 2.")
            # Prepare truncated history log.
            round_history = {}
            for p in players:
                # Note: final_score is dummy and final_bet is 0 if no showdown.
                round_history[p.index] = {
                    "hole_cards": p.hole_cards,
                    "final_score": 7463, 
                    "folded": p.has_folded,
                    "final_bet": 0, 
                    "equities": p.round_equities,
                    "stack": p.stack
                }
            round_history["community_cards"] = community_cards[:3] # Log only visible cards.
            round_history["pot_final"] = pot
            match_history.append(round_history)

            # Print end-of-game stacks and move to next game.
            for p in players:
                print(f"{p.name}: ${p.stack:.2f}")
            continue


        for idx in round2_active_indices:
            p = players[idx]

            # Recalculate win probability on the Turn (4 community cards).
            win_prob = calculate_multiplayer_equity(p.hole_cards, visible_community, num_players=num_r2_players)

            # STRATEGY CALL: Round 2 decision (returns a single bet value).
            val = p.strategy.round2(p.hole_cards, visible_community, r1_bets, current_stacks, pot, win_prob)

            # Engine enforces bet range relative to R1 bet: 
            #   0.5 * R1 <= R2 <= 1.5 * R1
            min_p = p.current_bet_r1 * 0.5
            max_p = p.current_bet_r1 * 1.5
            price = max(min_p, min(max_p, float(val)))

            # Cap bet at remaining stack.
            price = min(price, p.stack)

            print(f"Equity: {win_prob*100:.2f}%, {p.name} bet {price:.2f} in round 2")

            p.current_bet_r2 = price
            r2_bets[idx] = price
            p.stack -= price
            pot += price

            # Log Round 2 equity.
            p.round_equities.append(win_prob)


        # ------------------------------------------------------------
        # ROUND 3: RIVER BETTING (all 5 community cards visible)
        # ------------------------------------------------------------
        visible_community = community_cards
        print("\n", "\n", "Round 3 starting: River Betting")
        print(f"Visible Community Cards for Round 3 (River): {visible_community}")
        
        # Players active in R2 proceed to R3.
        num_r3_players = len(round2_active_indices)
        if num_r3_players == 0:
            continue
            
        for idx in round2_active_indices:
            p = players[idx]

            # Final win probability using the full board (River).
            win_prob = calculate_multiplayer_equity(p.hole_cards, visible_community, num_players=num_r3_players)

            # STRATEGY CALL: Round 3 decision (returns a single bet value).
            val = p.strategy.round3(p.hole_cards, visible_community, r1_bets, r2_bets, current_stacks, pot, win_prob)

            # Engine enforces bet range relative to R2 bet: 
            #   0.75 * R2 <= R3 <= 1.25 * R2
            min_p = p.current_bet_r2 * 0.75
            max_p = p.current_bet_r2 * 1.25
            price = max(min_p, min(max_p, float(val)))

            # Cap bet at remaining stack.
            price = min(price, p.stack)

            print(f"Equity: {win_prob*100:.2f}%, {p.name} bet {price:.2f} in round 3")

            # Finalize Round 3 bet (this is the final bet used for pot cap).
            p.final_round_bet = price
            p.stack -= price
            pot += price

            # Log Round 3 equity.
            p.round_equities.append(win_prob)

        # ------------------------------------------------------------
        # 3. SHOWDOWN & POT ALLOCATION
        # ------------------------------------------------------------
        print("\n", "\n", "Showdown & Pot Allocation")

        best_score = 7463 # Worst possible hand score in treys.
        winners = []
        round_history = {} 

        # Step 1: Evaluate hands for all players who did not fold.
        for idx in active_players_indices:
            p = players[idx]
            score = 0
            is_folded = p.has_folded
            
            if not is_folded:
                # Calculate the final hand score (lower is better).
                score = evaluate_hand(p.hole_cards, community_cards)
                p.hand_score = score
                
                # Determine the best hand(s).
                if score < best_score:
                    best_score = score
                    winners = [p]
                elif score == best_score:
                    winners.append(p)
            
            # Log player data regardless of fold status.
            round_history[p.index] = {
                "hole_cards": p.hole_cards,
                "final_score": score,
                "folded": is_folded,
                "final_bet": p.final_round_bet,
                "equities": p.round_equities,
                "stack": p.stack
            }

        if not winners:
            print("Error: No winner determined in showdown.")
            continue

        # Step 2: Split Pot among winners and Apply Winning Cap.
        num_winners = len(winners)
        winning_pot_share_max = pot / num_winners # What each winner would get without a cap.
        total_win = 0
        
        for winner in winners:
            # Record the win (fractional if drawn).
            no_of_wins[winner.index] += 1 / num_winners
            
            # Winning cap logic: max payout = 4 * (BUY_IN + final_round_bet)
            winning_cap = 4 * (BUY_IN + winner.current_bet_r1 + winner.current_bet_r2 + winner.final_round_bet)
            actual_win_for_winner = min(winning_cap, winning_pot_share_max)
            
            # Distribute capped winnings.
            winner.stack += actual_win_for_winner
            total_win += actual_win_for_winner

        remaining_pot = pot - total_win

        # Finalize history log for this game.
        round_history["community_cards"] = community_cards
        round_history["pot_final"] = pot
        match_history.append(round_history)
        
        # Output results.
        winner_names = ", ".join([w.name for w in winners])

        if num_winners > 1:
            print(f"**DRAW!** Winners: {winner_names} all share Hand Score {best_score}")
        else:
            print(f"Winner: {winner_names} with Hand Score {best_score}")

        print(f"Total Pot: {pot:.2f}, Total Win Amount Distributed: {total_win:.2f}")
        
        # Step 3: Redistribution Law
        # Any pot left over due to the cap is redistributed evenly among 
        # players who reached the River (i.e., active in Round 3 / Round 2).
        if remaining_pot > 0:
            recipients = [players[i] for i in round2_active_indices] # Players who were active in R2/R3.
            if recipients:
                share = remaining_pot / len(recipients)
                print(f"Redistributing {remaining_pot:.2f} ({share:.2f} each) to {len(recipients)} late-round players.")
                for p in recipients:
                    p.stack += share

        # Print stacks after this game.
        print("\nGame End Stacks:")
        for p in players:
            print(f"{p.name}: ${p.stack:.2f}")

    # ========================================================
    # 4. FINAL RESULTS
    # ========================================================
    print("\n--- Match Over ---")
    final_stacks = [(p.name, p.stack) for p in players]
    # Sort players by final stack size.
    final_stacks.sort(key=lambda x: x[1], reverse=True)
    
    print("\nFinal Standings:")
    for name, stack in final_stacks:
        print(f"{name}: ${stack:.2f}")

    print("\nTotal Fractional Wins per Player:")
    for i, p in enumerate(players):
        print(f"{p.name}: {no_of_wins[i]} wins")

    print("\nNote: This rankings are for demonstration purpose only. Clearly, these are highly influenced by the number of wins of the players. Focus only on maximising profit in a game with a winning hand, and minimising loss in a game with a losing hand. ")


# Standard Python entry-point pattern: run the tournament if main.py is executed directly.
if __name__ == "__main__":
    play_match()