import random
import math
from itertools import combinations
from collections import Counter

from pypokerengine.players import BasePokerPlayer

RANK_MAP = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
HAND_RANKINGS = ['High Card', 'One Pair', 'Two Pair', 'Three of a Kind', 'Straight', 'Flush', 'Full House', 'Four of a Kind', 'Straight Flush', 'Royal Flush']

def setup_ai():
    return WaterBottle()

class WaterBottle(BasePokerPlayer):

    def __init__(self):
        self.my_uuid = None
        self.my_stack = 0
        self.my_index = -1
        self.num_players = 0
        self.table_aggression_history = {}

    def declare_action(self, valid_actions, hole_card, round_state):
        street = round_state['street']
        community_card = round_state['community_card']
        pot_data = round_state['pot']
        dealer_btn_index = round_state['dealer_btn']
        seats = round_state['seats']
        action_histories = round_state['action_histories']
        small_blind_amount = round_state['small_blind_amount']

        if self.my_uuid is None:
            for i, seat in enumerate(seats):
                if seat['name'] == 'WaterBottle':
                    self.my_uuid = seat['uuid']
                    self.my_index = i
                    break
            self.num_players = len(seats)

        for seat in seats:
            if seat['uuid'] == self.my_uuid:
                self.my_stack = seat['stack']
                break

        if self.my_uuid is None:
             return self.do_fold(valid_actions)

        num_active_players = len([s for s in seats if s['state'] == 'participating' and s['uuid'] != self.my_uuid])

        my_position_category = self.get_position_category(self.my_index, dealer_btn_index, self.num_players)

        can_fold = valid_actions[0]['action'] == 'fold'
        can_call = valid_actions[1]['action'] == 'call'
        amount_to_call = valid_actions[1]['amount']
        can_raise = len(valid_actions) > 2 and valid_actions[2]['action'] == 'raise'

        min_raise = valid_actions[2]['amount']['min'] if can_raise else 0
        max_raise = valid_actions[2]['amount']['max'] if can_raise else self.my_stack

        current_hand_strength = self.calculate_hand_strength_new(hole_card, community_card, street, my_position_category)
        hand_potential = self.calculate_hand_potential(hole_card, community_card)
        pot_details = self.calculate_pot_details(pot_data)
        current_pot = pot_details['total_pot']

        pot_odds_ratio = amount_to_call / (current_pot + amount_to_call) if amount_to_call > 0 else 0
        pot_odds_percent = pot_odds_ratio * 100

        street_aggression = self.analyze_table_aggression(action_histories.get(street, []), self.my_uuid)

        estimated_win_prob_percent = (current_hand_strength + hand_potential.get('draw_strength_bonus', 0)) * 100

        has_significant_leader = False
        if self.my_uuid is not None:
            for seat in seats:
                if seat['uuid'] != self.my_uuid and seat['stack'] >= self.my_stack * 2:
                    has_significant_leader = True
                    break

        if not has_significant_leader and self.my_uuid is not None:
            player_stacks = sorted([seat['stack'] for seat in seats if seat['uuid'] != self.my_uuid], reverse=True)
            if len(player_stacks) > 1:
                second_highest_stack = player_stacks[0]
                if self.my_stack >= second_highest_stack * 2:
                    if amount_to_call == 0 and current_pot <= self.my_stack:
                         return self.do_fold(valid_actions)

        risk_factor = 1.0
        if has_significant_leader:
            risk_factor = 1.2

        spr = self.my_stack / (current_pot + amount_to_call) if (current_pot + amount_to_call) > 0 else float('inf')

        if current_hand_strength > 0.95 * (2.0 - risk_factor):
            if can_raise: return self.do_all_in(valid_actions)
            elif can_call: return self.do_call(valid_actions)
            else: return self.do_fold(valid_actions)

        if current_hand_strength > 0.75 * (2.0 - risk_factor):
             if can_raise:
                 raise_amount = min(max_raise, max(min_raise, int(current_pot * 0.75)))
                 raise_amount = max(raise_amount, amount_to_call + min_raise)
                 raise_amount = min(raise_amount, self.my_stack)
                 return self.do_raise(valid_actions, raise_amount, round_state)
             elif can_call:
                 return self.do_call(valid_actions)
             else: return self.do_fold(valid_actions)

        if street != 'river' and hand_potential['outs'] >= 8 * (2.0 - risk_factor):
             if can_raise:
                 raise_amount = min(max_raise, max(min_raise, int(current_pot * 0.5)))
                 raise_amount = max(raise_amount, amount_to_call + min_raise)
                 raise_amount = min(raise_amount, self.my_stack)
                 if my_position_category in ['late', 'blind'] or num_active_players <= 2:
                      return self.do_raise(valid_actions, raise_amount, round_state)
                 else:
                      if can_call: return self.do_call(valid_actions)
                      else: return self.do_fold(valid_actions)
             elif can_call:
                 if estimated_win_prob_percent >= pot_odds_percent * 0.8 * (2.0 - risk_factor):
                      return self.do_call(valid_actions)
                 else:
                      if can_fold and risk_factor == 1.0: return self.do_fold(valid_actions)
                      else: return self.do_call(valid_actions)
             else:
                 if can_fold and risk_factor == 1.0: return self.do_fold(valid_actions)
                 else: return self.do_call(valid_actions)

        if can_call:
            if amount_to_call == 0:
                return self.do_call(valid_actions)

            required_equity = pot_odds_ratio
            draw_bonus_factor = hand_potential.get('draw_strength_bonus', 0)
            if street == 'flop': draw_bonus_factor *= 1.5
            elif street == 'turn': draw_bonus_factor *= 1.0
            else: draw_bonus_factor = 0

            adjusted_required_equity = required_equity * (1 - draw_bonus_factor * 0.5)

            if estimated_win_prob_percent >= adjusted_required_equity * 100 * (2.0 - risk_factor):
                 if street_aggression > 0.7 and estimated_win_prob_percent < pot_odds_percent * 1.1 and risk_factor == 1.0:
                      if can_fold: return self.do_fold(valid_actions)
                      else: return self.do_call(valid_actions)
                 else:
                      return self.do_call(valid_actions)

            if pot_odds_percent > 25 * (2.0 - risk_factor) and (current_hand_strength > 0.1 or hand_potential['outs'] >= 4):
                 random_call_chance = 0.2 + (pot_odds_percent / 100.0) * 0.4
                 if has_significant_leader: random_call_chance *= risk_factor

                 if random.random() < random_call_chance:
                      return self.do_call(valid_actions)
                 else:
                      if can_fold and risk_factor == 1.0: return self.do_fold(valid_actions)
                      else: return self.do_call(valid_actions)

        if can_raise and amount_to_call > 0:
             bluff_chance = 0.0
             if my_position_category in ['late', 'blind']: bluff_chance += 0.05
             if num_active_players <= 1: bluff_chance += 0.05
             if street == 'river': bluff_chance += 0.05

             board_suits = [c[0] for c in community_card]
             board_suit_counts = Counter(board_suits)
             board_has_flush_draw = any(count >= 3 for count in board_suit_counts.values())

             if not board_has_flush_draw:
                  bluff_chance += 0.05

             if hand_potential['outs'] > 0 and street != 'river': bluff_chance += hand_potential['outs'] / 20.0

             if has_significant_leader: bluff_chance *= risk_factor

             if random.random() < bluff_chance and self.my_stack > amount_to_call:
                  bluff_raise_amount = min(max_raise, max(min_raise, int(amount_to_call * 2.5)))
                  if bluff_raise_amount > current_pot * 0.4:
                       return self.do_raise(valid_actions, bluff_raise_amount, round_state)

        if can_fold and risk_factor == 1.0:
            return self.do_fold(valid_actions)

        if can_call:
             return self.do_call(valid_actions)

        return self.do_fold(valid_actions)

    def get_position_category(self, my_index, dealer_btn_index, num_players):
        if num_players <= 3:
            if my_index == dealer_btn_index: return 'blind'
            elif (my_index - dealer_btn_index + num_players) % num_players == 1: return 'blind'
            else: return 'late'
        else:
            distance_from_button = (my_index - dealer_btn_index + num_players) % num_players

            if distance_from_button == 0: return 'late'
            if distance_from_button == 1 or distance_from_button == 2: return 'blind'

            remaining_players = num_players - 3
            if remaining_players <= 0: return 'late'

            relative_utg_distance = distance_from_button - 3

            if relative_utg_distance < (remaining_players / 3.0): return 'early'
            elif relative_utg_distance < (remaining_players * 2.0 / 3.0): return 'middle'
            else: return 'late'

    def calculate_hand_strength_new(self, hole_card, community_card, street, position_category):
        num_community_cards = len(community_card)

        if num_community_cards == 0:
            card1_rank = RANK_MAP[hole_card[0][1]]
            card2_rank = RANK_MAP[hole_card[1][1]]
            card1_suit = hole_card[0][0]
            card2_suit = hole_card[1][0]
            is_suited = card1_suit == card2_suit
            is_pair = card1_rank == card2_rank

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
                elif gap > 3: score -= gap

            strength = max(0, score - 5) / 25.0

            if position_category == 'early': strength *= 0.7
            elif position_category == 'middle': strength *= 0.9
            elif position_category == 'late': strength *= 1.1
            elif position_category == 'blind': strength *= 1.0

            strength = max(0, min(1.0, strength * (1 + random.uniform(-0.1, 0.1))))

            return strength

        else:
            all_cards = hole_card + community_card
            if len(all_cards) < 5: return 0

            hand_rank_details = self.evaluate_best_hand(all_cards)
            hand_type = hand_rank_details['type']

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
            else:
                 high_card_score = sum(hand_rank_details['rank'])
                 score = 100 + high_card_score / 5.0

            strength = max(0, score - 100) / 900.0

            return max(0, min(1.0, strength))

    def calculate_hand_potential(self, hole_card, community_card):
        potential = {'outs': 0, 'flush_draw': False, 'straight_draw': False, 'draw_strength_bonus': 0}
        num_community = len(community_card)

        if not (num_community == 3 or num_community == 4):
            return potential

        all_cards = hole_card + community_card
        suits = [c[0] for c in all_cards]
        ranks = sorted([RANK_MAP[c[1]] for c in all_cards])
        unique_ranks = sorted(list(set(ranks)))

        suit_counts = Counter(suits)
        flush_suit = None
        for suit, count in suit_counts.items():
            if count == 4:
                potential['flush_draw'] = True
                flush_suit = suit
                potential['outs'] += (13 - 4)
                break

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

        total_outs = 0
        if potential['flush_draw']: total_outs += 9
        if potential['straight_draw']: total_outs += straight_outs

        potential['outs'] = min(total_outs, 15)

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
        main_pot = pot_data['main']['amount']
        side_pots_total = sum(p['amount'] for p in pot_data.get('side', []))
        current_total_pot = main_pot + side_pots_total
        return {'total_pot': current_total_pot}

    def analyze_table_aggression(self, street_history, my_uuid):
        num_actions = 0
        num_aggressive = 0
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
        if len(cards) < 5:
            if len(cards) == 2:
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

        if is_straight and is_flush:
            if straight_high_card == 14:
                 return {'type': 'Royal Flush', 'rank': [straight_high_card], 'best_cards': five_cards_tuples}
            else:
                 return {'type': 'Straight Flush', 'rank': [straight_high_card], 'best_cards': five_cards_tuples}
        elif sorted_rank_counts[0][1] == 4:
            quad_rank = sorted_rank_counts[0][0]
            kicker = [r for r in ranks if r != quad_rank][0]
            return {'type': 'Four of a Kind', 'rank': [quad_rank, kicker], 'best_cards': five_cards_tuples}
        elif sorted_rank_counts[0][1] == 3 and sorted_rank_counts[1][1] == 2:
            trips_rank = sorted_rank_counts[0][0]
            pair_rank = sorted_rank_counts[1][0]
            return {'type': 'Full House', 'rank': [trips_rank, pair_rank], 'best_cards': five_cards_tuples}
        elif is_flush:
            return {'type': 'Flush', 'rank': ranks, 'best_cards': five_cards_tuples}
        elif is_straight:
            return {'type': 'Straight', 'rank': [straight_high_card], 'best_cards': five_cards_tuples}
        elif sorted_rank_counts[0][1] == 3:
            trips_rank = sorted_rank_counts[0][0]
            kickers = sorted([r for r in ranks if r != trips_rank], reverse=True)
            return {'type': 'Three of a Kind', 'rank': [trips_rank] + kickers[:2], 'best_cards': five_cards_tuples}
        elif sorted_rank_counts[0][1] == 2 and sorted_rank_counts[1][1] == 2:
            pair1_rank = sorted_rank_counts[0][0]
            pair2_rank = sorted_rank_counts[1][0]
            kicker = [r for r in ranks if r != pair1_rank and r != pair2_rank][0]
            return {'type': 'Two Pair', 'rank': sorted([pair1_rank, pair2_rank], reverse=True) + [kicker], 'best_cards': five_cards_tuples}
        elif sorted_rank_counts[0][1] == 2:
            pair_rank = sorted_rank_counts[0][0]
            kickers = sorted([r for r in ranks if r != pair_rank], reverse=True)
            return {'type': 'One Pair', 'rank': [pair_rank] + kickers[:3], 'best_cards': five_cards_tuples}
        else:
            return {'type': 'High Card', 'rank': ranks[:5], 'best_cards': five_cards_tuples}

    def compare_hands(self, hand1_info, hand2_info):
        rank1_idx = HAND_RANKINGS.index(hand1_info['type'])
        rank2_idx = HAND_RANKINGS.index(hand2_info['type'])

        if rank1_idx > rank2_idx: return 1
        if rank1_idx < rank2_idx: return -1

        for r1, r2 in zip(hand1_info['rank'], hand2_info['rank']):
            if r1 > r2: return 1
            if r1 < r2: return -1

        return 0

    def receive_game_start_message(self, game_info):
        self.my_uuid = None
        self.my_stack = 0
        self.my_index = -1
        self.num_players = game_info["player_num"]
        self.table_aggression_history = {}

    def receive_round_start_message(self, round_count, hole_card, seats):
        for i, seat in enumerate(seats):
            if seat['name'] == 'WaterBottle':
                self.my_stack = seat['stack']
                self.my_index = i
                break
        self.num_players = len(seats)

    def receive_street_start_message(self, street, round_state):
        pass

    def receive_game_update_message(self, action, round_state):
        pass

    def receive_round_result_message(self, winners, hand_info, round_state):
        pass

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

