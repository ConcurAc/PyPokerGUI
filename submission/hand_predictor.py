import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from enum import Enum

from cards import Card

class Hand(Enum):
    """Enum class defining poker hand rankings from weakest to strongest."""
    HIGH_CARD = 0      # No matching cards
    PAIR = 1           # Two cards of same value
    TWO_PAIR = 2       # Two different pairs
    THREE_OF_A_KIND = 3 # Three cards of same value
    STRAIGHT = 4       # Five cards in sequence
    FLUSH = 5          # Five cards of same suit
    FULL_HOUSE = 6     # Three of a kind plus a pair
    FOUR_OF_A_KIND = 7 # Four cards of same value
    STRAIGHT_FLUSH = 8 # Straight of same suit
    ROYAL_FLUSH = 9    # Ace-high straight flush


class PokerHandPredictor:
    """Class for predicting poker hands using a random forest model."""

    def __init__(self, sample = None):
        """Initialize the predictor with training data and model.

        Args:
            sample (int, optional): Number of random training samples to use.
                If None, use full training dataset.
        """
        # load training data from CSV file
        df_train = pd.read_csv("data/poker-hand-training-true.csv")

        # optionally random sample training data
        if isinstance(sample, int):
            df_train = df_train.sample(sample)

        # initialize random forest regressor model
        self._regressor = RandomForestRegressor()

        # split data into features (x) and target (y)
        y_train = df_train["CLASS"]
        x_train = df_train.drop("CLASS", axis=1)

        # train the model
        self._regressor.fit(x_train.values, y_train.values)

    def predict(self, cards: list[Card]) -> Hand:
        """Predict the poker hand rank for a set of cards.

        Args:
            cards (list[Card]): List of Card objects representing a poker hand

        Returns:
            Hand: Predicted poker hand rank as Hand enum
        """
        # convert cards to input format
        x_test = pd.Series()

        # for each card, add its suit and value to the test data
        for i, card in enumerate(cards):
            x_test[f"S{i + 1}"] = card.suit.value
            x_test[f"C{i + 1}"] = card.value.value

        # make prediction using trained model
        prediction = self._regressor.predict([x_test.values])[0]
        # convert numeric prediction to Hand enum and return
        return Hand(int(prediction))

# run tests if file is executed directly
if __name__ == "__main__":
    # test code
    import unittest
    import seaborn as sns
    from matplotlib import pyplot as plt

    TRAIN_SAMPLES = 1000
    TEST_SAMPLES = 500

    class TestPokerPrediction(unittest.TestCase):
        """Test class for evaluating poker hand predictions."""

        def setUp(self):
            """Set up the test environment."""
            self.predictor = PokerHandPredictor(TRAIN_SAMPLES)

        def test_predict(self):
            """Test prediction accuracy on test dataset."""
            # load test data
            df_test = pd.read_csv("data/poker-hand-testing.csv")
            # optionally sample test data
            if TEST_SAMPLES:
                df_test = df_test.sample(TEST_SAMPLES)

            total = len(df_test)
            correct = 0

            print(f"Total test samples: {total}")

            predictions = []
            # test each hand in the test dataset
            for _, row in df_test.iterrows():
                prediction = self.predictor.predict(Card.from_row(row))
                if prediction == Hand(row["CLASS"]):
                    correct += 1
                predictions.append(prediction.value)
            # print accuracy results
            print(f"Accuracy: {correct / total}")

    unittest.main()
