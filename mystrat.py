import numpy as np

class Fujin:
    """
    Implements a highly reactive strategy using the previous game's Equity-Normalized 
    Aggression (V-Factor) adjusted by long-term Looseness and a Hand Weakness bonus.
    """
    
    # --- Configuration Constants (Class Attributes) ---
    STARTING_STACK = 10000 
    MAX_SCORE_TREYS = 7462.0 
    # Normalization constant for the V-Factor
    MAX_EXPECTED_STRENGTH = 2.0  
    NUM_PLAYERS = 5
    BUY_IN = 100 
    
    # Window Size: Only the immediately previous game is used
    NUM_GAMES_TO_TRACK = 1 
    
    def __init__(self):
        self.my_index = -1
        
        # 1. Final calculated strength (0-1) for each player.
        self.opponent_strengths = [0.0] * self.NUM_PLAYERS
        
        # 2. Looseness tracking (Used for _calculate_opponent_strength and R1 logic)
        self.looseness_tracker = {
            i: {"games_seen": 0, "games_played": 0} 
            for i in range(self.NUM_PLAYERS)
        }


    def initialize_game(self, match_history, current_game_num):
        """
        Updates the looseness tracker first, then calculates the opponent strength.
        """
        self._update_looseness_tracker(match_history)
        self.opponent_strengths = self._calculate_opponent_strength_final(match_history)


    def _update_looseness_tracker(self, match_history):
        """
        Updates the long-term looseness model based on the last completed game.
        """
        if not match_history:
            return

        last_game = match_history[-1]
        
        for pid_int in range(self.NUM_PLAYERS):
            if pid_int == self.my_index:
                continue

            p_data = last_game.get(pid_int)
            if p_data is None: continue
                
            profile = self.looseness_tracker.get(pid_int)
            
            if p_data.get("hole_cards") and profile is not None:
                profile["games_seen"] += 1
                if not p_data.get("folded", True):
                    profile["games_played"] += 1


    def _calculate_opponent_strength_final(self, match_history):
        """
        Calculates strength based on the last game using:
        1. Equity-Normalized Aggression (V-Factor)
        2. Looseness (L_i)
        3. Hand Weakness Bonus (H_it)
        """
        opponent_strengths = [0.0] * self.NUM_PLAYERS
        
        # Only consider the last game
        if not match_history:
            return opponent_strengths 

        game_data = match_history[-1]
        
        for i in range(self.NUM_PLAYERS):
            if i == self.my_index: 
                continue

            p_data = game_data.get(i)
            # If player was not active in the last game, their strength score defaults to 0.0
            if p_data is None or not p_data.get("hole_cards"):
                opponent_strengths[i] = 0.0
                continue

            # --- 1. Calculate Looseness (L_i) ---
            l_data = self.looseness_tracker.get(i)
            games_seen = l_data.get("games_seen", 0) if l_data else 0
            
            if games_seen > 0:
                looseness = l_data["games_played"] / games_seen
                L_i = max(0.05, min(looseness, 0.5)) 
            else:
                L_i = 0.2 # Default looseness
            
            # --- 2. Calculate Aggression (V-Factor) ---
            r_bets = p_data.get("Round Bets", {})
            r3_win_prob = p_data.get("Win Probabilities", [0, 0, 0])[-1] 
            is_folded = p_data.get("folded", True)

            V_factor = 0.0
            if not is_folded:
                total_bets = r_bets.get(1, 0) + r_bets.get(2, 0) + r_bets.get(3, 0)
                
                if r3_win_prob > 0.01:
                    V_factor = total_bets / (r3_win_prob * self.STARTING_STACK) 
                elif total_bets > 0:
                    # Heuristic for near-zero equity (aggressive, unstable score)
                    V_factor = total_bets / (0.01 * self.STARTING_STACK) 
                
            # --- 3. Calculate Hand Weakness Bonus (H_it) ---
            H_it = 1.0
            final_score = p_data.get("Final Hand Score", self.MAX_SCORE_TREYS)
            # Apply bonus if they reached showdown with a weak hand (Weakness > 0.5)
            if final_score < self.MAX_SCORE_TREYS:
                weakness = min(final_score / self.MAX_SCORE_TREYS, 1.0)
                if weakness > 0.5:
                    # Simple Bonus: Add the weakness factor directly (1.5x max)
                    H_it = 1.0 + weakness 
            
            # --- 4. Final Aggregation (S_Final) ---
            # S_Final = V_Factor * H_it * L_i (Looseness acts as a weight/damper)
            # Using Looseness (L_i) as a simple multiplier for the final score, 
            # implying that aggression from tight players is weighted higher.
            # We use an inverse L_i to reward tight players' aggression: (1 / L_i)
            
            # Simple Scaler: Rewards aggression from tighter players
            L_scaler = min(3.0, 1.0 / L_i) if L_i > 0 else 1.0

            S_final = V_factor * H_it * L_scaler

            # Normalize to [0, 1]
            opponent_strengths[i] = min(S_final / self.MAX_EXPECTED_STRENGTH, 1.0)
            
        return opponent_strengths


    # --- Betting Round Implementations (Placeholder Logic) ---
    
    def round1(self, hole, comm, stacks, pot, win_prob):
        """
        R1 logic: Folds based on a threshold influenced by average opponent strength.
        """
        active_opp_strengths = [s for i, s in enumerate(self.opponent_strengths) if i != self.my_index]
        avg_opp_strength = np.mean(active_opp_strengths) if active_opp_strengths else 0.5
        
        fold_threshold = 0.10 + (0.10 * avg_opp_strength)
        
        if win_prob < fold_threshold:
            return "fold", 0

        # Bet size scales with equity, amplified if average opponent is weak
        bet_size = self.BUY_IN + win_prob * (300 - self.BUY_IN) * (1.5 - avg_opp_strength)
        
        return "play", max(100.0, min(300.0, bet_size))


    def round2(self, hole, comm, r1_bets, stacks, pot, win_prob):
        
        base_bet = r1_bets[self.my_index]
        
        is_opp_aggressive = any(b > base_bet for i, b in r1_bets.items() if i != self.my_index and i < self.NUM_PLAYERS)
        
        multiplier = 0.5 + win_prob
        
        if win_prob > 0.7 and not is_opp_aggressive:
            multiplier = 1.5
        elif win_prob < 0.4 and is_opp_aggressive:
            multiplier = 0.5
            
        return max(base_bet * 0.5, min(base_bet * 1.5, base_bet * multiplier))

    def round3(self, hole, comm, r1_bets, r2_bets, stacks, pot, win_prob):
        
        base_bet = r2_bets[self.my_index]
        
        multiplier = 0.75 + win_prob * 0.5 
        
        if win_prob > 0.8:
            multiplier = 1.25
        elif win_prob < 0.5:
            multiplier = 0.75
            
        return max(base_bet * 0.75, min(base_bet * 1.25, base_bet * multiplier))