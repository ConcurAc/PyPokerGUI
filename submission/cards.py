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
    def __init__(self, suit: Suit, value: Value):
        self.suit = suit
        self.value = value

    # String representation of card
    def __repr__(self) -> str:
        return f"{self.value.name} of {self.suit.name}"

    # Create card from raw int values
    @classmethod
    def from_raw(cls, suit: int, value: int):
        return cls(Card.Suit(suit), Card.Value(value))

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
            cls(Card.Suit(row["S1"]), Card.Value(row["C1"])),
            cls(Card.Suit(row["S2"]), Card.Value(row["C2"])),
            cls(Card.Suit(row["S3"]), Card.Value(row["C3"])),
            cls(Card.Suit(row["S4"]), Card.Value(row["C4"])),
            cls(Card.Suit(row["S5"]), Card.Value(row["C5"]))
        ]
