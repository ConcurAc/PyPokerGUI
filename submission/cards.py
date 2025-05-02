import pandas as pd
from enum import Enum

# Enum class for card suits
class Suit(Enum):
    HEARTS = 1
    SPADES = 2
    DIAMONDS = 3
    CLUBS = 4

# Enum class for card values
class Value(Enum):
    ACE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13

# Class representing a playing card
class Card:
    # Initialize card with suit and value
    def __init__(self, suit: Suit, value: Value):
        self.suit = suit
        self.value = value

    # String representation of card
    def __repr__(self) -> str:
        return f"{self.value.name} of {self.suit.name}"

    # Create card from raw int values
    @classmethod
    def from_raw(cls, suit: int, value: int):
        return cls(Suit(suit), Value(value))

    @classmethod
    def from_str(cls, card_str: str):
        suit_map = {
            "H": Suit.HEARTS,
            "S": Suit.SPADES,
            "D": Suit.DIAMONDS,
            "C": Suit.CLUBS
        }

        value_map = {
            "A": Value.ACE,
            "2": Value.TWO,
            "3": Value.THREE,
            "4": Value.FOUR,
            "5": Value.FIVE,
            "6": Value.SIX,
            "7": Value.SEVEN,
            "8": Value.EIGHT,
            "9": Value.NINE,
            "T": Value.TEN,
            "J": Value.JACK,
            "Q": Value.QUEEN,
            "K": Value.KING
        }

        suit = suit_map[card_str[0]]
        value = value_map[card_str[1]]
        return cls(suit, value)

    # Create list of cards from pandas Series row
    @classmethod
    def from_row(cls, row: pd.Series):
        return [
            cls(Suit(row["S1"]), Value(row["C1"])),
            cls(Suit(row["S2"]), Value(row["C2"])),
            cls(Suit(row["S3"]), Value(row["C3"])),
            cls(Suit(row["S4"]), Value(row["C4"])),
            cls(Suit(row["S5"]), Value(row["C5"]))
        ]
