import json
import os
import time

class HistoryManager:
    """
    HistoryManager handles all poker game history operations.
    It tracks rounds, actions, and player results.
    """

    def __init__(self, bot_name="JasperBot", debug_mode=True):
        """Initialize the HistoryManager with optional bot name and debug mode"""
        self.bot_name = bot_name
        self.debug_mode = False # Disable debug mode to remove console logs
        
        # Initialize history logs
        self.game_history = []
        self.current_round_history = []
        self.action_history = []
        self.my_hole_cards = []
        
        # Initialize opponent tracking
        self.opponents = {}  # uuid -> stats
        self.bot_uuid = None
        
        # Debug logs removed for cleaner display
        
    def _format_cards(self, cards):
        """Formats a list of cards into proper poker notation.
        Converts from 'SuitRank' format (where S is suit and R is rank) to standard 'Rs' format.
        For example, converts 'HK' to 'Kh', 'DT' to 'Td', etc."""
        if not cards:
            return []
        
        formatted_cards = []
        for card in cards:
            if len(card) == 2:
                suit = card[0].lower()  # First character is the suit, make lowercase
                rank = card[1]  # Second character is the rank
                
                # Convert to rank+suit format (e.g., Kh)
                formatted_cards.append(f"{rank}{suit}")
            else:
                # If the format is unexpected, just use the original
                formatted_cards.append(card)
                
        return formatted_cards

    def log_state(self, state_type, data):
        """Log game state information"""
        log_entry = {
            "type": state_type,
            "data": data,
            "timestamp": time.time()
        }
        self.current_round_history.append(log_entry)
        
        # For action history, maintain a more focused record
        if state_type == "action":
            self.action_history.append(data)
    
    def save_history(self):
        """Save history (no longer writes to file)"""
        # Debug logs removed for cleaner display
    
    def load_history(self):
        """Load history (no longer reads from file)"""
        # History is now only kept in memory
        self.game_history = []
        # Debug logs removed for cleaner display

    def print_history_analysis(self):
        """Print comprehensive history analysis"""
        if not self.game_history:
            print("\nNo historical data available yet.")
            return
            
        print("\n============ POKER HISTORY ANALYSIS ============")
        print(f"Total rounds recorded: {len(self.game_history)}")
        
        # Overall statistics
        total_actions = 0
        wins = 0
        losses = 0
        action_counts = {"fold": 0, "call": 0, "raise": 0}
        street_wins = {"preflop": 0, "flop": 0, "turn": 0, "river": 0}
        street_losses = {"preflop": 0, "flop": 0, "turn": 0, "river": 0}
        
        # Hand strength analysis
        strength_results = {
            "weak": {"win": 0, "loss": 0},    # 1-4
            "medium": {"win": 0, "loss": 0},  # 5-7
            "strong": {"win": 0, "loss": 0}   # 8-10
        }
        
        # Analyze all recorded actions
        for round_idx, round_data in enumerate(self.game_history):
            for entry in round_data:
                if entry["type"] == "action":
                    total_actions += 1
                    action = entry["data"].get("action", "").lower()
                    result = entry["data"].get("result", "").lower()
                    street = entry["data"].get("street", "").lower()
                    strength = entry["data"].get("hand_strength", 0)
                    
                    # Count action types
                    if action in action_counts:
                        action_counts[action] += 1
                    
                    # Count wins/losses
                    if result == "win":
                        wins += 1
                        if street in street_wins:
                            street_wins[street] += 1
                    elif result == "loss":
                        losses += 1
                        if street in street_losses:
                            street_losses[street] += 1
                    
                    # Categorize by hand strength
                    strength_category = ""
                    if strength <= 4:
                        strength_category = "weak"
                    elif strength <= 7:
                        strength_category = "medium"
                    else:
                        strength_category = "strong"
                        
                    if strength_category and result in ["win", "loss"]:
                        strength_results[strength_category][result] += 1
        
        # Print overall statistics
        print("\n--- OVERALL STATISTICS ---")
        win_rate = (wins / total_actions) * 100 if total_actions > 0 else 0
        print(f"Total actions: {total_actions}")
        print(f"Wins: {wins}, Losses: {losses}")
        print(f"Win rate: {win_rate:.1f}%")
        
        print("\n--- ACTION DISTRIBUTION ---")
        for action, count in action_counts.items():
            percentage = (count / total_actions) * 100 if total_actions > 0 else 0
            print(f"{action.upper()}: {count} times ({percentage:.1f}%)")
        
        print("\n--- PERFORMANCE BY STREET ---")
        for street in ["preflop", "flop", "turn", "river"]:
            street_total = street_wins[street] + street_losses[street]
            win_rate = (street_wins[street] / street_total) * 100 if street_total > 0 else 0
            print(f"{street.upper()}: {street_wins[street]} wins, {street_losses[street]} losses ({win_rate:.1f}% win rate)")
        
        print("\n--- PERFORMANCE BY HAND STRENGTH ---")
        for category, results in strength_results.items():
            category_total = results["win"] + results["loss"]
            win_rate = (results["win"] / category_total) * 100 if category_total > 0 else 0
            print(f"{category.upper()} hands: {results['win']} wins, {results['loss']} losses ({win_rate:.1f}% win rate)")
        
        print("\n--- RECENT HAND RESULTS ---")
        # Show most recent 5 rounds
        recent_rounds = min(5, len(self.game_history))
        for i in range(recent_rounds):
            round_idx = len(self.game_history) - i - 1
            round_data = self.game_history[round_idx]
            
            # Get round info
            round_info = next((entry["data"] for entry in round_data if entry["type"] == "round_start"), {})
            round_count = round_info.get("round_count", f"Round {round_idx+1}")
            
            # Get winner info
            result_info = next((entry["data"] for entry in round_data if entry["type"] == "round_result"), {})
            is_winner = result_info.get("is_winner", False)
            
            # Get our actions
            actions = [entry["data"] for entry in round_data if entry["type"] == "action"]
            
            print(f"\nRound {round_count}: {'WON' if is_winner else 'LOST'}")
            if round_info.get("hole_card"):
                formatted_cards = self._format_cards(round_info['hole_card'])
                print(f"Hole cards: {', '.join(formatted_cards)}")
            
            for action_data in actions:
                street = action_data.get("street", "")
                action = action_data.get("action", "").upper()
                amount = action_data.get("amount", "")
                strength = action_data.get("hand_strength", 0)
                
                amount_str = f" ({amount})" if amount else ""
                print(f"  {street}: {action}{amount_str} with hand strength {strength}/10")
                
        print("\n============================================")

    def get_hand_history(self, hole_card, community_card, round_state):
        """Return accurate past history of hands without prediction using XML-like tags"""
        
        # Print historical data for the user - using XML-like tags
        print("\n<HISTORICAL_HAND_DATA>")
        
        # Extract current hand info
        current_street = round_state['street']
        current_hole_cards = [card for card in hole_card]
        current_community_cards = [card for card in community_card]
        
        # Extract more context
        seats = round_state.get('seats', [])
        dealer_btn = round_state.get('dealer_btn', -1)
        small_blind_pos = round_state.get('small_blind_pos', -1)
        big_blind_pos = round_state.get('big_blind_pos', -1)
        pot = round_state.get('pot', {}).get('main', {}).get('amount', 0)
        action_histories = round_state.get('action_histories', {})
        
        # Current street and cards
        print(f"Current street: {current_street}")
        formatted_hole_cards = self._format_cards(current_hole_cards)
        print(f"Current hole cards: {', '.join(formatted_hole_cards)}")
        if current_community_cards:
            formatted_community_cards = self._format_cards(current_community_cards)
            print(f"Current community cards: {', '.join(formatted_community_cards)}")
        
        # Print positions and stacks of all players
        print("<TABLE_INFO>")
        for i, seat in enumerate(seats):
            player_name = seat.get('name', 'Unknown')
            player_stack = seat.get('stack', 0)
            player_state = seat.get('state', '')
            position = "Unknown"
            
            # Calculate position
            if i == dealer_btn:
                position = "Button"
            elif i == small_blind_pos:
                position = "Small Blind"
            elif i == big_blind_pos:
                position = "Big Blind"
            elif len(seats) <= 3:  # Heads-up or 3-handed
                position = "Button" if i == dealer_btn else "Big Blind"
            else:
                # Calculate relative position
                position_index = (i - dealer_btn) % len(seats)
                if position_index == 0:
                    position = "Button"
                elif position_index == 1:
                    position = "Small Blind" 
                elif position_index == 2:
                    position = "Big Blind"
                else:
                    third = len(seats) // 3
                    if position_index <= 2 + third:
                        position = "Early"
                    elif position_index <= 2 + (2 * third):
                        position = "Middle"
                    else:
                        position = "Late"
            
            print(f"  Player: {player_name}, Position: {position}, Stack: {player_stack}, State: {player_state}")
        print("</TABLE_INFO>")
        
        # Previous action in current street
        if action_histories:
            street_actions = action_histories.get(current_street.lower(), [])
            if street_actions:
                print("<STREET_ACTIONS>")
                for action in street_actions:
                    player_uuid = action.get('uuid', '')
                    player_name = "Unknown"
                    for seat in seats:
                        if seat.get('uuid') == player_uuid:
                            player_name = seat.get('name', 'Unknown')
                            break
                    
                    action_type = action.get('action', '').upper()
                    amount = action.get('amount', 0)
                    amount_str = f" ({amount})" if amount and action_type not in ['FOLD', 'CHECK'] else ""
                    print(f"  {player_name}: {action_type}{amount_str}")
                print("</STREET_ACTIONS>")
        
        # Debug info removed for cleaner display
        
        print("</HISTORICAL_HAND_DATA>")
        
        # Display the current round information first
        has_displayed_info = False
        
        if self.current_round_history and len(self.current_round_history) > 0:
            has_displayed_info = True
            print("<CURRENT_HAND_HISTORY>")
            
            # Extract current round data from current_round_history
            round_info = next((entry["data"] for entry in self.current_round_history if entry["type"] == "round_start"), None)
            if round_info:
                round_count = round_info.get("round_count", "Current Round")
                print(f"Round {round_count} (IN PROGRESS)")
                
                # Get hole cards - should be the same as current_hole_cards
                hole_cards = round_info.get("hole_card", [])
                if hole_cards:
                    formatted_hole_cards = self._format_cards(hole_cards)
                    print(f"Hole cards: {', '.join(formatted_hole_cards)}")
                
                # Get community cards from street_start entries
                last_street_data = next((entry["data"] for entry in reversed(self.current_round_history) 
                                    if entry["type"] == "street_start"), None)
                if last_street_data and last_street_data.get("community_cards"):
                    community_cards = last_street_data.get("community_cards")
                    formatted_community_cards = self._format_cards(community_cards)
                    print(f"Community cards: {', '.join(formatted_community_cards)}")
                
                # Get all actions in the current round
                my_actions = [entry["data"] for entry in self.current_round_history if entry["type"] == "action"]
                if my_actions:
                    print("My actions this round:")
                    for action_data in my_actions:
                        street = action_data.get("street", "")
                        action = action_data.get("action", "").upper()
                        amount = action_data.get("amount", "")
                        
                        amount_str = f" ({amount})" if amount else ""
                        print(f"  {street}: {action}{amount_str}")
                
                # Get opponent actions
                opp_actions = [entry["data"] for entry in self.current_round_history if entry["type"] == "opponent_action"]
                if opp_actions:
                    print("Opponent actions this round:")
                    for action_data in opp_actions:
                        player_name = action_data.get("player_name", "Unknown")
                        street = action_data.get("street", "")
                        action = action_data.get("action", "").upper()
                        amount = action_data.get("amount", "")
                        
                        amount_str = f" ({amount})" if amount else ""
                        print(f"  {player_name} on {street}: {action}{amount_str}")
            
            print("</CURRENT_HAND_HISTORY>")
        
        # Now show previous rounds from game_history
        print("<PREVIOUS_ROUNDS_HISTORY>")
        if not self.game_history or len(self.game_history) == 0:
            if not has_displayed_info:
                print("No historical data available yet.")
            else:
                print("No previous rounds recorded yet.")
            print("</PREVIOUS_ROUNDS_HISTORY>")
            return None
        
        # We have history from previous rounds - display it
        print(f"Total completed rounds: {len(self.game_history)}")
        
        # Overall statistics
        total_actions = 0
        wins = 0
        losses = 0
        action_counts = {"fold": 0, "call": 0, "raise": 0}
        
        # Track all hand combinations and their outcomes
        hand_outcomes = {}
        
        # Print all hands and their outcomes
        print("--- COMPLETE HAND RECORD ---")
        for round_idx, round_data in enumerate(self.game_history):
            if self.debug_mode:
                print(f"[DEBUG] Processing round {round_idx+1} with {len(round_data)} entries")
                
            # Get round info
            round_info = next((entry["data"] for entry in round_data if entry["type"] == "round_start"), None)
            if not round_info:
                # Debug logs removed for cleaner display
                round_count = f"Round {round_idx+1}"
                hole_cards = []
            else:
                round_count = round_info.get("round_count", f"Round {round_idx+1}")
                hole_cards = round_info.get("hole_card", [])
            
            # Get community cards - most likely from the last street start entry
            last_street_data = next((entry["data"] for entry in reversed(round_data) 
                                 if entry["type"] == "street_start"), None)
            community_cards = last_street_data.get("community_cards", []) if last_street_data else []
            
            # Get winner info
            result_info = next((entry["data"] for entry in round_data if entry["type"] == "round_result"), None)
            is_winner = result_info.get("is_winner", False) if result_info else False
            
            # Get our actions
            actions = [entry["data"] for entry in round_data if entry["type"] == "action"]
            
            # Debug logs removed for cleaner display
            
            # Track outcomes
            for action_data in actions:
                total_actions += 1
                action = action_data.get("action", "").lower()
                result = "win" if is_winner else "loss"
                
                if action in action_counts:
                    action_counts[action] += 1
                
                if result == "win":
                    wins += 1
                else:
                    losses += 1
                
                # Create a key based on hole cards
                if hole_cards:
                    hole_key = ",".join(sorted(hole_cards))
                    if hole_key not in hand_outcomes:
                        hand_outcomes[hole_key] = {"wins": 0, "losses": 0, "actions": []}
                    
                    hand_outcomes[hole_key]["actions"].append({
                        "round": round_count,
                        "action": action,
                        "street": action_data.get("street", ""),
                        "result": result
                    })
                    
                    if result == "win":
                        hand_outcomes[hole_key]["wins"] += 1
                    else:
                        hand_outcomes[hole_key]["losses"] += 1
            
            # Print detailed hand info
            print(f"Round {round_count}: {'WON' if is_winner else 'LOST'}")
            if hole_cards:
                formatted_hole_cards = self._format_cards(hole_cards)
                print(f"Hole cards: {', '.join(formatted_hole_cards)}")
            if community_cards:
                formatted_community_cards = self._format_cards(community_cards)
                print(f"Community cards: {', '.join(formatted_community_cards)}")
            
            for action_data in actions:
                street = action_data.get("street", "")
                action = action_data.get("action", "").upper()
                amount = action_data.get("amount", "")
                
                amount_str = f" ({amount})" if amount else ""
                print(f"  {street}: {action}{amount_str}")
        
        if hand_outcomes:
            # Print win rate for each hand combination
            print("--- HAND COMBINATION RECORDS ---")
            for hole_key, outcomes in hand_outcomes.items():
                total = outcomes["wins"] + outcomes["losses"]
                win_rate = (outcomes["wins"] / total) * 100 if total > 0 else 0
                print(f"Hand {hole_key}: {outcomes['wins']} wins, {outcomes['losses']} losses ({win_rate:.1f}% win rate)")
                
                # Print detailed actions for this hand
                for action_record in outcomes["actions"]:
                    print(f"  Round {action_record['round']} - {action_record['street']}: {action_record['action'].upper()} - {action_record['result'].upper()}")
        else:
            print("No detailed hand combination records available yet.")
        
        # Print overall stats if we have any actions
        if total_actions > 0:
            print("--- OVERALL STATISTICS ---")
            win_rate = (wins / total_actions) * 100 if total_actions > 0 else 0
            print(f"Total actions: {total_actions}")
            print(f"Wins: {wins}, Losses: {losses}")
            print(f"Win rate: {win_rate:.1f}%")
            
            print("--- ACTION DISTRIBUTION ---")
            for action, count in action_counts.items():
                percentage = (count / total_actions) * 100 if total_actions > 0 else 0
                print(f"{action.upper()}: {count} times ({percentage:.1f}%)")
        else:
            print("No action statistics available yet.")
            
        print("</PREVIOUS_ROUNDS_HISTORY>")
        return None

    def handle_game_start(self, game_info):
        """Handle game start event"""
        # Log game start
        self.log_state("game_start", game_info)
        
        # Reset round history for new game
        self.current_round_history = []
        
        # Initialize opponent tracking if we have seat information
        seats = game_info.get('seats', [])
        for seat in seats:
            player_uuid = seat.get('uuid')
            player_name = seat.get('name')
            if player_name == self.bot_name:
                self.bot_uuid = player_uuid
                continue
                
            if player_uuid and player_uuid not in self.opponents:
                self.opponents[player_uuid] = {
                    'id': player_uuid,
                    'name': player_name,
                    'hands_observed': 0,
                    'preflop_actions': [],  # List of actions, used to calculate VPIP, PFR
                    'postflop_actions': [], # List of actions on flop, turn, river
                    'big_bet_responses': [], # Responses to 5BB+ raises
                    'three_bet_opportunities': 0,
                    'three_bets_made': 0,
                    'position_history': {},  # Positions played
                    'notes': [],  # Qualitative observations
                    'history': {
                        'fold_to_5bb_shove': 0.0,   # F5S value (0-1)
                        'call_range_width': 0.0,    # CRW value (0-1)
                        'short_stack_adjustment': 1.0,  # SSAF value (0-3)
                        'observations': 0,          # Number of observations
                        'last_10_hands': []         # Array of recent actions
                    }
                }

    def handle_round_start(self, round_count, hole_card, seats):
        """Handle round start event"""
        # Store hole cards directly from the received data (in original format)
        self.my_hole_cards = hole_card
        
        # Get round state information
        round_state_entry = next((entry["data"] for entry in self.current_round_history 
                                if entry["type"] == "round_start"), None)
        dealer_btn = -1
        small_blind_pos = -1
        big_blind_pos = -1
        
        if round_state_entry:
            dealer_btn = round_state_entry.get("dealer_btn", -1)
            small_blind_pos = round_state_entry.get("small_blind_pos", -1)
            big_blind_pos = round_state_entry.get("big_blind_pos", -1)
        
        # Log round start with hole card data
        self.log_state("round_start", {
            "round_count": round_count,
            "hole_card": hole_card,
            "seats": [{
                "name": seat.get("name", "Unknown"),
                "uuid": seat.get("uuid", ""),
                "stack": seat.get("stack", 0),
                "state": seat.get("state", "")
            } for seat in seats],
            "dealer_btn": dealer_btn,
            "small_blind_pos": small_blind_pos,
            "big_blind_pos": big_blind_pos
        })
        
        # Update opponent stats for each round
        for i, seat in enumerate(seats):
            player_uuid = seat.get("uuid")
            if player_uuid != self.bot_uuid and player_uuid in self.opponents:
                # Update hands observed counter
                self.opponents[player_uuid]['hands_observed'] += 1
                
                # Update stack in opponent data (for JSON format)
                self.opponents[player_uuid]['stack'] = seat.get("stack", 0)
                
                # Determine position
                position = "Unknown"
                if i == dealer_btn:
                    position = "Button"
                elif i == small_blind_pos:
                    position = "Small Blind"
                elif i == big_blind_pos:
                    position = "Big Blind"
                elif len(seats) == 2:  # Heads-up
                    position = "Button" if i == dealer_btn else "Big Blind"
                else:
                    # Calculate relative position
                    position_index = (i - dealer_btn) % len(seats)
                    if position_index == 0:
                        position = "Button"
                    elif position_index == 1:
                        position = "Small Blind" 
                    elif position_index == 2:
                        position = "Big Blind"
                    else:
                        third = len(seats) // 3
                        if position_index <= 2 + third:
                            position = "Early"
                        elif position_index <= 2 + (2 * third):
                            position = "Middle"
                        else:
                            position = "Late"
                
                # Track position history
                if position not in self.opponents[player_uuid]['position_history']:
                    self.opponents[player_uuid]['position_history'][position] = 1
                else:
                    self.opponents[player_uuid]['position_history'][position] += 1
        
        # Debug logs removed for cleaner display
        
        # If previous round ended, save it to history before starting new round
        if self.current_round_history and any(entry["type"] == "round_result" for entry in self.current_round_history):
            # Debug logs removed for cleaner display
            self.game_history.append(self.current_round_history)
            self.current_round_history = []
            
            # Update history in memory
            self.save_history()

    def handle_street_start(self, street, community_cards, pot=0):
        """Handle street start event"""
        # Log street start with community cards
        self.log_state("street_start", {
            "street": street,
            "community_cards": community_cards,
            "pot": pot
        })

    def handle_game_update(self, action, player_uuid, player_name, street):
        """Handle game update event (opponent actions)"""
        # Log opponent actions
        if player_uuid:
            action_type = action.get("action", "").lower()
            amount = action.get("amount", 0)
            
            self.log_state("opponent_action", {
                "player_uuid": player_uuid,
                "player_name": player_name,
                "action": action_type,
                "amount": amount,
                "street": street
            })
            
            # Update opponent stats if this is a tracked opponent
            if player_uuid in self.opponents:
                # Get round state to check for betting context
                round_state_entry = next((entry["data"] for entry in self.current_round_history 
                                       if entry["type"] == "round_start"), None)
                small_blind_amount = 0
                if round_state_entry:
                    small_blind_amount = round_state_entry.get("small_blind_amount", 0)
                
                # Get current pot size for bet sizing context
                pot_size = 0
                last_street_data = next((entry["data"] for entry in reversed(self.current_round_history) 
                                    if entry["type"] == "street_start"), None)
                if last_street_data:
                    pot_size = last_street_data.get("pot", 0)
                
                # Get the current position of the player and stack
                player_position = "Unknown"
                player_stack = 0
                if round_state_entry:
                    seats = round_state_entry.get("seats", [])
                    dealer_btn = round_state_entry.get("dealer_btn", -1)
                    small_blind_pos = round_state_entry.get("small_blind_pos", -1)
                    big_blind_pos = round_state_entry.get("big_blind_pos", -1)
                    
                    for i, seat in enumerate(seats):
                        if seat.get("uuid") == player_uuid:
                            player_stack = seat.get("stack", 0)
                            if i == dealer_btn:
                                player_position = "Button"
                            elif i == small_blind_pos:
                                player_position = "Small Blind"
                            elif i == big_blind_pos:
                                player_position = "Big Blind"
                            elif len(seats) == 2:  # Heads-up
                                player_position = "Button" if i == dealer_btn else "Big Blind"
                            else:
                                # Calculate relative position
                                position_index = (i - dealer_btn) % len(seats)
                                if position_index == 0:
                                    player_position = "Button"
                                elif position_index == 1:
                                    player_position = "Small Blind" 
                                elif position_index == 2:
                                    player_position = "Big Blind"
                                else:
                                    third = len(seats) // 3
                                    if position_index <= 2 + third:
                                        player_position = "Early"
                                    elif position_index <= 2 + (2 * third):
                                        player_position = "Middle"
                                    else:
                                        player_position = "Late"
                            break
                
                # Calculate bet sizing relative to pot (if applicable)
                pot_ratio = 0
                if pot_size > 0 and amount > 0:
                    pot_ratio = amount / pot_size
                
                # Store more detailed action data 
                action_data = {
                    'action': action_type,
                    'amount': amount,
                    'street': street.lower(),
                    'position': player_position,
                    'pot_size': pot_size,
                    'pot_ratio': pot_ratio,
                    'stack': player_stack,
                    'timestamp': time.time()
                }
                
                # Update the last 10 hands in the JSON history
                hand_record = {
                    'action': action_type,
                    'amount': amount if amount > 0 else None,
                    'position': player_position,
                    'street': street.lower()
                }
                
                # If this is a facing big bet decision, note it specially
                if action_type in ['call', 'fold', 'raise'] and small_blind_amount > 0:
                    min_big_bet = small_blind_amount * 10  # 5BB = 10 small blinds
                    # Determine if this was facing a big bet
                    preflop_history = [a for a in self.opponents[player_uuid]['preflop_actions'] 
                                     if a['street'] == "preflop"]
                    facing_big_bet = False
                    for i, hist_action in enumerate(preflop_history):
                        if hist_action['action'] == 'raise' and hist_action['amount'] >= min_big_bet:
                            facing_big_bet = True
                            break
                    if facing_big_bet:
                        hand_record['facing_5bb'] = True
                
                # Add to history tracking
                self.opponents[player_uuid]['history']['last_10_hands'].append(hand_record)
                # Keep only the last 10 hands
                if len(self.opponents[player_uuid]['history']['last_10_hands']) > 10:
                    self.opponents[player_uuid]['history']['last_10_hands'] = self.opponents[player_uuid]['history']['last_10_hands'][-10:]
                
                # Increment observations
                self.opponents[player_uuid]['history']['observations'] += 1
                
                # Track preflop actions for VPIP and PFR
                if street.lower() == "preflop":
                    # Store action with enhanced context
                    self.opponents[player_uuid]['preflop_actions'].append(action_data)
                    
                    # Log detailed preflop behavior
                    if 'preflop_details' not in self.opponents[player_uuid]:
                        self.opponents[player_uuid]['preflop_details'] = {
                            'position_actions': {}, # Actions by position
                            'raise_sizes': [],      # Track raise sizing
                            'open_raises': 0,       # First to raise
                            'cold_calls': 0,        # Call after raise
                            'squeeze_plays': 0,     # Raise after call and raise
                        }
                    
                    # Track position-based actions
                    if player_position not in self.opponents[player_uuid]['preflop_details']['position_actions']:
                        self.opponents[player_uuid]['preflop_details']['position_actions'][player_position] = []
                    self.opponents[player_uuid]['preflop_details']['position_actions'][player_position].append(action_type)
                    
                    # Track raise sizing
                    if action_type == 'raise' and amount > 0:
                        self.opponents[player_uuid]['preflop_details']['raise_sizes'].append(amount)
                    
                    # Track preflop history to determine action context
                    preflop_history = [a for a in self.opponents[player_uuid]['preflop_actions'] 
                                     if a['street'] == "preflop"]
                    
                    # Track special preflop patterns
                    current_round_actions = [entry["data"] for entry in self.current_round_history 
                                           if entry["type"] == "opponent_action" and 
                                              entry["data"].get("street", "").lower() == "preflop"]
                    
                    # Check if this was an open raise (first raise preflop)
                    if action_type == 'raise':
                        is_first_raise = not any(a.get("action") == "raise" for a in current_round_actions)
                        if is_first_raise:
                            self.opponents[player_uuid]['preflop_details']['open_raises'] += 1
                    
                    # Check if this was a cold call (calling after a raise)
                    if action_type == 'call':
                        previous_raise = any(a.get("action") == "raise" for a in current_round_actions)
                        if previous_raise:
                            self.opponents[player_uuid]['preflop_details']['cold_calls'] += 1
                    
                    # Check if this was a squeeze play (raising after call(s) and a raise)
                    if action_type == 'raise':
                        previous_call = any(a.get("action") == "call" for a in current_round_actions)
                        previous_raise = any(a.get("action") == "raise" for a in current_round_actions)
                        if previous_call and previous_raise:
                            self.opponents[player_uuid]['preflop_details']['squeeze_plays'] += 1
                    
                    # If there was a raise before this player acted
                    has_previous_raise = any(a['action'] == 'raise' for a in preflop_history[:-1]) 
                    
                    if has_previous_raise:
                        # This was a 3-bet opportunity
                        self.opponents[player_uuid]['three_bet_opportunities'] += 1
                        
                        # Check if player 3-bet
                        if action_type == 'raise':
                            self.opponents[player_uuid]['three_bets_made'] += 1
                    
                    # Track response to big bets (5BB+)
                    if action_type in ['call', 'fold', 'raise'] and small_blind_amount > 0:
                        # Check if facing a bet of 5BB or more
                        # This is a simplified approximation - would need to check actual bet faced
                        min_big_bet = small_blind_amount * 10  # 5BB = 10 small blinds
                        facing_big_bet = False
                        
                        # Check if recent actions have a big raise
                        for i, hist_action in enumerate(preflop_history):
                            if hist_action['action'] == 'raise' and hist_action['amount'] >= min_big_bet:
                                facing_big_bet = True
                                break
                        
                        if facing_big_bet:
                            # Store more context with response
                            big_bet_response = {
                                'action': action_type,
                                'amount': amount,
                                'position': player_position,
                                'facing_amount': min_big_bet
                            }
                            self.opponents[player_uuid]['big_bet_responses'].append(action_type)
                            
                            # Track detailed big bet responses if not exists
                            if 'detailed_big_bet_responses' not in self.opponents[player_uuid]:
                                self.opponents[player_uuid]['detailed_big_bet_responses'] = []
                            self.opponents[player_uuid]['detailed_big_bet_responses'].append(big_bet_response)
                else:
                    # Track postflop actions with enhanced data
                    self.opponents[player_uuid]['postflop_actions'].append(action_data)
                    
                    # Initialize postflop details tracking if not exists
                    if 'postflop_details' not in self.opponents[player_uuid]:
                        self.opponents[player_uuid]['postflop_details'] = {
                            'streets': {'flop': [], 'turn': [], 'river': []},
                            'bet_sizing': {'flop': [], 'turn': [], 'river': []},
                            'check_raise_counts': {'flop': 0, 'turn': 0, 'river': 0},
                            'donk_bet_counts': {'flop': 0, 'turn': 0, 'river': 0},
                            'delayed_cbet_counts': {'turn': 0, 'river': 0}
                        }
                    
                    current_street = street.lower()
                    if current_street in ['flop', 'turn', 'river']:
                        # Track detailed action by street
                        self.opponents[player_uuid]['postflop_details']['streets'][current_street].append(action_type)
                        
                        # Track bet sizing by street
                        if action_type in ['raise', 'bet'] and amount > 0:
                            self.opponents[player_uuid]['postflop_details']['bet_sizing'][current_street].append({
                                'amount': amount,
                                'pot_size': pot_size,
                                'pot_ratio': pot_ratio
                            })
                        
                        # Get previous actions on this street to identify patterns
                        street_actions = [entry["data"] for entry in self.current_round_history 
                                         if entry["type"] == "opponent_action" and 
                                            entry["data"].get("street", "").lower() == current_street]
                        
                        # Check for check-raise
                        if action_type == 'raise':
                            has_checked = any(a.get("player_uuid") == player_uuid and a.get("action") == "call" and a.get("amount") == 0 
                                            for a in street_actions[:-1])
                            if has_checked:
                                self.opponents[player_uuid]['postflop_details']['check_raise_counts'][current_street] += 1
                        
                        # Check for donk bets (betting into previous street aggressor)
                        if action_type in ['bet', 'raise'] and current_street in ['flop', 'turn', 'river']:
                            # Identify the previous street
                            prev_street = None
                            if current_street == 'flop':
                                prev_street = 'preflop'
                            elif current_street == 'turn':
                                prev_street = 'flop'
                            elif current_street == 'river':
                                prev_street = 'turn'
                            
                            if prev_street:
                                # Find last aggressor on previous street
                                prev_street_actions = [entry["data"] for entry in self.current_round_history 
                                                     if entry["type"] == "opponent_action" and 
                                                        entry["data"].get("street", "").lower() == prev_street]
                                
                                if prev_street_actions:
                                    last_aggressor = None
                                    for a in reversed(prev_street_actions):
                                        if a.get("action") in ['raise', 'bet']:
                                            last_aggressor = a.get("player_uuid")
                                            break
                                    
                                    # If last aggressor wasn't this player, it's a donk bet
                                    if last_aggressor and last_aggressor != player_uuid:
                                        self.opponents[player_uuid]['postflop_details']['donk_bet_counts'][current_street] += 1
                        
                        # Check for delayed continuation bet
                        if action_type in ['bet', 'raise'] and current_street in ['turn', 'river']:
                            # Check if they raised preflop but checked flop
                            has_pf_raise = any(a['action'] == 'raise' and a['street'] == 'preflop' 
                                             for a in self.opponents[player_uuid]['preflop_actions'])
                            
                            if has_pf_raise:
                                # Check if they checked previous street
                                prev_street = 'flop' if current_street == 'turn' else 'turn'
                                checked_prev = False
                                
                                for a in self.opponents[player_uuid]['postflop_actions']:
                                    if a['street'] == prev_street and a['action'] == 'call' and a['amount'] == 0:
                                        checked_prev = True
                                        break
                                
                                if checked_prev:
                                    self.opponents[player_uuid]['postflop_details']['delayed_cbet_counts'][current_street] += 1
                
                # Debug logs removed for cleaner display

    def handle_round_result(self, winners, hand_info, round_state, bot_uuid):
        """Handle round result event"""
        # Log round result
        winner_uuids = [winner.get("uuid") for winner in winners]
        is_winner = bot_uuid in winner_uuids
        
        # Debug logs removed for cleaner display
        
        # Update all pending actions with result
        for entry in self.current_round_history:
            if entry["type"] == "action" and entry["data"].get("result") == "pending":
                entry["data"]["result"] = "win" if is_winner else "loss"
                # Debug logs removed for cleaner display
        
        # Get final community cards
        community_cards = round_state.get("community_card", [])
        
        # Get all hole cards shown at showdown
        shown_hole_cards = {}
        if hand_info:
            for player_hand in hand_info:
                player_uuid = player_hand.get("uuid")
                if player_uuid and player_hand.get("hand_cards"):
                    shown_hole_cards[player_uuid] = player_hand.get("hand_cards")
                    
                    # Update opponent's last hand record with shown cards if available
                    if player_uuid in self.opponents and player_uuid != bot_uuid:
                        # Only add if this opponent has actions recorded
                        if self.opponents[player_uuid]['history']['last_10_hands']:
                            # Add shown cards to the most recent hand (in proper poker notation)
                            recent_hand = self.opponents[player_uuid]['history']['last_10_hands'][-1]
                            shown_cards = player_hand.get("hand_cards", [])
                            formatted_shown_cards = self._format_cards(shown_cards)
                            recent_hand['hand_shown'] = formatted_shown_cards
                            
                            # Update fold to 5bb shove stats if applicable
                            if 'preflop_details' in self.opponents[player_uuid] and self.opponents[player_uuid]['big_bet_responses']:
                                total_big_bet_responses = len(self.opponents[player_uuid]['big_bet_responses'])
                                fold_count = self.opponents[player_uuid]['big_bet_responses'].count('fold')
                                self.opponents[player_uuid]['history']['fold_to_5bb_shove'] = fold_count / total_big_bet_responses if total_big_bet_responses > 0 else 0.0
                            
                            # Update call range width based on hands shown
                            if 'call_hands' not in self.opponents[player_uuid]:
                                self.opponents[player_uuid]['call_hands'] = []
                            
                            last_action = recent_hand.get('action')
                            if last_action == 'call' and player_hand.get("hand_cards"):
                                # Add to call_hands with proper formatting
                                shown_cards = player_hand.get("hand_cards", [])
                                formatted_shown_cards = self._format_cards(shown_cards)
                                self.opponents[player_uuid]['call_hands'].append(formatted_shown_cards)
                                
                                # Calculate call range width (0-1) - more hands = wider range
                                call_hands_count = len(self.opponents[player_uuid]['call_hands'])
                                # Normalize to 0-1 range (assuming 20+ unique call hands is maximum range)
                                self.opponents[player_uuid]['history']['call_range_width'] = min(call_hands_count / 20, 1.0)
        
        # Update short stack adjustment factor for all opponents based on their stack sizes
        for player_uuid, data in self.opponents.items():
            if player_uuid != bot_uuid:
                # Check all players' stacks after this hand
                for player in winners + (round_state.get('seats', []) if round_state else []):
                    if player.get('uuid') == player_uuid:
                        player_stack = player.get('stack', 0)
                        starting_stack = 100  # Standard starting stack
                        
                        # Calculate adjustment factor (1.0 = normal, higher = more aggressive when short)
                        if player_stack < starting_stack * 0.5:  # Less than half starting stack
                            # Check if their betting gets more aggressive when short
                            recent_actions = [h for h in data['history']['last_10_hands'] if h.get('action') in ['raise', 'call']]
                            aggressive_count = sum(1 for h in recent_actions if h.get('action') == 'raise')
                            
                            if len(recent_actions) > 0:
                                aggression_ratio = aggressive_count / len(recent_actions)
                                
                                # Scale from 1.0 (normal) to 3.0 (very aggressive when short)
                                short_stack_adjustment = 1.0 + (2.0 * aggression_ratio)
                                data['history']['short_stack_adjustment'] = short_stack_adjustment
                        else:
                            # Reset to normal when stack is healthy
                            data['history']['short_stack_adjustment'] = 1.0
                        break
        
        # Log the round result
        self.log_state("round_result", {
            "winners": [{
                "name": winner.get("name", "Unknown"),
                "uuid": winner.get("uuid"),
                "stack": winner.get("stack")
            } for winner in winners],
            "community_cards": community_cards,
            "shown_hands": shown_hole_cards,
            "is_winner": is_winner
        })
        
        # Debug logs removed for cleaner display
        
        # Save history at the end of each round
        # First make a copy of the current round data
        current_round_copy = self.current_round_history.copy()
        
        # Then append it to the game history
        if current_round_copy and len(current_round_copy) > 0:
            self.game_history.append(current_round_copy)
            
            # Debug logs removed for cleaner display
        
        # Clear current round data for next round
        self.current_round_history = []
        
        # Update history in memory
        self.save_history()
        
        # Debug logs removed for cleaner display

    def log_action(self, action, street, hole_card, community_card, amount=None):
        """Log player action"""
        self.log_state("action", {
            "action": action,
            "street": street,
            "hole_card": hole_card,
            "community_card": community_card,
            "amount": amount,
            "result": "pending"
        })
        
    def get_opponent_stats(self):
        """Calculate and return opponent statistics, now with JSON format"""
        stats = []
        
        for uuid, data in self.opponents.items():
            if data['hands_observed'] < 1:
                continue  # Skip opponents we haven't observed
                
            # Add JsonHistory data to return - serialize into standard format
            # JSON history is already being updated throughout the game history tracking
                
            # Calculate VPIP (Voluntarily Put $ In Pot)
            vpip_actions = 0
            for action in data['preflop_actions']:
                # Only count voluntary actions (not blinds)
                if action['action'] in ['call', 'raise'] and not action.get('is_blind', False):
                    vpip_actions += 1
            
            vpip = (vpip_actions / data['hands_observed']) * 100 if data['hands_observed'] > 0 else 0
            
            # Calculate PFR (Pre-Flop Raise)
            pfr_actions = 0
            for action in data['preflop_actions']:
                if action['action'] == 'raise' and not action.get('is_blind', False):
                    pfr_actions += 1
            
            pfr = (pfr_actions / data['hands_observed']) * 100 if data['hands_observed'] > 0 else 0
            
            # Calculate fold to 5BB+
            fold_to_big_bet = 0
            big_bet_responses = [a for a in data['big_bet_responses'] if a in ['fold', 'call', 'raise']]
            if big_bet_responses:
                folds = big_bet_responses.count('fold')
                fold_to_big_bet = (folds / len(big_bet_responses)) * 100
            
            # Calculate call 5BB+
            call_big_bet = 0
            if big_bet_responses:
                calls = big_bet_responses.count('call')
                call_big_bet = (calls / len(big_bet_responses)) * 100
            
            # Calculate 3-bet percentage
            three_bet_pct = 0
            if data['three_bet_opportunities'] > 0:
                three_bet_pct = (data['three_bets_made'] / data['three_bet_opportunities']) * 100
            
            # Calculate aggression factor (Raises + Bets) / Calls
            raises = sum(1 for a in data['preflop_actions'] + data['postflop_actions'] if a['action'] == 'raise')
            calls = sum(1 for a in data['preflop_actions'] + data['postflop_actions'] if a['action'] == 'call')
            agg_factor = round(raises / calls, 1) if calls > 0 else 0
            
            # Calculate continuation bet percentage
            cont_bet_pct = 0
            postflop_streets = ['flop', 'turn', 'river']
            cont_bet_opps = 0
            cont_bets_made = 0
            
            # Count number of times they bet after raising preflop
            for i, action in enumerate(data['preflop_actions']):
                if action['action'] == 'raise':
                    # Check if they bet on the following street
                    for post_action in data['postflop_actions']:
                        if post_action['street'] == 'flop' and post_action['action'] in ['raise', 'bet']:
                            cont_bets_made += 1
                            break
                    cont_bet_opps += 1
            
            if cont_bet_opps > 0:
                cont_bet_pct = (cont_bets_made / cont_bet_opps) * 100
            
            # Determine most common position
            most_common_position = "Unknown"
            if data['position_history']:
                most_common_position = max(data['position_history'].items(), key=lambda x: x[1])[0]
            
            # Generate playing style assessment based on stats
            playing_style = []
            
            if vpip < 15:
                playing_style.append("Tight")
            elif vpip > 35:
                playing_style.append("Loose")
            else:
                playing_style.append("Medium")
                
            if pfr / max(vpip, 1) < 0.25:  # Less than 25% of VPIP hands are raised
                playing_style.append("Passive")
            elif pfr / max(vpip, 1) > 0.75:  # More than 75% of VPIP hands are raised
                playing_style.append("Aggressive")
            else:
                playing_style.append("Balanced")
                
            # Analyze position awareness
            position_play = ""
            button_vpip = 0
            early_vpip = 0
            button_actions = 0
            early_actions = 0
            
            for action in data['preflop_actions']:
                if action.get('position', '') in ['Button', 'Small Blind', 'Big Blind']:
                    button_actions += 1
                    if action['action'] in ['call', 'raise']:
                        button_vpip += 1
                elif action.get('position', '') in ['Early', 'UTG', 'UTG+1']:
                    early_actions += 1
                    if action['action'] in ['call', 'raise']:
                        early_vpip += 1
            
            button_vpip_pct = (button_vpip / button_actions * 100) if button_actions > 0 else 0
            early_vpip_pct = (early_vpip / early_actions * 100) if early_actions > 0 else 0
            
            # If button VPIP is significantly higher than early position VPIP, they're position aware
            if button_vpip_pct - early_vpip_pct > 20 and button_actions > 3 and early_actions > 3:
                position_play = "Position-aware"
            elif button_actions > 3 and early_actions > 3:
                position_play = "Position-unaware"
            
            if position_play:
                playing_style.append(position_play)
            
            # Determine if player is a calling station
            if vpip > 30 and pfr < 10 and calls > raises * 2:
                playing_style.append("Calling Station")
            
            # Determine if player is a maniac
            if vpip > 45 and pfr > 35:
                playing_style.append("Maniac")
            
            # Get advanced stats from detailed tracking
            advanced_stats = {}
            
            # Extract detailed preflop stats if available
            if 'preflop_details' in data:
                preflop_details = data['preflop_details']
                open_raise_pct = (preflop_details.get('open_raises', 0) / data['hands_observed']) * 100 if data['hands_observed'] > 0 else 0
                
                # Calculate average raise size
                avg_raise_size = 0
                if preflop_details.get('raise_sizes', []):
                    avg_raise_size = sum(preflop_details['raise_sizes']) / len(preflop_details['raise_sizes'])
                
                # Calculate positional tendencies
                position_stats = {}
                for pos, actions in preflop_details.get('position_actions', {}).items():
                    if actions:
                        fold_count = actions.count('fold')
                        call_count = actions.count('call')
                        raise_count = actions.count('raise')
                        total = len(actions)
                        
                        position_stats[pos] = {
                            'fold_pct': (fold_count / total) * 100 if total > 0 else 0,
                            'call_pct': (call_count / total) * 100 if total > 0 else 0,
                            'raise_pct': (raise_count / total) * 100 if total > 0 else 0,
                            'total_actions': total
                        }
                
                # Add to advanced stats
                advanced_stats.update({
                    'open_raise_pct': round(open_raise_pct, 1),
                    'avg_raise_size': round(avg_raise_size, 1),
                    'squeeze_play_count': preflop_details.get('squeeze_plays', 0),
                    'cold_call_count': preflop_details.get('cold_calls', 0),
                    'position_stats': position_stats
                })
            
            # Extract detailed postflop stats if available
            if 'postflop_details' in data:
                postflop_details = data['postflop_details']
                
                # Calculate check-raise frequency
                total_check_raises = sum(postflop_details.get('check_raise_counts', {}).values())
                
                # Calculate donk betting frequency
                total_donk_bets = sum(postflop_details.get('donk_bet_counts', {}).values())
                
                # Calculate delayed c-bet frequency
                total_delayed_cbets = sum(postflop_details.get('delayed_cbet_counts', {}).values())
                
                # Calculate betting patterns by street
                street_stats = {}
                for street, actions in postflop_details.get('streets', {}).items():
                    if actions:
                        fold_count = actions.count('fold')
                        call_count = actions.count('call')
                        raise_count = actions.count('raise')
                        bet_count = actions.count('bet')
                        check_count = sum(1 for a in actions if a == 'call' and postflop_details.get('bet_sizing', {}).get(street, []))
                        total = len(actions)
                        
                        street_stats[street] = {
                            'fold_pct': (fold_count / total) * 100 if total > 0 else 0,
                            'call_pct': (call_count / total) * 100 if total > 0 else 0,
                            'raise_pct': (raise_count / total) * 100 if total > 0 else 0,
                            'bet_pct': (bet_count / total) * 100 if total > 0 else 0,
                            'check_pct': (check_count / total) * 100 if total > 0 else 0,
                            'total_actions': total
                        }
                
                # Calculate average bet sizing as percentage of pot
                avg_bet_sizing = {}
                for street, bets in postflop_details.get('bet_sizing', {}).items():
                    if bets:
                        avg_ratio = sum(bet.get('pot_ratio', 0) for bet in bets) / len(bets)
                        avg_bet_sizing[street] = round(avg_ratio * 100, 1)  # As percentage of pot
                
                # Add to advanced stats
                advanced_stats.update({
                    'check_raise_count': total_check_raises,
                    'donk_bet_count': total_donk_bets,
                    'delayed_cbet_count': total_delayed_cbets,
                    'street_stats': street_stats,
                    'avg_bet_sizing': avg_bet_sizing
                })
            
            # Generate automatic notes based on detailed stats
            auto_notes = []
            
            # Basic stat-based notes
            if vpip < 10 and data['hands_observed'] > 10:
                auto_notes.append("Very tight player, likely only playing premium hands")
            elif vpip > 50 and data['hands_observed'] > 10:
                auto_notes.append("Extremely loose player, playing many weak hands")
                
            if fold_to_big_bet > 80 and len(big_bet_responses) > 3:
                auto_notes.append("Folds to big bets frequently, consider bluffing")
            elif fold_to_big_bet < 20 and len(big_bet_responses) > 3:
                auto_notes.append("Rarely folds to big bets, avoid bluffing")
                
            if agg_factor > 3:
                auto_notes.append("Highly aggressive, raises frequently")
            elif agg_factor < 0.5:
                auto_notes.append("Very passive, mostly calls")
                
            if three_bet_pct > 15 and data['three_bet_opportunities'] > 5:
                auto_notes.append("Frequent 3-bettor, be careful raising into them")
                
            if cont_bet_pct > 80 and cont_bet_opps > 3:
                auto_notes.append("Almost always c-bets the flop")
            elif cont_bet_pct < 30 and cont_bet_opps > 3:
                auto_notes.append("Rarely c-bets, likely check-folding when they miss")
            
            # Advanced stat-based notes
            if 'open_raise_pct' in advanced_stats and advanced_stats['open_raise_pct'] > 30:
                auto_notes.append("Frequently opens with raises, likely steal attempts in late position")
            
            if 'check_raise_count' in advanced_stats and advanced_stats['check_raise_count'] >= 3:
                auto_notes.append("Uses check-raise frequently, be cautious when betting into them")
            
            if 'donk_bet_count' in advanced_stats and advanced_stats['donk_bet_count'] >= 3:
                auto_notes.append("Makes donk bets when they hit a strong hand or as a bluff")
            
            if 'delayed_cbet_count' in advanced_stats and advanced_stats['delayed_cbet_count'] >= 2:
                auto_notes.append("Uses delayed c-bets on turn/river, may be trapping with strong hands")
            
            if 'avg_bet_sizing' in advanced_stats:
                flop_sizing = advanced_stats['avg_bet_sizing'].get('flop', 0)
                if flop_sizing > 100:  # Over pot-sized bets
                    auto_notes.append("Makes large over-pot bets on flop, often polarized to very strong hands or bluffs")
                elif flop_sizing < 50:  # Small bets
                    auto_notes.append("Makes small bets on flop, likely for value or as a blocking bet")
            
            if 'position_stats' in advanced_stats:
                btn_stats = advanced_stats['position_stats'].get('Button', {})
                if btn_stats.get('raise_pct', 0) > 60 and btn_stats.get('total_actions', 0) > 5:
                    auto_notes.append("Aggressive button stealer, defends less when facing resistance")
            
            if 'squeeze_play_count' in advanced_stats and advanced_stats['squeeze_play_count'] >= 2:
                auto_notes.append("Uses squeeze plays when others are entering the pot")
            
            # Add any data-generated notes to existing notes
            all_notes = data['notes'] + auto_notes
            
            # Create JSON-compatible opponent stats output
            opponent_stats = {
                'uuid': uuid,
                'player_name': data['name'],
                'position': most_common_position,
                'hands': data['hands_observed'],
                'vpip': round(vpip, 1),
                'pfr': round(pfr, 1),
                'fold_to_5bb': round(fold_to_big_bet, 1),
                'call_5bb': round(call_big_bet, 1),
                'threeBet': round(three_bet_pct, 1),
                'aggression_factor': agg_factor,
                'continuation_bet': round(cont_bet_pct, 1),
                'playing_style': ' '.join(playing_style),
                'notes': all_notes,
                'advanced_stats': advanced_stats,  # Include all advanced stats
                # Add extra stats for UI display
                'open_raise': advanced_stats.get('open_raise_pct', 0),
                'check_raise': advanced_stats.get('check_raise_count', 0),
                'donk_bet': advanced_stats.get('donk_bet_count', 0), 
                'squeeze_play': advanced_stats.get('squeeze_play_count', 0),
                'cold_call': advanced_stats.get('cold_call_count', 0),
                # Include the JSON formatted history
                'history': data.get('history', {}),
                # Add stack info
                'stack': data.get('stack', 100),
                'position': most_common_position
            }
            
            # Add to stats
            stats.append(opponent_stats)
            
            # Debug output removed for cleaner display
        
        return stats