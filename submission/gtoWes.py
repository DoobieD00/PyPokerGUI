from pypokerengine.players import BasePokerPlayer
import pied_poker as pp

# Notes
# All cards follow this format: Suit + Rank : 4 of Hearts = 4H, 10 of Spades = ST [2,3,4,5,6,7,8,9,T,J,Q,K,A] [S,C,D,H]

def setup_ai():
    return gtowes()

class gtowes(BasePokerPlayer):  # Do not forget to make parent class as "BasePokerPlayer"

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

        # Minimum and maximum raise values (max raise ==> all in)
        min_raise = valid_actions[2]['amount']['min']
        max_raise = valid_actions[2]['amount']['max']

        # --------------------------------------------------------------------------------------------------------#
        #LOGIC BEGINS HERE

        total_participating = 0
        for player in seats:
            if player['state'] == 'participating':
                total_participating += 1
       
        reformated_holecard = []
        reformat_community = []

        # SET reformatted hole card and commiunity card
        for card in hole_card:
            if 'T' in card:
                reformated_holecard.append(('10' + card[0].lower()))
            else:
                reformated_holecard.append(card[::-1].lower())
        for card in community_card:
            if 'T' in card:
                reformat_community.append(('10' + card[0]).lower())
            else:
                reformat_community.append((card[::-1].lower()))
                
        #Conduct simulation of hand
        p1 = pp.Player('WES', pp.Card.of(reformated_holecard[0], reformated_holecard[1]))
        simulator = pp.PokerRound.PokerRoundSimulator(community_cards= pp.Card.of(*reformat_community),
                       players=[p1],
                      total_players=total_participating)
        num_simulations = 1000
        simulation_result = simulator.simulate(n=num_simulations, n_jobs=1)

        winpercent = str(simulation_result.probability_of(pp.Probability.PlayerWins())).split('%')[0]

        benchmarkpercent = 100 / total_participating

        # fold or do min-raise
        if float(winpercent) >= (int((valid_actions[1]['amount']) / 
                                        (int((valid_actions[1]['amount'])) + int(pot["main"]["amount"])) * 100)):
            action = "call"
        else:
            action = "fold"

        if (max_raise != -1):
            if float(winpercent) > float(benchmarkpercent):
                action = 'raise'
                amount = max_raise

        # Sample code: feel free to rewrite
        if action == "call":
            return self.do_call(valid_actions)
        if action == "fold":
            return self.do_fold(valid_actions)
        if action == 'raise':
            return self.do_raise(valid_actions, amount, round_state)
    
        # -------------------------------------------------------------------------------------------------------#
        # Make sure that you call one of the actions (self.do_fold, self.do_call, self.do_raise, self.do_all_in)
        # All in is defined as raise using all of your remaining stack (chips)



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
