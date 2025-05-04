import random

from pypokerengine.players import BasePokerPlayer
from pypokerengine.utils.card_utils import gen_cards, estimate_hole_card_win_rate


def setup_ai():
    return KarlynBot2()

class KarlynBot2(BasePokerPlayer):

    def declare_action(self, valid_actions, hole_card, round_state):
        community_card = round_state['community_card']
        nb_simulation = 100  # Monte Carlo simulations

        win_rate = estimate_hole_card_win_rate(
            nb_simulation, 2,
            gen_cards(hole_card),
            gen_cards(community_card)
        )

        # Extract available actions
        fold_action = [a for a in valid_actions if a["action"] == "fold"][0]
        call_action = [a for a in valid_actions if a["action"] == "call"][0]
        raise_action = [a for a in valid_actions if a["action"] == "raise"][0]

        # Decision logic based on win rate
        if win_rate >= 0.7:
            action = raise_action["action"]
            amount = raise_action["amount"]["max"]
        elif win_rate >= 0.3:
            action = call_action["action"]
            amount = call_action["amount"]
        else:
            action = fold_action["action"]
            amount = fold_action["amount"]

        return action, amount

    def receive_game_start_message(self, game_info):
        pass

    def receive_round_start_message(self, round_count, hole_card, seats):
        pass

    def receive_street_start_message(self, street, round_state):
        pass

    def receive_game_update_message(self, new_action, round_state):
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