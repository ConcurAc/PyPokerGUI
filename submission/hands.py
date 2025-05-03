
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

def get_best_hand(cards) -> Hand:
    """
    Determine the highest poker hand ranking for a list of cards.

    Args:
        cards (list): A list of Card objects

    Returns:
        tuple: (Hand ranking enum, list of relevant cards for tiebreaking)
    """
    consecutive = get_consecutive_values(cards)
    same = get_same_values(cards)
    royal_flush = get_royal_flush(consecutive)
    if isinstance(royal_flush, Hand):
        return royal_flush
    straight_flush = get_straight_flush(consecutive)
    if isinstance(straight_flush, Hand):
        return straight_flush
    four_of_a_kind = get_four_of_a_kind(same)
    if isinstance(four_of_a_kind, Hand):
        return four_of_a_kind
    full_house = get_full_house(same)
    if isinstance(full_house, Hand):
        return full_house
    flush = get_flush(cards)
    if isinstance(flush, Hand):
        return flush
    straight = get_straight(consecutive)
    if isinstance(straight, Hand):
        return straight
    three_of_a_kind = get_three_of_a_kind(same)
    if isinstance(three_of_a_kind, Hand):
        return three_of_a_kind
    two_pair = get_two_pair(same)
    if isinstance(two_pair, Hand):
        return two_pair
    pair = get_pair(same)
    if isinstance(pair, Hand):
        return pair
    return get_high_card(cards)

def score_closest_hand(cards: list[Card]) -> float:
    """Score the closest hand."""
    consecutive = get_consecutive_values(cards)
    same_suit = get_same_suit(cards)
    same_value = get_same_values(cards)

    longest = max(consecutive, key=len)
    common_suit = max(same_suit, key=len)
    common_value = max(same_value, key=len)

    longest_score = 4.0 * len(longest) / 5.0
    common_suit_score = 5.0 * len(common_suit) / 4.0
    common_value_score = 6.0 * len(common_value) / 5.0

    print(f"longest_score: {longest_score}")
    print(f"common_suit_score: {common_suit_score}")
    print(f"common_value_score: {common_value_score}")
    return longest_score + common_suit_score + common_value_score

def get_royal_flush(consecutive: list[list[Card]]) -> Hand | None:
    for cards in consecutive:
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

            for suit, count in suit_dict.items():
                if count >= 5:
                    royal_cards = list(filter(lambda card: card.value in royal_flush_values and card.suit == suit, cards))
                    return Hand.ROYAL_FLUSH.with_cards(royal_cards)
    return None

def get_straight_flush(consecutive: list[list[Card]]) -> Hand | None:
    """Get straight flush cards."""
    for cards in consecutive:
        same = get_same_suit(cards)
        common_suit = max(same, key=len)
        if len(cards) >= 5:
            if len(common_suit) >= 5:
            # Check if it's a straight flush
                straight_flush_cards = sorted(common_suit, key=lambda card: card.value.value)[-5:]
                return Hand.STRAIGHT_FLUSH.with_cards(straight_flush_cards)
    return None

def get_flush(cards: list[Card]) -> Hand | None:
    """Get flush cards."""
    # Group cards by suit
    same = get_same_suit(cards)
    common_suit = max(same, key=len)
    if len(common_suit) >= 5:
        # Check if it's a straight flush
        flush_cards = sorted(common_suit, key=lambda card: card.value.value)[-5:]
        return Hand.FLUSH.with_cards(flush_cards)
    return None

def get_straight(consecutive: list[list[Card]]) -> Hand | None:
    """Get straight cards."""
    for cards in consecutive:
        if len(cards) >= 5:
            return Hand.STRAIGHT.with_cards(cards[len(cards) - 5:])
    return None

def get_four_of_a_kind(same: list[list[Card]]) -> Hand | None:
    """Get four of a kind cards."""
    for cards in same:
        if len(cards) >= 4:
            return Hand.FOUR_OF_A_KIND.with_cards(cards[len(cards) - 4:])
    return None

def get_full_house(same: list[list[Card]]) -> Hand | None:
    """Get full house cards."""
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
            return Hand.FULL_HOUSE.with_cards(three_of_a_kind[len(three_of_a_kind) - 3:] + pair[len(pair) - 2:])
    return None

def get_three_of_a_kind(same: list[list[Card]]) -> Hand | None:
    """Get three of a kind cards."""
    for cards in same:
        if len(cards) >= 3:
            return Hand.THREE_OF_A_KIND.with_cards(cards[len(cards) - 3:])
    return None

def get_two_pair(same: list[list[Card]]) -> Hand | None:
    """Get two pair cards."""
    pair_indices = []
    for i in range(len(same)):
        if len(same[i]) >= 2:
            pair_indices.append(i)
    if len(pair_indices) >= 2:
        pair1 = same[pair_indices[0]]
        pair2 = same[pair_indices[1]]
        return Hand.TWO_PAIR.with_cards(pair1[len(pair1) - 2:] + pair2[len(pair2) - 2:])
    return None

def get_pair(same: list[list[Card]]) -> Hand | None:
    """Get a pair of cards."""
    for cards in same:
        if len(cards) >= 2:
            return Hand.PAIR.with_cards(cards[len(cards) - 2:])
    return None

def get_high_card(cards: list[Card]) -> Hand:
    """Get the highest card."""
    return Hand.HIGH_CARD.with_cards([max(cards, key=lambda card: card.value.value)])

def get_same_suit(cards: list[Card]) -> list[list[Card]]:
    """Get cards of the same suit."""
    cards = sorted(cards, key=lambda card: card.suit.value)
    groups = []
    skip = 0
    for i in range(len(cards) - 1):
        if skip > 0:
            skip -= 1
            continue
        same = [cards[i]]
        for j in range(1, len(cards) - i):
            if cards[i].suit == cards[i + j].suit:
                same.append(cards[i + j])
                skip += 1
        if len(same) > 1:
            groups.append(same)
    return groups[::-1]

def get_missing_suit(cards: list[Card]) -> list[Card]:
    """Get missing cards of the same suit."""
    cards = sorted(cards, key=lambda card: card.suit.value)
    common_suit = max(get_same_suit(cards), key=len)[0].suit
    missing_suits = []
    for card in cards:
        if common_suit != card.suit:
            missing_suits.append(Card(common_suit, card.value))
    return missing_suits

def get_consecutive_values(cards: list[Card]) -> list[list[Card]]:
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

def get_missing_consecutive(cards: list[Card]) -> list[list[Card]]:
    """Get missing consecutive cards."""
    cards = sorted(cards, key=lambda card: card.value.value)
    common_suit = max(get_same_suit(cards), key=len)[0].suit
    groups = []
    for i in range(len(cards)):
        missing_consecutive = []
        value = (cards[i].value.value + 1) % len(Hand)
        while value != cards[(i + 1) % len(cards)].value.value:
            missing_consecutive.append(Card(common_suit, value))
            value = (value + 1) % len(Hand)
        if len(missing_consecutive) > 0:
            groups.append(missing_consecutive)
    return groups[::-1]

def get_same_values(cards: list[Card]) -> list[list[Card]]:
    """Get cards with same value."""
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
