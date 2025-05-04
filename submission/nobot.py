import random
from pypokerengine.players import BasePokerPlayer
from pypokerengine.utils.card_utils import gen_cards, estimate_hole_card_win_rate

class HandStrengthEvaluator:
    @staticmethod
    def evaluate_hand_strength(hole_cards, community_cards):
        total_cards = hole_cards + community_cards

        # Check for premium starting hands
        if len(community_cards) == 0:
            ranks = [card[1] for card in hole_cards]
            suits = [card[0] for card in hole_cards]

            # Pocket pairs
            if ranks[0] == ranks[1]:
                if ranks[0] in ['A', 'K', 'Q', 'J', 'T']:
                    return 0.95  # Premium pocket pairs
                elif ranks[0] in ['9', '8', '7']:
                    return 0.85  # Medium pocket pairs
                else:
                    return 0.75  # Low pocket pairs

            # Suited high cards
            if suits[0] == suits[1]:
                if set(ranks) & set(['A', 'K', 'Q', 'J']):
                    return 0.8  # Suited high cards

            # High card combinations
            if 'A' in ranks:
                if 'K' in ranks or 'Q' in ranks or 'J' in ranks:
                    return 0.75  # Ace with face card
                return 0.6  # Ace with lower card

            if 'K' in ranks and ('Q' in ranks or 'J' in ranks):
                return 0.65  # King with face card

            # Connected cards
            card_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
                          '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
            if abs(card_values[ranks[0]] - card_values[ranks[1]]) == 1:
                return 0.65 if max(card_values[ranks[0]], card_values[ranks[1]]) > 10 else 0.55

            # Default preflop strength
            return 0.4

        # For post-flop, we'll use a Monte Carlo simulation
        if len(total_cards) < 7:
            win_rate = estimate_hole_card_win_rate(
                nb_simulation=1000,
                nb_player=2,
                hole_card=gen_cards(hole_cards),
                community_card=gen_cards(community_cards)
            )
            return win_rate

        # For completed hands, we'll assign a strength value directly
        return 0.7  # Default for completed hand

class PositionEvaluator:
    @staticmethod
    def evaluate_position(seats, dealer_btn, my_uuid):
        num_active_players = sum(1 for seat in seats if seat['state'] == 'participating')

        # Find my position relative to dealer
        my_position = -1
        for i, seat in enumerate(seats):
            if seat['uuid'] == my_uuid:
                my_position = i
                break

        if my_position == -1:
            return 0.5  # Default if we can't determine position

        # Calculate relative position (0 = early, 1 = late)
        relative_position = 0
        if num_active_players <= 3:
            # Heads up or 3-handed
            if my_position == dealer_btn:
                relative_position = 1  # Button is best
            else:
                relative_position = 0.3
        else:
            # Multi-handed game
            positions_after_dealer = (my_position - dealer_btn) % len(seats)
            if positions_after_dealer < num_active_players / 3:
                relative_position = 0.2  # Early position
            elif positions_after_dealer < 2 * num_active_players / 3:
                relative_position = 0.6  # Middle position
            else:
                relative_position = 0.9  # Late position

        return relative_position

class OpponentModeling:
    def __init__(self):
        self.player_profiles = {}  # uuid -> profile data

    def update_profile(self, uuid, action, amount, street, pot_size):
        if uuid not in self.player_profiles:
            self.player_profiles[uuid] = {
                'aggression_factor': 0.5,  # 0 = passive, 1 = aggressive
                'preflop_vpip': 0.5,       # Voluntarily put money in pot
                'pfr': 0.3,                # Preflop raise %
                'af_by_street': {'preflop': 0.5, 'flop': 0.5, 'turn': 0.5, 'river': 0.5},
                'n_hands': 0,
                'actions': []
            }

        profile = self.player_profiles[uuid]
        profile['n_hands'] += 1
        profile['actions'].append((street, action, amount, pot_size))

        # Update aggression metrics
        if action == 'RAISE' or action == 'CALL':
            # Update VPIP for preflop
            if street == 'preflop':
                profile['preflop_vpip'] = (profile['preflop_vpip'] * (profile['n_hands'] - 1) + 1) / profile['n_hands']
                if action == 'RAISE':
                    profile['pfr'] = (profile['pfr'] * (profile['n_hands'] - 1) + 1) / profile['n_hands']

            # Update aggression factor
            if action == 'RAISE':
                street_af = profile['af_by_street'][street]
                profile['af_by_street'][street] = (street_af * 4 + 1) / 5  # Exponential moving average
                profile['aggression_factor'] = sum(profile['af_by_street'].values()) / 4

    def get_exploit_strategy(self, uuid, hand_strength, position_value, pot_odds):
        if uuid not in self.player_profiles or self.player_profiles[uuid]['n_hands'] < 5:
            return None  # Not enough data to exploit

        profile = self.player_profiles[uuid]

        # Against aggressive players, tighten up and value bet more
        if profile['aggression_factor'] > 0.7:
            # They're aggressive, we should be more selective but value bet stronger
            if hand_strength > 0.7:
                return 'value_bet'  # Bet for value against aggressive player
            elif hand_strength < 0.5:
                return 'fold'  # Fold weak hands against aggression

        # Against passive players, bluff more and value bet thinner
        elif profile['aggression_factor'] < 0.3:
            if position_value > 0.7 and hand_strength > 0.3:
                return 'bluff'  # Bluff in position against passive players
            elif hand_strength > 0.6:
                return 'value_bet'  # Value bet good hands

        # Against balanced players, play more GTO
        return None

class PotOddsCalculator:
    @staticmethod
    def calculate_pot_odds(call_amount, pot_size):
        if call_amount == 0:
            return 0  # No need to call, pot odds are 0 (always check)

        return call_amount / (pot_size + call_amount)

    @staticmethod
    def should_call(hand_strength, pot_odds, implied_odds_factor=1.2):
        # Add implied odds to the calculation
        effective_pot_odds = pot_odds / implied_odds_factor
        return hand_strength >= effective_pot_odds

class StrategyManager:
    def __init__(self):
        self.hand_evaluator = HandStrengthEvaluator()
        self.position_evaluator = PositionEvaluator()
        self.opponent_modeler = OpponentModeling()
        self.pot_odds_calculator = PotOddsCalculator()
        self.my_stack_history = []

    def decide_action(self, valid_actions, hole_card, community_card, round_state, my_uuid):
        street = round_state['street']
        pot = round_state['pot']['main']['amount']
        dealer_btn = round_state['dealer_btn']
        seats = round_state['seats']
        action_histories = round_state['action_histories']

        # Calculate current pot odds
        call_amount = valid_actions[1]['amount']
        pot_odds = self.pot_odds_calculator.calculate_pot_odds(call_amount, pot)

        # Evaluate hand strength
        hand_strength = self.hand_evaluator.evaluate_hand_strength(hole_card, community_card)

        # Evaluate position
        position_value = self.position_evaluator.evaluate_position(seats, dealer_btn, my_uuid)

        # Track opponent actions and update models
        if street in action_histories:
            for action_info in action_histories[street]:
                if action_info['uuid'] != my_uuid:
                    self.opponent_modeler.update_profile(
                        action_info['uuid'],
                        action_info['action'],
                        action_info.get('amount', 0),
                        street,
                        pot
                    )

        # Determine optimal strategy based on hand strength, position, and opponent tendencies
        action, amount = self.determine_strategy(
            valid_actions,
            hand_strength,
            position_value,
            pot_odds,
            street,
            pot,
            call_amount,
            my_uuid
        )

        return action, amount

    def determine_strategy(self, valid_actions, hand_strength, position_value, pot_odds, street, pot, call_amount, my_uuid):
        # Preflop strategy
        if street == 'preflop':
            return self.preflop_strategy(valid_actions, hand_strength, position_value, pot_odds)

        # Postflop strategies
        if hand_strength > 0.8:  # Very strong hand
            return self.strong_hand_strategy(valid_actions, hand_strength, pot)
        elif hand_strength > 0.6:  # Good hand
            return self.good_hand_strategy(valid_actions, hand_strength, position_value, pot)
        elif hand_strength > 0.4:  # Mediocre hand
            return self.mediocre_hand_strategy(valid_actions, hand_strength, position_value, pot_odds)
        else:  # Weak hand
            return self.weak_hand_strategy(valid_actions, position_value, pot_odds)

    def preflop_strategy(self, valid_actions, hand_strength, position_value, pot_odds):
        # Premium hands - raise or re-raise
        if hand_strength > 0.85:
            if valid_actions[2]['amount']['min'] != -1:  # Can raise
                raise_amount = valid_actions[2]['amount']['min'] * 3  # 3x raise
                return 'raise', min(raise_amount, valid_actions[2]['amount']['max'])
            return 'call', valid_actions[1]['amount']

        # Strong hands - raise from late, call from early
        if hand_strength > 0.7:
            if position_value > 0.6 and valid_actions[2]['amount']['min'] != -1:  # Late position and can raise
                raise_amount = valid_actions[2]['amount']['min'] * 2.5  # 2.5x raise
                return 'raise', min(raise_amount, valid_actions[2]['amount']['max'])
            return 'call', valid_actions[1]['amount']

        # Speculative hands - call from late, fold from early unless great pot odds
        if hand_strength > 0.5:
            if position_value > 0.7 or pot_odds < 0.15:  # Late position or getting great odds
                return 'call', valid_actions[1]['amount']
            else:
                return 'fold', 0

        # Weak hands - mostly fold, occasionally raise as a bluff from late position
        if position_value > 0.9 and random.random() < 0.2:  # Occasional bluff from button
            if valid_actions[2]['amount']['min'] != -1:
                raise_amount = valid_actions[2]['amount']['min'] * 2.5
                return 'raise', min(raise_amount, valid_actions[2]['amount']['max'])

        # Default to folding weak hands
        if pot_odds < 0.1:  # Very cheap to call
            return 'call', valid_actions[1]['amount']
        return 'fold', 0

    def strong_hand_strategy(self, valid_actions, hand_strength, pot):
        # With very strong hands, maximize value
        if valid_actions[2]['amount']['min'] != -1:  # Can raise
            # Size bet relative to pot and hand strength
            raise_amount = int(pot * (0.5 + hand_strength * 0.5))  # 50-100% pot bet
            return 'raise', min(raise_amount, valid_actions[2]['amount']['max'])
        return 'call', valid_actions[1]['amount']

    def good_hand_strategy(self, valid_actions, hand_strength, position_value, pot):
        # With good hands, bet for value but be cautious
        if valid_actions[2]['amount']['min'] != -1:
            # Bet more aggressively in position
            bet_sizing = 0.5 if position_value > 0.6 else 0.3
            raise_amount = int(pot * bet_sizing)
            return 'raise', min(raise_amount, valid_actions[2]['amount']['max'])
        return 'call', valid_actions[1]['amount']

    def mediocre_hand_strategy(self, valid_actions, hand_strength, position_value, pot_odds):
        # With mediocre hands, check/call or make small bets in position
        if pot_odds == 0:  # Can check
            if position_value > 0.7 and valid_actions[2]['amount']['min'] != -1:
                # Small bet as a semi-bluff in position
                raise_amount = valid_actions[2]['amount']['min']
                return 'raise', raise_amount
            return 'call', 0  # Check

        # Call if getting decent odds
        if self.pot_odds_calculator.should_call(hand_strength, pot_odds):
            return 'call', valid_actions[1]['amount']
        return 'fold', 0

    def weak_hand_strategy(self, valid_actions, position_value, pot_odds):
        # With weak hands, mostly check/fold, occasionally bluff
        if pot_odds == 0:  # Can check
            if position_value > 0.8 and random.random() < 0.3 and valid_actions[2]['amount']['min'] != -1:
                # Occasional bluff from late position
                raise_amount = valid_actions[2]['amount']['min']
                return 'raise', raise_amount
            return 'call', 0  # Check

        # Call only with great pot odds
        if pot_odds < 0.1:
            return 'call', valid_actions[1]['amount']
        return 'fold', 0

def setup_ai():
    return NoBot()

class NoBot(BasePokerPlayer):  # Do not forget to make parent class as "BasePokerPlayer"
    def __init__(self):
        super().__init__()
        self.strategy_manager = StrategyManager()
        self.uuid = None
        self.hole_cards_history = []
        self.round_state_history = []
        self.action_history = []

    #  we define the logic to make an action through this method. (so this method would be the core of your AI)
    def declare_action(self, valid_actions, hole_card, round_state):
        # Determine my UUID if we don't have it yet
        if self.uuid is None:
            self.uuid = self.find_my_uuid(round_state)

        # Store history for learning
        self.hole_cards_history.append(hole_card)
        self.round_state_history.append(round_state)

        # Get the optimal action from our strategy manager
        action, amount = self.strategy_manager.decide_action(
            valid_actions,
            hole_card,
            round_state['community_card'],
            round_state,
            self.uuid
        )

        # Record our action
        self.action_history.append((action, amount))

        # Execute the chosen action
        if action == "fold":
            return self.do_fold(valid_actions)
        elif action == "call":
            return self.do_call(valid_actions)
        elif action == "raise":
            if amount >= valid_actions[2]['amount']['max']:
                return self.do_all_in(valid_actions)
            return self.do_raise(valid_actions, amount)

        # Default to calling if somehow no action was selected
        return self.do_call(valid_actions)

    def find_my_uuid(self, round_state):
        # Try to find our uuid by matching the class name with the player name
        my_name = self.__class__.__name__
        for seat in round_state['seats']:
            if seat['name'] == my_name:
                return seat['uuid']

        # If that didn't work, use the next_player as a fallback
        return round_state['next_player']

    def receive_game_start_message(self, game_info):
        # Initialize game-specific parameters
        self.player_num = game_info["player_num"]
        self.max_round = game_info["rule"]["max_round"]
        self.small_blind_amount = game_info["rule"]["small_blind_amount"]
        self.ante_amount = game_info["rule"]["ante"]
        self.blind_structure = game_info["rule"]["blind_structure"]

    def receive_round_start_message(self, round_count, hole_card, seats):
        # Reset round-specific tracking
        self.current_round_hole_card = hole_card

    def receive_street_start_message(self, street, round_state):
        # Update state at the beginning of each street
        pass

    def receive_game_update_message(self, new_action, round_state):
        # Track opponent actions for modeling
        if self.uuid is None:
            self.uuid = self.find_my_uuid(round_state)

        # Update our opponent models with this new action
        if new_action['player_uuid'] != self.uuid:
            street = round_state['street']
            self.strategy_manager.opponent_modeler.update_profile(
                new_action['player_uuid'],
                new_action['action'],
                new_action.get('amount', 0),
                street,
                round_state['pot']['main']['amount']
            )

    def receive_round_result_message(self, winners, hand_info, round_state):
        # Learn from the round result
        self.analyze_round_result(winners, hand_info, round_state)

    def analyze_round_result(self, winners, hand_info, round_state):
        # Simple win/loss analysis to refine strategy
        my_uuid_in_winners = any(winner['uuid'] == self.uuid for winner in winners)

        # If we won, our strategy worked well for this hand
        if my_uuid_in_winners:
            # Could implement reinforcement learning here to adjust weights
            pass
        else:
            # Could implement learning from mistakes
            pass

    # Helper functions  -- call these in the declare_action function to declare your move
    def do_fold(self, valid_actions):
        action_info = valid_actions[0]
        amount = action_info["amount"]
        return action_info['action'], amount

    def do_call(self, valid_actions):
        action_info = valid_actions[1]
        amount = action_info["amount"]
        return action_info['action'], amount

    def do_raise(self, valid_actions, raise_amount):
        action_info = valid_actions[2]
        amount = max(action_info['amount']['min'], raise_amount)
        return action_info['action'], amount

    def do_all_in(self, valid_actions):
        action_info = valid_actions[2]
        amount = action_info['amount']['max']
        return action_info['action'], amount
