# mapping.py
import ast
import re

class PokerLogMapper:
    """
    Translates structured PyPokerGUI log entries into natural language descriptions.
    (Slightly adapted to work directly with game engine messages)
    """

    def __init__(self, bot_name="JasperBot"):
        self.player_map = {}  # Stores UUID -> Name mapping
        self.bot_uuid = None
        self.bot_name = bot_name # Store the name of our bot to identify its hole cards
        self.current_street = None
        self.small_blind_amount = 0
        self.my_hole_cards = []
        self.last_round_state = {} # Store last known state for context

    def _update_player_map(self, seats_data):
        """Updates the internal player map from seats data."""
        if not isinstance(seats_data, list):
            return
        for player in seats_data:
            if isinstance(player, dict) and 'uuid' in player and 'name' in player:
                # Store player UUID mapping regardless of state
                self.player_map[player['uuid']] = player['name']
                if player['name'] == self.bot_name:
                    self.bot_uuid = player['uuid']
                
                # Store special status for all-in or folded players
                if 'state' in player:
                    player_state = player.get('state', '').lower()
                    # Add state to player mapping for folded/all-in players to improve tracking

    def _get_player_name(self, uuid):
        """Gets player name from UUID, defaults to UUID if not found."""
        # Ensure uuid is string for lookup
        uuid_str = str(uuid)
        return self.player_map.get(uuid_str, f"Player {uuid_str}")

    def _format_cards(self, cards):
        """Formats a list of cards into a readable string with proper poker notation.
        Converts from 'SuitRank' format (where S is suit and R is rank) to standard 'Rs' format.
        For example, converts 'HK' to 'Kh', 'DT' to 'Td', etc."""
        if not cards:
            return "No cards"
        
        # Convert each card to proper poker notation (lowercase suits)
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
                
        return ", ".join(formatted_cards)

    def translate_game_start(self, game_info):
        """Translates game configuration."""
        if not isinstance(game_info, dict):
            return "Could not parse game configuration."

        # Update player map from initial seats if available in rule info (might not be)
        # Usually updated in round_start
        # self._update_player_map(game_info.get('seats', []))

        lines = ["--- New Game Starting ---"]
        lines.append(f"Number of players: {game_info.get('player_num', 'N/A')}")
        rule = game_info.get('rule', {})
        lines.append(f"Max rounds: {rule.get('max_round', 'N/A')}")
        lines.append(f"Initial small blind: {rule.get('small_blind_amount', 'N/A')}")
        lines.append(f"Initial ante: {rule.get('ante', 'N/A')}")
        # lines.append(f"Blind structure: {rule.get('blind_structure', 'N/A')}") # Can be verbose
        return "\n".join(lines)

    def translate_round_start(self, round_count, hole_card, seats):
        """Translates the start of a new round."""
        self._update_player_map(seats) # Ensure map is updated at start of round
        self.my_hole_cards = hole_card if hole_card else []
        self.current_street = None # Reset street
        self.last_round_state = {} # Reset state context

        lines = [f"\n--- Starting Round {round_count} ---"]
        if self.bot_uuid is not None and hole_card:
             lines.append(f"{self.bot_name} receives hole cards: {self._format_cards(hole_card)}")
        elif hole_card: # Should only happen if bot_uuid wasn't found yet
             lines.append(f"Bot receives hole cards: {self._format_cards(hole_card)}")

        lines.append("Initial Stacks:")
        for player in seats:
             if isinstance(player, dict):
                 lines.append(f"  {self._get_player_name(player['uuid'])}: {player.get('stack', 'N/A')} ({player.get('state', '')})")
        return "\n".join(lines)


    def translate_street_start(self, street, round_state):
        """Translates the start of a betting street."""
        self.current_street = str(street).upper()
        self.last_round_state = round_state # Update state context
        self._update_player_map(round_state.get('seats', [])) # Keep map updated

        community = self._format_cards(round_state.get('community_card', []))
        pot_main = round_state.get('pot', {}).get('main', {}).get('amount', 0)
        side_pots = round_state.get('pot', {}).get('side', [])
        pot_total = pot_main + sum(p.get('amount', 0) for p in side_pots if isinstance(p, dict))

        lines = [f"\n--- Street Start: {self.current_street} ---"]
        if community != "No cards":
            lines.append(f"Community Cards: [{community}]")
        lines.append(f"Pot: {pot_total}")

        # Add info about whose turn it is
        next_player_uuid = round_state.get('next_player')
        if next_player_uuid is not None:
            next_player_name = self._get_player_name(next_player_uuid)
            # Only add "Next to act" line if player exists in player_map
            if next_player_name != f"Player {next_player_uuid}":
                lines.append(f"Next to act: {next_player_name}")
            else:
                # Don't show "Player not_found" message
                lines.append(f"Waiting for next action...")

        return "\n".join(lines)


    def translate_game_update(self, action, round_state):
        """Translates a player action and updates state."""
        self.last_round_state = round_state # Update state context before translating action
        self._update_player_map(round_state.get('seats', [])) # Keep map updated
        self.current_street = round_state.get('street', self.current_street).upper()
        self.small_blind_amount = round_state.get('small_blind_amount', self.small_blind_amount)

        if not isinstance(action, dict):
            return "Could not parse action."

        # Determine player UUID robustly
        player_uuid = action.get('player_uuid')
        if player_uuid is None and 'uuid' in action: # Handle blind/engine action format
            player_uuid = action['uuid']
        if player_uuid is None:
            return "Action received without player UUID."

        player_name = self._get_player_name(player_uuid)
        action_type = action.get('action', 'UNKNOWN').upper()
        amount = action.get('amount', 0)

        # Store action details before returning string (optional, for stateful logic)
        # self.last_action = action

        # Translate action to natural language
        if action_type == "FOLD":
            return f"  ACTION: {player_name} folds."
        elif action_type == "CALL":
            paid = action.get('paid', amount) # Use 'paid' if available
            # Check detection - more robust needed if严格required
            is_check = False
            if paid == 0 and self.current_street not in ['PREFLOP', None]:
                # Simple check: If last significant action wasn't a bet/raise, it's likely a check.
                history = self.last_round_state.get('action_histories', {}).get(self.current_street.lower(), [])
                if history:
                    # Find last non-check/non-fold action
                    last_meaningful_action = None
                    for act in reversed(history):
                        if act.get('action') not in ['CALL', 'FOLD'] or act.get('amount',0) > 0 :
                             # If the action dict itself is the last one, check if it's a bet/raise
                             if act is action: continue # don't compare to self if it's the last in history
                             last_meaningful_action = act
                             break
                    # If there was no prior bet/raise in this street's history, it's a check
                    if last_meaningful_action is None or last_meaningful_action.get('action') not in ['RAISE', 'BIGBLIND', 'SMALLBLIND']:
                       is_check = True
                    # Handle BB checking option preflop
                elif self.current_street == 'PREFLOP' and str(round_state.get('big_blind_pos')) == str(player_uuid):
                     # check if BB is calling 0 facing no raise
                     preflop_history = self.last_round_state.get('action_histories', {}).get('preflop', [])
                     bb_action_index = -1
                     is_raised = False
                     for idx, act in enumerate(preflop_history):
                         if act.get('uuid') == str(player_uuid) and act.get('action') == 'BIGBLIND':
                             bb_action_index = idx
                         if act.get('action') == 'RAISE':
                             is_raised = True
                             break
                     if not is_raised and paid==0: # BB option check
                        is_check = True

                # More direct check for check: amount is 0, paid is 0, not preflop blind completion
                if amount == 0 and paid == 0 and self.current_street != 'PREFLOP':
                     is_check = True # Override if explicitly amount=0, paid=0 post-flop

            if is_check:
                 return f"  ACTION: {player_name} checks."
            else:
                 # Distinguish completing SB/BB from a standard call
                 add_amount = action.get('add_amount')
                 if self.current_street == 'PREFLOP':
                      if str(round_state.get('small_blind_pos')) == str(player_uuid) and amount == round_state.get('small_blind_amount') * 2 and paid == round_state.get('small_blind_amount'):
                           return f"  ACTION: {player_name} completes small blind to {amount}."
                      if str(round_state.get('big_blind_pos')) == str(player_uuid) and paid == 0: # BB already paid
                           return f"  ACTION: {player_name} checks (Big Blind option)."


                 return f"  ACTION: {player_name} calls {paid}." # Use 'paid' amount

        elif action_type == "RAISE":
            paid = action.get('paid', amount)
            add_amount = action.get('add_amount')
            state = ""
            
            # Enhanced all-in detection
            player_seat = next((p for p in round_state.get('seats', []) if str(p.get('uuid')) == str(player_uuid)), None)
            
            # Check if player is all-in based on their final stack or state
            if player_seat and player_seat.get('stack', 1) == 0:
                state = " (all-in)"
            # Check if player's state explicitly indicates all-in
            elif player_seat and player_seat.get('state', '').lower() == 'allin':
                state = " (all-in)"
            # Additional check for all-in based on amount raised vs starting stack
            elif player_seat and action.get('amount', 0) >= player_seat.get('stack', 0) + paid:
                state = " (all-in)"
                
            # Format the output based on whether we have add_amount or not
            if add_amount is not None:
                return f"  ACTION: {player_name} raises by {add_amount} to {amount}{state}."
            else:
                return f"  ACTION: {player_name} raises to {amount}{state} (pays {paid})."

        elif action_type == "SMALLBLIND":
            return f"  ACTION: {player_name} posts small blind of {amount}."
        elif action_type == "BIGBLIND":
            return f"  ACTION: {player_name} posts big blind of {amount}."
        else:
            return f"  ACTION: Unknown action by {player_name}: {action_type} {amount}"


    def translate_round_result(self, winners, hand_info, round_state):
        """Translates the winner information and showdown."""
        self.last_round_state = round_state # Final state update
        self._update_player_map(round_state.get('seats', []))

        lines = ["\n--- Round End ---"]
        pot_main = round_state.get('pot', {}).get('main', {}).get('amount', 0)
        side_pots_info = round_state.get('pot', {}).get('side', [])
        total_pot = pot_main + sum(p.get('amount', 0) for p in side_pots_info if isinstance(p, dict))
        lines.append(f"Final Pot: {total_pot}")

        # --- Winner Declaration ---
        if not isinstance(winners, list) or not winners:
            lines.append("Could not determine winner.")
        elif len(winners) == 1:
            winner = winners[0]
            winner_name = self._get_player_name(winner['uuid'])
            lines.append(f"{winner_name} wins the pot.")
            lines.append(f"  Final stack: {winner.get('stack', 'N/A')}")
        else:
            lines.append("Multiple winners (split pot):")
            for winner in winners:
                winner_name = self._get_player_name(winner['uuid'])
                # Pot distribution logic is complex, just state they won part
                lines.append(f"  {winner_name} wins a portion. Final stack: {winner.get('stack', 'N/A')}")

        # --- Showdown ---
        if isinstance(hand_info, list) and hand_info:
            lines.append("\n--- Showdown ---")
            community = self._format_cards(round_state.get('community_card', []))
            lines.append(f"Board: [{community}]")

            # Create a map for faster lookup
            hand_info_map = {str(h.get('uuid')): h for h in hand_info if 'uuid' in h}

            # Process ALL players who were part of this hand, even if folded
            all_players = round_state.get('seats', [])
            
            shown_hands = False
            for player in all_players:
                uuid_str = str(player.get('uuid'))
                player_name = self._get_player_name(uuid_str)
                player_state = player.get('state', '').lower()
                player_hand_data = hand_info_map.get(uuid_str)
                
                # Only display hands for players who actually had cards
                # this avoids showing "Player not_found shows" errors
                if player_name == f"Player {uuid_str}":
                    continue
                    
                # For players in showdown with hand data
                if player_hand_data:
                    shown_hands = True
                    hand = player_hand_data.get('hand', {})
                    hand_cards = player_hand_data.get('hand_cards')  # Actual hole cards shown

                    # Use stored cards if log doesn't show them again (for our bot)
                    if not hand_cards and uuid_str == str(self.bot_uuid):
                        hand_cards = self.my_hole_cards

                    strength = hand.get('hand', {}).get('strength', 'N/A')

                    if hand_cards:
                        lines.append(f"  {player_name} shows {self._format_cards(hand_cards)} => {strength}")
                    elif strength != 'N/A':
                        lines.append(f"  {player_name} had {strength} (cards not shown/mucked).")
                # For folded players, show state
                elif player_state == 'folded':
                    # Skip trying to show cards for folded players
                    pass
                    
            if not shown_hands and not winners:
                lines.append("  (No cards shown - likely everyone folded before showdown)")
            elif not shown_hands and winners:
                lines.append("  (No cards shown - pot awarded without contest)")
        elif not winners:
            lines.append("(No winner information - likely error or game ended)")

        # Display final stacks for all players at the end of the round result
        lines.append("\nFinal Stacks for Round:")
        for player in round_state.get('seats', []):
            if isinstance(player, dict):
                player_uuid = player.get('uuid')
                player_name = self._get_player_name(player_uuid) 
                
                # Skip showing non-existent players (e.g., "Player not_found")
                if player_name == f"Player {player_uuid}":
                    continue
                    
                lines.append(f"  {player_name}: {player.get('stack', 'N/A')} ({player.get('state', '')})")


        return "\n".join(lines)