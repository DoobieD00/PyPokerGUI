import random
from pypokerengine.players import BasePokerPlayer
from pypokerengine.players import BasePokerPlayer
from pypokerengine.utils.card_utils import gen_cards, estimate_hole_card_win_rate
from pypokerengine.engine.hand_evaluator import HandEvaluator
from collections import Counter
from treys import Card, Evaluator

#EXTERNAL LIBRARY: Treys
#pip install treys

def setup_ai():
    return SMPEX()


class SMPEX(BasePokerPlayer):  # Do not forget to make parent class as "BasePokerPlayer"
    def transform_poker_hand(self, hand):
        """
        Convert a list of cards like ['CJ','SA','S10'] (suit+rank)
        into ['Jc','As','10s'] (rank+suit lowercase).
        """
        newCards = [card[1:] + card[0].lower() for card in hand]
        handFormat = []
        for i in newCards:
            handFormat.append(Card.new(i))
        return handFormat

    #  we define the logic to make an action through this method. (so this method would be the core of your AI)
    def declare_action(self, valid_actions, hole_card, round_state):
        # For your convenience:
        community_card = round_state[
            "community_card"
        ]  # array, starting from [] to [] of 5 elems
        street = round_state["street"]  # preflop, flop, turn, river
        pot = round_state[
            "pot"
        ]  # dict : {'main': {'amount': int}, 'side': {'amount': int}}
        dealer_btn = round_state[
            "dealer_btn"
        ]  # int : user id of the player acting as the dealer
        next_player = round_state["next_player"]  # int : user id of next player
        small_blind_pos = round_state[
            "small_blind_pos"
        ]  # int : user id of player with small blind (next player is big blind)
        big_blind_pos = round_state[
            "big_blind_pos"
        ]  # int : user id of player with big blind
        round_count = round_state["round_count"]  # int : round number
        small_blind_amount = round_state[
            "small_blind_amount"
        ]  # int : amount of starting small blind
        seats = round_state[
            "seats"
        ]  # {'name' : the AI name, 'uuid': their user id, 'stack': their stack/remaining money, 'state': participating/folded}
        # we recommend if you're going to try to find your own user id, name your own class name and ai name the same
        action_histories = round_state[
            "action_histories"
        ]  # {'preflop': [{'action': 'SMALLBLIND', 'amount': 10, 'add_amount': 10, 'uuid': '1'}, {'action': 'BIGBLIND', 'amount': 20, 'add_amount': 10, 'uuid': '2'},
        #   {'action': 'CALL', 'amount': 20, 'paid': 20, 'uuid': '3'}, {'action': 'CALL', 'amount': 20, 'paid': 20, 'uuid': '0'},
        #   {'action': 'CALL', 'amount': 20, 'paid': 10, 'uuid': '1'}, {'action': 'FOLD', 'uuid': '2'}]}   -- sample action history for preflop
        # {'flop': [{'action': 'CALL', 'amount': 0, 'paid': 0, 'uuid': '1'}]}  -- sample for flop

        # Minimum and maximum raise values (max raise ==> all in)
        min_raise = valid_actions[2]["amount"]["min"]
        max_raise = valid_actions[2]["amount"]["max"]

        # --------------------------------------------------------------------------------------------------------#
        # Sample code: feel free to rewrite
        """action = random.choice(valid_actions)["action"]
        if action == "raise":
            action_info = valid_actions[2]
            amount = random.randint(action_info["amount"]["min"], action_info["amount"]["max"])
            if amount == -1: action = "call"
        if action == "call":
            return self.do_call(valid_actions)
        if action == "fold":
            return self.do_fold(valid_actions)
        return self.do_raise(valid_actions, amount)   # action returned here is sent to the poker engine"""
        # -------------------------------------------------------------------------------------------------------#
        # Make sure that you call one of the actions (self.do_fold, self.do_call, self.do_raise, self.do_all_in)
        # All in is defined as raise using all of your remaining stack (chips)
        evaluator = Evaluator()
        transformed_card = self.transform_poker_hand(hole_card)
        # Update community cards from game state
        self.community_cards = round_state["community_card"]
        # Get current game phase
        street = round_state["street"]
        # Calculate current stack size by finding player's seat
        # seat = [s for s in round_state["seats"] if s["uuid"] == self.uuid][0]["uuid"]

        # current_stack = [s for s in round_state["seats"] if s["uuid"] == self.uuid][0][
        #   "stack"
        # ]
        seat = [s for s in round_state["seats"] if s["uuid"] == self.uuid][0]["uuid"]
        #print(f"mybot uuid:{seat}", file=sys.stderr, flush=True)
        ##print("my seat", seat, file=sys.stderr, flush=True)
        ##print("my uuid", self.uuid, file=sys.stderr, flush=True)
        ##print(
        #    "starting stack pre alter", self.starting_stack, file=sys.stderr, flush=True
        #)
        blind_state = "None"
        if str(seat) == str(round_state["big_blind_pos"]) and self.blind_adjusted == False:
            self.starting_stack += round_state["small_blind_amount"] * 2
            self.blind_adjusted = True
            blind_state = "Big"
        elif str(seat) == str(round_state["small_blind_pos"]) and self.blind_adjusted == False:
                self.starting_stack += round_state["small_blind_amount"]
                self.blind_adjusted = True
                blind_state = "Small"
        # Route to phase-specific logic
        if street == "preflop":
            if blind_state == "Big" or blind_state == "Small":
                #Card.#print_pretty_cards(transformed_card)
                return self.preflop_action(valid_actions, hole_card)
            else:
                #Card.#print_pretty_cards(transformed_card)
                return self.preflop_action(valid_actions, hole_card)
        elif street == "flop":
            # #print(evaluator.evaluate(self.community_cards, hole_card), flush=True)
            return self.flop_action(valid_actions, hole_card, round_state)
            # return self.do_fold(valid_actions)
        elif street == "turn":
            # return self.turn_action(valid_actions, hole_card, current_stack)
            return self.turn_action(valid_actions,hole_card, round_state)
        elif street == "river":
            # return self.river_action(valid_actions, hole_card, current_stack)
            return self.river_action(valid_actions,hole_card, round_state)
        # Fallback to folding
        return self.do_fold(valid_actions)

    def preflop_action(self, valid_actions, hole_card):

        # Convert card ranks to numerical values (2=0, A=12)
        ranks = sorted([self.card_rank(c) for c in hole_card])
        # Check if cards are same suit
        suited = len({c[0] for c in hole_card}) == 1
        # Print suited status for debugging
        #print("Is suited?", suited, file=sys.stderr, flush=True)
        win_rate = estimate_hole_card_win_rate(
            nb_simulation=1000,
            nb_player=self.player_num,
            hole_card=gen_cards(hole_card),
            community_card=gen_cards([]),
        )
        #print("Our win rate is:", win_rate, suited, file=sys.stderr, flush=True)
        if valid_actions[1]["amount"] == 0:
            return self.do_call(valid_actions)
        '''if valid_actions[1]["call"] > (self.small_blind_amount) * 2 and win_rate <= (
            1.0 / self.player_num
        ):
            self.do_fold()'''
        # Playable hands: suited connectors or potential straights
        
        if suited or self.has_straight_potential(ranks):
            return self.do_call(valid_actions)
        elif hole_card[0][1:] == hole_card[1][1:]:
            return self.do_call(valid_actions)
        else:
            # Get highest card rank in hand
            max_rank = max([self.card_rank(c) for c in hole_card])
            #print("Max rank:", max_rank, file=sys.stderr, flush=True)
            return self.do_call(valid_actions)

    def flop_action(self, valid_actions, hole_card, round_state):
        # --- new straight‐draw branch ---
        cards = gen_cards(hole_card) + gen_cards(self.community_cards)

        # --- existing equity‐based logic ---
        win_rate = estimate_hole_card_win_rate(
            nb_simulation=10000,
            nb_player=self.player_num,
            hole_card=gen_cards(hole_card),
            community_card=gen_cards(self.community_cards),
        )
        #print(f"win rate for turn is:{win_rate}", file=sys.stderr, flush=True)
        if 0.2 <= win_rate <= 0.4:
            return self.do_call(valid_actions)
        elif 0.4 < win_rate <= 0.7:
            return self.do_raise(valid_actions, round(self.starting_stack * 0.2), round_state)
        elif win_rate > 0.7:
            return self.do_raise(valid_actions, round(self.starting_stack * 0.5), round_state)
        else:
            return self.do_call(valid_actions)
        RANK_MAP = {
            "2": 2,
            "3": 3,
            "4": 4,
            "5": 5,
            "6": 6,
            "7": 7,
            "8": 8,
            "9": 9,
            "T": 10,
            "J": 11,
            "Q": 12,
            "K": 13,
            "A": 14,
        }


    def turn_action(self, valid_actions, hole_card, round_state):
        # --- new straight‐draw branch ---
        cards = gen_cards(hole_card) + gen_cards(self.community_cards)

        # --- existing equity‐based logic ---
        win_rate = estimate_hole_card_win_rate(
            nb_simulation=10000,
            nb_player=self.player_num,
            hole_card=gen_cards(hole_card),
            community_card=gen_cards(self.community_cards),
        )
        #print(f"win rate for turn is:{win_rate}", file=sys.stderr, flush=True)
        if 0.2 <= win_rate <= 0.4:
            return self.do_call(valid_actions)
        elif 0.4 < win_rate <= 0.7:
            return self.do_raise(valid_actions, round(self.starting_stack * 0.4), round_state)
        elif win_rate > 0.7:
            return self.do_raise(valid_actions, round(self.starting_stack * 0.7), round_state)
        else:
            return self.do_call(valid_actions)
        RANK_MAP = {
            "2": 2,
            "3": 3,
            "4": 4,
            "5": 5,
            "6": 6,
            "7": 7,
            "8": 8,
            "9": 9,
            "T": 10,
            "J": 11,
            "Q": 12,
            "K": 13,
            "A": 14,
        }

    def river_action(self, valid_actions, hole_card, round_state):

        # --- existing equity‐based logic ---
        win_rate = estimate_hole_card_win_rate(
            nb_simulation=50000,
            nb_player=self.player_num,
            hole_card=gen_cards(hole_card),
            community_card=gen_cards(self.community_cards),
        )
        #print(f"win rate for river is:{win_rate}", file=sys.stderr, flush=True)
        if 0.2 <= win_rate <= 0.5:
            return self.do_call(valid_actions)
        elif 0.5 < win_rate <= 0.7:
            return self.do_raise(valid_actions, round(self.starting_stack * 0.5), round_state)
        elif win_rate > 0.7:
            return self.do_raise(valid_actions, round(self.starting_stack * 0.8), round_state)
        else:
            return self.do_call(valid_actions)
        
            
    def has_straight_draw(self,cards):
        """
        cards: list of Card objects or strings like 'Ah','Td', etc.
        Returns True if there's a gutshot or open‐ended straight draw.
        """
        RANK_MAP = {
            "2": 2,
            "3": 3,
            "4": 4,
            "5": 5,
            "6": 6,
            "7": 7,
            "8": 8,
            "9": 9,
            "T": 10,
            "J": 11,
            "Q": 12,
            "K": 13,
            "A": 14,
        }
        # Extract unique rank values
        ranks = set()
        for c in cards:
            r = c[0] if isinstance(c, str) else c.rank_char
            ranks.add(RANK_MAP[r])
    
        # Build all 5‑card sequences (including wheel)
        sequences = [list(range(start, start + 5)) for start in range(2, 11)]
        sequences.append([14, 2, 3, 4, 5])  # Ace‑to‑five wheel

        # Check for exactly 4 out of 5 ranks present
        for seq in sequences:
            if sum(1 for v in seq if v in ranks) == 4:
                return True
        return False

    def receive_game_start_message(self, game_info):
        # Predefined variables for various game information --  feel free to use them however you like
        self.player_num = game_info["player_num"]
        max_round = game_info["rule"]["max_round"]
        self.small_blind_amount = game_info["rule"]["small_blind_amount"]
        ante_amount = game_info["rule"]["ante"]
        blind_structure = game_info["rule"]["blind_structure"]
        # self.my_uuid = self.uuid

    def receive_round_start_message(self, round_count, hole_card, seats):
        for seat in seats:
            if seat["uuid"] == self.uuid:
                # TODO: Add the small blind and big blind shit
                self.starting_stack = seat["stack"]
                break
        self.blind_adjusted = False

    def receive_street_start_message(self, street, round_state):
        pass

    def receive_game_update_message(self, action, round_state):
        pass

    def receive_round_result_message(self, winners, hand_info, round_state):
        #print(round_state["action_histories"], file=sys.stderr, flush=True)
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


    def has_straight_potential(self, ranks):
        # Calculate gap between card ranks
        diff = max(ranks) - min(ranks)
        # Valid if gap <=4 or wheel straight (A-2-3-4-5)
        return diff <= 4 or (ranks == [0, 12] and diff == 12)

    def card_rank(self, card):
        # Extract rank character (second character in card string)
        rank_str = card[1]
        # Mapping dictionary for rank values
        return {
            "2": 0,
            "3": 1,
            "4": 2,
            "5": 3,
            "6": 4,
            "7": 5,
            "8": 6,
            "9": 7,
            "T": 8,
            "J": 9,
            "Q": 10,
            "K": 11,
            "A": 12,
        }[rank_str]

