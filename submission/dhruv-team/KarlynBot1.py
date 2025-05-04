import random

from pypokerengine.players import BasePokerPlayer
from pypokerengine.utils.card_utils import gen_cards, estimate_hole_card_win_rate



def setup_ai():
    return KarlynBot1()
class KarlynBot1(BasePokerPlayer):  # Do not forget to make parent class as "BasePokerPlayer"

    #  we define the logic to make an action through this method. (so this method would be the core of your AI)
    def declare_action(self, valid_actions, hole_card, round_state):
        # valid_actions format => [raise_action_info, call_action_info, fold_action_info]
        n = random.randint(0, 10)
        if n <= 6:
            call_action_info = valid_actions[1]
            amount = call_action_info["amount"]
        else:
            # raise
            call_action_info = valid_actions[2]
            amount = call_action_info["amount"]["min"]

        action = call_action_info["action"]
        print("valid_actions", valid_actions)
        print("return: ", action, amount)
        #print("round_state", round_state)
        return action, amount   # action returned here is sent to the poker engine

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

# from pypokerengine.api.game import setup_config, start_poker

# #config.register_player(name="p3", algorithm=FishPlayer())

# win_counts = {'AIPlayer': 0, 'RandomPlayer': 0}
# players = list(win_counts.keys())
# num_simulations = 100

# for _ in range(num_simulations):
#     config = setup_config(max_round=10, initial_stack=100, small_blind_amount=5)
#     config.register_player(name="AIPlayer", algorithm=TightAggressivePlayer())
#     config.register_player(name="RandomPlayer", algorithm=RandomPlayer())
#     game_result = start_poker(config, verbose=0)
#     # Determine the winner (player with the highest stack)
#     stacks = {player['name']: player['stack'] for player in game_result['players']}
#     winner = max(stacks, key=stacks.get)  # Player with the highest stack
#     win_counts[winner] += 1

# print(win_counts)