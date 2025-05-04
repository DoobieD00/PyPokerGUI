import random
import eval7
from pypokerengine.players import BasePokerPlayer

def setup_ai():
    return DhruvBot()

class DhruvBot(BasePokerPlayer):

    def declare_action(self, valid_actions, hole_card, round_state):
        community_card = round_state['community_card']
        street = round_state['street']

        # Only evaluate strength pre-flop
        if street == 'preflop':
            rand = random.random()

            # 13% chance to go all-in preflop
            if rand < 0.17:
                return self.do_all_in(valid_actions, round_state)
            # 12% chance to fold preflop
            elif rand < 0.25:
                return self.do_fold(valid_actions)

            # Estimate hand strength using eval7
            strength = self.estimate_hand_strength(hole_card, community_card)

            # Use strength to decide action
            if strength > 0.8:
                return self.do_all_in(valid_actions, round_state)
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
        print(hole_cards)
        hole = [eval7.Card(c[::-1][0] + c[::-1][1].lower()) for c in hole_cards]  # to match expected format

        community = [eval7.Card(c[::-1][0] + c[::-1][1].lower()) for c in community_cards]  # to match expected format

        
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