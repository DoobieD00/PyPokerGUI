from pypokerengine.players import BasePokerPlayer
from pypokerengine.utils.card_utils import estimate_hole_card_win_rate, gen_cards

# Notes
# All cards follow this format: Suit + Rank : 4 of Hearts = 4H, 10 of Spades = ST [2,3,4,5,6,7,8,9,T,J,Q,K,A] [S,C,D,H]


def setup_ai():
    return binger()


class binger(BasePokerPlayer):
    def __str__(self):
        return type(self).__name__

    def calculate_bet(self, win_rate, pot_size):
        call_threshold = 0.25

        if win_rate < call_threshold:
            return None  # fold

        edge = max(0.0, win_rate - call_threshold)
        edge **= 0.75
        return int(pot_size * edge / (1 - call_threshold))

    def declare_action(self, valid_actions, hole_card, round_state):

        ourname = str(self)

        # For your convenience:
        community_card = round_state["community_card"]  # array, starting from [] to [] of 5 elems
        street = round_state["street"]  # preflop, flop, turn, river
        pot = round_state["pot"]  # dict : {'main': {'amount': int}, 'side': {'amount': int}}
        dealer_btn = round_state["dealer_btn"]  # int : user id of the player acting as the dealer
        next_player = round_state["next_player"]  # int : user id of next player
        # int : user id of player with small blind (next player is big blind)
        small_blind_pos = round_state["small_blind_pos"]
        big_blind_pos = round_state["big_blind_pos"]  # int : user id of player with big blind
        round_count = round_state["round_count"]  # int : round number
        # int : amount of starting small blind
        small_blind_amount = round_state["small_blind_amount"]
        # {'name' : the AI name, 'uuid': their user id, 'stack': their stack/remaining money, 'state': participating/folded}
        # we recommend if you're going to try to find your own user id, name your own class name and ai name the same
        seats = round_state["seats"]
        # {'preflop': [{'action': 'SMALLBLIND', 'amount': 10, 'add_amount': 10, 'uuid': '1'}, {'action': 'BIGBLIND', 'amount': 20, 'add_amount': 10, 'uuid': '2'},
        #   {'action': 'CALL', 'amount': 20, 'paid': 20, 'uuid': '3'}, {'action': 'CALL', 'amount': 20, 'paid': 20, 'uuid': '0'},
        #   {'action': 'CALL', 'amount': 20, 'paid': 10, 'uuid': '1'}, {'action': 'FOLD', 'uuid': '2'}]}   -- sample action history for preflop
        # {'flop': [{'action': 'CALL', 'amount': 0, 'paid': 0, 'uuid': '1'}]}  -- sample for flop
        action_histories = round_state["action_histories"]

        # Minimum and maximum raise values (max raise ==> all in)
        min_raise = valid_actions[2]["amount"]["min"]
        max_raise = valid_actions[2]["amount"]["max"]

        num_players = len([seat for seat in seats if seat["state"] == "participating"])

        # --------------------------------------------------------------------------------------------------------#

        win_rate = estimate_hole_card_win_rate(
            nb_simulation=1000,
            nb_player=num_players,
            hole_card=gen_cards(hole_card),
            community_card=gen_cards(community_card),
        )

        print(
            f"[{self}] Win rate: {win_rate}, Hole card: {hole_card}, Community card: {community_card}"
        )

        pot_size = pot["main"]["amount"]

        # logic for last round of a game
        print(f"[{self}] {round_count = }, {self.max_round = }")
        if round_count == self.max_round - 1:
            print(f"[{self}] last round !!! ({round_count = }, {self.max_round = })")
            ours = None
            top = 0
            for player in seats:
                if player["name"] == ourname:
                    ours = player["stack"]
                top = max(top, player["stack"])

            # if cant find name hes all in
            if ours == None:
                print(f"[{self}] YOU ENTERED THE WRONG NAME")
                return self.do_all_in(valid_actions)

            print(f"[{self}] {ours = }, {top = }")

            # if our score is below average (100 idk) then go all in
            if ours <= 100:
                print(f"[{self}] All in")
                return self.do_all_in(valid_actions)
            elif ours < top:
                # something to make it riskier
                if street == "preflop":
                    print(f"[{self}] preflop, calling")
                    return self.do_call(valid_actions)

                bet = self.calculate_bet(win_rate, pot_size)
                if bet == None:
                    print(f"[{self}] shit winrate, folding")
                    return self.do_fold(valid_actions)

                if ours - bet < 100:
                    if win_rate >= 0.5:
                        print(f"[{self}] good winrate, all in")
                        return self.do_all_in(valid_actions)
                    else:
                        print(f"[{self}] bad winrate, folding")
                        return self.do_fold(valid_actions)

                else:
                    pass

            else:
                pass

        bet = self.calculate_bet(win_rate, pot_size)

        if bet is None:  # fold
            print(f"[{self}] Fold")
            return self.do_fold(valid_actions)

        print(
            f"[{self}] Pot: {pot_size}, Bet amount: {bet}, Min raise: {min_raise}, Max raise: {max_raise}"
        )

        if bet < min_raise:
            print(f"[{self}] Call {bet} < {min_raise}")
            return self.do_call(valid_actions)
        elif bet >= max_raise:
            print(f"[{self}] All in {bet} >= {max_raise}")
            return self.do_all_in(valid_actions)
        else:
            print(f"[{self}] Raise {bet}")
            return self.do_raise(valid_actions, bet)

        # -----------------------------------------------------------#

    def receive_game_start_message(self, game_info):
        player_num = game_info["player_num"]
        self.max_round = game_info["rule"]["max_round"]
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

    def do_fold(self, valid_actions):
        action_info = valid_actions[0]
        amount = action_info["amount"]
        return action_info["action"], amount

    def do_call(self, valid_actions):
        action_info = valid_actions[1]
        amount = action_info["amount"]
        return action_info["action"], amount

    def do_raise(self, valid_actions, raise_amount):
        action_info = valid_actions[2]
        amount = max(action_info["amount"]["min"], raise_amount)
        if amount <= 0:
            return self.do_call(valid_actions)  # no negative raise lol
        return action_info["action"], amount

    def do_all_in(self, valid_actions):
        action_info = valid_actions[2]
        amount = action_info["amount"]["max"]
        return action_info["action"], amount
