# player.py
# 玩家类

import random
from card import Card

class Player:
    def __init__(self, pid, name, is_human=True):
        self.id = pid
        self.name = name
        self.is_human = is_human
        self.hand = []
        self.skip_rounds = 0
        self.double_last_used_round = -999
        self.alive = True
        self.cunning_effect_active = False

    def count(self):
        return len(self.hand)

    def count_digits(self):
        return sum(1 for c in self.hand if c.is_digit() or (c.type == 'func' and c.value == "万能"))

    def func_list(self):
        funcs = {}
        for c in self.hand:
            if c.type == 'func':
                funcs[c.value] = funcs.get(c.value, 0) + 1
        return funcs

    def remove_cards_by_indices(self, indices):
        indices = sorted(indices, reverse=True)
        removed = []
        for i in indices:
            removed.append(self.hand.pop(i))
        removed.reverse()
        return removed

    def add_cards(self, cards):
        self.hand.extend(cards)

    def discard_random(self, n):
        discarded = []
        for _ in range(min(n, len(self.hand))):
            idx = random.randrange(len(self.hand))
            discarded.append(self.hand.pop(idx))
        return discarded

    def find_func_indices(self, func_name):
        return [i for i, c in enumerate(self.hand) if c.type == 'func' and c.value == func_name]

    def find_digit_indices(self):
        return [i for i, c in enumerate(self.hand) if c.is_digit() or (c.type == 'func' and c.value == "万能")]