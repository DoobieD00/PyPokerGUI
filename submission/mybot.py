from pypokerengine.players import BasePokerPlayer
from pypokerengine.utils.card_utils import gen_cards, estimate_hole_card_win_rate
import random

def setup_ai():
    return SmartPokerBot()

class SmartPokerBot(BasePokerPlayer):

    def __init__(self):
        super().__init__()
        self.aggression_factor = 1.3  # Controls how aggressive the bot is
        self.bluff_frequency = 0.15   # 15% chance to bluff in appropriate situations
        self.last_action = None

    def declare_action(self, valid_actions, hole_card, round_state):
        # Extract game information
        community_cards = round_state['community_card']
        street = round_state['street']
        pot_size = round_state['pot']['main']['amount']
        action_history = round_state['action_histories'].get(street, [])
        
        # Calculate hand strength
        win_rate = self.evaluate_hand(hole_card, community_cards, round_state)
        hand_strength = self.classify_hand_strength(win_rate)
        
        # Get position information
        position = self.get_position(round_state)
        
        # Determine action based on strategy
        action, amount = self.determine_action(
            valid_actions, 
            hand_strength, 
            position, 
            pot_size, 
            street, 
            action_history
        )
        
        self.last_action = action
        return action, amount

    def evaluate_hand(self, hole_card, community_cards, round_state):
        # Convert cards to pypokerengine format
        hole = gen_cards(hole_card)
        community = gen_cards(community_cards)
        
        # Estimate win probability (monte carlo simulation)
        win_rate = estimate_hole_card_win_rate(
            nb_simulation=1000,
            nb_player=self.count_active_players(round_state),
            hole_card=hole,
            community_card=community
        )
        return win_rate

    def count_active_players(self, round_state):
        return len([seat for seat in round_state['seats'] if seat['state'] == 'participating'])

    def classify_hand_strength(self, win_rate):
        if win_rate > 0.85: return "VERY_STRONG"
        if win_rate > 0.65: return "STRONG"
        if win_rate > 0.45: return "MEDIUM"
        if win_rate > 0.25: return "WEAK"
        return "VERY_WEAK"

    def get_position(self, round_state):
        btn_pos = round_state['dealer_btn']
        my_pos = [i for i, seat in enumerate(round_state['seats']) if seat['uuid'] == self.uuid][0]
        relative_pos = (my_pos - btn_pos) % len(round_state['seats'])
        return "early" if relative_pos < 2 else "late" if relative_pos > 3 else "middle"

    def determine_action(self, valid_actions, hand_strength, position, pot_size, street, action_history):
        # Basic strategy implementation
        can_raise = valid_actions[2]['amount']['min'] != -1
        min_raise = valid_actions[2]['amount']['min'] if can_raise else 0
        max_raise = valid_actions[2]['amount']['max'] if can_raise else 0
        call_amount = valid_actions[1]['amount']
        
        # Adjust strategy based on position
        position_factor = 1.2 if position == "late" else 0.8 if position == "early" else 1.0
        
        # Consider previous actions
        opponents_aggressive = any(
            act['action'] in ['raise', 'allin'] 
            for act in action_history 
            if act['uuid'] != self.uuid
        )
        
        # Bluff opportunity detection
        should_bluff = (random.random() < self.bluff_frequency and 
                       street != 'preflop' and 
                       len(action_history) < 3 and 
                       not opponents_aggressive)
        
        # Action decision logic
        if hand_strength == "VERY_STRONG":
            if can_raise:
                raise_amount = min(max_raise, int(pot_size * 0.75 * self.aggression_factor * position_factor))
                return self.do_raise(valid_actions, raise_amount)
            return self.do_call(valid_actions)
            
        elif hand_strength == "STRONG":
            if can_raise and (position == "late" or not opponents_aggressive):
                raise_amount = min(max_raise, int(pot_size * 0.5 * self.aggression_factor * position_factor))
                return self.do_raise(valid_actions, raise_amount)
            return self.do_call(valid_actions)
            
        elif hand_strength == "MEDIUM":
            if should_bluff and can_raise:
                return self.do_raise(valid_actions, min_raise)
            if call_amount == 0 or (position == "late" and not opponents_aggressive):
                return self.do_call(valid_actions)
            if opponents_aggressive and call_amount > pot_size * 0.3:
                return self.do_fold(valid_actions)
            return self.do_call(valid_actions)
            
        elif hand_strength == "WEAK":
            if should_bluff and can_raise and position == "late":
                return self.do_raise(valid_actions, min_raise)
            if call_amount == 0:
                return self.do_call(valid_actions)
            if call_amount > pot_size * 0.15 or opponents_aggressive:
                return self.do_fold(valid_actions)
            return self.do_call(valid_actions)
            
        else:  # VERY_WEAK
            if should_bluff and can_raise and position == "late" and len(action_history) == 0:
                return self.do_raise(valid_actions, min_raise)
            if call_amount == 0:
                return self.do_call(valid_actions)
            return self.do_fold(valid_actions)

    # The following methods are unchanged from the original
    def receive_game_start_message(self, game_info):
        pass

    def receive_round_start_message(self, round_count, hole_card, seats):
        pass

    def receive_street_start_message(self, street, round_state):
        pass

    def receive_game_update_message(self, action, round_state):
        pass

    def receive_round_result_message(self, winners, hand_info, round_state):
        pass

    def do_fold(self, valid_actions):
        action_info = valid_actions[0]
        return action_info['action'], action_info["amount"]

    def do_call(self, valid_actions):
        action_info = valid_actions[1]
        return action_info['action'], action_info["amount"]
    
    def do_raise(self, valid_actions, raise_amount):
        action_info = valid_actions[2]
        amount = max(action_info['amount']['min'], raise_amount)
        return action_info['action'], amount
    
    def do_all_in(self, valid_actions):
        action_info = valid_actions[2]
        amount = action_info['amount']['max']
        return action_info['action'], amount