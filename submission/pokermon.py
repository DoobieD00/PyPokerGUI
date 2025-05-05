import random
from pypokerengine.players import BasePokerPlayer

# Notes
# All cards follow this format: Suit + Rank : 4 of Hearts = 4H, 10 of Spades = ST [2,3,4,5,6,7,8,9,T,J,Q,K,A] [S,C,D,H]

def setup_ai():
    return pokermon()

class pokermon(BasePokerPlayer):  # Do not forget to make parent class as "BasePokerPlayer"

    #  we define the logic to make an action through this method. (so this method would be the core of your AI)
    def declare_action(self, valid_actions, hole_card, round_state):
        # For your convenience:
        community_card = round_state['community_card']                  # array, starting from [] to [] of 5 elems
        street = round_state['street']                                  # preflop, flop, turn, river
        pot = round_state['pot']                                        # dict : {'main': {'amount': int}, 'side': {'amount': int}}
        dealer_btn = round_state['dealer_btn']                          # int : user id of the player acting as the dealer
        next_player = round_state['next_player']                        # int : user id of next player
        small_blind_pos = round_state['small_blind_pos']                # int : user id of player with small blind (next player is big blind)
        big_blind_pos = round_state['big_blind_pos']                    # int : user id of player with big blind
        round_count = round_state['round_count']                        # int : round number
        small_blind_amount = round_state['small_blind_amount']          # int : amount of starting small blind
        seats = round_state['seats']                                    # {'name' : the AI name, 'uuid': their user id, 'stack': their stack/remaining money, 'state': participating/folded}
                                                                        # we recommend if you're going to try to find your own user id, name your own class name and ai name the same
        action_histories = round_state['action_histories']              # {'preflop': [{'action': 'SMALLBLIND', 'amount': 10, 'add_amount': 10, 'uuid': '1'}, {'action': 'BIGBLIND', 'amount': 20, 'add_amount': 10, 'uuid': '2'},
                                                                        #   {'action': 'CALL', 'amount': 20, 'paid': 20, 'uuid': '3'}, {'action': 'CALL', 'amount': 20, 'paid': 20, 'uuid': '0'}, 
                                                                        #   {'action': 'CALL', 'amount': 20, 'paid': 10, 'uuid': '1'}, {'action': 'FOLD', 'uuid': '2'}]}   -- sample action history for preflop
                                                                        # {'flop': [{'action': 'CALL', 'amount': 0, 'paid': 0, 'uuid': '1'}]}  -- sample for flop

        uuid = self.uuid
        seats = round_state['seats']
        my_stack = [p['stack'] for p in seats if p['uuid'] == uuid][0]

        rank_order = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
                    '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        ranks = [card[1] for card in hole_card]
        min_raise = max(valid_actions[2]['amount']['min'], 0)
        max_raise = max(valid_actions[2]['amount']['max'], 0)
        call_amount = valid_actions[1]['amount']

        def is_really_strong_preflop():
            return ranks[0] == ranks[1] and rank_order[ranks[0]] >= 13  # AA or KK

        def is_strong_preflop():
            r1, r2 = ranks
            return (r1 == r2 and rank_order[r1] >= 12) or \
                (set([r1, r2]) == set(['A', 'K']))

        def is_really_strong_postflop():
            board_ranks = [card[1] for card in community_card]
            return ranks[0] == ranks[1] and ranks[0] in board_ranks

        def is_strong_postflop():
            board_ranks = [card[1] for card in community_card]
            for r in ranks:
                if r in board_ranks:
                    return True
            if ranks[0] == ranks[1] and rank_order[ranks[0]] >= 10:
                return True
            return False

        def detect_suspicious_player():
            streets = ['preflop', 'flop', 'turn', 'river']
            current_idx = streets.index(street)
            if current_idx == 0:
                return False
            prev_street = streets[current_idx - 1]
            curr_actions = action_histories.get(street, [])
            prev_actions = action_histories.get(prev_street, [])

            passive_players = set()
            for action in prev_actions:
                if action['action'] in ['CALL', 'CHECK'] and action.get('paid', 0) == 0:
                    passive_players.add(action['uuid'])

            for action in curr_actions:
                if action['uuid'] in passive_players and action['action'] in ['RAISE', 'ALLIN']:
                    return True
            return False

        if detect_suspicious_player():
            return self.do_fold(valid_actions)

        if street == "preflop":
            really_strong = is_really_strong_preflop()
            strong = is_strong_preflop()
        else:
            really_strong = is_really_strong_postflop()
            strong = is_strong_postflop()

        if really_strong:
            return self.do_all_in(valid_actions, round_state)

        if strong:
            if min_raise <= max_raise:
                return self.do_raise(valid_actions, min_raise * 2, round_state)
            else:
                return self.do_call(valid_actions)

        if call_amount > 0.25 * my_stack:
            return self.do_fold(valid_actions)

        if call_amount == 0:
            return self.do_call(valid_actions)
        else:
            return self.do_call(valid_actions)



    def receive_game_start_message(self, game_info):
        # Predefined variables for various game information --  feel free to use them however you like
        player_num = game_info["player_num"]
        max_round = game_info["rule"]["max_round"]
        small_blind_amount = game_info["rule"]["small_blind_amount"]
        ante_amount = game_info["rule"]["ante"]
        blind_structure = game_info["rule"]["blind_structure"]

    def receive_round_start_message(self, round_count, hole_card, seats):
        pass

    def receive_street_start_message(self, street, round_state):
        pass

    def receive_game_update_message(self, action, round_state):
        pass

    def receive_round_result_message(self, winners, hand_info, round_state):
        pass


    # Helper functions  -- call these in the declare_action function to declare your move
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


