# deck.py
# 牌堆生成

import random
import constants
from card import Card

def draw_random_card(exclude_bomb=False):
    if random.random() < constants.FUNC_PROB:
        func_list = list(constants.FUNC_WEIGHTS.keys())
        weights = list(constants.FUNC_WEIGHTS.values())
        if exclude_bomb and "炸弹" in func_list:
            idx = func_list.index("炸弹")
            func_list.pop(idx)
            weights.pop(idx)
        if not func_list:
            return Card('digit', random.randint(0, 9))
        chosen = random.choices(func_list, weights=weights, k=1)[0]
        return Card('func', chosen)
    else:
        return Card('digit', random.randint(0, 9))

def generate_initial_hand():
    hand = []
    for _ in range(constants.MIN_DIGITS_INITIAL):
        hand.append(Card('digit', random.randint(0, 9)))
    while len(hand) < constants.INITIAL_HAND_SIZE:
        hand.append(draw_random_card(exclude_bomb=True))
    random.shuffle(hand)
    return hand