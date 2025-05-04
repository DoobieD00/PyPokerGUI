import random
from pypokerengine.players import BasePokerPlayer
from deepstack_agent import DeepStackAgent

def setup_ai():
    return GigaBrain()

class GigaBrain(BasePokerPlayer):
    def __init__(self):
        super(GigaBrain, self).__init__()
        self.agent = DeepStackAgent()

    def declare_action(self, valid_actions, hole_card, round_state):
        # Add try-except for robustness
        try:
            print("\n--- New decision point ---")
            print(f"Hole cards: {hole_card}")
            print(f"Community cards: {round_state['community_card']}")
            print(f"Valid actions: {valid_actions}")
            
            # Simply delegate to the DeepStack agent
            action, amount = self.agent.declare_action(valid_actions, hole_card, round_state)
            
            # Convert the action into the expected format using helper methods
            if action == "fold":
                return self.do_fold(valid_actions)
            elif action == "call":
                return self.do_call(valid_actions)
            elif action == "raise":
                return self.do_raise(valid_actions, amount, round_state)
            else:
                # Default fallback
                return self.do_call(valid_actions)
        except Exception as e:
            print(f"Error in declare_action: {e}")
            # Default to call in case of any error
            return self.do_call(valid_actions)

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

    # Helper functions remain unchanged
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
