import random
import eval7
from pypokerengine.players import BasePokerPlayer

def setup_ai():
    return MyBot()

class MyBot(BasePokerPlayer):

    def declare_action(self, valid_actions, hole_card, round_state):
        community_card = round_state['community_card']
        street = round_state['street']

        # Only evaluate strength pre-flop
        if street == 'preflop':
            rand = random.random()

            # 13% chance to go all-in preflop
            if rand < 0.17:
                return self.do_all_in(valid_actions)
            # 12% chance to fold preflop
            elif rand < 0.25:
                return self.do_fold(valid_actions)

            # Estimate hand strength using eval7
            strength = self.estimate_hand_strength(hole_card, community_card)

            # Use strength to decide action
            if strength > 0.8:
                return self.do_all_in(valid_actions)
            elif strength > 0.6:
                action_info = valid_actions[2]
                amount = action_info['amount']['min']
                return self.do_raise(valid_actions, amount)
            elif strength > 0.4:
                return self.do_call(valid_actions)
            else:
                return self.do_fold(valid_actions)

        # Simple post-flop logic: call 70% of time, fold 30%
        return self.do_call(valid_actions) if random.random() < 0.7 else self.do_fold(valid_actions)

    def estimate_hand_strength(self, hole_cards, community_cards, simulations=100):
        hole = [eval7.Card(self.convert_card(c)) for c in hole_cards]
        community = [eval7.Card(self.convert_card(c)) for c in community_cards]
        
        deck = eval7.Deck()
        for card in hole + community:
            deck.cards.remove(card)

        wins, ties = 0, 0
        for _ in range(simulations):
            deck.shuffle()
            opp_hand = deck.peek(2)
            remaining_community = deck.peek(5 - len(community), offset=2)

            our_hand = hole + community + remaining_community
            opp_full = opp_hand + community + remaining_community

            our_score = eval7.evaluate(our_hand)
            opp_score = eval7.evaluate(opp_full)

            if our_score > opp_score:
                wins += 1
            elif our_score == opp_score:
                ties += 1

        return (wins + ties * 0.5) / simulations

    def convert_card(self, card_str):
        # Converts PyPokerEngine card string (e.g. '10H') to eval7 format (e.g. 'Th')
        rank_conversion = {'10': 'T'}
        rank = rank_conversion.get(card_str[:-1], card_str[0])
        suit = card_str[-1].lower()
        return f"{rank}{suit}"

    # Game state methods
    def receive_game_start_message(self, game_info): pass
    def receive_round_start_message(self, round_count, hole_card, seats): pass
    def receive_street_start_message(self, street, round_state): pass
    def receive_game_update_message(self, action, round_state): pass
    def receive_round_result_message(self, winners, hand_info, round_state): pass

    # Action helpers
    def do_fold(self, valid_actions):
        return valid_actions[0]['action'], valid_actions[0]['amount']

    def do_call(self, valid_actions):
        return valid_actions[1]['action'], valid_actions[1]['amount']

    def do_raise(self, valid_actions, raise_amount):
        action_info = valid_actions[2]
        amount = max(action_info['amount']['min'], min(raise_amount, action_info['amount']['max']))
        return action_info['action'], amount

    def do_all_in(self, valid_actions):
        action_info = valid_actions[2]
        return action_info['action'], action_info['amount']['max']