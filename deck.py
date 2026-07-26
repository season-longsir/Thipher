# To create deck


import random
import constants
from card import Card


def draw_r(excl_bomb = False):
    if random.random() < constants.FUNC_PROB:
        func = list(constants.FUNC_WEIGHTS.keys())
        weights = list(constants.FUNC_WEIGHTS.values())

        if excl_bomb and '炸弹' in func:
            bomb_idx = func.index('炸弹')
            func.pop(bomb_idx)
            weights.pop(bomb_idx)

        choose = random.choices(func, weights = weights, k = 1)[0]
        return Card('func', choose)
    else:
        return Card('digit', random.randint(0, 9))

def gnrate_init():
    hand = []
    for _ in range(constants.MIN_DIGITS_INITIAL):
        hand.append(Card('digit', random.randint(0, 9)))
    while len(hand) < constants.INITIAL_HAND_SIZE:
        hand.append(draw_r(excl_bomb = True))
    random.shuffle(hand)
    return hand