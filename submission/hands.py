
from enum import Enum

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
