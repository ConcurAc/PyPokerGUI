import random
from pypokerengine.players import BasePokerPlayer
from pypokerengine.utils.card_utils import estimate_hole_card_win_rate
from pypokerengine.api.emulator import Emulator
from functools import lru_cache

# Notes
# All cards follow this format: Suit + Rank : 4 of Hearts = 4H, 10 of Spades = ST [2,3,4,5,6,7,8,9,T,J,Q,K,A] [S,C,D,H]

NB_SIMULATION = 150  # Increased number of monte carlo simulations for win rate estimation

# Card ranks for easy comparison
CARD_RANKS = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}

def setup_ai():
    return SmartBot()

class SmartBot(BasePokerPlayer):  # Do not forget to make parent class as "BasePokerPlayer"

    def __init__(self):
        self.confidence_threshold = 0.7  # High confidence threshold
        self.aggression_factor = 0.4     # Slightly increased aggression
        self.bluff_threshold = 0.05      # Reduced bluffing (was 0.1)
        self.position_weights = {        # Value of position (late positions are better)
            'early': 0.8,
            'middle': 1.0,
            'late': 1.3,                 # Increased value for late position
            'dealer': 1.4                # Increased value for dealer position
        }
        self.hand_history = []           # Track decisions made
        self.opponent_patterns = {}      # Track opponent tendencies
        self.uuid = None
        self.my_raise_this_round = False  # Track if we've raised this betting round
        self.committed_amount = 0         # Track how much we've invested in current hand
        self.hand_strength_cache = {}     # Cache for hand strength calculations

    #  we define the logic to make an action through this method. (so this method would be the core of your AI)
    def declare_action(self, valid_actions, hole_card, round_state):
        # Extract essential info
        community_card = round_state['community_card']
        street = round_state['street']
        pot = round_state['pot']['main']['amount']
        call_amount = valid_actions[1]['amount']
        seats = round_state.get('seats', [])  # Added .get() to prevent unbound error
        # Ensure max raise isn't too aggressive
        valid_actions[2]['amount']['max'] = min(valid_actions[2]['amount']['max'],
                                               valid_actions[2]['amount']['max'] // 2 + pot // 3)

        # Quick check for can check/fold scenarios
        if call_amount == 0:
            # Sometimes probe with a small bet when we can check
            if street != 'preflop' and random.random() < 0.2 and self._is_premium_hand(hole_card):
                if valid_actions[2]['amount']['min'] != -1:
                    raise_amount = valid_actions[2]['amount']['min']
                    return 'raise', raise_amount
            return 'call', 0  # Check when possible

        # Get position (simplified)
        my_pos = self._get_preflop_position(round_state)  # Extract position logic to helper method
        position_value = self.position_weights[my_pos]

        # Calculate how much we've already invested in this pot
        my_seat = next((seat for seat in seats if seat['uuid'] == self.uuid), None)
        if my_seat:
            self.committed_amount = my_seat.get('stack_history', {}).get(street, 0)

        # Preflop strategy
        if street == 'preflop':
            return self._handle_preflop(valid_actions, hole_card, my_pos, call_amount, pot)

        # Postflop strategy
        return self._handle_postflop(valid_actions, hole_card, community_card, seats,
                               position_value, street, pot, call_amount)

    def _get_preflop_position(self, round_state):
        """Determine player's position for preflop play"""
        my_pos = 'early'
        try:
            seats = round_state['seats']
            dealer_btn = round_state['dealer_btn']
            active_players = [p for p in seats if p['state'] == 'participating']
            if len(active_players) <= 3:
                my_pos = 'late' if seats[dealer_btn]['uuid'] == self.uuid else 'early'
            else:
                my_idx = next((i for i, p in enumerate(seats) if p['uuid'] == self.uuid), -1)
                positions_from_dealer = (my_idx - dealer_btn) % len(active_players)
                if positions_from_dealer == 0:
                    my_pos = 'dealer'
                elif positions_from_dealer > 2 * len(active_players) / 3:
                    my_pos = 'late'
                elif positions_from_dealer > len(active_players) / 3:
                    my_pos = 'middle'
        except Exception:
            pass
        return my_pos

    def _hand_strength(self, hole_card):
        """Calculate static hand strength based on starting cards"""
        if not hole_card or len(hole_card) != 2:
            return 0

        # Convert hole cards to ranks and suits
        ranks = [card[1] for card in hole_card]
        suits = [card[0] for card in hole_card]
        rank_values = [CARD_RANKS.get(r, 0) for r in ranks]

        # Sort ranks by value (higher first)
        rank_values.sort(reverse=True)

        # Check for pairs
        is_pair = ranks[0] == ranks[1]
        is_suited = suits[0] == suits[1]

        # Premium pairs: AA, KK, QQ, JJ, TT
        if is_pair:
            pair_value = CARD_RANKS.get(ranks[0], 0)
            if pair_value >= 10:  # TT or better
                return 0.95 - (14 - pair_value) * 0.05  # AA=0.95, KK=0.90, etc
            return 0.5 + pair_value * 0.03  # Small pairs get lower scores

        # Suited hands
        if is_suited:
            # Broadway suited cards
            if all(CARD_RANKS.get(r, 0) >= 10 for r in ranks):
                return 0.85 - (14 - rank_values[0]) * 0.03

            # Suited connectors
            if abs(rank_values[0] - rank_values[1]) == 1:
                return 0.6 + rank_values[0] * 0.01

            # Suited ace
            if 'A' in ranks:
                kicker = rank_values[1] if ranks[0] == 'A' else rank_values[0]
                return 0.65 + kicker * 0.01

        # Offsuit hands
        # Broadway offsuit cards
        if all(CARD_RANKS.get(r, 0) >= 10 for r in ranks):
            return 0.7 - (14 - rank_values[0]) * 0.03

        # Offsuit ace
        if 'A' in ranks:
            kicker = rank_values[1] if ranks[0] == 'A' else rank_values[0]
            if kicker >= 10:  # AK, AQ, AJ, AT
                return 0.65 - (14 - kicker) * 0.02
            return 0.4 + kicker * 0.01

        # Connected cards
        if abs(rank_values[0] - rank_values[1]) == 1:
            return 0.4 + rank_values[0] * 0.01

        # Everything else
        return 0.2 + rank_values[0] * 0.01

    def _handle_preflop(self, valid_actions, hole_card, my_pos, call_amount, pot):
        """Handle preflop decision making"""
        # Use cached or calculate hand strength (0-1)
        hole_key = ''.join(sorted(hole_card))
        hand_strength = self.hand_strength_cache.get(hole_key)
        if hand_strength is None:
            hand_strength = self._hand_strength(hole_card)
            self.hand_strength_cache[hole_key] = hand_strength

        # Apply position adjustment
        position_factor = self.position_weights.get(my_pos, 1.0)
        adjusted_strength = hand_strength * position_factor

        # Premium hand check (simplified to use strength)
        premium_hand = hand_strength > 0.7

        # Calculate pot commitment ratio
        pot_commitment = self.committed_amount / pot if pot > 0 else 0

        # Calculate risk-reward ratio
        if call_amount > 0:
            risk_reward = call_amount / (pot + call_amount)
        else:
            risk_reward = 0

        # Decision logic
        if premium_hand:
            # Raise with premium hands
            if valid_actions[2]['amount']['min'] != -1:
                # Raise more with stronger hands
                raise_factor = 1.3 + hand_strength * 0.7
                raise_amount = min(valid_actions[2]['amount']['min'] * raise_factor,
                                  valid_actions[2]['amount']['max'])
                raise_amount = int(raise_amount)  # Ensure integer amount
                self.my_raise_this_round = True
                return 'raise', raise_amount
            return 'call', call_amount

        # Play more hands in late position
        if my_pos in ['late', 'dealer']:
            if adjusted_strength > 0.5:
                # Sometimes raise with decent hands in position
                if valid_actions[2]['amount']['min'] != -1 and random.random() < adjusted_strength * 0.3:
                    raise_amount = valid_actions[2]['amount']['min']
                    self.my_raise_this_round = True
                    return 'raise', raise_amount
            if adjusted_strength > 0.4 or call_amount == 0:
                return 'call', call_amount

        # More selective from early/middle position
        if adjusted_strength > 0.6 or (adjusted_strength > 0.5 and call_amount == 0):
            return 'call', call_amount

        # Fold weak hands out of position, but only if we haven't invested much
        if pot_commitment <= 0.1 and adjusted_strength < 0.45:
            return 'fold', 0
        elif adjusted_strength > risk_reward or call_amount == 0:
            return 'call', call_amount
        else:
            return 'fold', 0

    @lru_cache(maxsize=128)
    def _estimate_win_rate(self, hole_card_str, community_card_str, active_players):
        """Cached version of win rate estimation"""
        hole_card = hole_card_str.split(',')
        community_card = community_card_str.split(',') if community_card_str else []

        # For very obvious scenarios, avoid simulation
        # Royal flush check on board+hand (simplified)
        if len(community_card) >= 3:
            # If we have nuts, return high confidence
            # This is highly simplified - a real implementation would check actual hand strength
            if self._has_nuts(hole_card, community_card):
                return 0.95

        return estimate_hole_card_win_rate(
            nb_simulation=min(30, NB_SIMULATION // active_players),  # Dynamic simulation count
            nb_player=active_players,
            hole_card=hole_card,
            community_card=community_card
        )

    def _has_nuts(self, hole_card, community_card):
        """Simplified check if we have the nuts - only checks for royal flush possibility"""
        # This is a placeholder for a more complex hand analysis
        # In a real implementation, you'd check all possible hands given the board
        all_cards = hole_card + community_card
        if len(all_cards) < 5:
            return False

        # Check for royal flush possibility (very simplified)
        suits = [card[0] for card in all_cards]
        most_common_suit = max(set(suits), key=suits.count)
        suited_cards = [card for card in all_cards if card[0] == most_common_suit]

        if len(suited_cards) >= 5:
            ranks = [card[1] for card in suited_cards]
            if all(r in ranks for r in ['A', 'K', 'Q', 'J', 'T']):
                return True

        return False

    def _handle_postflop(self, valid_actions, hole_card, community_card, seats,
                        position_value, street, pot, call_amount):
        """Handle postflop decision making"""
        # Get active player count for win rate estimation
        active_players = len([p for p in seats if p['state'] == 'participating'])

        # Use cached win rate estimation for performance
        hole_card_str = ','.join(sorted(hole_card))
        community_card_str = ','.join(sorted(community_card))
        win_rate = self._estimate_win_rate(hole_card_str, community_card_str, active_players)

        # Adjust win rate based on position
        win_rate *= position_value

        # More aggressive on later streets when we have strong hands
        if street == 'river' and win_rate > 0.8:
            win_rate += 0.1
        elif street == 'turn' and win_rate > 0.7:
            win_rate += 0.05

        # Calculate pot odds
        pot_odds = call_amount / (pot + call_amount) if pot > 0 and call_amount > 0 else 0

        # Check for special conditions that can lead to immediate decisions
        if self._should_auto_call(win_rate, call_amount, street):
            return 'call', call_amount

        # Apply adjustments to win rate
        win_rate = self._adjust_win_rate(win_rate, hole_card, community_card, street, pot)

        # Make decision based on hand strength
        return self._make_decision(valid_actions, win_rate, pot_odds, pot, street)

    def _should_auto_call(self, win_rate, call_amount, street):
        """Determine if we should automatically call"""
        # If we've already raised this round, be less likely to fold
        if self.my_raise_this_round and win_rate > 0.3:
            return True
        return False

    def _adjust_win_rate(self, win_rate, hole_card, community_card, street, pot):
        """Apply various adjustments to the win rate"""
        # If we've committed a significant amount to the pot, be more sticky
        pot_committed_ratio = self.committed_amount / pot if pot > 0 else 0
        if pot_committed_ratio > 0.2:
            # Reduce our folding threshold based on how much we've committed
            win_rate_adjustment = min(0.2, pot_committed_ratio)
            win_rate += win_rate_adjustment

        # Semi-bluff calculations for drawing hands
        has_draw = self._has_drawing_hand(hole_card, community_card, street)
        if has_draw and street in ['flop', 'turn']:
            win_rate += 0.1  # Increase effective win rate for drawing hands

        return win_rate

    def _make_decision(self, valid_actions, win_rate, pot_odds, pot, street):
        """Make the final decision based on hand strength"""
        # Basic strategy
        if win_rate > 0.8:  # Very strong hand - be aggressive
            if valid_actions[2]['amount']['min'] != -1:
                # Raise more on later streets
                raise_factor = 0.5 if street == 'flop' else 0.75
                raise_amount = min(int(pot * raise_factor), valid_actions[2]['amount']['max'])
                raise_amount = max(raise_amount, valid_actions[2]['amount']['min'])
                self.my_raise_this_round = True
                return 'raise', raise_amount
            return 'call', valid_actions[1]['amount']

        elif win_rate > 0.6:  # Strong hand
            if valid_actions[2]['amount']['min'] != -1:
                # Standard raise
                raise_amount = min(pot // 3, valid_actions[2]['amount']['max'])
                raise_amount = max(raise_amount, valid_actions[2]['amount']['min'])
                self.my_raise_this_round = True
                return 'raise', raise_amount
            return 'call', valid_actions[1]['amount']

        elif win_rate > 0.5:  # Decent hand
            return 'call', valid_actions[1]['amount']

        # Weak hand logic
        return self._handle_weak_hand(valid_actions, win_rate, pot_odds, pot)

    def _handle_weak_hand(self, valid_actions, win_rate, pot_odds, pot):
        """Handle logic for weak hands"""
        call_amount = valid_actions[1]['amount']

        # If we've already raised or committed a lot, be more willing to call
        if self.my_raise_this_round or self.committed_amount > pot * 0.15:
            pot_odds -= 0.1  # Make pot odds more favorable by reducing the threshold

        if win_rate > pot_odds:
            return 'call', call_amount

        # Even if win rate doesn't justify continuing, consider pot commitment
        if self.committed_amount > pot * 0.25:  # If we've committed >25% of pot
            return 'call', call_amount

        # Occasionally bluff in position
        position_value = self.position_weights.get(self._get_preflop_position({}), 1.0)
        if position_value > 1.2 and random.random() < 0.1 and call_amount < pot * 0.2:
            return 'call', call_amount

        return 'fold', 0

    def _has_drawing_hand(self, hole_card, community_card, street):
        """Check if we have a drawing hand (flush or straight draw)"""
        if street == 'river' or len(community_card) < 3:
            return False

        all_cards = hole_card + community_card

        # Check for flush draw
        suits = [card[0] for card in all_cards]
        for suit in set(suits):
            if suits.count(suit) == 4:  # One card away from flush
                return True

        # Check for open-ended straight draw (simplified)
        ranks = sorted([CARD_RANKS.get(card[1], 0) for card in all_cards])
        # Look for 4 consecutive ranks
        for i in range(len(ranks) - 3):
            if ranks[i+3] - ranks[i] == 3 and len(set(ranks[i:i+4])) == 4:
                return True

        return False

    def receive_game_start_message(self, game_info):
        self.uuid = game_info['seats'][game_info['player_num']-1]['uuid']
        # Set up emulator for future simulations
        player_num = game_info["player_num"]
        max_round = game_info["rule"]["max_round"]
        small_blind_amount = game_info["rule"]["small_blind_amount"]
        ante_amount = game_info["rule"]["ante"]
        blind_structure = game_info["rule"]["blind_structure"]

        self.emulator = Emulator()
        self.emulator.set_game_rule(player_num, max_round, small_blind_amount, ante_amount)
        self.emulator.set_blind_structure(blind_structure)

        # Register player models for simulation
        for player_info in game_info["seats"]:
            self.emulator.register_player(player_info["uuid"], FoldObserverModel())

    def receive_round_start_message(self, round_count, hole_card, seats):
        self.hole_card = hole_card
        self.my_raise_this_round = False
        self.committed_amount = 0
        # Initialize opponent tracking for this round
        for seat in seats:
            if seat['uuid'] != self.uuid:
                if seat['uuid'] not in self.opponent_patterns:
                    self.opponent_patterns[seat['uuid']] = {
                        'aggression': 0.5,  # Initial neutral assessment
                        'fold_frequency': 0.5,
                        'actions': []
                    }

    def receive_street_start_message(self, street, round_state):
        # Reset raise tracking on new betting round
        self.my_raise_this_round = False

    def receive_game_update_message(self, new_action, round_state):
        # Track opponent actions to build a model
        if new_action['player_uuid'] != self.uuid:
            self.hand_history.append(new_action)

            # Update opponent patterns
            if new_action['player_uuid'] in self.opponent_patterns:
                player = self.opponent_patterns[new_action['player_uuid']]
                player['actions'].append(new_action)

                # Update aggression metric
                if new_action['action'] == 'raise':
                    player['aggression'] = min(0.9, player['aggression'] + 0.1)
                elif new_action['action'] == 'fold':
                    player['fold_frequency'] = min(0.9, player['fold_frequency'] + 0.1)
                    player['aggression'] = max(0.1, player['aggression'] - 0.05)
        else:
            # Track our own raises
            if new_action['action'] == 'raise':
                self.my_raise_this_round = True

            # Update committed amount
            if new_action['action'] in ['call', 'raise']:
                self.committed_amount += new_action['amount']

    def receive_round_result_message(self, winners, hand_info, round_state):
        # Reset tracking for next hand
        self.my_raise_this_round = False
        self.committed_amount = 0

        # Learn from results
        for winner in winners:
            if winner['uuid'] in self.opponent_patterns:
                player = self.opponent_patterns[winner['uuid']]
                # Winning players who were aggressive get positive reinforcement
                actions = [a['action'] for a in player['actions']]
                if 'raise' in actions:
                    player['aggression'] = min(0.9, player['aggression'] + 0.05)

    # Helper functions for decision making
    def _get_position(self, seats, dealer_btn):
        """Determine player's position at the table"""
        active_players = [p for p in seats if p['state'] == 'participating']
        num_players = len(active_players)

        if num_players <= 3:
            if seats[dealer_btn]['uuid'] == self.uuid:
                return 'dealer'
            else:
                return 'early' if seats[dealer_btn]['uuid'] != self.uuid else 'late'

        # Find my position relative to dealer
        my_idx = next((i for i, p in enumerate(seats) if p['uuid'] == self.uuid), -1)
        if my_idx == -1:
            return 'early'  # Default to early if not found

        positions_from_dealer = (my_idx - dealer_btn) % num_players

        if positions_from_dealer == 0:
            return 'dealer'
        elif positions_from_dealer < num_players / 3:
            return 'early'
        elif positions_from_dealer < 2 * num_players / 3:
            return 'middle'
        else:
            return 'late'

    def _is_premium_hand(self, hole_card):
        """Check if we have a premium starting hand"""
        if len(hole_card) != 2:
            return False

        hole_key = ''.join(sorted(hole_card))
        hand_strength = self.hand_strength_cache.get(hole_key)
        if hand_strength is None:
            hand_strength = self._hand_strength(hole_card)
            self.hand_strength_cache[hole_key] = hand_strength

        return hand_strength > 0.7

    def _should_bluff(self, win_rate, street, pot, position):
        """Determine if we should bluff based on various factors"""
        # Bluff more in late positions
        position_factor = 1.5 if position in ['late', 'dealer'] else 0.7

        # Bluff more in later streets with small pots
        street_factor = 1.0
        if street == 'turn':
            street_factor = 1.2
        elif street == 'river':
            street_factor = 1.5

        # Reduce bluffing with hands that have some equity
        equity_factor = 1.0 - win_rate

        bluff_probability = self.bluff_threshold * position_factor * street_factor * equity_factor
        return random.random() < bluff_probability

    def _make_aggressive_action(self, valid_actions, pot):
        """Make an aggressive play - raise or bet big"""
        if valid_actions[2]['amount']['min'] == -1:  # Can't raise
            return self.do_call(valid_actions)

        # Calculate raise amount (adjusted to 30-60% of pot)
        raise_amount = valid_actions[2]['amount']['min']
        pot_raise = int(pot * (0.3 + 0.3 * random.random()))

        if pot_raise > raise_amount:
            raise_amount = min(pot_raise, valid_actions[2]['amount']['max'])

        # Reduced all-in frequency from 5% to 2%
        if random.random() < 0.02:
            # Limit all-in to 80% of maximum to avoid true all-ins
            all_in_amount = int(valid_actions[2]['amount']['max'] * 0.8)
            all_in_amount = max(all_in_amount, valid_actions[2]['amount']['min'])
            return self.do_raise(valid_actions, all_in_amount)

        self.my_raise_this_round = True
        return self.do_raise(valid_actions, raise_amount)

    def _make_value_action(self, valid_actions, win_rate, pot_odds):
        """Make a value-oriented play"""
        if win_rate > pot_odds + 0.2:  # Good value
            # Sometimes raise for value
            if random.random() < win_rate * self.aggression_factor:
                if valid_actions[2]['amount']['min'] != -1:
                    # Just use minimum raise to be more conservative
                    raise_amount = valid_actions[2]['amount']['min']
                    self.my_raise_this_round = True
                    return self.do_raise(valid_actions, raise_amount)

            return self.do_call(valid_actions)
        elif win_rate > pot_odds:  # Marginal value
            return self.do_call(valid_actions)
        else:
            # If we've already raised this round, be reluctant to fold
            if self.my_raise_this_round:
                return self.do_call(valid_actions)
            return self.do_fold(valid_actions)

    def _make_conservative_action(self, valid_actions, win_rate, pot_odds):
        """Make a conservative play with marginal hands"""
        # Call only if we have the right pot odds
        if valid_actions[1]['amount'] == 0:  # Can check
            return self.do_call(valid_actions)

        if win_rate > pot_odds:
            return self.do_call(valid_actions)
        else:
            # Consider pot commitment and previous raises
            if self.my_raise_this_round or self.committed_amount > 0:
                # If we've already raised or committed chips, be more reluctant to fold
                return self.do_call(valid_actions)
            return self.do_fold(valid_actions)

    def _make_positional_action(self, valid_actions, win_rate, pot_odds):
        """Make a play exploiting positional advantage"""
        # In position, we can play more hands
        adjusted_win_rate = win_rate * 1.2

        if valid_actions[1]['amount'] == 0:  # Can check
            # Reduce semi-bluff raising
            if random.random() < (self.aggression_factor * 0.7) and valid_actions[2]['amount']['min'] != -1:
                raise_amount = valid_actions[2]['amount']['min']
                self.my_raise_this_round = True
                return self.do_raise(valid_actions, raise_amount)
            return self.do_call(valid_actions)

        if adjusted_win_rate > pot_odds:
            return self.do_call(valid_actions)
        else:
            # If we've already raised, continue with the hand
            if self.my_raise_this_round:
                return self.do_call(valid_actions)
            return self.do_fold(valid_actions)

    def _make_bluff(self, valid_actions):
        """Make a bluff"""
        # If we can raise, make a smaller raise to sell the bluff
        if valid_actions[2]['amount']['min'] != -1:
            # Reduced multiplier from 2.5x to 1.5x minimum
            raise_amount = max(valid_actions[2]['amount']['min'],
                              int(valid_actions[2]['amount']['min'] * 1.5))
            raise_amount = min(raise_amount, valid_actions[2]['amount']['max'])
            self.my_raise_this_round = True
            return self.do_raise(valid_actions, raise_amount)

        # If we can only call or fold, usually better to fold as a bluff wouldn't make sense
        if valid_actions[1]['amount'] == 0:  # Can check
            return self.do_call(valid_actions)
        else:
            return self.do_fold(valid_actions)

    # Helper functions for actions
    def do_fold(self, valid_actions):
        action_info = valid_actions[0]
        amount = action_info["amount"]
        return action_info['action'], amount

    def do_call(self, valid_actions):
        action_info = valid_actions[1]
        amount = action_info["amount"]
        return action_info['action'], amount

    def do_raise(self, valid_actions, raise_amount):
        action_info = valid_actions[2]
        amount = max(action_info['amount']['min'], raise_amount)
        amount = min(amount, action_info['amount']['max'])
        return action_info['action'], amount

    def do_all_in(self, valid_actions):
        action_info = valid_actions[2]
        # Reduce all-in size to 90% of maximum to be more conservative
        amount = int(action_info['amount']['max'] * 0.9)
        amount = max(amount, action_info['amount']['min'])
        return action_info['action'], amount

# Advanced player model for emulator
class FoldObserverModel(BasePokerPlayer):
    def __init__(self):
        self.win_rate_threshold = 0.5
        self.aggression_factor = 0.2
        self.fold_history = []
        self.action_history = {}
        self.uuid = None
        self.current_street = None

    def declare_action(self, valid_actions, hole_card, round_state):
        # Basic strategy: fold weak hands, call/check medium hands, raise strong hands
        community_card = round_state['community_card']

        # Estimate hand strength
        win_rate = 0.0
        if hole_card:
            win_rate = estimate_hole_card_win_rate(
                nb_simulation=NB_SIMULATION // 4,  # Use fewer simulations for speed
                nb_player=len(round_state['seats']),
                hole_card=hole_card,
                community_card=community_card
            )

        # Determine action based on hand strength
        if win_rate > self.win_rate_threshold + 0.2:
            # Strong hand - raise
            if valid_actions[2]['amount']['min'] != -1:
                raise_amount = valid_actions[2]['amount']['min']
                return valid_actions[2]['action'], raise_amount
            else:
                return valid_actions[1]['action'], valid_actions[1]['amount']
        elif win_rate > self.win_rate_threshold:
            # Medium hand - call/check
            return valid_actions[1]['action'], valid_actions[1]['amount']
        else:
            # Weak hand - fold if there's a bet, otherwise check
            if valid_actions[1]['amount'] > 0:
                return valid_actions[0]['action'], valid_actions[0]['amount']
            else:
                return valid_actions[1]['action'], valid_actions[1]['amount']
