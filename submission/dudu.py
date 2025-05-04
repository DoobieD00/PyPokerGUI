import random
from itertools import combinations
from pypokerengine.players import BasePokerPlayer

# Strategic MyBot:
# - Preflop: call if pair, face+connector/gap≤2, Ace+connector, or suited with at least one Ten+ and connector;
# - Flop: call if pair on board, flush draw, or straight draw; otherwise fold
# - Turn/River: always call

def setup_ai(model_path=None):
    return DuduBot()

class DuduBot(BasePokerPlayer):
    def __init__(self):
        super(DuduBot, self).__init__()

    # Log hole cards at round start
    def receive_round_start_message(self, round_count, hole_card, seats):
        print(f"[Round {round_count}] Hole cards: {hole_card}")

    # Core decision logic
    def declare_action(self, valid_actions, hole_card, round_state):
        community_card = round_state['community_card']
        street         = round_state['street']
        round_count    = round_state['round_count']
        print(f"[Decide R{round_count}] Street: {street}, Hole: {hole_card}, Community: {community_card}")

        # Unpack hole cards: suit then rank
        s0, r0 = hole_card[0]
        s1, r1 = hole_card[1]
        ranks      = [r0, r1]
        order      = '23456789TJQKA'
        idx0, idx1 = order.index(r0), order.index(r1)
        pair       = (r0 == r1)
        connector  = abs(idx0 - idx1) <= 3  # gap ≤2 ranks
        # suited-high-connector: suited AND connector AND at least one Ten+ card
        high_ranks = set('TJQKA')
        suited_hc  = (s0 == s1 and connector and (r0 in high_ranks or r1 in high_ranks))

        # Preflop logic
        if street == 'preflop':
            if pair or suited_hc or (not suited_hc and connector and any(r in 'QKAJ' for r in ranks)):
                print("=> Preflop: playing hand")
                return self.do_call(valid_actions)
            print("=> Preflop: folding hand")
            return self.do_fold(valid_actions)

        # Flop logic
        if street == 'flop':
            flop = community_card[:3]
            board_ranks = [c[0] for c in flop]
            board_suits = [c[1] for c in flop]
            pair_on_board = any(r in board_ranks for r in ranks)
            flush_draw    = (s0 == s1 and board_suits.count(s0) >= 2)
            straight_draw = False
            unique        = sorted(set(ranks + board_ranks), key=lambda r: order.index(r))
            for combo in combinations(unique, 4):
                idxs = [order.index(r) for r in combo]
                if max(idxs) - min(idxs) == 3:
                    straight_draw = True
                    break
            if pair_on_board or flush_draw or straight_draw:
                print("=> Flop: continuing")
                return self.do_call(valid_actions)
            print("=> Flop: folding")
            return self.do_fold(valid_actions)

        # Turn/River: always call
        print(">=> Turn/River: always call")
        return self.do_call(valid_actions)

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



    def receive_game_start_message(self, game_info): 
        pass
    def receive_street_start_message(self, street, round_state): 
        pass
    def receive_game_update_message(self, action, round_state):
        pass
    def receive_round_result_message(self, winners, hand_info, round_state): 
        pass