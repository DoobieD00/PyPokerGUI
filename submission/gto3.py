import random
from pypokerengine.players import BasePokerPlayer
from collections import defaultdict

# Constants for hand evaluation
CARD_RANKS = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}

def setup_ai():
    return gto3()

class gto3(BasePokerPlayer):
    def __init__(self):
        super().__init__()
        self.uuid = None
        self.total_rounds = 5
        self.starting_stack = 100
        self.position_value = {'early': 0.6, 'middle': 0.8, 'late': 1.0, 'sb': 0.7, 'bb': 0.9}
        self.hand_ranges = self._create_hand_ranges()
        self.bluffing_threshold = 0.15  # Probability to bluff
        self.round_aggression = {1: 0.7, 2: 0.8, 3: 0.9, 4: 1.0, 5: 1.1}  # Adjust aggression by round
        
    def _create_hand_ranges(self):
        # Simplified hand ranges for different positions
        ranges = {
            'early': {'premium': 0.1, 'strong': 0.2, 'playable': 0.3},
            'middle': {'premium': 0.1, 'strong': 0.25, 'playable': 0.4},
            'late': {'premium': 0.1, 'strong': 0.3, 'playable': 0.5},
            'sb': {'premium': 0.1, 'strong': 0.2, 'playable': 0.35},
            'bb': {'premium': 0.1, 'strong': 0.2, 'playable': 0.3}
        }
        return ranges

    def declare_action(self, valid_actions, hole_card, round_state):
        # Call our decision-making function
        action, amount = self.choose_action(valid_actions, hole_card, round_state)
        return action, amount

    def choose_action(self, valid_actions, hole_card, round_state):
        """Core decision-making function implementing GTO principles"""
        # Extract key game state information
        community_cards = round_state['community_card']
        street = round_state['street']
        pot = round_state['pot']['main']['amount']
        my_stack = self._get_my_stack(round_state['seats'])
        position = self._determine_position(round_state)
        round_count = round_state['round_count']
        
        # Calculate hand strength
        hand_strength = self._evaluate_hand_strength(hole_card, community_cards, street)
        
        # Calculate pot odds if facing a bet
        pot_odds = self._calculate_pot_odds(valid_actions, pot)
        
        # Calculate position value adjustment
        position_multiplier = self.position_value.get(position, 0.7)
        
        # Adjust for round progression
        round_multiplier = self.round_aggression.get(round_count, 1.0)
        
        # Effective stack consideration
        effective_stack_ratio = my_stack / self.starting_stack
        stack_multiplier = 1.2 if effective_stack_ratio > 0.7 else 0.8
        
        # Calculate EV-adjusted hand strength
        ev_adjusted_strength = hand_strength * position_multiplier * round_multiplier * stack_multiplier
        
        # Decision logic based on adjusted strength
        if street == 'preflop':
            return self._preflop_strategy(valid_actions, ev_adjusted_strength, position, pot_odds, round_state)
        else:
            return self._postflop_strategy(valid_actions, ev_adjusted_strength, pot_odds, street, community_cards, round_state)

    def _preflop_strategy(self, valid_actions, hand_strength, position, pot_odds, round_state):
        """GTO-based preflop strategy"""
        # Premium hands - play aggressively
        if hand_strength > 0.8:
            if random.random() < 0.8:  # Mixing strategy for unpredictability
                return self._get_raise_action(round_state, valid_actions, 2.5)  # Raise 2.5x BB
            else:
                return self.do_call(valid_actions)
                
        # Strong hands - raise or call based on position
        elif hand_strength > 0.6:
            pos_factor = self.position_value.get(position, 0.7)
            if random.random() < pos_factor:
                return self._get_raise_action(round_state, valid_actions, 2.2)
            else:
                return self.do_call(valid_actions)
                
        # Playable hands - call or occasionally raise in good position
        elif hand_strength > 0.4:
            if position in ['late', 'bb'] and random.random() < 0.4:
                return self._get_raise_action(round_state, valid_actions, 2.0)
            elif pot_odds > hand_strength:
                return self.do_call(valid_actions)
            else:
                return self.do_fold(valid_actions)
                
        # Weak hands - mostly fold, occasionally bluff in late position
        else:
            if position == 'late' and random.random() < self.bluffing_threshold:
                return self._get_raise_action(round_state, valid_actions, 2.0)  # Bluff raise
            elif pot_odds > 0.5 and hand_strength > 0.3:  # Very good pot odds
                return self.do_call(valid_actions)
            else:
                return self.do_fold(valid_actions)

    def _postflop_strategy(self, valid_actions, hand_strength, pot_odds, street, community_cards, round_state):
        """GTO-based postflop strategy"""
        # Calculate board texture
        board_paired = self._has_pair(community_cards)
        board_draw = self._has_draw_potential(community_cards)
        
        # Strong hands - bet for value
        if hand_strength > 0.8:
            # On draw-heavy boards, bet bigger to charge draws
            if board_draw and street != 'river':
                return self._get_raise_action(round_state, valid_actions, 0.7)  # 70% pot bet
            else:
                return self._get_raise_action(round_state, valid_actions, 0.6)  # 60% pot bet
                
        # Medium-strong hands - value bet or call
        elif hand_strength > 0.65:
            if street == 'river':
                return self._get_raise_action(round_state, valid_actions, 0.5)  # Smaller value bet on river
            elif random.random() < 0.7:
                return self._get_raise_action(round_state, valid_actions, 0.5)
            else:
                return self.do_call(valid_actions)
                
        # Medium hands - mix of checking, calling, and occasional betting
        elif hand_strength > 0.5:
            if pot_odds > hand_strength and valid_actions[1]['amount'] > 0:
                return self.do_call(valid_actions)
            elif valid_actions[1]['amount'] == 0 and random.random() < 0.3:  # We can check
                return self._get_raise_action(round_state, valid_actions, 0.4)  # Small bet
            else:
                return self.do_call(valid_actions)  # Check if possible
                
        # Weak hands with draw potential
        elif hand_strength > 0.3 and board_draw and street != 'river':
            if pot_odds > hand_strength * 1.5:  # Adjust for implied odds
                return self.do_call(valid_actions)
            else:
                return self.do_fold(valid_actions)
                
        # Bluffing opportunity
        elif street == 'river' and random.random() < self.bluffing_threshold:
            return self._get_raise_action(round_state, valid_actions, 0.7)  # Bluff on river
            
        # Default action for weak hands
        else:
            if valid_actions[1]['amount'] == 0:  # We can check
                return self.do_call(valid_actions)
            elif pot_odds > hand_strength * 1.2:  # Very good pot odds
                return self.do_call(valid_actions)
            else:
                return self.do_fold(valid_actions)

    def _evaluate_hand_strength(self, hole_cards, community_cards, street):
        """Evaluate the strength of the current hand"""
        if not hole_cards:
            return 0
            
        if street == 'preflop':
            return self._evaluate_preflop_hand(hole_cards)
        else:
            # Simple hand strength evaluation
            return self._estimate_hand_strength(hole_cards, community_cards)
    
    def _evaluate_preflop_hand(self, hole_cards):
        """Evaluate preflop hand strength"""
        if not hole_cards or len(hole_cards) != 2:
            return 0
            
        # Extract ranks and suits
        ranks = [card[1] for card in hole_cards]
        suits = [card[0] for card in hole_cards]
        
        # Convert ranks to numeric values
        rank_values = [CARD_RANKS.get(rank, 0) for rank in ranks]
        rank_values.sort(reverse=True)
        
        # Check for pairs
        is_pair = rank_values[0] == rank_values[1]
        is_suited = suits[0] == suits[1]
        
        # High pairs (JJ+)
        if is_pair and rank_values[0] >= 11:
            return 0.9
        # Medium pairs (TT-99)
        elif is_pair and rank_values[0] >= 9:
            return 0.8
        # Low pairs (88-22)
        elif is_pair:
            return 0.7
        # High suited cards (AK, AQ, AJ suited)
        elif is_suited and rank_values[0] == 14 and rank_values[1] >= 11:
            return 0.85
        # High offsuit cards (AK, AQ offsuit)
        elif rank_values[0] == 14 and rank_values[1] >= 12:
            return 0.8
        # Medium suited connectors (KQ, QJ, JT suited)
        elif is_suited and rank_values[0] >= 10 and rank_values[0] - rank_values[1] == 1:
            return 0.75
        # Ax suited
        elif is_suited and rank_values[0] == 14:
            return 0.7
        # Broadway cards (AKQJT)
        elif rank_values[0] >= 10 and rank_values[1] >= 10:
            return 0.65
        # Suited connectors
        elif is_suited and rank_values[0] - rank_values[1] == 1:
            return 0.6
        # Suited cards with gaps <= 2
        elif is_suited and rank_values[0] - rank_values[1] <= 3:
            return 0.55
        # Ax offsuit
        elif rank_values[0] == 14:
            return 0.5
        # Face cards
        elif rank_values[0] >= 11:
            return 0.45
        # Suited cards
        elif is_suited:
            return 0.4
        # Connected cards
        elif rank_values[0] - rank_values[1] == 1:
            return 0.35
        # Everything else
        else:
            # Scale remaining hands from 0.1 to 0.3 based on highest card
            return 0.1 + (rank_values[0] / 14.0) * 0.2

    def _estimate_hand_strength(self, hole_cards, community_cards):
        """Estimate postflop hand strength using a simplified algorithm"""
        if not community_cards:
            return self._evaluate_preflop_hand(hole_cards)
            
        # For simplicity, we'll use a basic made-hand evaluation
        # This would ideally be replaced with a more sophisticated equity calculator
        all_cards = hole_cards + community_cards
        
        # Count occurrences of each rank
        rank_count = defaultdict(int)
        for card in all_cards:
            rank = card[1]
            rank_count[rank] += 1
        
        # Check for simple made hands
        max_count = max(rank_count.values()) if rank_count else 0
        
        # Check for flush potential
        suit_count = defaultdict(int)
        for card in all_cards:
            suit = card[0]
            suit_count[suit] += 1
        
        has_flush = max(suit_count.values()) >= 5 if suit_count else False
        
        # Check for straight potential (simplified)
        ranks_present = set()
        for card in all_cards:
            ranks_present.add(CARD_RANKS.get(card[1], 0))
        
        has_straight = False
        for i in range(2, 15 - 4):  # 2 through 10 as starting rank
            if all(r in ranks_present for r in range(i, i+5)):
                has_straight = True
                break
        
        # Simple hand strength classification
        if has_flush and has_straight:
            return 0.95  # Straight flush
        elif max_count == 4:
            return 0.9  # Four of a kind
        elif max_count == 3 and len([c for c in rank_count.values() if c >= 2]) >= 2:
            return 0.85  # Full house
        elif has_flush:
            return 0.8  # Flush
        elif has_straight:
            return 0.75  # Straight
        elif max_count == 3:
            return 0.7  # Three of a kind
        elif len([c for c in rank_count.values() if c == 2]) >= 2:
            return 0.6  # Two pair
        elif max_count == 2:
            return 0.5  # One pair
        else:
            # High card - scale by highest card
            highest_rank = max([CARD_RANKS.get(card[1], 0) for card in all_cards])
            return 0.2 + (highest_rank / 14.0) * 0.3  # Scale between 0.2 and 0.5

    def _has_pair(self, community_cards):
        """Check if the community cards contain a pair"""
        if len(community_cards) < 2:
            return False
            
        ranks = [card[1] for card in community_cards]
        for rank in set(ranks):
            if ranks.count(rank) >= 2:
                return True
        return False

    def _has_draw_potential(self, community_cards):
        """Check if the board has potential for draws (flush/straight)"""
        if len(community_cards) < 3:
            return False
            
        # Check for flush draw
        suits = [card[0] for card in community_cards]
        for suit in set(suits):
            if suits.count(suit) >= 3:
                return True
                
        # Check for straight draw (simplified)
        ranks = sorted([CARD_RANKS.get(card[1], 0) for card in community_cards])
        if len(ranks) >= 3:
            # Check for at least 3 cards in sequence or with one gap
            for i in range(len(ranks) - 2):
                if ranks[i+2] - ranks[i] <= 4:  # Maximum gap of 4 for a potential straight
                    return True
                    
        return False

    def _calculate_pot_odds(self, valid_actions, pot):
        """Calculate pot odds when facing a bet"""
        call_amount = valid_actions[1]["amount"]
        if call_amount <= 0:
            return 1.0  # No bet to call
            
        return pot / (pot + call_amount)

    def _get_my_stack(self, seats):
        """Get my current stack from the seats information"""
        for seat in seats:
            if seat['uuid'] == self.uuid:
                return seat['stack']
        return 0

    def _determine_position(self, round_state):
        """Determine position based on dealer button and player count"""
        my_seat = None
        total_players = 0
        active_players = 0
        
        # Find my seat and count players
        for i, seat in enumerate(round_state['seats']):
            if seat['state'] != 'folded':
                active_players += 1
            total_players += 1
            if seat['uuid'] == self.uuid:
                my_seat = i
                
        if my_seat is None:
            return 'middle'  # Default
            
        # Special positions
        if my_seat == round_state['small_blind_pos']:
            return 'sb'
        if my_seat == round_state['big_blind_pos']:
            return 'bb'
            
        # Relative to button
        btn = round_state['dealer_btn']
        positions_from_btn = (my_seat - btn) % total_players
        
        if active_players >= 6:
            if positions_from_btn < active_players // 3:
                return 'early'
            elif positions_from_btn < (2 * active_players) // 3:
                return 'middle'
            else:
                return 'late'
        else:
            if positions_from_btn <= 1:
                return 'early'
            elif positions_from_btn == active_players - 1:
                return 'late'
            else:
                return 'middle'

    def _get_raise_action(self,round_state, valid_actions, pot_fraction=None, bb_multiplier=None):
        """Get a raise action with either pot percentage or BB multiplier"""
        action_info = valid_actions[2]
        min_raise = action_info["amount"]["min"]
        max_raise = action_info["amount"]["max"]
        
        if min_raise == -1:  # Cannot raise
            return self.do_call(valid_actions)
        
        # If we're all-in or close to it
        if max_raise <= min_raise + 1:
            return self.do_raise(valid_actions, max_raise, round_state)
            
        if pot_fraction is not None:
            # Calculate raise based on pot fraction
            pot = 0
            for action_history in self._get_all_action_histories().values():
                for action in action_history:
                    if 'amount' in action:
                        pot += action['amount']
                        
            target_amount = int(pot * pot_fraction)
            raise_amount = max(min_raise, min(max_raise, target_amount))
        elif bb_multiplier is not None:
            # Calculate raise based on BB multiplier
            bb_amount = 2 * 5  # 2 * small_blind
            target_amount = int(bb_amount * bb_multiplier)
            raise_amount = max(min_raise, min(max_raise, target_amount))
        else:
            # Default to min raise
            raise_amount = min_raise
            
        return self.do_raise(valid_actions, raise_amount, round_state)

    def _get_all_action_histories(self):
        """Safely get action histories"""
        try:
            return self.round_state['action_histories']
        except (AttributeError, KeyError):
            return {}

    # Required methods for PyPokerEngine
    def receive_game_start_message(self, game_info):
        self.total_rounds = game_info["rule"]["max_round"]
        self.starting_stack = game_info["rule"]["initial_stack"]

    def receive_round_start_message(self, round_count, hole_card, seats):
        pass

    def receive_street_start_message(self, street, round_state):
        self.round_state = round_state  # Store for later use

    def receive_game_update_message(self, action, round_state):
        self.round_state = round_state  # Keep track of latest state

    def receive_round_result_message(self, winners, hand_info, round_state):
        pass

    # Helper functions for actions
    def do_fold(self, valid_actions):
        action_info = valid_actions[0]
        amount = action_info["amount"]
        return action_info["action"], int(amount)

    def do_call(self, valid_actions):
        action_info = valid_actions[1]
        amount = action_info["amount"]
        return action_info["action"], int(amount)

    def do_raise(self, valid_actions, raise_amount, round_state):
        print(str(self))
        name = str(self)
        stack = self.search_stack(name, round_state)
        
        action_info = valid_actions[2]
        # amount has to be at least min -- this is the intended raise amount
        amount = max(action_info["amount"]["min"], raise_amount)

        if (stack < 0):
            print(f"Player: {name}, Stack: {stack}, Requested Raise: {raise_amount}, Final Amount: {amount}")
            assert(1==0)

        # cap the actual raise based on the player's actual stack
        print(stack, amount)
        if(amount == stack):
            assert(1==0)
        amount = min(amount, stack)
        if amount <= 0:
            assert(1==0)
        return action_info["action"], int(amount)

    def do_all_in(self, valid_actions, round_state):
        print(str(self))
        name = str(self)
        stack = self.search_stack(name, round_state)
        if (stack < 0):
            raise KeyError("Name not found")
        
        action_info = valid_actions[2]
        amount = stack
        return action_info["action"], amount

    # Gets the stack for a player with a given name
    def search_stack(self, name, round_state):
        stack = -1
        print(name, str(self))
        for i in round_state["seats"]:
            if i['name'] == name:
                print(f"Name found : {name} = {str(self)}")
                stack = i["stack"]
                print(stack)
        return stack

    def __str__(self):
        return type(self).__name__
