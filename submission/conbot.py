import random
from pypokerengine.players import BasePokerPlayer
from pypokerengine.utils.card_utils import estimate_hole_card_win_rate
from pypokerengine.api.emulator import Emulator

# Notes
# All cards follow this format: Suit + Rank : 4 of Hearts = 4H, 10 of Spades = ST [2,3,4,5,6,7,8,9,T,J,Q,K,A] [S,C,D,H]

NB_SIMULATION = 100  # Number of monte carlo simulations for win rate estimation

def setup_ai():
    return ConservativeBot()

class ConservativeBot(BasePokerPlayer):  # Do not forget to make parent class as "BasePokerPlayer"

    def __init__(self):
        self.confidence_threshold = 0.7  # High confidence threshold
        self.aggression_factor = 0.3     # Reduced aggression (was 0.3)
        self.bluff_threshold = 0.05      # Reduced bluffing (was 0.1)
        self.position_weights = {        # Value of position (late positions are better)
            'early': 0.8,
            'middle': 1.0,
            'late': 1.2,
            'dealer': 1.3
        }
        self.hand_history = []           # Track decisions made
        self.uuid = None
        self.my_raise_this_round = False  # Track if we've raised this betting round
        self.committed_amount = 0         # Track how much we've invested in current hand

    #  we define the logic to make an action through this method. (so this method would be the core of your AI)
    def declare_action(self, valid_actions, hole_card, round_state):
        # Extract essential info
        community_card = round_state['community_card']
        street = round_state['street']
        pot = round_state['pot']['main']['amount']
        call_amount = valid_actions[1]['amount']
        seats = round_state.get('seats', [])  # Added .get() to prevent unbound error
        valid_actions[2]['amount']['max'] //= 2
        # Quick check for can check/fold scenarios
        if call_amount == 0:
            return 'call', 0  # Always check when possible

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
        except:
            pass
        return my_pos

    def _handle_preflop(self, valid_actions, hole_card, my_pos, call_amount, pot):
        """Handle preflop decision making"""
        ranks = [card[1] for card in hole_card]
        suits = [card[0] for card in hole_card]
        is_pair = ranks[0] == ranks[1]
        is_suited = suits[0] == suits[1]

        # Premium hand check
        premium_hand = False
        if is_pair and ranks[0] in ['A', 'K', 'Q', 'J', 'T']:
            premium_hand = True
        elif is_suited and all(r in ['A', 'K', 'Q', 'J', 'T'] for r in ranks):
            premium_hand = True
        elif 'A' in ranks and any(r in ['K', 'Q', 'J', 'T'] for r in ranks):
            premium_hand = True

        if premium_hand:
            # Raise with premium hands but with smaller amounts
            if valid_actions[2]['amount']['min'] != -1:
                # Reduced raise size from 2x min to 1.3x min
                raise_amount = min(valid_actions[2]['amount']['min'] * 1.3, valid_actions[2]['amount']['max'])
                raise_amount = int(raise_amount)  # Ensure integer amount
                self.my_raise_this_round = True
                return 'raise', raise_amount
            return 'call', call_amount

        # Play more hands in late position
        if my_pos in ['late', 'dealer']:
            return 'call', call_amount

        # Fold weak hands out of position, but only if we haven't invested much
        if self.committed_amount <= pot * 0.1:
            return 'fold', 0
        else:
            return 'call', call_amount  # Continue if we've already invested

    def _handle_postflop(self, valid_actions, hole_card, community_card, seats,
                        position_value, street, pot, call_amount):
        """Handle postflop decision making"""
        # Simplified postflop strategy - use fewer simulations
        active_players = len([p for p in seats if p['state'] == 'participating'])
        win_rate = estimate_hole_card_win_rate(
            nb_simulation=20,  # Reduced from 100
            nb_player=active_players,
            hole_card=hole_card,
            community_card=community_card
        )

        # Adjust win rate based on position
        win_rate *= position_value

        # If we've already raised this round, be less likely to fold
        if self.my_raise_this_round and win_rate > 0.3:
            return 'call', call_amount

        # If we've committed a significant amount to the pot, be more sticky
        pot_committed_ratio = self.committed_amount / pot if pot > 0 else 0
        if pot_committed_ratio > 0.2:
            # Reduce our folding threshold based on how much we've committed
            win_rate_adjustment = min(0.2, pot_committed_ratio)
            win_rate += win_rate_adjustment

        # Basic strategy
        if win_rate > 0.7:  # Strong hand
            if valid_actions[2]['amount']['min'] != -1:
                # Reduced raise size from pot/2 to pot/3
                raise_amount = min(pot // 3, valid_actions[2]['amount']['max'])
                raise_amount = max(raise_amount, valid_actions[2]['amount']['min'])
                self.my_raise_this_round = True
                return 'raise', raise_amount
            return 'call', call_amount
        elif win_rate > 0.5:  # Decent hand
            return 'call', call_amount
        else:  # Weak hand
            # Calculate pot odds for a more informed decision
            pot_odds = 0
            if pot > 0 and call_amount > 0:
                pot_odds = call_amount / (pot + call_amount)

            # If we've already raised or committed a lot, be more willing to call
            if self.my_raise_this_round or self.committed_amount > pot * 0.15:
                pot_odds -= 0.1  # Make pot odds more favorable by reducing the threshold

            if win_rate > pot_odds:
                return 'call', call_amount

            # Even if win rate doesn't justify continuing, consider pot commitment
            if self.committed_amount > pot * 0.25:  # If we've committed >25% of pot
                return 'call', call_amount

            return 'fold', 0

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

    def receive_street_start_message(self, street, round_state):
        # Reset raise tracking on new betting round
        self.my_raise_this_round = False

    def receive_game_update_message(self, new_action, round_state):
        # Track opponent actions to build a model
        if new_action['player_uuid'] != self.uuid:
            self.hand_history.append(new_action)
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

        ranks = [card[1] for card in hole_card]
        suits = [card[0] for card in hole_card]
        is_pair = ranks[0] == ranks[1]
        is_suited = suits[0] == suits[1]

        # High pairs
        if is_pair and ranks[0] in ['A', 'K', 'Q', 'J', 'T']:
            return True
        # High suited cards
        if is_suited and all(r in ['A', 'K', 'Q', 'J', 'T'] for r in ranks):
            return True
        # Ace with high kicker
        if 'A' in ranks and any(r in ['K', 'Q', 'J', 'T'] for r in ranks):
            return True
        return False

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

        # Calculate raise amount (reduced from 50-100% to 25-50% of pot)
        raise_amount = valid_actions[2]['amount']['min']
        pot_raise = int(pot * (0.25 + 0.25 * random.random()))

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
                nb_simulation=NB_SIMULATION // 2,  # Use fewer simulations for speed
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

    def receive_game_start_message(self, game_info):
        self.uuid = game_info['player_uuid']
        self.action_history = {}

    def receive_round_start_message(self, round_count, hole_card, seats):
        self.hole_card = hole_card
        for seat in seats:
            player_id = seat['uuid']
            if player_id not in self.action_history:
                self.action_history[player_id] = []

    def receive_street_start_message(self, street, round_state):
        self.current_street = street

    def receive_game_update_message(self, new_action, round_state):
        player_uuid = new_action['player_uuid']
        if player_uuid != self.uuid and self.current_street is not None:
            self.action_history[player_uuid].append({
                'action': new_action['action'],
                'amount': new_action['amount'],
                'street': self.current_street
            })

            # Record fold actions specifically
            if new_action['action'] == 'fold':
                self.fold_history.append({
                    'player': player_uuid,
                    'street': self.current_street,
                    'pot': round_state['pot']['main']['amount']
                })

    def receive_round_result_message(self, winners, hand_info, round_state):
        # Reset per-round tracking
        self.fold_history = []
