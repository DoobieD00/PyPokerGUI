import datetime
import numpy as np
from keras import initializers
from keras.layers import Input, Dense, Conv2D,concatenate,Flatten
from keras.models import Model

from pypokerengine.players import BasePokerPlayer
from pypokerengine.api.emulator import Emulator
from pypokerengine.utils.game_state_utils import restore_game_state
from pypokerengine.utils.card_utils import gen_cards, estimate_hole_card_win_rate


def setup_ai():
    return Poker_AI()

class Poker_AI(BasePokerPlayer):
    my_uuid = ""
    suits = {'S': 0, 'H': 1, 'D': 2, 'C': 3}
    ranks = {'A': 12, 'K': 11, 'Q': 10, 'J': 9, 'T': 8, '9': 7, '8': 6, '7': 5, '6': 4, '5': 3, '4': 2, '3': 1, '2': 0}
    y = 0.9
    e = 1 - y
    max_replay_size = 15
    my_starting_stack = 10000
    opp_starting_stack = 10000
    starting_stack = 10000

    def __init__(self):

        super().__init__()

        self.vvh = 0
        self.action_sb = 3
        # self.table = {}
        # self.my_cards = []
        self.sb_features = None
        self.prev_round_features = []
        self.prev_reward_state = []
        self.has_played = False
        self.model = self.keras_model()
        self.target_Q = [[0, 0, 0]]

    def keras_model(self):
        input_cards = Input(shape=(4,13,4), name="cards_input")        # Shape: (4,13,4)
        input_actions = Input(shape=(2,6,4), name="actions_input")     # Shape: (2,6,4)
        input_position = Input(shape=(1,), name="position_input")      # Shape: (1,)

        # Conv on cards
        x1 = Conv2D(32, (2,2), activation='relu')(input_cards)
        x1 = Dense(128, activation='relu')(x1)
        x1 = Flatten()(x1)

        # Conv on actions
        x2 = Conv2D(32, (2,2), activation='relu')(input_actions)
        x2 = Dense(128, activation='relu')(x2)
        x2 = Flatten()(x2)

        # Dense on position
        x3 = Dense(1, activation='relu')(input_position)

        # Concatenate all features
        x = concatenate([x1, x2, x3])  # x has shape (5249,) when Flatten works correctly

        x = Dense(128)(x)
        x = Dense(128)(x)
        x = Dense(128)(x)
        x = Dense(128)(x)
        x = Dense(32)(x)
        out = Dense(3)(x)

        model = Model(inputs=[input_cards, input_actions, input_position], outputs=out)
        
        model.load_weights('strategy2.h5')  # No `by_name=True`, to ensure layer names align
        print("✅ Loaded pretrained weights successfully.")

        model.compile(optimizer='rmsprop', loss='mse')
        return model


        def keras_model_random_initialise():
            input_cards = Input(shape=(4,13,4), name="cards_input")
            input_actions = Input(shape=(2,6,4), name="actions_input")
            input_position = Input(shape=(1,),name="position_input")

            x1 = Conv2D(32,(2,2),activation='relu', kernel_initializer="random_uniform")(input_cards)
            x2 = Conv2D(32,(2,2),activation='relu', kernel_initializer="random_uniform")(input_actions)
            x3 = Dense(1,activation='relu', kernel_initializer="random_uniform")(input_position)

            d1 = Dense(128,activation='relu', kernel_initializer="random_uniform")(x1)
            d1 = Flatten()(d1)
            d2 = Dense(128,activation='relu', kernel_initializer="random_uniform")(x2)
            d2 = Flatten()(d2)
            x = concatenate([d1,d2,x3])
            x = Dense(128, kernel_initializer="random_uniform")(x)
            x = Dense(128, kernel_initializer="random_uniform")(x)
            x = Dense(128, kernel_initializer="random_uniform")(x)
            x = Dense(128, kernel_initializer="random_uniform")(x)
            x = Dense(32, kernel_initializer="random_uniform")(x)
            out = Dense(3)(x)

            model = Model(inputs=[input_cards, input_actions,input_position], outputs=out)
            model.compile(optimizer='rmsprop', loss='mse')

            return model


    def declare_action(self, valid_actions, hole_card, round_state):

        def get_card_x(card):
            suit = card[0]
            return Poker_AI.suits[suit]

        def get_card_y(card):
            small_or_big_blind_turn = card[1]
            return Poker_AI.ranks[small_or_big_blind_turn]

        def get_street_grid(cards):
            grid = np.zeros((4,13))
            for card in cards:
                grid[get_card_x(card), get_card_y(card)] = 1
            return grid

        def convert_to_image_grid(player_stack, round_state, street):
            image = np.zeros((2,6))
            actions = round_state["action_histories"][street]
            small_or_big_blind_turn = 0
            idx_of_action = 0
            for action in actions:
                #max of 12actions per street
                if 'amount' in action and idx_of_action < 6:
                    image[small_or_big_blind_turn, idx_of_action] = action['amount'] / player_stack
                    small_or_big_blind_turn += 1

                if small_or_big_blind_turn % 2 == 0:
                    small_or_big_blind_turn = 0
                    idx_of_action += 1

            return image

        def record_state():
            # Choose action with highest Q value
            self.cur_Q_values = self.model.predict(self.sb_features)
            self.action_sb = np.argmax(self.cur_Q_values)

            if self.has_played:
                reward_sb = Poker_AI.y * np.max(self.cur_Q_values)
                self.target_Q[0, self.action_sb] = reward_sb
                self.vvh = self.vvh + 1
                # new_name = 'my_model_weights'
                # model.fit(self.old_state,self.target_Q,verbose=0)
                self.prev_round_features.append(self.old_state)
                self.prev_reward_state.append(self.target_Q)
                if len(self.prev_round_features) > Poker_AI.max_replay_size:
                    del self.prev_round_features[0]
                    del self.prev_reward_state[0]

            # if self.vvh > 2000:
            # save_weights()

        # Maybe don't modularise this, the program takes up more ram when this is modularised
        def pick_action():
            if np.random.rand(1) < Poker_AI.e:
                self.action_sb = np.random.randint(0, 4)

            if self.action_sb == 3 or len(valid_actions) == 2:
                self.action_sb = 1

            chosen_action = valid_actions[self.action_sb]["action"]

            if chosen_action == "fold":
                return "fold", 0
            elif chosen_action == "call":
                amount = [a for a in valid_actions if a["action"] == "call"][0]["amount"]
                return "call", amount
            elif chosen_action == "raise":
                raise_action = [a for a in valid_actions if a["action"] == "raise"][0]
                min_raise = raise_action["amount"]["min"]
                max_raise = raise_action["amount"]["max"]

                # Estimate win rate
                community_card = round_state.get("community_card", [])
                win_rate = estimate_hole_card_win_rate(
                    nb_simulation=100,
                    hole_card=gen_cards(hole_card),
                    community_card=gen_cards(community_card),
                    nb_player=len(round_state["seats"])
                )

                # Scale raise amount based on win rate
                scaled_raise = int(min_raise + (max_raise - min_raise) * win_rate)
                return "raise", scaled_raise
            else:
                # fallback to fold
                return "fold", 0


        def save_weights():
            # new_name = "setup/" + datetime.datetime.now().strftime("%d-%m_%H:%M:%S_") + str(self.vvh) + '.h5'
            new_name = "setup/training_weights2" + '.h5'
            self.model.save_weights(new_name)

        #####################################################################
        # SETUPBLOCK - Setup features to train model

        preflop_cards = [hole_card[0], hole_card[1]]

        preflop_cards_img = get_street_grid(preflop_cards)
        flop_cards_img = np.zeros((4,13))
        turn_cards_img = np.zeros((4,13))
        river_cards_img = np.zeros((4,13))

        flop_actions = np.zeros((2,6))
        turn_actions = np.zeros((2,6))
        river_actions = np.ones((2,6))

        if(round_state['next_player'] == round_state['small_blind_pos']):
            sb_position = 1
        else:
            sb_position = 0

        # starting_stack = round_state['seats'][round_state['next_player']]['stack']
        # print("starting stack is")
        # print(starting_stack)

        if self.has_played:
            self.old_state = self.sb_features
            self.target_Q = self.cur_Q_values
            #self.old_action = self.action_sb

        preflop_actions = convert_to_image_grid(Poker_AI.starting_stack, round_state, 'preflop')

        if round_state['street'] == 'flop':
            flop = round_state['community_card']
            flop_cards_img = get_street_grid(flop)
            flop_actions = convert_to_image_grid(Poker_AI.starting_stack, round_state, 'flop')

        if round_state['street'] == 'turn':
            turn = round_state['community_card'][3]
            turn_cards_img = get_street_grid([turn])
            turn_actions = convert_to_image_grid(Poker_AI.starting_stack, round_state, 'turn')

        if round_state['street'] == 'river':
            river = round_state['community_card'][4]
            river_cards_img = get_street_grid([river])
            river_actions = convert_to_image_grid(Poker_AI.starting_stack, round_state, 'river')

        # Form action features
        actions_feature = np.stack([preflop_actions,flop_actions,turn_actions,river_actions],axis=2).reshape((1,2,6,4))

        # Form card features
        sb_cards_feature = np.stack([preflop_cards_img, flop_cards_img, turn_cards_img, river_cards_img],
                                    axis=2).reshape((1,4,13,4))
        # print("action_feature ---- {}".format(actions_feature.shape))
        # print("sb_cards_feature ---- {}".format(sb_cards_feature.shape)")

        # All features together
        self.sb_features = [sb_cards_feature,actions_feature,np.array([sb_position]).reshape((1,1))]
        # print("All features together ---- {}".format(self.sb_features.shape)")

        # ENDBLOCK
        #############################################################

        record_state()

        self.has_played = True

        # for ve in range(len(self.prev_round_features)):
        #     self.model.fit(self.prev_round_features[ve], self.prev_reward_state[ve], verbose=0)

        return pick_action()

    def receive_game_start_message(self, game_info):
        if hasattr(self, 'uuid'):
            Poker_AI.my_uuid = self.uuid
        else:
            print("[Error] uuid not set before receive_game_start_message.")


    def receive_round_start_message(self, round_count, hole_card, seats):
        for seat in seats:
            if Poker_AI.my_uuid == seat["uuid"]:
                Poker_AI.my_starting_stack = seat["stack"]
            else:
                Poker_AI.opp_starting_stack = seat["stack"]

    def receive_street_start_message(self, street, round_state):
        pass

    def receive_game_update_message(self, action, round_state):
        pass

    def receive_round_result_message(self, winners, hand_info, round_state):
        def get_real_reward():
            if winners[0]['uuid'] == Poker_AI.my_uuid:
                return winners[0]['stack'] - Poker_AI.my_starting_stack
            else:
                return -(winners[0]['stack'] - Poker_AI.opp_starting_stack)

        reward = int(get_real_reward())
        self.target_Q = self.model.predict(self.sb_features)
        if self.action_sb == 0:
            # If the best move is not FOLD, we punish AI severely
            if np.argmax(self.target_Q) != 0:
                self.target_Q[0, self.action_sb] = reward * Poker_AI.y
            # Else we reward it slightly
            else:
                self.target_Q[0, self.action_sb] = 0
        else:
            self.target_Q[0, self.action_sb] = reward

        self.prev_round_features.append(self.sb_features)
        self.prev_reward_state.append(self.target_Q)

        if len(self.prev_round_features) > Poker_AI.max_replay_size:
            del self.prev_round_features[0]
            del self.prev_reward_state[0]

        # for ev in range(len(self.prev_round_features)):
        #     self.model.fit(self.prev_round_features[ev], self.prev_reward_state[ev], verbose=0)

    def set_uuid(self, uuid):
        self.uuid = uuid








