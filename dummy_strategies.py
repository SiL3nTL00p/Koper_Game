"""
dummy_strategies.py

This file contains ONLY:
    • The 5 Dummy Strategies used as examples / fallbacks.
    • Clean, per-strategy import logic for participant strategies.
    • No engine logic, no play_match, no deck, no evaluator.

WHY THIS FILE EXISTS:
---------------------
This file acts as a "teaching set" for participants.
Each DummyStrategy shows HOW to use the information provided
by the engine in round1, round2, round3:
    - hole cards
    - community cards
    - stacks
    - pot
    - win_prob
    - r1_bets, r2_bets
    - tournament history
    - self.my_index

Participants who read this file understand:
    • What a strategy class looks like
    • What functions they must implement
    • What information they will receive each round
    • How to return legal actions/bets
"""


# ======================================================================
# =========================  DUMMY STRATEGIES  ==========================
# ======================================================================
# These strategies serve as EXAMPLES.
# They deliberately show different "themes" and are optimized to be
# simple, clear, and competitively robust for testing purposes.
# ======================================================================



# ----------------------------------------------------------------------
# --------------------------- DummyStrategy1 (Equity) ----------------------------
# ----------------------------------------------------------------------
class DummyStrategy1:
    """
    PURPOSE:
        • Demonstrates the simplest possible equity-based logic.
        • Good "starter example" showing the basic return format.

    WHAT IT TEACHES:
        • win_prob is a number 0..1 (your estimated chance of winning).
        • You can scale your bets linearly using win_prob.
        • Fold when equity is very low.
    """

    def __init__(self):
        # The engine sets this: tells the strategy what player number it is (0–4).
        self.my_index = -1

    def initialize_game(self, match_history, current_game_num):
        # This strategy does not use game history, so we pass.
        pass

    def round1(self, hole, comm, stacks, pot, win_prob):
        """
        RETURNS: ("fold", 0) OR ("play", amount)
        """
        # Basic example: fold if very weak (equity < 10%).
        if win_prob < 0.10:
            return "fold", 0

        # Otherwise bet between 100–300 (engine clamps).
        # Bet linearly scales from 100 (min) up to 300 (max) based on win_prob.
        return "play", 100 + win_prob * 200

    def round2(self, hole, comm, r1_bets, stacks, pot, win_prob):
        # Demonstrates using your Round 1 bet as a base.
        base = r1_bets[self.my_index]
        
        # Bet multiplier scales from 0.5x (min allowed) to 1.5x (max allowed).
        # win_prob=0 -> 0.5x, win_prob=1 -> 1.5x
        return base * (0.5 + win_prob)

    def round3(self, hole, comm, r1_bets, r2_bets, stacks, pot, win_prob):
        # Demonstrates using your Round 2 bet as a base.
        base = r2_bets[self.my_index]
        
        # Bet multiplier scales from 0.75x (min allowed) to 1.25x (max allowed).
        # win_prob=0 -> 0.75x, win_prob=1 -> 1.25x
        return base * (0.75 + win_prob * 0.5)



# ----------------------------------------------------------------------
# --------------------------- DummyStrategy2 (Opponent Bets) ----------------------------
# ----------------------------------------------------------------------
class DummyStrategy2:
    """
    PURPOSE:
        • Demonstrates how to read >>> opponent bets <<< using r1_bets/r2_bets.

    WHAT IT TEACHES:
        • You can loop through rX_bets (DICT of {player_index : amount}).
        • Compare others’ bets with your own (self.my_index).
        • Adjust aggression based on how many opponents are betting high.
    """

    def __init__(self):
        self.my_index = -1
    def initialize_game(self, *args):
        pass

    def round1(self, hole, comm, stacks, pot, win_prob):
        if win_prob < 0.10:
            return "fold", 0
        return "play", 100 + win_prob * 200

    def round2(self, hole, comm, r1_bets, stacks, pot, win_prob):
        my_bet = r1_bets[self.my_index]
        
        # Count opponents whose R1 bet was higher than ours
        higher = sum(b > my_bet for b in r1_bets.values())

        # If we are strong and no one is fighting us, bet max (1.5x)
        if win_prob > 0.6 and higher == 0:
            multiplier = 1.5
        # If we are weak or opponents are aggressive, bet minimum (0.5x)
        else:
            multiplier = 0.5
            
        return my_bet * multiplier

    def round3(self, hole, comm, r1_bets, r2_bets, stacks, pot, win_prob):
        my_bet = r2_bets[self.my_index]
        
        # Count opponents whose R2 bet was higher than ours
        higher = sum(b > my_bet for b in r2_bets.values())

        # If we are very strong and no one is fighting us, bet max (1.25x)
        if win_prob > 0.7 and higher == 0:
            multiplier = 1.25
        # Otherwise, bet minimum (0.75x)
        else:
            multiplier = 0.75
            
        return my_bet * multiplier


# ----------------------------------------------------------------------
# --------------------------- DummyStrategy3 (Memory: Equity Trend) ---------------------------
# ----------------------------------------------------------------------
class DummyStrategy3:
    """
    PURPOSE:
        • Demonstrates storing memory INSIDE the class instance.

    WHAT IT TEACHES:
        • How to store state variables (like win_prob) between rounds
          of the same hand using 'self.variable'.
        • Logic: Compares current win_prob to previous win_prob. If equity
          improved, we bet aggressively; if it worsened, we bet cautiously.
    """

    def __init__(self):
        self.my_index = -1
        # Memory across rounds of the SAME GAME/HAND.
        self.prev_winprob_r1 = None
        self.prev_winprob_r2 = None

    def initialize_game(self, match_history, current_game_num):
        # Reset memory for every new game/hand
        self.prev_winprob_r1 = None
        self.prev_winprob_r2 = None

    def round1(self, hole, comm, stacks, pot, win_prob):
        # Store win_prob for Round 2 comparison.
        self.prev_winprob_r1 = win_prob

        if win_prob < 0.10:
            return "fold", 0
        return "play", 100 + win_prob * 200

    def round2(self, hole, comm, r1_bets, stacks, pot, win_prob):
        old = self.prev_winprob_r1
        base = r1_bets[self.my_index]
        # Store current win_prob for Round 3 comparison.
        self.prev_winprob_r2 = win_prob 

        if old is None: return base * 1.0 # Neutral if no prior data

        # Aggressive (1.5x) if the new board cards increased our win_prob
        if win_prob > old:
            multiplier = 1.5 
        # Cautious (0.5x) if the new board cards hurt our win_prob
        else:
            multiplier = 0.5 
        
        return base * multiplier


    def round3(self, hole, comm, r1_bets, r2_bets, stacks, pot, win_prob):
        old = self.prev_winprob_r2
        base = r2_bets[self.my_index]

        if old is None: return base * 1.0 # Neutral

        # Max bet (1.25x) if hand is strong AND equity improved from R2
        if win_prob > old and win_prob > 0.6:
            multiplier = 1.25
        # Min bet (0.75x) otherwise (if no improvement or weak hand)
        else:
            multiplier = 0.75
        
        return base * multiplier


# ----------------------------------------------------------------------
# --------------------------- DummyStrategy4 (Stack & Pot) --------------------------
# ----------------------------------------------------------------------
class DummyStrategy4:
    """
    PURPOSE:
        • Demonstrates using STACK SIZE and POT SIZE for bet sizing.

    WHAT IT TEACHES:
        • Stack Awareness: How to use 'stacks' to play cautiously when short-stacked.
        • Pot Awareness: How to use 'pot' to increase betting for value when the pot is large.
    """

    def __init__(self):
        self.my_index = -1
    def initialize_game(self, *args):
        pass

    def round1(self, hole, comm, stacks, pot, win_prob):
        my_stack = stacks[self.my_index]
        # Define "short" as having less than 1000 money
        is_short_stacked = my_stack < 1000

        # Fold Check: Play tighter (higher threshold) if short-stacked.
        fold_threshold = 0.20 if is_short_stacked else 0.10
        if win_prob < fold_threshold:
            return "fold", 0

        # Bet max (300) if strong, otherwise bet minimum (100) if short-stacked
        bet = 300 if win_prob > 0.6 else (100 if is_short_stacked else 250)
        return "play", bet

    def round2(self, hole, comm, r1_bets, stacks, pot, win_prob):
        base = r1_bets[self.my_index]

        # Pot Awareness: If the pot is big (e.g., > 1000), we increase the bet.
        is_big_pot = pot > 1000

        # Max bet (1.5x) if strong AND pot is large (max value extraction)
        if win_prob > 0.6 and is_big_pot:
            multiplier = 1.5
        # Base bet (1.0x) if medium strength
        elif win_prob > 0.4:
            multiplier = 1.0
        # Min bet (0.5x) if weak/drawing
        else:
            multiplier = 0.5
            
        return base * multiplier

    def round3(self, hole, comm, r1_bets, r2_bets, stacks, pot, win_prob):
        base = r2_bets[self.my_index]
        
        # Final Round: Purely equity-based value betting.
        if win_prob > 0.7: 
            # Very Strong Hand: Bet max (1.25x)
            multiplier = 1.25
        # Weak/Marginal Hand: Bet minimum (0.75x)
        else:
            multiplier = 0.75
            
        return base * multiplier
            
            
# ----------------------------------------------------------------------
# --------------------------- DummyStrategy5 (Match History) --------------------------
# ----------------------------------------------------------------------
class DummyStrategy5:
    """
    PURPOSE:
        • Demonstrates using TOURNAMENT HISTORY to create a simple opponent looseness model.

    WHAT IT TEACHES:
        • History Model: How to initialize and update a tracking dictionary 
          (self.looseness_model) using data from 'match_history'.
        • Concept: Tracks how often opponents play Round 1 to classify them as 
          "Loose" or "Tight" players and adjust betting for value.
    """

    def __init__(self):
        self.my_index = -1
        # looseness_model: { player_index : { "games_played": int, "games_seen": int } }
        self.looseness_model = {}

    def initialize_game(self, match_history, current_game_num):
        # 1. Initialize profiles on first run
        if current_game_num == 1:
            for i in range(5):
                if i != self.my_index:
                    self.looseness_model[i] = {"games_played": 0, "games_seen": 0}
            return

        # 2. Update profiles based on the LAST completed game
        last_game = match_history[-1]
        for pid_int, pdata in last_game.items():
            if isinstance(pid_int, int) and pid_int != self.my_index:
                
                profile = self.looseness_model.setdefault(pid_int, {"games_played": 0, "games_seen": 0})
                profile["games_seen"] += 1
                # Increment games_played if they did NOT fold in Round 1
                if not pdata.get("folded", False):
                    profile["games_played"] += 1

    def get_avg_opp_looseness(self):
        """Calculates the average looseness score (R1 participation rate) across all opponents."""
        total_looseness = 0.0
        total_players = 0
        
        for profile in self.looseness_model.values():
            if profile["games_seen"] > 0:
                total_looseness += profile["games_played"] / profile["games_seen"]
                total_players += 1
                
        # Default looseness is 20% if no data is available
        return total_looseness / total_players if total_players > 0 else 0.20

    def round1(self, hole, comm, stacks, pot, win_prob):
        avg_looseness = self.get_avg_opp_looseness()
        
        # Fold tighter if the table is very tight (<15% looseness)
        fold_threshold = 0.15 if avg_looseness < 0.15 else 0.10
        if win_prob < fold_threshold:
            return "fold", 0

        # Bet maximum (300) against loose players for value (they call more).
        # Bet minimum (100) against tight players to keep them in.
        bet = 300 if avg_looseness > 0.25 else 100
        return "play", bet

    def round2(self, hole, comm, r1_bets, stacks, pot, win_prob):
        base = r1_bets[self.my_index]
        avg_looseness = self.get_avg_opp_looseness()
        
        # Aggressive (1.3x) if strong (win_prob > 0.6) AND opponents are loose (> 0.25)
        if win_prob > 0.6 and avg_looseness > 0.25:
            multiplier = 1.3
        # Cautious (0.5x) otherwise
        else:
            multiplier = 0.5
            
        return max(base * 0.5, min(base * 1.5, base * multiplier))

    def round3(self, hole, comm, r1_bets, r2_bets, stacks, pot, win_prob):
        base = r2_bets[self.my_index]
        # Final round bet is based purely on our hand strength for simple value.
        multiplier = 1.25 if win_prob > 0.7 else 0.75
        return max(base * 0.75, min(base * 1.25, base * multiplier))


# ======================================================================
# ==================== PARTICIPANT STRATEGY IMPORTS  ====================
# ======================================================================
# The user can submit a file: participant_strategies.py
# containing classes:
#       Strategy1
#       Strategy2
#       Strategy3
#       Strategy4
#       Strategy5
#
# For each one:
#   - If import works → use participant strategy.
#   - If import fails → fallback to DummyStrategyX.
#
# This is SIMPLE, READABLE, and BEGINNER-FRIENDLY.
# ======================================================================

"""Change here the variable YourStrategyName with your team name"""

try:
    from mystrat import YourStrategyName
    strategyA = YourStrategyName()
except ImportError:
    strategyA = DummyStrategy5()

try:
    from mystrat import Strategy2 as ParticipantStrategyB
    strategyB = ParticipantStrategyB()
except ImportError:
    strategyB = DummyStrategy2()

try:
    from mystrat import Strategy3 as ParticipantStrategyC
    strategyC = ParticipantStrategyC()
except ImportError:
    strategyC = DummyStrategy3()

try:
    from mystrat import Strategy4 as ParticipantStrategyD
    strategyD = ParticipantStrategyD()
except ImportError:
    strategyD = DummyStrategy4()

try:
    from mystrat import Strategy5 as ParticipantStrategyE
    strategyE = ParticipantStrategyE()
except ImportError:
    strategyE = DummyStrategy1()