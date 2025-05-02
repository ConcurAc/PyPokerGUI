from hand_predictor import PokerHandPredictor
from cards import Card

class Decider:
    def __init__(self):
        self.hand_predictor = PokerHandPredictor()

    def decide(self, valid_actions, hole_card, community_card) -> tuple[str, int]:
        hole_card =  list(map(lambda x: Card.from_str(x), hole_card))
        community_card = list(map(lambda x: Card.from_str(x), community_card))
        full_hand = hole_card + community_card

        # this shouldn't work just here for the sake of suggesting how to go about
        # calculating confidence
        hand_type = self.hand_predictor.predict(full_hand)
        community_potential = self.hand_predictor.predict(community_card)
        confidence = hand_type.value / community_potential.value

        if confidence > 0.5:
            return ("call", 0)
        else:
            return ("fold", 0)
