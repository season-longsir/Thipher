# Controll the whole game.


import random
import constants
from player import Player
from deck import gnrate_init


class Game:
    def __init__(self, nump, hump):
        self.n = nump
        self.players:list[Player] = []
        for i in range(nump):
            is_human = (i < hump)
            p = Player(i, f'P{i+1}', is_human = is_human)
            p.hand = gnrate_init()
            self.players.append(p)

        self.secret = random.randint(constants.SECRET_MIN, constants.SECRET_MAX)

        self.round = 0
        self.curplayer_idx = 0

        self.bomb_active = False
        self.bombholder_idx = None
        self.bomb_passes = 0
        self.pass_limit = 1 if nump == 2 else 2

        self.chal_bdries = set()

    def nxtplayer_idx(self, idx):
        return (idx + 1) % self.n

    def preplayer_idx(self, idx):
        return (idx - 1) % self.n

    def show_public_state(self):
        print('\n' + '=' * 40)
        print('【公共信息】')
        for p in self.players:
            funcs = p.func_list()
            if funcs:
                func_str = ', '.join(f'{name}x{count}' for name, count in funcs.items())
            else:
                func_str = '无'
            print(func_str)  # TODO

    def run(self):
        # TODO
        pass