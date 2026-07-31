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
            print(f'{p.name}：手牌数 = {p.count()}, 跳过轮次 = {p.skipped}')

        if self.bomb_active and self.bombholder_idx is not None:
            holder = self.players[self.bombholder_idx]
            print(f'炸弹持有者：{holder.name}, 传递次数：{self.bomb_passes}/{self.pass_limit}')
        else:
            print('场上无炸弹。')

        print('=' * 40)

    def show_hand(self, player: Player):
        print(f'\n【{player.name}的手牌】')
        hands = []
        for i, card in enumerate(player.hand):
            hands.append(f'[{i}]{card.name}')
        print(' ' + ' '.join(hands))

    def run(self):
        print(f'游戏开始！\n共有{self.n}位玩家，秘密数字已生成！')
        self.show_public_state()
        cur = self.players[self.curplayer_idx]
        self.show_hand(cur)
        # TODO