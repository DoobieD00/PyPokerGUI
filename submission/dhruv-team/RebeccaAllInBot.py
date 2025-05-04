from pypokerengine.players import BasePokerPlayer

def setup_ai():
    return RebeccaAllInBot()

class RebeccaAllInBot(BasePokerPlayer):
    def __init__(self):
        super().__init__()

    def declare_action(self, valid_actions, hole_card, round_state):
        # Always go all-in if possible
        my_stack = next((seat['stack'] for seat in round_state['seats'] if seat['uuid'] == self.uuid), 0)
        if my_stack == 0:
            return self.do_fold(valid_actions)
        return self.do_all_in(valid_actions)

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

    # Helper functions
    def do_fold(self, valid_actions):
        action_info = next((act for act in valid_actions if act['action'] == 'fold'), valid_actions[0])
        return action_info['action'], action_info['amount']

    def do_all_in(self, valid_actions):
        action_info = next((act for act in valid_actions if act['action'] == 'raise'), valid_actions[2])
        amount = action_info['amount']['max']
        return action_info['action'], amount
