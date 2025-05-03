
from enum import Enum

from cards import Card

class Hand(Enum):
    """Enum class defining poker hand rankings from weakest to strongest."""
    HIGH_CARD = 0       # No matching cards
    PAIR = 1            # Two cards of same value
    TWO_PAIR = 2        # Two different pairs
    THREE_OF_A_KIND = 3 # Three cards of same value
    STRAIGHT = 4        # Five cards in sequence
    FLUSH = 5           # Five cards of same suit
    FULL_HOUSE = 6      # Three of a kind plus a pair
    FOUR_OF_A_KIND = 7  # Four cards of same value
    STRAIGHT_FLUSH = 8  # Straight of same suit
    ROYAL_FLUSH = 9     # Ace-high straight flush
    def with_cards(self, cards):
        self.cards = cards
        return self

def get_best_hand(cards):
    """
    Determine the highest poker hand ranking for a list of cards.

    Args:
        cards (list): A list of Card objects

    Returns:
        tuple: (Hand ranking enum, list of relevant cards for tiebreaking)
    """
    consecutive = get_consecutive_cards(cards)
    same = get_same_cards(cards)

    royal_flush = get_royal_flush(consecutive)
    if royal_flush:
        return Hand.ROYAL_FLUSH.with_cards(royal_flush)
    straight_flush = get_straight_flush(consecutive)
    if straight_flush:
        return Hand.STRAIGHT_FLUSH.with_cards(straight_flush)
    four_of_a_kind = get_four_of_a_kind(same)
    if four_of_a_kind:
        return Hand.FOUR_OF_A_KIND.with_cards(four_of_a_kind)
    full_house = get_full_house(same)
    if full_house:
        return Hand.FULL_HOUSE.with_cards(full_house)
    three_of_a_kind = get_three_of_a_kind(same)
    if three_of_a_kind:
        return Hand.THREE_OF_A_KIND.with_cards(three_of_a_kind)
    two_pair = get_two_pair(same)
    if two_pair:
        return Hand.TWO_PAIR.with_cards(two_pair)
    pair = get_pair(same)
    if pair:
        return Hand.PAIR.with_cards(pair)
    return Hand.HIGH_CARD, get_high_card(cards)

def get_royal_flush(consecutive: list[list[Card]]) -> list[Card]:
    for cards in consecutive:
        if len(cards) < 5:
            continue
        royal_flush_values = {
            Card.Value.ACE,
            Card.Value.KING,
            Card.Value.QUEEN,
            Card.Value.JACK,
            Card.Value.TEN
        }

        values = set(card.value for card in cards)
        if royal_flush_values.issubset(values):
            suit_dict = {}

            for card in cards:
                if card.value in royal_flush_values:
                    suit_dict[card.suit] = suit_dict.get(card.suit, 0) + 1
            for s, count in suit_dict.items():
                if count >= 5:
                    return list(filter(lambda card: card.value in royal_flush_values and card.suit == s, cards))
    return []

def get_straight_flush(consecutive: list[list[Card]]) -> list[Card]:
    """Get straight flush cards."""
    for cards in consecutive:
        if len(cards) < 5:
            continue
        # Group cards by suit
        suit_groups = {}
        for card in cards:
            if card.suit not in suit_groups:
                suit_groups[card.suit] = []
            suit_groups[card.suit].append(card)
    return []

def get_flush(cards: list[Card]) -> list[Card]:
    """Get flush cards."""
    # Group cards by suit
    suit_groups = {}
    for card in cards:
        if card.suit not in suit_groups:
            suit_groups[card.suit] = []
        suit_groups[card.suit].append(card)

    # Find a suit with 5 or more cards
    for suit, suited_cards in suit_groups.items():
        if len(suited_cards) >= 5:
            # Return the 5 highest cards of that suit
            return sorted(suited_cards, key=lambda card: card.value.value)[len(suited_cards) - 5:]
    return []

def get_straight(consecutive: list[list[Card]]) -> list[Card]:
    """Get straight cards."""
    for cards in consecutive:
        if len(cards) >= 5:
            return cards[len(cards) - 5:]
    return []

def get_four_of_a_kind(same: list[list[Card]]) -> list[Card]:
    """Get four of a kind cards."""
    for cards in same:
        if len(cards) >= 4:
            return cards[len(cards) - 4:]
    return []

def get_full_house(same: list[list[Card]]) -> list[Card]:
    """Get three of a kind cards."""
    three_of_a_kind_index = None
    pair_index = None
    for i in range(len(same)):
        if len(same[i]) >= 3:
            if not three_of_a_kind_index:
                three_of_a_kind_index = i
        elif len(same[i]) >= 2:
            if not pair_index:
                pair_index = i
        if three_of_a_kind_index and pair_index:
            three_of_a_kind = same[three_of_a_kind_index]
            pair = same[pair_index]
            return three_of_a_kind[len(three_of_a_kind) - 3:] + pair[len(pair) - 2:]
    return []

def get_three_of_a_kind(same: list[list[Card]]) -> list[Card]:
    """Get three of a kind cards."""
    for cards in same:
        if len(cards) >= 3:
            return cards[len(cards) - 3:]
    return []

def get_two_pair(same: list[list[Card]]) -> list[Card]:
    """Get two pair cards."""
    pair_indices = []
    for i in range(len(same)):
        if len(same[i]) >= 2:
            pair_indices.append(i)
    if len(pair_indices) >= 2:
        pair1 = same[pair_indices[0]]
        pair2 = same[pair_indices[1]]
        return pair1[len(pair1) - 2:] + pair2[len(pair2) - 2:]
    return []

def get_pair(same: list[list[Card]]) -> list[Card]:
    """Get a pair of cards."""
    for cards in same:
        if len(cards) >= 2:
            return cards[len(cards) - 2:]
    return []

def get_high_card(cards: list[Card]) -> list[Card]:
    """Get the highest card."""
    return [max(cards, key=lambda card: card.value.value)]

def get_consecutive_cards(cards: list[Card]) -> list[list[Card]]:
    """Get consecutive cards."""
    cards = sorted(cards, key=lambda card: card.value.value)
    groups = []
    skip = 0
    for i in range(len(cards) - 1):
        if skip > 0:
            skip -= 1
            continue
        consecutive = [cards[i]]
        for j in range(1, len(cards) - i):
            if cards[i].value.value + j == cards[i + j].value.value:
                consecutive.append(cards[i + j])
                skip += 1
        if len(consecutive) > 1:
            groups.append(consecutive)
    return groups[::-1]


def get_same_cards(cards) -> list[list[Card]]:
    """Get same cards."""
    cards = sorted(cards, key=lambda card: card.value.value)
    groups = []
    skip = 0
    for i in range(len(cards) - 1):
        if skip > 0:
            skip -= 1
            continue
        same = [cards[i]]
        for j in range(1, len(cards) - i):
            if cards[i].value == cards[i + j].value:
                same.append(cards[i + j])
                skip += 1
        if len(same) > 1:
            groups.append(same)
    return groups
