from pypokerengine.players import BasePokerPlayer
import torch
import numpy as np
import os
import gc
import time
from collections import namedtuple
from pypokerengine.engine.card import Card

RESOLVE_ITERATIONS = 10  # Reduced to save memory
DEPTH_LIMIT = 2
NORMALIZATION_FACTOR = 10.0

# Define action tuple for proper hashing
Action = namedtuple('Action', ['action', 'amount'])

# Pre-compute lookup tables for cards for faster indexing
RANKS = [str(n) for n in range(2, 10)] + ['T', 'J', 'Q', 'K', 'A']
SUITS = ['S', 'C', 'D', 'H'] 

# Full deck cards as strings for faster comparison
FULL_DECK_STRS = [s+r for s in SUITS for r in RANKS]

class StateRepresentation:
    """Memory-optimized poker state representation"""
    def __init__(self, pot, community_cards, hole_cards, depth=0, terminal=False):
        self.pot = pot
        # Store just the string representations
        self.community_cards = [str(card) for card in community_cards]
        self.hole_cards = [str(card) for card in hole_cards]
        self.depth = depth
        self.terminal = terminal
        self.hero_hand_index = self._fast_hand_index()
        
    def is_terminal(self):
        return self.terminal
    
    def to_features(self):
        """Convert state to feature vector, optimized for memory usage"""
        # Pre-allocate numpy array of exact size needed
        expected_cards = 4 if len(self.community_cards) > 3 else 3
        feature_size = 1 + (expected_cards * 52)  # pot + card one-hot encodings
        features = np.zeros(feature_size, dtype=np.float32)
        
        # Set pot value
        features[0] = self.pot / NORMALIZATION_FACTOR
        
        # Set community card features efficiently
        for i, card_str in enumerate(self.community_cards):
            if i >= expected_cards:
                break
            try:
                # Find index in FULL_DECK_STRS
                card_idx = FULL_DECK_STRS.index(card_str)
                # Set the corresponding position in the feature vector
                features[1 + (i * 52) + card_idx] = 1.0
            except ValueError:
                pass
                
        return features
    
    def _fast_hand_index(self):
        """Calculate hand index without generating combinations"""
        if len(self.hole_cards) != 2:
            return 0
        
        # Convert cards to canonical form for comparison
        canonical_hole = sorted(self.hole_cards)
        
        # Get cards not in community
        available_strs = [card for card in FULL_DECK_STRS if card not in self.community_cards]
        
        # Check if our hole cards are among available cards
        if canonical_hole[0] not in available_strs or canonical_hole[1] not in available_strs:
            return 0
            
        # Calculate index using combinatorial rank
        idx1 = available_strs.index(canonical_hole[0])
        idx2 = available_strs.index(canonical_hole[1])
        
        if idx2 < idx1:
            idx1, idx2 = idx2, idx1
            
        # Use combinatorial formula to find position
        return idx1 * (len(available_strs) - idx1 - 1) // 2 + (idx2 - idx1 - 1)
    
    def copy(self):
        return StateRepresentation(
            self.pot, 
            self.community_cards.copy(),
            self.hole_cards,
            self.depth,
            self.terminal
        )

class DeepStackAgent(BasePokerPlayer):
    def __init__(self):
        """Initialize the DeepStack agent"""
        self.debug = False  # Disable debug output to reduce memory usage
        self.flop_model = None
        self.turn_model = None
        
    def setup_models(self):
        """Load models if they haven't been loaded yet"""
        if self.flop_model is not None and self.turn_model is not None:
            return  # Models already loaded
            
        try:
            import torch
            from deepstack_model import create_flop_model, create_turn_model
            device = torch.device("cpu")  # Force CPU to avoid CUDA memory issues

            if self.flop_model is None:
                self.flop_model = create_flop_model(hidden_units=64)  # Smaller model
                self.flop_model.load_state_dict(
                    torch.load("./submission/models/flop_model.pth", map_location=device)
                )
                self.flop_model.eval()
                
            if self.turn_model is None:
                self.turn_model = create_turn_model(hidden_units=64)  # Smaller model
                self.turn_model.load_state_dict(
                    torch.load("./submission/models/turn_model.pth", map_location=device)
                )
                self.turn_model.eval()
                
            # Use half-precision to reduce memory usage
            if hasattr(torch, 'float16'):
                self.flop_model = self.flop_model.half()
                self.turn_model = self.turn_model.half()
                
        except Exception as e:
            if self.debug:
                print(f"Error loading models: {e}")
            self.flop_model = None
            self.turn_model = None

    def declare_action(self, valid_actions, hole_card, round_state):
        """Memory-optimized action declaration"""
        # Make sure models are loaded
        self.setup_models()
        
        # Encode current state
        state_repr = self._encode_state(round_state, hole_card)
        
        # Choose model based on number of community cards
        num_community = len(round_state['community_card'])
        model = self.flop_model if num_community <= 3 else self.turn_model
        
        if model is None:
            # Simple heuristic strategy if model not available
            action_prob = np.random.random()
            if action_prob < 0.1:
                return "fold", 0
            elif action_prob < 0.8:
                return "call", valid_actions[1]["amount"]
            else:
                raise_action = valid_actions[2]
                min_amount = raise_action["amount"]["min"]
                max_amount = raise_action["amount"]["max"]
                return "raise", np.random.randint(min_amount, max_amount)
        
        # Get best action
        best_action = self._resolve_action(state_repr, valid_actions, model)
        
        # Force garbage collection to free memory
        gc.collect()
        
        return best_action.action, best_action.amount

    def _resolve_action(self, state_repr, valid_actions, model):
        """Memory-efficient action resolution"""
        # Create abstract actions
        actions_to_consider = self._abstract_actions(valid_actions, state_repr.pot)
        
        # Prepare action list and initial probabilities
        action_list = list(actions_to_consider)
        action_names = [a.action for a in action_list]
        
        # Use numpy array for probabilities (more memory efficient)
        probabilities = np.zeros(len(action_list), dtype=np.float32)
        
        # Initialize with bias against folding
        for i, action in enumerate(action_list):
            if action.action == "fold":
                probabilities[i] = 0.1
            elif action.action == "call":
                probabilities[i] = 0.4
            else:
                probabilities[i] = 0.5
        
        # Normalize
        probabilities /= np.sum(probabilities)
        
        # Get features once, outside the loop
        features = state_repr.to_features()
        
        # Time limit
        start_time = time.time()
        max_time = 0.5  # Reduced time limit to avoid memory buildup
        
        try:
            # Run a limited number of iterations
            for _ in range(min(3, RESOLVE_ITERATIONS)):  # Maximum 3 iterations to save memory
                if time.time() - start_time > max_time:
                    break
                
                # Convert features to tensor
                features_tensor = torch.tensor([features], dtype=torch.float32)
                
                # Forward pass with memory cleanup
                with torch.no_grad():
                    output = model(features_tensor).cpu().numpy().flatten()
                    
                # Clean up tensor memory immediately
                del features_tensor
                torch.cuda.empty_cache() if torch.cuda.is_available() else None
                
                # Update probabilities
                for i, action in enumerate(action_list):
                    value = 0
                    if action.action == "fold":
                        value = -1
                    elif action.action == "call":
                        value = output[state_repr.hero_hand_index] if state_repr.hero_hand_index < len(output) else 0
                    else:
                        # Properly access namedtuple field
                        bonus = min(action.amount / max(1, state_repr.pot), 1.0)
                        value = output[min(state_repr.hero_hand_index, len(output)-1)] * (1.0 + bonus/2)
                    
                    probabilities[i] = max(0.01, value)
                
                # Normalize
                probabilities /= np.sum(probabilities)
                
        except Exception as e:
            if self.debug:
                print(f"Error in _resolve_action: {e}")
            # Default to call
            for i, action in enumerate(action_list):
                if action.action == "call":
                    probabilities[i] = 0.9
                else:
                    probabilities[i] = 0.05
        
        # Choose best action
        best_idx = np.argmax(probabilities)
        return action_list[best_idx]
    
    def _encode_state(self, round_state, hole_card):
        """Memory-efficient state encoding"""
        # Convert cards directly to Card objects only when needed
        hole_cards = [Card.from_str(card) for card in hole_card]
        community_cards = [Card.from_str(card) for card in round_state['community_card']]
        
        # Get pot size
        pot_amount = round_state['pot']['main']['amount']
        
        return StateRepresentation(pot_amount, community_cards, hole_cards)

    def _abstract_actions(self, valid_actions, pot):
        """Create abstract actions from valid actions"""
        actions = []
        
        # Add fold and call actions
        for act in valid_actions:
            if act["action"] == "fold":
                actions.append(Action(action="fold", amount=0))
            elif act["action"] == "call":
                actions.append(Action(action="call", amount=act["amount"]))
        
        # Add raise actions more efficiently
        raise_actions = [act for act in valid_actions if act["action"] == "raise"]
        if raise_actions:
            raise_action = raise_actions[0]
            min_amount = raise_action["amount"]["min"]
            max_amount = raise_action["amount"]["max"]
            
            # Add just a few raise sizes to consider (less memory)
            actions.append(Action(action="raise", amount=min_amount))
            
            # Only add pot-sized raise if significantly different
            if pot > min_amount * 1.5:
                pot_raise = min(pot, max_amount)
                actions.append(Action(action="raise", amount=pot_raise))
            
            # Add all-in only if significantly different
            if max_amount > pot * 1.5:
                actions.append(Action(action="raise", amount=max_amount))
        
        return actions
    
    # Required methods for PyPokerEngine integration - simplified to save memory
    def receive_game_start_message(self, game_info):
        self.setup_models()
    
    def receive_round_start_message(self, round_count, hole_card, seats):
        pass
    
    def receive_street_start_message(self, street, round_state):
        pass
    
    def receive_game_update_message(self, action, round_state):
        pass
    
    def receive_round_result_message(self, winners, hand_info, round_state):
        # Force garbage collection after each round
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()