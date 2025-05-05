# from https://github.com/Elytride/adacadabra

import random
import math
from itertools import combinations
from collections import Counter

from pypokerengine.players import BasePokerPlayer

# Map ranks to numerical values for easier comparison
RANK_MAP = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
# List of hand rankings for comparison
HAND_RANKINGS = ['High Card', 'One Pair', 'Two Pair', 'Three of a Kind', 'Straight', 'Flush', 'Full House', 'Four of a Kind', 'Straight Flush', 'Royal Flush']

def setup_ai():
    """Factory function to create the AI instance."""
    return adacadabra()

class adacadabra(BasePokerPlayer):

    def __init__(self):
        """Initialize player state variables."""
        self.my_uuid = None
        self.my_stack = 0
        self.my_index = -1
        self.num_players = 0
        # Track aggression per opponent UUID (currently simple per-street)
        self.table_aggression_history = {}
        # Track VPIP and PFR for each opponent (basic stats)
        self.opponent_stats = {}

    def declare_action(self, valid_actions, hole_card, round_state):
        """Decide on the action to take based on the current round state."""
        # Extract essential information from round_state
        street = round_state['street']
        community_card = round_state['community_card']
        pot_data = round_state['pot']
        dealer_btn_index = round_state['dealer_btn']
        seats = round_state['seats']
        action_histories = round_state['action_histories']
        # small_blind_amount = round_state['small_blind_amount'] # Not directly used in logic

        # Identify self and update instance variables if not already set
        if self.my_uuid is None:
            for i, seat in enumerate(seats):
                if seat['name'] == 'adacadabra':
                    self.my_uuid = seat['uuid']
                    self.my_index = i
                    break
            self.num_players = len(seats)

        # Update stack for the current round
        for seat in seats:
            if seat['uuid'] == self.my_uuid:
                self.my_stack = seat['stack']
                break

        # If self cannot be identified, fold as a safety measure
        if self.my_uuid is None:
             return self.do_fold(valid_actions)

        # Calculate total chips in play to assess chip lead
        total_chips = sum(seat['stack'] for seat in seats)
        has_significant_chip_lead = self.my_stack > 0.40 * total_chips

        # Count active opponents
        num_active_players = len([s for s in seats if s['state'] == 'participating' and s['uuid'] != self.my_uuid])

        # Determine player's position category
        my_position_category = self.get_position_category(self.my_index, dealer_btn_index, self.num_players)

        # Extract available actions and betting information
        can_fold = valid_actions[0]['action'] == 'fold'
        can_call = valid_actions[1]['action'] == 'call'
        amount_to_call = valid_actions[1]['amount']
        can_raise = len(valid_actions) > 2 and valid_actions[2]['action'] == 'raise'

        min_raise = valid_actions[2]['amount']['min'] if can_raise else 0
        max_raise = valid_actions[2]['amount']['max'] if can_raise else self.my_stack

        # Analyze current hand strength, potential, and pot details
        current_hand_strength = self.calculate_hand_strength_new(hole_card, community_card, street, my_position_category)
        hand_potential = self.calculate_hand_potential(hole_card, community_card)
        pot_details = self.calculate_pot_details(pot_data)
        current_pot = pot_details['total_pot']

        # Calculate Pot Odds
        pot_odds_ratio = amount_to_call / (current_pot + amount_to_call) if amount_to_call > 0 else 0
        pot_odds_percent = pot_odds_ratio * 100

        # Analyze Table Aggression (simple per-street)
        street_aggression = self.analyze_table_aggression(action_histories.get(street, []), self.my_uuid)

        # Estimate Win Probability (combining hand strength and potential)
        estimated_win_prob_percent = (current_hand_strength + hand_potential.get('draw_strength_bonus', 0)) * 100

        # --- Decision Logic ---

        # Adjust strategy based on significant chip lead
        if has_significant_chip_lead:
            # Play much tighter when having a significant chip lead
            # Only play very strong hands or call with excellent pot odds

            # Always check if possible (amount_to_call == 0)
            if can_call and amount_to_call == 0:
                return self.do_call(valid_actions)

            # Only consider playing if hand strength is very high
            required_strength_for_action = 0.85
            required_equity_for_call = pot_odds_percent * 1.0

            # Play monster hands aggressively
            if current_hand_strength > 0.95:
                if can_raise: return self.do_all_in(valid_actions, round_state)
                elif can_call: return self.do_call(valid_actions)
                else: return self.do_fold(valid_actions)

            # Play strong hands with controlled aggression
            if current_hand_strength > required_strength_for_action:
                 if can_raise:
                     # Value bet/raise, slightly smaller to avoid scaring opponents
                     raise_amount = min(max_raise, max(min_raise, int(current_pot * 0.6)))
                     raise_amount = max(raise_amount, amount_to_call + min_raise)
                     raise_amount = min(raise_amount, self.my_stack)
                     return self.do_raise(valid_actions, raise_amount, round_state)
                 elif can_call:
                     return self.do_call(valid_actions)
                 else: return self.do_fold(valid_actions)

            # Consider calling with good pot odds and reasonable equity
            if can_call and pot_odds_percent > 30 and estimated_win_prob_percent >= required_equity_for_call:
                 # Add a small random chance to call marginal hands with good odds
                 if random.random() < 0.1:
                      return self.do_call(valid_actions)
                 else:
                      if can_fold: return self.do_fold(valid_actions)
                      else: return self.do_call(valid_actions)

            # Default to Folding when having a chip lead unless conditions for playing are met
            if can_fold:
                return self.do_fold(valid_actions)
            else:
                 return self.do_call(valid_actions) # Must call 0 if fold not an option

        # --- Original Logic (when not having a significant chip lead) ---
        else:
            # Consider all-in situations (short stack or monster hand)
            is_short_stack = self.my_stack < (current_pot + amount_to_call) * 2

            # Play monster hands aggressively (all-in for max value)
            if current_hand_strength > 0.95:
                if can_raise: return self.do_all_in(valid_actions, round_state)
                elif can_call: return self.do_call(valid_actions)
                else: return self.do_fold(valid_actions)

            # Consider aggressive play with strong hands or strong draws
            if current_hand_strength > 0.65 or (street != 'river' and hand_potential['outs'] >= 7):
                 if can_raise:
                     # Be more aggressive with value bets and semi-bluffs
                     if current_hand_strength > 0.8:
                          raise_amount = min(max_raise, max(min_raise, int(current_pot * random.uniform(1.0, 1.5))))
                     elif current_hand_strength > 0.65:
                          raise_amount = min(max_raise, max(min_raise, int(current_pot * random.uniform(0.8, 1.2))))
                     elif street != 'river' and hand_potential['outs'] >= 10:
                          raise_amount = min(max_raise, max(min_raise, int(current_pot * random.uniform(0.6, 1.0))))
                     elif street != 'river' and hand_potential['outs'] >= 7:
                          raise_amount = min(max_raise, max(min_raise, int(current_pot * random.uniform(0.5, 0.8))))
                     else:
                          raise_amount = min_raise

                     # Ensure raise is valid
                     raise_amount = max(raise_amount, amount_to_call + min_raise)
                     raise_amount = min(raise_amount, self.my_stack)

                     # Consider shoving if short stacked with a strong hand or draw
                     if is_short_stack and (current_hand_strength > 0.5 or hand_potential['outs'] >= 8):
                          return self.do_all_in(valid_actions, round_state)
                     else:
                          return self.do_raise(valid_actions, raise_amount, round_state)

                 elif can_call:
                     # Call if estimated win probability is better than pot odds, adjusted for draws/short stack
                     required_equity = pot_odds_ratio
                     if is_short_stack:
                          adjusted_required_equity = required_equity * 0.9
                     else:
                          draw_bonus_factor = hand_potential.get('draw_strength_bonus', 0)
                          if street == 'flop': draw_bonus_factor *= 1.5
                          elif street == 'turn': draw_bonus_factor *= 1.0
                          else: draw_bonus_factor = 0
                          adjusted_required_equity = required_equity * (1 - draw_bonus_factor * 0.5)

                     if estimated_win_prob_percent >= adjusted_required_equity * 100:
                          return self.do_call(valid_actions)
                     else:
                          if can_fold: return self.do_fold(valid_actions)
                          else: return self.do_call(valid_actions)
                 else:
                     if can_fold: return self.do_fold(valid_actions)
                     else: return self.do_call(valid_actions)

            # Consider calling with weaker hands/draws or when not strong/drawing
            if can_call:
                # Check if facing no bet (call 0)
                if amount_to_call == 0:
                    return self.do_call(valid_actions)

                # Check Pot Odds vs Estimated Win Probability, adjusted for implied odds
                required_equity = pot_odds_ratio
                draw_bonus_factor = hand_potential.get('draw_strength_bonus', 0)
                if street == 'flop': draw_bonus_factor *= 1.5
                elif street == 'turn': draw_bonus_factor *= 1.0
                else: draw_bonus_factor = 0

                adjusted_required_equity = required_equity * (1 - draw_bonus_factor * 0.5)

                # Call if estimated win probability is better than adjusted required equity
                if estimated_win_prob_percent >= adjusted_required_equity * 100:
                     # Consider table aggression - fold marginal hands against aggressive tables
                     if street_aggression > 0.7 and estimated_win_prob_percent < pot_odds_percent * 1.1 and not is_short_stack:
                          if can_fold: return self.do_fold(valid_actions)
                          else: return self.do_call(valid_actions)
                     else:
                          return self.do_call(valid_actions)

                # Consider calling with weak hands/draws if pot odds are very good
                if pot_odds_percent > 20 and (current_hand_strength > 0.1 or hand_potential['outs'] >= 3):
                     # Add a random element weighted by pot odds
                     if random.random() < 0.25 + (pot_odds_percent / 100.0) * 0.5:
                          return self.do_call(valid_actions)
                     else:
                          if can_fold: return self.do_fold(valid_actions)
                          else: return self.do_call(valid_actions)

            # Consider Bluffing
            if can_raise and amount_to_call > 0:
                 # Bluffing conditions: late position/blind, few opponents, random chance
                 bluff_chance = 0.05
                 if my_position_category in ['late', 'blind']: bluff_chance += 0.10
                 if num_active_players <= 1: bluff_chance += 0.05
                 if street == 'river': bluff_chance += 0.05

                 # Simple check for a "dry" board (no obvious flush draws)
                 board_suits = [c[0] for c in community_card]
                 board_suit_counts = Counter(board_suits)
                 board_has_flush_draw = any(count >= 3 for count in board_suit_counts.values())

                 if not board_has_flush_draw:
                      bluff_chance += 0.03

                 # Adjust bluff chance based on hand strength (semi-bluff with weak draws)
                 if hand_potential['outs'] > 0 and street != 'river': bluff_chance += hand_potential['outs'] / 15.0

                 # Increase bluff chance significantly when short stacked
                 if is_short_stack: bluff_chance += 0.20

                 if random.random() < bluff_chance and self.my_stack > amount_to_call:
                      # Bluff raise size: 2x to 3x the bet, capped by max_raise
                      bluff_raise_amount = min(max_raise, max(min_raise, int(amount_to_call * random.uniform(2.0, 3.0))))
                      # Ensure bluff raise is meaningful relative to pot
                      if bluff_raise_amount > current_pot * 0.5:
                           return self.do_raise(valid_actions, bluff_raise_amount, round_state)

            # Default to Folding if no other profitable action
            if can_fold:
                return self.do_fold(valid_actions)

            # Fallback: If somehow no action was returned and call is possible (e.g., check)
            if can_call:
                 return self.do_call(valid_actions)

            # Final fallback (should not be reached)
            return self.do_fold(valid_actions)


    # --- Helper Functions ---

    def get_position_category(self, my_index, dealer_btn_index, num_players):
        """Determines player position category (early, middle, late, blind)."""
        if num_players <= 3:
            if my_index == dealer_btn_index: return 'blind'
            elif (my_index - dealer_btn_index + num_players) % num_players == 1: return 'blind'
            else: return 'late'
        else:
            # Calculate distance from the button (clockwise)
            distance_from_button = (my_index - dealer_btn_index + num_players) % num_players

            if distance_from_button == 0: return 'late' # Button
            if distance_from_button == 1 or distance_from_button == 2: return 'blind' # SB, BB

            # Adjust distance to be relative to UTG (distance 3)
            relative_utg_distance = distance_from_button - 3
            remaining_players = num_players - 3

            if remaining_players <= 0: return 'late'

            if relative_utg_distance < (remaining_players / 3.0): return 'early'
            elif relative_utg_distance < (remaining_players * 2.0 / 3.0): return 'middle'
            else: return 'late'


    def calculate_hand_strength_new(self, hole_card, community_card, street, position_category):
        """Evaluates current hand strength, considering position pre-flop."""
        num_community_cards = len(community_card)

        if num_community_cards == 0: # Pre-flop
            card1_rank = RANK_MAP[hole_card[0][1]]
            card2_rank = RANK_MAP[hole_card[1][1]]
            card1_suit = hole_card[0][0]
            card2_suit = hole_card[1][0]
            is_suited = card1_suit == card2_suit
            is_pair = card1_rank == card2_rank

            # Simple Pre-flop Hand Strength Score
            high_card_rank = max(card1_rank, card2_rank)
            low_card_rank = min(card1_rank, card2_rank)

            score = 0
            if is_pair:
                score = high_card_rank * 2
            else:
                score = high_card_rank + low_card_rank / 2.0
                if is_suited: score += 4
                gap = high_card_rank - low_card_rank - 1
                if gap == 0: score += 3
                elif gap == 1: score += 2
                elif gap == 2: score += 1
                elif gap > 3: score -= gap * 0.8 # Reduced penalty for gappers

            # Normalize score to roughly 0-1 range
            strength = max(0, score - 5) / 25.0

            # Adjust for position - play looser in later positions and blinds
            if position_category == 'early': strength *= 0.7
            elif position_category == 'middle': strength *= 1.0
            elif position_category == 'late': strength *= 1.2
            elif position_category == 'blind': strength *= 1.1

            # Add some randomness
            strength = max(0, min(1.0, strength * (1 + random.uniform(-0.1, 0.1))))

            return strength

        else: # Flop, Turn, River
            all_cards = hole_card + community_card
            if len(all_cards) < 5: return 0

            hand_rank_details = self.evaluate_best_hand(all_cards)
            hand_type = hand_rank_details['type']

            # More granular scoring based on hand type and kicker/rank
            score = 0
            if hand_type == 'Royal Flush': score = 1000
            elif hand_type == 'Straight Flush': score = 950 + hand_rank_details['rank'][0]
            elif hand_type == 'Four of a Kind': score = 900 + hand_rank_details['rank'][0]
            elif hand_type == 'Full House': score = 850 + hand_rank_details['rank'][0] * 10 + hand_rank_details['rank'][1]
            elif hand_type == 'Flush':
                 flush_ranks_score = sum(hand_rank_details['rank'])
                 score = 700 + flush_ranks_score / 5.0
            elif hand_type == 'Straight': score = 600 + hand_rank_details['rank'][0]
            elif hand_type == 'Three of a Kind':
                 trips_rank = hand_rank_details['rank'][0]
                 kickers_score = sum(hand_rank_details['rank'][1:])
                 score = 500 + trips_rank * 10 + kickers_score / 2.0
            elif hand_type == 'Two Pair':
                 pair1_rank = hand_rank_details['rank'][0]
                 pair2_rank = hand_rank_details['rank'][1]
                 kicker_score = hand_rank_details['rank'][2]
                 score = 400 + pair1_rank * 10 + pair2_rank * 5 + kicker_score
            elif hand_type == 'One Pair':
                 pair_rank = hand_rank_details['rank'][0]
                 kickers_score = sum(hand_rank_details['rank'][1:])
                 score = 300 + pair_rank * 5 + kickers_score / 3.0
            else: # High Card
                 high_card_score = sum(hand_rank_details['rank'])
                 score = 100 + high_card_score / 5.0

            # Normalize score
            strength = max(0, score - 100) / 900.0

            return max(0, min(1.0, strength))


    def calculate_hand_potential(self, hole_card, community_card):
        """Calculates draw potential (outs) on flop and turn."""
        potential = {'outs': 0, 'flush_draw': False, 'straight_draw': False, 'draw_strength_bonus': 0}
        num_community = len(community_card)

        if not (num_community == 3 or num_community == 4): # Only calculate on Flop/Turn
            return potential

        all_cards = hole_card + community_card
        suits = [c[0] for c in all_cards]
        ranks = sorted([RANK_MAP[c[1]] for c in all_cards])
        unique_ranks = sorted(list(set(ranks)))

        # Flush Draw Check
        suit_counts = Counter(suits)
        for suit, count in suit_counts.items():
            if count == 4:
                potential['flush_draw'] = True
                potential['outs'] += 9
                break

        # Straight Draw Check
        straight_outs = 0
        for i in range(len(unique_ranks) - 3):
             if unique_ranks[i+3] - unique_ranks[i] == 3:
                 straight_outs += 8
                 potential['straight_draw'] = True
                 break

        if not potential['straight_draw'] and len(unique_ranks) >= 4:
             for i in range(len(unique_ranks) - 3):
                 slice4 = unique_ranks[i:i+4]
                 if slice4[-1] - slice4[0] == 4:
                     straight_outs += 4
                     potential['straight_draw'] = True
                     break

        # Check Ace-low straights
        if not potential['straight_draw'] and set(unique_ranks).issuperset({14, 2, 3, 4}) and 5 not in unique_ranks:
             straight_outs += 4
             potential['straight_draw'] = True
        if not potential['straight_draw'] and set(unique_ranks).issuperset({14, 2, 3, 5}) and 4 not in unique_ranks:
             straight_outs += 4
             potential['straight_draw'] = True
        if not potential['straight_draw'] and set(unique_ranks).issuperset({14, 2, 4, 5}) and 3 not in unique_ranks:
             straight_outs += 4
             potential['straight_draw'] = True
        if not potential['straight_draw'] and set(unique_ranks).issuperset({14, 3, 4, 5}) and 2 not in unique_ranks:
             straight_outs += 4
             potential['straight_draw'] = True

        # Combine outs (simplified)
        total_outs = 0
        if potential['flush_draw']: total_outs += 9
        if potential['straight_draw']: total_outs += straight_outs

        potential['outs'] = min(total_outs, 15)

        # Add bonus based on outs
        if potential['outs'] >= 12:
            potential['draw_strength_bonus'] = 0.25
        elif potential['outs'] >= 8:
            potential['draw_strength_bonus'] = 0.15
        elif potential['outs'] >= 4:
            potential['draw_strength_bonus'] = 0.05
        else:
            potential['draw_strength_bonus'] = 0

        return potential


    def calculate_pot_details(self, pot_data):
        """Calculates total pot."""
        main_pot = pot_data['main']['amount']
        side_pots_total = sum(p['amount'] for p in pot_data.get('side', []))
        current_total_pot = main_pot + side_pots_total
        return {'total_pot': current_total_pot}


    def analyze_table_aggression(self, street_history, my_uuid):
        """Analyzes action history for aggression level (simple version)."""
        num_actions = 0
        num_aggressive = 0 # Bets or Raises
        if not street_history: return 0

        for action in street_history:
            action_type = action['action']
            if action_type in ['SMALLBLIND', 'BIGBLIND']: continue
            if action_type == 'CALL' and action.get('amount', 0) == 0: continue

            if action['uuid'] == my_uuid: continue

            num_actions += 1
            if action_type == 'RAISE':
                 num_aggressive += 1

        if num_actions == 0: return 0
        aggression_score = num_aggressive / num_actions
        return min(1.0, aggression_score)


    def evaluate_best_hand(self, cards):
        """Evaluates the best 5-card poker hand from a list of 5 to 7 cards."""
        if len(cards) < 5:
            if len(cards) == 2: # Pre-flop
                 ranks = sorted([RANK_MAP[c[1]] for c in cards], reverse=True)
                 return {'type': 'High Card', 'rank': ranks, 'best_cards': cards}
            elif len(cards) < 5:
                 ranks = sorted([RANK_MAP[c[1]] for c in cards], reverse=True)
                 return {'type': 'High Card', 'rank': ranks, 'best_cards': cards}
            else:
                 pass

        evaluated_cards = [(RANK_MAP[card[1]], card[0]) for card in cards]
        best_hand_info = {'type': 'High Card', 'rank': [0], 'best_cards': []}

        card_combinations = combinations(evaluated_cards, 5)

        for hand_combination in card_combinations:
            current_hand_info = self.get_5card_hand_type(list(hand_combination))
            if self.compare_hands(current_hand_info, best_hand_info) > 0:
                best_hand_info = current_hand_info

        return best_hand_info


    def get_5card_hand_type(self, five_cards_tuples):
        """Determines the type and rank of a 5-card hand."""
        ranks = sorted([card[0] for card in five_cards_tuples], reverse=True)
        suits = [card[1] for card in five_cards_tuples]
        rank_counts = Counter(ranks)
        sorted_rank_counts = sorted(rank_counts.items(), key=lambda item: (-item[1], -item[0]))

        is_flush = len(set(suits)) == 1
        unique_ranks = sorted(list(set(ranks)), reverse=True)
        is_straight = False
        straight_high_card = 0
        if len(unique_ranks) >= 5:
            for i in range(len(unique_ranks) - 4):
                if unique_ranks[i] - unique_ranks[i+4] == 4:
                    is_straight = True
                    straight_high_card = unique_ranks[i]
                    break
            if not is_straight and set(unique_ranks).issuperset({14, 2, 3, 4, 5}):
                 is_straight = True
                 straight_high_card = 5

        # Hand Ranking Logic
        if is_straight and is_flush:
            if straight_high_card == 14:
                 return {'type': 'Royal Flush', 'rank': [straight_high_card], 'best_cards': five_cards_tuples}
            else:
                 return {'type': 'Straight Flush', 'rank': [straight_high_card], 'best_cards': five_cards_tuples}
        elif sorted_rank_counts[0][1] == 4: # Four of a kind
            quad_rank = sorted_rank_counts[0][0]
            kicker = [r for r in ranks if r != quad_rank][0]
            return {'type': 'Four of a Kind', 'rank': [quad_rank, kicker], 'best_cards': five_cards_tuples}
        elif sorted_rank_counts[0][1] == 3 and sorted_rank_counts[1][1] == 2: # Full House
            trips_rank = sorted_rank_counts[0][0]
            pair_rank = sorted_rank_counts[1][0]
            return {'type': 'Full House', 'rank': [trips_rank, pair_rank], 'best_cards': five_cards_tuples}
        elif is_flush:
            return {'type': 'Flush', 'rank': ranks, 'best_cards': five_cards_tuples}
        elif is_straight:
            return {'type': 'Straight', 'rank': [straight_high_card], 'best_cards': five_cards_tuples}
        elif sorted_rank_counts[0][1] == 3: # Three of a kind
            trips_rank = sorted_rank_counts[0][0]
            kickers = sorted([r for r in ranks if r != trips_rank], reverse=True)
            return {'type': 'Three of a Kind', 'rank': [trips_rank] + kickers[:2], 'best_cards': five_cards_tuples}
        elif sorted_rank_counts[0][1] == 2 and sorted_rank_counts[1][1] == 2: # Two Pair
            pair1_rank = sorted_rank_counts[0][0]
            pair2_rank = sorted_rank_counts[1][0]
            kicker = [r for r in ranks if r != pair1_rank and r != pair2_rank][0]
            return {'type': 'Two Pair', 'rank': sorted([pair1_rank, pair2_rank], reverse=True) + [kicker], 'best_cards': five_cards_tuples}
        elif sorted_rank_counts[0][1] == 2: # One Pair
            pair_rank = sorted_rank_counts[0][0]
            kickers = sorted([r for r in ranks if r != pair_rank], reverse=True)
            return {'type': 'One Pair', 'rank': [pair_rank] + kickers[:3], 'best_cards': five_cards_tuples}
        else: # High Card
            return {'type': 'High Card', 'rank': ranks[:5], 'best_cards': five_cards_tuples}


    def compare_hands(self, hand1_info, hand2_info):
        """Compares two hands based on type and rank list."""
        rank1_idx = HAND_RANKINGS.index(hand1_info['type'])
        rank2_idx = HAND_RANKINGS.index(hand2_info['type'])

        if rank1_idx > rank2_idx: return 1
        if rank1_idx < rank2_idx: return -1

        for r1, r2 in zip(hand1_info['rank'], hand2_info['rank']):
            if r1 > r2: return 1
            if r1 < r2: return -1

        return 0 # Tie


    def receive_game_start_message(self, game_info):
        """Reset state for a new game."""
        self.my_uuid = None
        self.my_stack = 0
        self.my_index = -1
        self.num_players = game_info["player_num"]
        self.table_aggression_history = {}
        self.opponent_stats = {}
        for player_info in game_info["seats"]:
            if player_info["uuid"] != self.my_uuid:
                self.opponent_stats[player_info["uuid"]] = {
                    "hands_played": 0,
                    "vpip_events": 0,
                    "pfr_events": 0
                }


    def receive_round_start_message(self, round_count, hole_card, seats):
        """Update state at the start of each round."""
        for i, seat in enumerate(seats):
            if seat['uuid'] == self.my_uuid:
                self.my_stack = seat['stack']
                self.my_index = i
                break
        self.num_players = len(seats)

        for uuid in self.opponent_stats:
            self.opponent_stats[uuid]["hands_played"] += 1

    def receive_street_start_message(self, street, round_state):
        pass

    def receive_game_update_message(self, action, round_state):
        """Track opponent actions for VPIP and PFR."""
        action_type = action.get('action')
        street = round_state.get('street')

        if action_type and street and 'uuid' in action:
            player_uuid = action['uuid']

            if player_uuid != self.my_uuid and player_uuid in self.opponent_stats:
                # VPIP: Any action except fold pre-flop
                if street == 'preflop' and action_type in ['CALL', 'RAISE', 'SMALLBLIND', 'BIGBLIND']:
                     self.opponent_stats[player_uuid]["vpip_events"] += 1

                # PFR: Raise pre-flop
                if street == 'preflop' and action_type == 'RAISE':
                     self.opponent_stats[player_uuid]["pfr_events"] += 1


    def receive_round_result_message(self, winners, hand_info, round_state):
        pass

    # Helper functions to declare actions
    def do_fold(self, valid_actions):
        action_info = valid_actions[0]
        amount = action_info["amount"]
        return action_info["action"], int(amount)

    def do_call(self, valid_actions):
        action_info = valid_actions[1]
        amount = action_info["amount"]
        return action_info["action"], int(amount)

    def do_raise(self, valid_actions, raise_amount, round_state):
        name = str(self)
        stack = self.search_stack(name, round_state)
        
        action_info = valid_actions[2]
        # amount has to be at least min -- this is the intended raise amount
        amount = max(action_info["amount"]["min"], raise_amount)

        # cap the actual raise based on the player's actual stack
        amount = min(amount, stack)
        assert (amount > 0) , "Tried to raise an amount <= 0"           
        return action_info["action"], int(amount)

    def do_all_in(self, valid_actions, round_state):
        name = str(self)
        stack = self.search_stack(name, round_state)
        
        action_info = valid_actions[2]
        amount = stack
        return action_info["action"], amount

    # Gets the stack for a player with a given name
    def search_stack(self, name, round_state):
        stack = -1
        for i in round_state["seats"]:
            if i['name'] == name:
                print(f"[self.search_stack] => found name : {i['name']} = {name}")
                stack = i["stack"]

        assert (stack > -1), f"Unable to find matching player name in config for {name}"
        return stack

    def __str__(self):
        return type(self).__name__