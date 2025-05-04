import random
from pypokerengine.engine.hand_evaluator import HandEvaluator
from pypokerengine.players import BasePokerPlayer
from pypokerengine.utils.card_utils import _pick_unused_card, _fill_community_card, gen_cards

def simulate_win_rate(simulations: int, total_players: int, my_hole_cards: list, community_cards: list = None) -> float:
    """
    Estimate the winning probability via Monte Carlo simulations.
    """
    community = gen_cards(community_cards or [])
    hole = gen_cards(my_hole_cards)

    wins = 0
    for _ in range(simulations):
        if _run_simulation(total_players, hole, community):
            wins += 1
    return wins / simulations


def _run_simulation(total_players: int, hole_cards: list, community_cards: list) -> bool:
    # complete community to 5 cards
    full_community = _fill_community_card(community_cards, used_card=hole_cards + community_cards)
    # deal opponents
    needed = (total_players - 1) * 2
    deck = _pick_unused_card(needed, hole_cards + full_community)
    opponents = [deck[i * 2:(i * 2) + 2] for i in range(total_players - 1)]

    my_score = HandEvaluator.eval_hand(hole_cards, full_community)
    opp_scores = [HandEvaluator.eval_hand(h, full_community) for h in opponents]
    return my_score >= max(opp_scores)


def count_active_players(seat_info: list) -> int:
    """
    Count how many players are still in the hand.
    """
    return sum(1 for p in seat_info if p.get('state') == 'participating')


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


class BillionDollarBot(BasePokerPlayer):
    def __init__(self):
        super().__init__()
        self.wins = 0
        self.losses = 0
        self.thresholds = {
            'call': {'preflop': 0.13, 'flop': 0.3, 'turn': 0.4, 'river': 0.7},
            'raise1': {'preflop': 0.17, 'flop': 0.45, 'turn': 0.47, 'river': 0.8},
            'raise2': {'preflop': 0.20, 'flop': 0.55, 'turn': 0.47, 'river': 0.9}
        }

    def _choose_action(self, valid_actions, action_type, amount=None):
        for act in valid_actions:
            if act['action'] == action_type:
                if amount is None:
                    return action_type, act.get('amount', 0)
                min_amt = act['amount']['min']
                max_amt = act['amount']['max']
                if amount < min_amt:
                    return action_type, min_amt
                if amount > max_amt:
                    return action_type, max_amt
                return action_type, amount
        return None

    def _fold_or_check(self, valid_actions):
        # prefer check if available
        for act in valid_actions:
            if act['action'] == 'call' and act['amount'] == 0:
                return 'call', 0
        return 'fold', 0

    def declare_action(self, valid_actions, hole_card, round_state):
        win_prob = simulate_win_rate(
            simulations=100,
            total_players=self._remaining,
            my_hole_cards=hole_card,
            community_cards=round_state['community_card']
        )
        stage = round_state['street']

        if win_prob > self.thresholds['raise2'][stage]:
            choice = self._choose_action(valid_actions, 'raise',
                                         self.thresholds['raise2'][stage] * valid_actions[-1]['amount']['min'])
        elif win_prob > self.thresholds['raise1'][stage]:
            choice = self._choose_action(valid_actions, 'raise',
                                         self.thresholds['raise1'][stage] * valid_actions[-1]['amount']['min'])
        elif win_prob > self.thresholds['call'][stage]:
            choice = self._choose_action(valid_actions, 'call')
        else:
            return self._fold_or_check(valid_actions)

        return choice or self._fold_or_check(valid_actions)

    def receive_game_start_message(self, game_info):
        self._players_count = game_info['player_num']

    def receive_round_start_message(self, round_count, hole_card, seats):
        self._remaining = count_active_players(seats)

    def receive_round_result_message(self, winners, hand_info, round_state):
        won = any(w['uuid'] == self.uuid for w in winners)
        self.wins += int(won)
        self.losses += int(not won)

    def receive_street_start_message(self, street, round_state):
        pass

    def receive_game_update_message(self, action, round_state):
        pass


def setup_ai():
    return BillionDollarBot()