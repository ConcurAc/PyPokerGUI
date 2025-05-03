import pandas as pd
from enum import Enum

# Class representing a playing card
class Card:
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

    # Initialize card with suit and value
    def __init__(self, suit: Suit | int, value: Value | int):
        if isinstance(suit, Card.Suit):
            self.suit = suit
        else:
            self.suit = Card.Suit(suit)
        if isinstance(value, Card.Value):
            self.value = value
        else:
            self.value = Card.Value(value)

    # String representation of card
    def __repr__(self) -> str:
        return f"{self.value.name} of {self.suit.name}"

    @classmethod
    def from_str(cls, card_str: str):
        suit_map = {
            "H": Card.Suit.HEARTS,
            "S": Card.Suit.SPADES,
            "D": Card.Suit.DIAMONDS,
            "C": Card.Suit.CLUBS
        }

        value_map = {
            "A": Card.Value.ACE,
            "2": Card.Value.TWO,
            "3": Card.Value.THREE,
            "4": Card.Value.FOUR,
            "5": Card.Value.FIVE,
            "6": Card.Value.SIX,
            "7": Card.Value.SEVEN,
            "8": Card.Value.EIGHT,
            "9": Card.Value.NINE,
            "T": Card.Value.TEN,
            "J": Card.Value.JACK,
            "Q": Card.Value.QUEEN,
            "K": Card.Value.KING
        }
        try:
            suit = suit_map[card_str[0]]
            value = value_map[card_str[1]]
        except KeyError:
            try:
                suit = suit_map[card_str[1]]
                value = value_map[card_str[0]]
            except KeyError:
                raise ValueError(f"Invalid card string: {card_str}")
        return cls(suit, value)

    # Create list of cards from pandas Series row
    @classmethod
    def from_row(cls, row: pd.Series):
        return [
            cls(row["S1"], row["C1"]),
            cls(row["S2"], row["C2"]),
            cls(row["S3"], row["C3"]),
            cls(row["S4"], row["C4"]),
            cls(row["S5"], row["C5"])
        ]
