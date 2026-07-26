# Define object Player


import random
from card import Card


class Player:
    def __init__(self, pid, name, is_human = True):
        self.id = pid
        self.name = name
        self.is_human = is_human

        self.hand:list[Card] = []

        self.skipped:int = 0  # The rounds the player skipped

        self.dble_lround = -999

        self.alive = True

        self.cunning = False

    def count(self):
        return len(self.hand)

    def cnt_digits(self):
        return sum(1 for c in self.hand \
                   if c.is_digit() or (c.is_func() and c.value == '万能'))

    def func_list(self) -> dict:
        funcs = {}
        for c in self.hand:
            if c.is_func():
                funcs[c.value] = funcs.get(c.value, 0) + 1
        return funcs

    def rmv_cards(self, indices):
        indices = sorted(indices, reverse = True)
        removed = []
        for i in indices:
            removed.append(self.hand.pop(i))
        removed.reverse()
        return removed

    def add_cards(self, cards):
        self.hand.extend(cards)

    def discard_r(self, n):
        discarded = []
        for _ in range(min(n, len(self.hand))):
            idx = random.randrange(len(self.hand))
            discarded.append(self.hand.pop(idx))
        return discarded

    def find_func(self, name):
        return [i for i, c in enumerate(self.hand) \
                if c.is_func() and c.value == name]

    def find_digit(self):
        return [i for i, c in enumerate(self.hand) \
                   if c.is_digit() or (c.is_func() and c.value == '万能')]

