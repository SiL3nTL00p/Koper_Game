"""
engine_core.py

Core engine components extracted from main.py:
 - configuration constants (NUM_GAMES, STARTING_STACK, BUY_IN, etc.)
 - PlayerState class (Manages per-player, per-game data)
 - TREYS / equity helper functions (Poker card math and win probability calculation)
 - Uses the 'treys' library (Evaluator, Card, lookup) for hand scoring.
 - Preserves original function signatures and behavior from the source file.
"""

import random
import itertools
# Note: Ensure the 'treys' library is installed: pip install treys
from treys import Evaluator, Card, lookup


# ============================================================
# 1. CONFIGURATION
# ============================================================
#
# These constants define the fundamental rules and structure of the tournament.

NUM_GAMES = 50          # Total number of games (hands) to be played in the match.
STARTING_STACK = 10000  # The initial stack (money) each player starts with.
BUY_IN = 100            # The mandatory amount paid by all active players to enter each game (hand).

# Friendly labels for printing and logging. These correspond to the strategies loaded.
PLAYER_NAMES = ["Player A", "Player B", "Player C", "Player D", "Player E"]

# Standard card representation:
#   - SUITS: 'h' (hearts), 'd' (diamonds), 's' (spades), 'c' (clubs)
#   - RANKS: '2'..'9', 'T' (Ten), 'J' (Jack), 'Q' (Queen), 'K' (King), 'A' (Ace)
SUITS = ['h', 'd', 's', 'c']
RANKS = ['2','3','4','5','6','7', '8', '9', 'T', 'J', 'Q', 'K', 'A']


# ============================================================
# 2. PLAYER STATE CLASS
# ============================================================
#
# PlayerState is a container that holds all mutable, real-time data for one player
# in the context of the tournament and the current game.

class PlayerState:
    def __init__(self, name, strategy, index):
        self.name = name                 # Player's display name (e.g., "Player A").
        self.strategy = strategy         # Reference to the actual strategy object (e.g., strategyA).
        self.index = index               # Unique index (0 to N-1) for this player, used for lookup.

        # Tournament-Level State (Persists across games):
        self.stack = STARTING_STACK      # Current total money available.
        self.is_lost_match = False       # True if stack < BUY_IN, meaning player is eliminated.

        # Game-Level State (Resets every hand):
        self.hole_cards = []             # The 2 private cards dealt to the player.
        self.current_bet_r1 = 0          # Amount bet in Round 1 (Flop).
        self.current_bet_r2 = 0          # Amount bet in Round 2 (Turn).
        self.final_round_bet = 0         # Amount bet in Round 3 (River). Used for the winning cap.
        self.has_folded = False          # Whether this player chose to fold in any betting round.
        self.hand_score = 0              # Final numerical score (treys format: lower is better).
        self.round_equities = []         # Stores [R1 equity, R2 equity, R3 equity] for history.

    def reset_round(self):
        """
        Resets all per-game (hand) state before dealing new cards, but preserves the stack.
        Called by main.py at the start of every new game.
        """
        self.hole_cards = []
        self.current_bet_r1 = 0
        self.current_bet_r2 = 0
        self.final_round_bet = 0
        self.hand_score = 0
        self.has_folded = False
        self.round_equities = []


# ============================================================
# 3. TREYS / EQUITY HELPER FUNCTIONS
# ============================================================

# treys hand evaluator instance. This is used globally for all hand scoring.
evaluator = Evaluator() 


def create_deck():
    """
    Generates a list of all 52 card strings, e.g., 'Ah', 'Td', '7s'.
    This is the initial, unshuffled deck.
    """
    return [r + s for s in SUITS for r in RANKS]


def evaluate_best_hand(seven_cards):
    """
    Calculates the best possible 5-card score (lower is better) from a 7-card set
    (2 hole cards + 5 community cards) using the 'treys' evaluator.
    
    Args:
        seven_cards (list[str]): A list of 7 card strings (e.g., ['Ad', 'As', 'Kd', 'Ks', 'Qd', 'Qs', 'Jd']).

    Returns:
        int: The numerical treys score (1=Royal Flush, 7462=7-high).
    """
    # The worst possible score in treys is 7462, use 7463 as the sentinel.
    best_score = 7463 
    
    # Check all possible 5-card combinations from the 7 available cards.
    for combo in itertools.combinations(seven_cards, 5):
        try:
            # Convert string representation (e.g., 'Ah') to treys Card objects.
            combo_objs = [Card.new(c) for c in combo]
            
            # Evaluate the 5-card combination.
            # treys.evaluate expects two lists: hand and board. We put all 5 cards
            # in the 'hand' argument and use an empty board '[]'.
            score = evaluator.evaluate(combo_objs, []) 
            
            # Find the minimum (best) score.
            if score < best_score:
                best_score = score
        except Exception:
            # Ignore any errors during card parsing (should not happen with valid input).
            continue
            
    return best_score


def get_clean_deck():
    """
    Returns a consistent list of 52 card strings for simulation purposes.
    (Used mainly by the equity calculator).
    """
    ranks = '23456789TJQKA'
    suits = 'hdsc'
    return [r+s for r in ranks for s in suits]


def calculate_multiplayer_equity(hero_hand, current_board, num_players=5, iterations=500):
    """
    Estimates the win probability (equity) for the Hero's hand against a field
    of randomly dealt opponents using Monte Carlo simulation.
    
    This function is computationally expensive and runs on a background thread in the real
    competition environment (not shown here) but runs synchronously in this file.

    Args:
        hero_hand (list[str]): Hero's two hole cards (e.g., ['Ad', 'Ks']).
        current_board (list[str]): The community cards revealed so far (0, 3, 4, or 5 cards).
        num_players (int): The total number of players currently in the hand.
        iterations (int): The number of times to run the simulation.

    Returns:
        tuple (float, float): (Win Percentage, Tie Percentage - unused/returns 0.0)
    """
    wins = 0
    full_deck = get_clean_deck()
    
    # Identify all cards we know (Hero's hand + community board).
    known_cards = set(hero_hand + current_board)
    
    # The deck of unknown cards from which opponents and remaining board cards will be drawn.
    remaining_deck = [c for c in full_deck if c not in known_cards]
    num_opponents = num_players - 1

    for _ in range(iterations):
        random.shuffle(remaining_deck)
        
        # Calculate how many community cards are still needed (max 5).
        cards_needed_on_board = 5 - len(current_board)
        
        # Safety check: Ensure enough cards exist in the deck for the simulation run.
        if cards_needed_on_board + num_opponents * 2 > len(remaining_deck):
            continue

        # 1. Complete the board (the 'runout' of remaining community cards).
        runout = remaining_deck[:cards_needed_on_board]
        final_board = current_board + runout
        
        # 2. Deal 2 cards per opponent from the remaining deck.
        deck_idx = cards_needed_on_board
        opponent_hands = []
        for _ in range(num_opponents):
            opp_hole = remaining_deck[deck_idx : deck_idx + 2]
            opponent_hands.append(opp_hole)
            deck_idx += 2

        # 3. Evaluate Hero's final 7-card hand score.
        hero_score = evaluate_best_hand(hero_hand + final_board)
        
        # 4. Evaluate all Opponents' final 7-card hand scores.
        opp_scores = [evaluate_best_hand(opp_hole + final_board) for opp_hole in opponent_hands]
        
        # Find the best score among all opponents (lowest numerical score).
        if not opp_scores:
            # If no opponents (num_players=1), Hero always wins.
            best_opponent_score = 7463 
        else:
            best_opponent_score = min(opp_scores)

        # 5. Check outcome for this iteration.
        if hero_score < best_opponent_score:
            wins += 1    # Hero wins (score is lower/better than best opponent)
        elif hero_score == best_opponent_score:
            wins += 0.5  # Hero ties with the best opponent

    # Calculate final win percentage based on total iterations.
    if iterations == 0:
        win_pct = 0.0
    else:
        # Scale to 0-100%
        win_pct = (wins / iterations) * 100

    return win_pct/100

def evaluate_hand(hole_cards, community_cards):
    """
    A simple wrapper function used at Showdown (end of the hand) to get the final score.
    
    Args:
        hole_cards (list[str]): Hero's two cards.
        community_cards (list[str]): All five community cards.

    Returns:
        int: The numerical treys score of the player's best 5-card hand.
    """
    return evaluate_best_hand(hole_cards + community_cards)