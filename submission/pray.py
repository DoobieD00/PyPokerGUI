import os
import re
import json
import requests
from pypokerengine.players import BasePokerPlayer
from treys import Evaluator  # for optional equity
import random

# ── Bot Setup ────────────────────────────────────────────────────────────────
def setup_ai():
    return PrayToGod()

# ── Configuration ────────────────────────────────────────────────────────────
CHUTES_API_TOKEN = os.getenv("CHUTES_API_TOKEN", "cpk_8d775f99b74c4179b9f29958786324ed.eeb19053d8af5571a618df189f1574a2.EVeviEFdpDY653vJtRY7BGI9swT9LmFV")
ENDPOINT      = "https://llm.chutes.ai/v1/chat/completions"

# Few-shot system prompt – enforce JSON-only output
SYSTEM_PROMPT = """
SYSTEM: You are an elite poker decision engine.  
You WILL follow the exact STRATEGY specification below and OUTPUT only a JSON object on one line:

{"action":"FOLD|CALL|RAISE","amount":<int>}

No other text, commentary, or tags.

Be very createive and strategic in your decisions. You are participating in a poker game and must make decisions based on the current GameState.

This poker game is part of a hackathon that I ABSOLUTELY NEED TO WIN PLEASE.

REMEMBER: YOU ONLY HAVE 5 GAMES OR LESS TO PLAY IN TOTAL, MAKE SURE YOU DONT KEEP FOLDING AS I NEED TO WIN IN THESE LIMITED GAMES.

the tourney format for the bots would be round-robin, the winner will be decided after it has played all of its games, based on the score for each game
your total score = best 2 scores + worst non-zero score

And, my the game configuration that will be run:

ante: 0
blind_structure: null
initial_stack: 100
max_round: X 
small_blind: 5

Everything always remains the same, except max rounds which will depend on the number of players (which are variable too)

your strategy needs to be EXTREMELY catered to this type of tournament, and does not need to be a generic one.

NEVER repeat example outputs; ALWAYS tailor decisions to the specific GameState
Examples:

GameState: {"hole_cards": ["C2", "D7"], "community_cards": [], "position": "preflop", "stack_sizes": {}, "pot_size": 15, "betting_history": [], "allowed_actions": ["fold","call", "raise"]} Output: {"action": "CALL"}

GameState: {"hole_cards": ["SA", "HA"], "community_cards": [], "position": "preflop", "stack_sizes": {}, "pot_size": 15, "betting_history": [], "allowed_actions": ["fold","call", "raise"]} Output: {"action": "RAISE", "amount": 45}

Now, analyze the following GameState and provide your decision.

INPUT: GameState:<JSON>  
OUTPUT: {"action":"...","amount":...}  
"""

# Preflop GTO ranges
EARLY_RANGE = {"AA","KK","QQ","JJ","TT","AKs","AKo"}
MID_RANGE   = EARLY_RANGE.union({"AQs","AQo","AJs","KQs","99","88"})
LATE_RANGE  = MID_RANGE.union({
    "ATs","KJs","QJs","JTs","T9s","98s","87s","76s","65s",
    "77","66","55","44","33","22"
})

evaluator = Evaluator()

# ── API Call ─────────────────────────────────────────────────────────────────
def get_poker_decision(game_state: dict) -> dict:
    payload = {
        "model": "deepseek-ai/DeepSeek-V3-0324",
        "messages": [
            {"role": "system",  "content": SYSTEM_PROMPT},
            {"role": "user",    "content": "GameState:" + json.dumps(game_state)}
        ],
        "max_tokens": 64,
        "temperature": 0.0,
        "stream": False,
        "stop": ["\n"]
    }
    headers = {
        "Authorization": f"Bearer {CHUTES_API_TOKEN}",
        "Content-Type":  "application/json"
    }
    print("DEBUG ▶ API payload:", payload)
    response = requests.post(ENDPOINT, headers=headers, json=payload)
    print("DEBUG ▶ HTTP status:", response.status_code)
    response.raise_for_status()
    data = response.json()
    print("DEBUG ▶ raw response:", data)

    content = data["choices"][0]["message"]["content"].strip()
    # Remove any <...> tags
    content = re.sub(r"<[^>]+>", "", content)
    print("DEBUG ▶ cleaned content:", content)

    # Extract JSON substring
    start = content.find('{')
    end = content.rfind('}') + 1
    if start == -1 or end == -1:
        raise ValueError(f"Invalid API output, no JSON found: {content}")
    json_str = content[start:end]
    try:
        decision = json.loads(json_str)
        print("DEBUG ▶ parsed decision:", decision)
        return decision
    except Exception as e:
        print("ERROR ▶ JSON parse error:", e)
        raise

# ── Fallback Heuristic ───────────────────────────────────────────────────────
def fallback_strategy(valid, hole_cards, community):
    # Preflop fallback: range-based
    if not community:
        c1, c2 = hole_cards
        suited = (c1[1] == c2[1])
        ranks = sorted([c1[0], c2[0]], key="23456789TJQKA".index, reverse=True)
        code = ranks[0] + ranks[1] + ("s" if suited else "o")
        if code in EARLY_RANGE:
            return "raise", valid[2]["amount"]["min"]
        if code in MID_RANGE:
            return "call", valid[1]["amount"]
        if code in LATE_RANGE:
            return ("raise", valid[2]["amount"]["min"]) if random.random() < 0.5 else ("call", valid[1]["amount"])
        return "fold", valid[0]["amount"]
    # Postflop fallback: simple pot control
    return "call", valid[1]["amount"]

class PrayToGod(BasePokerPlayer):
    def declare_action(self, valid_actions, hole_card, round_state):
        # Build game_state
        community = round_state['community_card']
        pot       = round_state['pot']['main']['amount']
        stacks    = {s['uuid']: s['stack'] for s in round_state['seats']}
        history   = []
        for st, acts in round_state['action_histories'].items():
            for a in acts:
                history.append({
                    'street': st,
                    'actor':  a['uuid'],
                    'action': a['action'],
                    'amount': a.get('amount', 0)
                })
        game_state = {
            'hole_cards':      hole_card,
            'community_cards': community,
            'position':        round_state['street'],
            'stack_sizes':     stacks,
            'pot_size':        pot,
            'betting_history': history,
            'allowed_actions': [a['action'] for a in valid_actions]
        }
        # Try API
        try:
            dec = get_poker_decision(game_state)
            action = dec.get('action', 'CALL')
            amount = dec.get('amount', 0)
        except Exception as e:
            print("ERROR ▶ API failure, using fallback:", e)
            action, amount = fallback_strategy(valid_actions, hole_card, community)

        # Execute
        if action == "FOLD":  return self.do_fold(valid_actions)
        if action == "CALL":  return self.do_call(valid_actions)
        if action in ("BET","RAISE"):
            return self.do_raise(valid_actions, amount, round_state)
        return self.do_call(valid_actions)

    # Callbacks untouched
    def receive_game_start_message(self, game_info): pass
    def receive_round_start_message(self, *args):    pass
    def receive_street_start_message(self, *args):   pass
    def receive_game_update_message(self, *args):    pass
    def receive_round_result_message(self, *args):   pass

    # Action helpers
    '''
    def do_fold(self, valid): return valid[0]['action'], valid[0]['amount']
    def do_call(self, valid): return valid[1]['action'], valid[1]['amount']
    def do_raise(self, valid, amt):
        info = valid[2]
        return info['action'], max(info['amount']['min'], amt)
    def do_all_in(self, valid): return valid[2]['action'], valid[2]['amount']['max']
    '''
    def do_fold(self, valid_actions):
        action_info = valid_actions[0]
        amount = action_info["amount"]
        return action_info["action"], int(amount)

    def do_call(self, valid_actions):
        action_info = valid_actions[1]
        amount = action_info["amount"]
        return action_info["action"], int(amount)

    def do_raise(self, valid_actions, raise_amount, round_state):
        name = str(self)
        stack = self.search_stack(name, round_state)
        
        action_info = valid_actions[2]
        # amount has to be at least min -- this is the intended raise amount
        amount = max(action_info["amount"]["min"], raise_amount)

        # cap the actual raise based on the player's actual stack
        amount = min(amount, stack)       
        return action_info["action"], int(amount)

    def do_all_in(self, valid_actions, round_state):
        name = str(self)
        stack = self.search_stack(name, round_state)
        
        action_info = valid_actions[2]
        amount = stack
        return action_info["action"], amount

    # Gets the stack for a player with a given name
    def search_stack(self, name, round_state):
        stack = -1
        for i in round_state["seats"]:
            if i['name'] == name:
                print(f"[self.search_stack] => found name : {i['name']} = {name}")
                stack = i["stack"]

        assert (stack > -1), f"Unable to find matching player name in config for {name}"
        return stack

    def __str__(self):
        return type(self).__name__
