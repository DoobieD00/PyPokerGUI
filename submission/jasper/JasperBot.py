import random
import json
import requests
from pypokerengine.players import BasePokerPlayer
from mapping import PokerLogMapper
from history import HistoryManager
import os

# Notes
# All cards follow this format: Rank + Suit : 4 of Hearts = 4h, 10 of Spades = Ts [2,3,4,5,6,7,8,9,T,J,Q,K,A] [s,c,d,h]

def setup_ai():
    return JasperBot()

class JasperBot(BasePokerPlayer):  # Do not forget to make parent class as "BasePokerPlayer"

    def __init__(self):
        super().__init__() # Initialize the base class
        # Create an instance of the mapper, giving it our bot's name
        self.mapper = PokerLogMapper(bot_name="JasperBot")
        
        # Initialize the history manager
        self.history_manager = HistoryManager(bot_name="JasperBot", debug_mode=False)
        
        # Get AI Agent endpoint from environment variables with fallbacks
        self.api_host = os.environ.get("AI_AGENT_HOST", "localhost")
        self.api_port = int(os.environ.get("AI_AGENT_PORT", 8080))
        self.api_path = os.environ.get("AI_AGENT_PATH", "/process")
        self.api_protocol = os.environ.get("AI_AGENT_PROTOCOL", "http")

        # AI Agent endpoint for poker decisions
        self.api_endpoint = f"{self.api_protocol}://{self.api_host}:{self.api_port}{self.api_path}"

        print(f"AI Agent endpoint configured as: {self.api_endpoint}")
        
    #  we define the logic to make an action through this method. (so this method would be the core of your AI)
    def display_poker_state(self, hole_card, community_card, pot_amount, round_state, valid_actions):
        """Function to display the entire poker game state with XML tags"""
        min_raise = valid_actions[2]['amount']['min'] if len(valid_actions) > 2 else -1
        max_raise = valid_actions[2]['amount']['max'] if len(valid_actions) > 2 else -1
        
        # Get my position and stack information
        seats = round_state['seats']
        dealer_btn = round_state['dealer_btn']
        small_blind_pos = round_state['small_blind_pos']
        big_blind_pos = round_state['big_blind_pos']
        
        # Find my position and stack
        my_seat = None
        my_position = "Unknown"
        my_stack = 0
        
        for i, seat in enumerate(seats):
            if seat['uuid'] == self.mapper.bot_uuid:
                my_seat = i
                my_stack = seat['stack']
                break
        
        # Determine position
        if my_seat is not None:
            if my_seat == dealer_btn:
                my_position = "Button"
            elif my_seat == small_blind_pos:
                my_position = "Small Blind"
            elif my_seat == big_blind_pos:
                my_position = "Big Blind"
            elif len(seats) == 2:  # Heads-up
                my_position = "Button" if my_seat == dealer_btn else "Big Blind"
            else:
                # Calculate relative position
                positions = ["Early", "Middle", "Late"]
                position_index = (my_seat - dealer_btn) % len(seats)
                if position_index == 0:
                    my_position = "Button"
                elif position_index == 1:
                    my_position = "Small Blind" 
                elif position_index == 2:
                    my_position = "Big Blind"
                else:
                    third = len(seats) // 3
                    if position_index <= 2 + third:
                        my_position = "Early"
                    elif position_index <= 2 + (2 * third):
                        my_position = "Middle"
                    else:
                        my_position = "Late"
        
        # Display current game state with XML tags
        print("\n<HOLE_CARDS>", hole_card, "</HOLE_CARDS>")
        print("<COMMUNITY_CARDS>", community_card, "</COMMUNITY_CARDS>")
        print("<POT>", pot_amount, "</POT>")
        print("<POSITION>", my_position, "</POSITION>")
        print("<STACK>", my_stack, "</STACK>")
        print("<HAND>", hole_card, "</HAND>")
        
        # Get opponent stats
        opponents_stats = self.history_manager.get_opponent_stats()
        
        # Display opponent stats with XML tags
        display_opponents = False
        opponent_stats_content = []
        
        if opponents_stats:
            for opponent in opponents_stats:
                if opponent['hands'] < 5:  # Skip opponents with few observed hands
                    continue
                    
                display_opponents = True
                opponent_stats_content.append(f"  <OPPONENT uuid=\"{opponent['uuid']}\">")
                opponent_stats_content.append(f"    <n>{opponent['player_name']}</n>")
                opponent_stats_content.append(f"    <POSITION>{opponent['position']}</POSITION>")
                opponent_stats_content.append(f"    <HANDS_OBSERVED>{opponent['hands']}</HANDS_OBSERVED>")
                opponent_stats_content.append(f"    <STYLE>{opponent.get('playing_style', 'Unknown')}</STYLE>")
                
                # Basic stats
                opponent_stats_content.append(f"    <BASIC_STATS>")
                opponent_stats_content.append(f"      <VPIP>{opponent['vpip']}%</VPIP>")
                opponent_stats_content.append(f"      <PFR>{opponent['pfr']}%</PFR>")
                opponent_stats_content.append(f"      <FOLD_TO_5BB>{opponent['fold_to_5bb']}%</FOLD_TO_5BB>")
                opponent_stats_content.append(f"      <CALL_5BB>{opponent['call_5bb']}%</CALL_5BB>")
                opponent_stats_content.append(f"      <THREE_BET>{opponent['threeBet']}%</THREE_BET>")
                if 'aggression_factor' in opponent:
                    opponent_stats_content.append(f"      <AGGRESSION>{opponent['aggression_factor']}</AGGRESSION>")
                if 'continuation_bet' in opponent:
                    opponent_stats_content.append(f"      <CBET>{opponent['continuation_bet']}%</CBET>")
                opponent_stats_content.append(f"    </BASIC_STATS>")
                
                # Advanced stats - if available
                opponent_stats_content.append(f"    <ADVANCED_STATS>")
                # Preflop tendencies
                if 'open_raise' in opponent:
                    opponent_stats_content.append(f"      <OPEN_RAISE>{opponent['open_raise']}%</OPEN_RAISE>")
                if 'squeeze_play' in opponent:
                    opponent_stats_content.append(f"      <SQUEEZE_PLAYS>{opponent['squeeze_play']}</SQUEEZE_PLAYS>")
                if 'cold_call' in opponent:
                    opponent_stats_content.append(f"      <COLD_CALLS>{opponent['cold_call']}</COLD_CALLS>")
                    
                # Postflop tendencies
                if 'check_raise' in opponent:
                    opponent_stats_content.append(f"      <CHECK_RAISES>{opponent['check_raise']}</CHECK_RAISES>")
                if 'donk_bet' in opponent:
                    opponent_stats_content.append(f"      <DONK_BETS>{opponent['donk_bet']}</DONK_BETS>")
                
                # Include JSON format history stats if available
                if 'history' in opponent:
                    history = opponent.get('history', {})
                    opponent_stats_content.append(f"      <HISTORY>")
                    
                    # Key stats from JSON format
                    if 'fold_to_5bb_shove' in history:
                        opponent_stats_content.append(f"        <FOLD_TO_5BB_SHOVE>{history['fold_to_5bb_shove']:.2f}</FOLD_TO_5BB_SHOVE>")
                    if 'call_range_width' in history:
                        opponent_stats_content.append(f"        <CALL_RANGE_WIDTH>{history['call_range_width']:.2f}</CALL_RANGE_WIDTH>")
                    if 'short_stack_adjustment' in history:
                        opponent_stats_content.append(f"        <SHORT_STACK_ADJUSTMENT>{history['short_stack_adjustment']:.2f}</SHORT_STACK_ADJUSTMENT>")
                    if 'observations' in history:
                        opponent_stats_content.append(f"        <OBSERVATIONS>{history['observations']}</OBSERVATIONS>")
                    
                    # Last hands in pretty format
                    if 'last_10_hands' in history and history['last_10_hands']:
                        opponent_stats_content.append(f"        <LAST_HANDS>")
                        for i, hand in enumerate(reversed(history['last_10_hands'][:5])):  # Show most recent 5 hands
                            hand_str = f"          <HAND_{i+1}>"
                            hand_str += f"{hand.get('action', 'unknown').upper()}"
                            if hand.get('amount'):
                                hand_str += f" ({hand['amount']})"
                            if hand.get('position'):
                                hand_str += f" from {hand['position']}"
                            if hand.get('street'):
                                hand_str += f" on {hand['street']}"
                            if hand.get('hand_shown'):
                                hand_str += f" with {', '.join(hand['hand_shown'])}"
                            hand_str += f"</HAND_{i+1}>"
                            opponent_stats_content.append(hand_str)
                        opponent_stats_content.append(f"        </LAST_HANDS>")
                    
                    opponent_stats_content.append(f"      </HISTORY>")
                
                # Include detailed advanced stats if they exist
                if 'advanced_stats' in opponent:
                    adv_stats = opponent.get('advanced_stats', {})
                    
                    # Bet sizing patterns
                    if 'avg_bet_sizing' in adv_stats:
                        bet_sizing = adv_stats['avg_bet_sizing']
                        opponent_stats_content.append(f"      <BET_SIZING>")
                        for street, size in bet_sizing.items():
                            opponent_stats_content.append(f"        <{street.upper()}>{size}% of pot</{street.upper()}>")
                        opponent_stats_content.append(f"      </BET_SIZING>")
                    
                    # Position-based tendencies
                    if 'position_stats' in adv_stats:
                        pos_stats = adv_stats['position_stats']
                        opponent_stats_content.append(f"      <POSITION_TENDENCIES>")
                        for position, stats in pos_stats.items():
                            if stats.get('total_actions', 0) > 3:  # Only include positions with enough data
                                opponent_stats_content.append(f"        <{position}>")
                                opponent_stats_content.append(f"          <FOLD>{stats.get('fold_pct', 0):.1f}%</FOLD>")
                                opponent_stats_content.append(f"          <CALL>{stats.get('call_pct', 0):.1f}%</CALL>")
                                opponent_stats_content.append(f"          <RAISE>{stats.get('raise_pct', 0):.1f}%</RAISE>")
                                opponent_stats_content.append(f"        </{position}>")
                        opponent_stats_content.append(f"      </POSITION_TENDENCIES>")
                    
                    # Street-by-street tendencies
                    if 'street_stats' in adv_stats:
                        street_stats = adv_stats['street_stats']
                        opponent_stats_content.append(f"      <STREET_TENDENCIES>")
                        for street, stats in street_stats.items():
                            if stats.get('total_actions', 0) > 3:  # Only include streets with enough data
                                opponent_stats_content.append(f"        <{street.upper()}>")
                                opponent_stats_content.append(f"          <FOLD>{stats.get('fold_pct', 0):.1f}%</FOLD>")
                                opponent_stats_content.append(f"          <CALL>{stats.get('call_pct', 0):.1f}%</CALL>")
                                opponent_stats_content.append(f"          <RAISE>{stats.get('raise_pct', 0):.1f}%</RAISE>")
                                opponent_stats_content.append(f"          <BET>{stats.get('bet_pct', 0):.1f}%</BET>")
                                opponent_stats_content.append(f"          <CHECK>{stats.get('check_pct', 0):.1f}%</CHECK>")
                                opponent_stats_content.append(f"        </{street.upper()}>")
                        opponent_stats_content.append(f"      </STREET_TENDENCIES>")
                
                opponent_stats_content.append(f"    </ADVANCED_STATS>")
                
                # Notes and observations
                if opponent['notes']:
                    opponent_stats_content.append(f"    <NOTES>{'; '.join(opponent['notes'])}</NOTES>")
                opponent_stats_content.append(f"  </OPPONENT>")
        
        # Only print opponent stats section if we have valid opponents to display
        if display_opponents:
            print("\n<OPPONENT_STATS>")
            for line in opponent_stats_content:
                print(line)
            print("</OPPONENT_STATS>")
        
        # Display hand history without predictions
        self.history_manager.get_hand_history(hole_card, community_card, round_state)
        
        # Export opponents data as JSON for logging
        self.export_opponents_json()
        
        # Show available actions with XML-like tags
        print("\n<AVAILABLE_ACTIONS>")
        actions_info = []
        if valid_actions[0]['action'] == 'fold':
            print(f"1: Fold")
            actions_info.append(('fold', 0))
            
        if valid_actions[1]['action'] == 'call':
            call_amount = valid_actions[1]['amount']
            print(f"2: Call (amount: {call_amount})")
            actions_info.append(('call', call_amount))
            
        if len(valid_actions) > 2 and valid_actions[2]['action'] == 'raise' and valid_actions[2]['amount']['min'] != -1:
            print(f"3: Raise (min: {min_raise}, max: {max_raise})")
            actions_info.append(('raise', (min_raise, max_raise)))
        print("</AVAILABLE_ACTIONS>")
        
        print("\nMAKE YOUR OWN PREDICTION based on the history above.")
        
        return actions_info
    
    def declare_action(self, valid_actions, hole_card, round_state):
        community_card = round_state['community_card']
        street = round_state['street']
        pot = round_state['pot']
        dealer_btn = round_state['dealer_btn']
        next_player = round_state['next_player']
        small_blind_pos = round_state['small_blind_pos']
        big_blind_pos = round_state['big_blind_pos']
        round_count = round_state['round_count']
        small_blind_amount = round_state['small_blind_amount']
        seats = round_state['seats']
        action_histories = round_state['action_histories']

        # --------------------------------------------------------------------------------------------------------#
        # Auto-play for check/disqualified cases
        
        # Check if this is a "check" situation (call amount is 0)
        if valid_actions[1]['action'] == 'call' and valid_actions[1]['amount'] == 0:
            print("\nAUTO-PLAY: Call amount is 0, automatically checking")
            # Log the action
            self.history_manager.log_action("call", street, hole_card, community_card, 0)
            return self.do_call(valid_actions)
            
        # --------------------------------------------------------------------------------------------------------#
        # AI Agent-based decision making
        
        # Use the dedicated function to display poker state
        actions_info = self.display_poker_state(hole_card, community_card, pot['main']['amount'], round_state, valid_actions)
        
        # Format opponents information for JSON output
        opponents_stats = self.history_manager.get_opponent_stats()
        opponents_json_str = ""
        if opponents_stats:
            import json
            opponents_data = {
                "opponents": [
                    {
                        "id": opponent['uuid'],
                        "position": opponent['position'],
                        "stack": opponent.get('stack', 0),
                        "history": opponent.get('history', {})
                    } for opponent in opponents_stats
                ]
            }
            opponents_json_str = f"<OPPONENTS_JSON>\n{json.dumps(opponents_data, indent=2)}\n</OPPONENTS_JSON>"
        
        # Get hand history - capture stdout to a string
        import io
        import sys
        original_stdout = sys.stdout
        hand_history_capture = io.StringIO()
        sys.stdout = hand_history_capture
        self.history_manager.get_hand_history(hole_card, community_card, round_state)
        sys.stdout = original_stdout
        hand_history = hand_history_capture.getvalue()
        
        # Format the available actions as they appear in the provided example
        available_actions_str = "<AVAILABLE_ACTIONS>\n"
        if valid_actions[0]['action'] == 'fold':
            available_actions_str += f"1: Fold\n"
            
        if valid_actions[1]['action'] == 'call':
            call_amount = valid_actions[1]['amount']
            available_actions_str += f"2: Call (amount: {call_amount})\n"
            
        if len(valid_actions) > 2 and valid_actions[2]['action'] == 'raise' and valid_actions[2]['amount']['min'] != -1:
            min_raise = valid_actions[2]['amount']['min']
            max_raise = valid_actions[2]['amount']['max']
            available_actions_str += f"3: Raise (min: {min_raise}, max: {max_raise})\n"
        available_actions_str += "</AVAILABLE_ACTIONS>"
        
        # Build the complete context in the exact format provided in the example
        game_state = f"""
<HOLE_CARDS> {hole_card} </HOLE_CARDS>
<COMMUNITY_CARDS> {community_card} </COMMUNITY_CARDS>
<POT> {pot['main']['amount']} </POT>
<POSITION> {self.get_position(round_state)} </POSITION>
<STACK> {self.get_my_stack(round_state)} </STACK>
<HAND> {hole_card} </HAND>

{hand_history}

{opponents_json_str}

{available_actions_str}

MAKE YOUR OWN PREDICTION based on the history above.
"""
        
        try:
            print("\nWaiting for response from AI Agent...")
            response = requests.post(
                self.api_endpoint,
                json={"game_state": game_state},
                headers={"Content-Type": "application/json"},
                timeout=600  # 600 seconds (10 minutes) timeout
            )
            
            if response.status_code == 200:
                try:
                    # Parse AI Agent response
                    api_decision = response.json()
                    print(f"AI Agent response: {api_decision}")
                    
                    # Expected format:
                    # {"action": "fold" | "call" | "raise", "amount": integer_value (only for raise)}
                    
                    action_type = api_decision.get("action", "").lower()
                    amount = api_decision.get("amount", 0)
                    
                    # Validate and execute the action
                    if action_type == "fold":
                        print("Executing FOLD action from AI Agent")
                        self.history_manager.log_action("fold", street, hole_card, community_card)
                        return self.do_fold(valid_actions)
                        
                    elif action_type == "call":
                        print(f"Executing CALL action from AI Agent (amount: {valid_actions[1]['amount']})")
                        self.history_manager.log_action("call", street, hole_card, community_card, valid_actions[1]['amount'])
                        return self.do_call(valid_actions)
                        
                    elif action_type == "raise" and len(valid_actions) > 2:
                        # Ensure the raise amount is valid
                        min_raise = valid_actions[2]['amount']['min']
                        max_raise = valid_actions[2]['amount']['max']
                        
                        # Validate raise amount
                        try:
                            raise_amount = int(amount)
                            # Clamp the value to valid range
                            raise_amount = max(min_raise, min(raise_amount, max_raise))
                            print(f"Executing RAISE action from AI Agent (amount: {raise_amount})")
                            self.history_manager.log_action("raise", street, hole_card, community_card, raise_amount)
                            return self.do_raise(valid_actions, raise_amount)
                        except (ValueError, TypeError):
                            print(f"Invalid raise amount: {amount}, defaulting to minimum raise")
                            self.history_manager.log_action("raise", street, hole_card, community_card, min_raise)
                            return self.do_raise(valid_actions, min_raise)
                    
                    else:
                        # Default to call if AI Agent returns invalid action
                        print(f"Invalid action from AI Agent: '{action_type}', defaulting to call")
                        self.history_manager.log_action("call", street, hole_card, community_card, valid_actions[1]['amount'])
                        return self.do_call(valid_actions)
                        
                except Exception as e:
                    print(f"Error parsing AI Agent response: {e}, defaulting to call")
                    self.history_manager.log_action("call", street, hole_card, community_card, valid_actions[1]['amount'])
                    return self.do_call(valid_actions)
            
            else:
                print(f"AI Agent error: {response.status_code} - {response.text}")
                # Default to call on AI Agent error
                self.history_manager.log_action("call", street, hole_card, community_card, valid_actions[1]['amount'])
                return self.do_call(valid_actions)
                
        except Exception as e:
            print(f"Error communicating with AI Agent: {e}")
            # Default to call on exception
            self.history_manager.log_action("call", street, hole_card, community_card, valid_actions[1]['amount'])
            return self.do_call(valid_actions)
        # -------------------------------------------------------------------------------------------------------#
    
    def get_position(self, round_state):
        """Get the player's position at the table"""
        seats = round_state['seats']
        dealer_btn = round_state['dealer_btn']
        small_blind_pos = round_state['small_blind_pos']
        big_blind_pos = round_state['big_blind_pos']
        
        my_seat = None
        my_position = "Unknown"
        
        for i, seat in enumerate(seats):
            if seat['uuid'] == self.mapper.bot_uuid:
                my_seat = i
                break
        
        if my_seat is not None:
            if my_seat == dealer_btn:
                my_position = "Button"
            elif my_seat == small_blind_pos:
                my_position = "Small Blind"
            elif my_seat == big_blind_pos:
                my_position = "Big Blind"
            elif len(seats) == 2:  # Heads-up
                my_position = "Button" if my_seat == dealer_btn else "Big Blind"
            else:
                # Calculate relative position
                positions = ["Early", "Middle", "Late"]
                position_index = (my_seat - dealer_btn) % len(seats)
                if position_index == 0:
                    my_position = "Button"
                elif position_index == 1:
                    my_position = "Small Blind" 
                elif position_index == 2:
                    my_position = "Big Blind"
                else:
                    third = len(seats) // 3
                    if position_index <= 2 + third:
                        my_position = "Early"
                    elif position_index <= 2 + (2 * third):
                        my_position = "Middle"
                    else:
                        my_position = "Late"
        
        return my_position
    
    def get_my_stack(self, round_state):
        """Get the player's current stack"""
        seats = round_state['seats']
        for seat in seats:
            if seat['uuid'] == self.mapper.bot_uuid:
                return seat['stack']
        return 0

    def receive_game_start_message(self, game_info):
        # Translate the game_info using the mapper and print
        translation = self.mapper.translate_game_start(game_info)
        print(translation)
        print("-" * 40) # Separator
        
        # Handle game start in history manager
        self.history_manager.handle_game_start(game_info)

    def receive_round_start_message(self, round_count, hole_card, seats):
        # Translate the round start info using the mapper and print
        translation = self.mapper.translate_round_start(round_count, hole_card, seats)
        print(translation)
        print("-" * 40) # Separator
        
        # Handle round start in history manager
        self.history_manager.handle_round_start(round_count, hole_card, seats)

    def receive_street_start_message(self, street, round_state):
        # Translate the street start info using the mapper and print
        translation = self.mapper.translate_street_start(street, round_state)
        print(translation)
        # No separator here, actions will follow immediately
        
        # Get community cards directly from round_state
        community_cards = round_state.get("community_card", [])
        pot = round_state.get("pot", {}).get("main", {}).get("amount", 0)
        
        # Handle street start in history manager
        self.history_manager.handle_street_start(street, community_cards, pot)

    def receive_game_update_message(self, action, round_state):
        # Translate the action using the mapper (which uses round_state for context) and print
        translation = self.mapper.translate_game_update(action, round_state)
        print(translation)
        # No separator here, allows actions to flow naturally
        
        # Handle game update in history manager (only for opponent actions)
        if action.get("player_uuid") != self.mapper.bot_uuid:
            street = round_state.get("street")
            player_name = self.mapper._get_player_name(action.get("player_uuid"))
            self.history_manager.handle_game_update(action, action.get("player_uuid"), player_name, street)
            
        # Update result for previous actions if this action concludes a hand
        if action.get("action") == "fold":
            # The history manager will handle updating the result
            pass

    def receive_round_result_message(self, winners, hand_info, round_state):
        # Translate the round result using the mapper and print
        translation = self.mapper.translate_round_result(winners, hand_info, round_state)
        print(translation)
        print("-" * 40) # Separator after round results
        
        # Handle round result in history manager
        self.history_manager.handle_round_result(winners, hand_info, round_state, self.mapper.bot_uuid)

    # Helper functions remain the same
    def do_fold(self, valid_actions):
        action_info = valid_actions[0]
        amount = action_info["amount"]
        return action_info['action'], amount

    def do_call(self, valid_actions):
        action_info = valid_actions[1]
        amount = action_info["amount"]
        return action_info['action'], amount

    def do_raise(self,  valid_actions, raise_amount):
        action_info = valid_actions[2]
        # Ensure the raise amount is valid
        min_raise = action_info['amount']['min']
        max_raise = action_info['amount']['max']
        if min_raise == -1 : # Cannot raise (e.g. only calls/folds possible)
             # Fallback to call if raise isn't possible but was intended
             return self.do_call(valid_actions)
        
        amount = int(max(min_raise, min(raise_amount, max_raise))) # Clamp amount
        # If clamping makes it just a call, perform call instead
        if amount <= valid_actions[1]['amount']:
             return self.do_call(valid_actions)
             
        return action_info['action'], amount

    def do_all_in(self,  valid_actions):
        action_info = valid_actions[2]
        amount = action_info['amount']['max']
        if amount == -1 or amount <= valid_actions[1]['amount']: # If max raise is -1 or just a call
            return self.do_call(valid_actions) # Cannot all-in, just call
        return action_info['action'], amount
        
    def export_opponents_json(self):
        """Export opponent tracking data in JSON format"""
        opponents_stats = self.history_manager.get_opponent_stats()
        if not opponents_stats:
            return
            
        # Display JSON formatted opponent data for debugging
        opponents_json = []
        for opponent in opponents_stats:
            # Include all opponents, even with few hands
            json_data = {
                "id": opponent['uuid'],
                "position": opponent['position'],
                "stack": opponent.get('stack', 0),
                "history": {
                    "fold_to_5bb_shove": opponent.get('history', {}).get('fold_to_5bb_shove', 0.0),
                    "call_range_width": opponent.get('history', {}).get('call_range_width', 0.0),
                    "short_stack_adjustment": opponent.get('history', {}).get('short_stack_adjustment', 1.0),
                    "observations": opponent.get('history', {}).get('observations', 0),
                    "last_10_hands": opponent.get('history', {}).get('last_10_hands', [])
                }
            }
            
            opponents_json.append(json_data)
        
        if opponents_json:
            print("\n<OPPONENTS_JSON>")
            import json
            print(json.dumps({"opponents": opponents_json}, indent=2))
            print("</OPPONENTS_JSON>")