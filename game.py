# Controll the whole game.


import random
import constants
import sys
from player import Player
from deck import gnrate_init, draw_r


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
    
    def rev_comp(self, player:Player, guess):
        if guess == self.secret:
            print(f'【私人】{player.name}，你的出牌{guess}与目标数字相等！')
        elif guess < self.secret:
            print(f'【私人】{player.name}，你的出牌{guess}小于目标数字！')
        else:
            print(f'【私人】{player.name}，你的出牌{guess}大于目标数字！')

    def check_game_over(self):
        alive = [p for p in self.players if p.alive]
        if len(alive) == 0:
            print("所有玩家都失败了，游戏结束。")
            sys.exit(0)
        elif len(alive) == 1:
            winner = alive[0]
            print(f"🏆 游戏结束，胜利者是 {winner.name}！")
            sys.exit(0)

    def advce_turn(self):
        self.check_game_over()

        self.curplayer_idx = self.nxtplayer_idx(self.curplayer_idx)
        if self.curplayer_idx == 0:
            self.round_index += 1

        self.check_game_over()

    def draw_cards(self, player: Player, count: int):
        cards = [draw_r() for _ in range(count)]
        player.add_cards(cards)
        return cards

    def game_over(self):
        print("游戏结束！")
        sys.exit(0)

    def select_cards_to_play(self, player: Player):
        if player.is_human:
            while True:
                print("请选择要出的牌（输入空格分隔的索引）。")
                self.show_player_hand(player)
                sel = input("输入索引（例如: 0 2 3），或输入 'cancel' 取消: ").strip()
                if sel.lower() == "cancel":
                    return None, None
                try:
                    indices = list(map(int, sel.split()))
                    if not indices:
                        print("至少选择一张牌。")
                        continue
                    if any(i < 0 or i >= len(player.hand) for i in indices):
                        print("索引越界，请重试。")
                        continue
                    has_digit = any(player.hand[i].is_digit() or (player.hand[i].type == 'func' and player.hand[i].value == "万能") for i in indices)
                    if not has_digit:
                        print("出牌必须包含至少一张数字牌（数字或万能）。")
                        continue
                    if len(indices) > 5:
                        print("最多出5张牌。")
                        continue
                    played = player.remove_cards_by_indices(indices)
                    used_funcs = [c.value for c in played if c.type == 'func']
                    return played, used_funcs
                except ValueError:
                    print("请输入整数索引，用空格分隔。")
        else:
            # AI自动选择
            # 简单策略：选择1-3张数字牌（优先数字牌，若无则用万能）
            digit_indices = player.find_digit_indices()
            if not digit_indices:
                # 没有可作数字的牌，无法出牌
                print(f"{player.name} 没有数字牌，无法出牌。")
                return None, None
            # 随机选择1-2张（最多5，但简单选1-2）
            num_to_play = random.randint(1, min(2, len(digit_indices), 5))
            chosen_indices = random.sample(digit_indices, num_to_play)
            # 可能还会随机添加一张功能牌（比如加牌），但为了简单，只出数字牌
            # TODO: 如果需要加入功能牌，可在这里扩展
            played = player.remove_cards_by_indices(chosen_indices)
            used_funcs = [c.value for c in played if c.type == 'func']
            print(f"{player.name} 出了 {len(played)} 张牌。")
            return played, used_funcs

    def form_number_from_cards(self, cards, player: Player):
        digit_cards = [c for c in cards if c.is_digit() or (c.type == 'func' and c.value == "万能")]
        if not digit_cards:
            return None

        if len(digit_cards) == 1:
            c = digit_cards[0]
            if c.is_digit():
                return c.value
            else:
                if player.is_human:
                    while True:
                        val = input(f"万能牌替代数字（0-9）：").strip()
                        if val.isdigit() and 0 <= int(val) <= 9:
                            return int(val)
                        print("请输入0-9的数字。")
                else:
                    return random.randint(0, 9)

        if player.is_human:
            print("你出的数字牌（含万能）如下：")
            for idx, c in enumerate(digit_cards):
                print(f"  pos {idx}: {c.name}")
            while True:
                order_input = input("请输入这些牌的顺序（空格分隔的索引，例如 '0 1 2'）：").strip()
                try:
                    order = list(map(int, order_input.split()))
                    if sorted(order) != list(range(len(digit_cards))):
                        print(f"必须包含 0 到 {len(digit_cards)-1} 的所有数字。")
                        continue
                    break
                except ValueError:
                    print("请输入整数。")
            replacements = {}
            for idx, c in enumerate(digit_cards):
                if c.type == 'func' and c.value == "万能":
                    while True:
                        val = input(f"万能牌（位置 {idx}）替代数字（0-9）：").strip()
                        if val.isdigit() and 0 <= int(val) <= 9:
                            replacements[idx] = int(val)
                            break
                        print("请输入0-9。")
            num_str = ""
            for pos in order:
                c = digit_cards[pos]
                if c.is_digit():
                    num_str += str(c.value)
                else:
                    num_str += str(replacements[pos])
            if len(num_str) > 1 and num_str[0] == '0':
                print("数字不允许前导零，请重新组合。")
                return None
            return int(num_str)
        else:
            random.shuffle(digit_cards)
            num_str = ""
            for c in digit_cards:
                if c.is_digit():
                    num_str += str(c.value)
                else:
                    if not num_str and len(digit_cards) > 1:
                        num_str += str(random.randint(1, 9))
                    else:
                        num_str += str(random.randint(0, 9))
            if len(num_str) > 1 and num_str[0] == '0':
                num_str = '1' + num_str[1:]
            return int(num_str)

    def play_turn(self):
        cur = self.players[self.curplayer_idx]
        print(f'\n=========={cur.name}的回合==========')

        if cur.skipped > 0:
            print(f'{cur.name}被禁止，跳过回合，剩余：{cur.skipped - 1}回合')
            cur.skipped -= 1
            self.advce_turn()
            return

        # TODO: Bomb

        can_draw = (cur.count() <= 5)
        action = None
        if cur.is_human:
            while True:
                print(f'你的手牌数量：{cur.count()}')
                if can_draw:
                    print('选项1：抽取3张牌')
                print('选项2：出牌')
                choice = input('请选择你的行动：').strip()
                if choice == '1' and can_draw:
                    action = 'draw'
                    break
                elif choice == '2':
                    action = 'play'
                    break
                else:
                    print('无效的选择，请重新输入。')
        else:
            if can_draw and random.random() < 0.2:
                action = 'draw'
            else:
                action = 'play'
            print(f'{cur.name}选择了：{'抽3张' if action == 'draw' else '出牌'}')

        if action == 'draw':
            drawn = self.draw_cards(cur, 3)  # TODO
            print(f"{cur.name} 抽到了: {[c.name for c in drawn]}")
            self.advance_turn()
            return
        
        played_cards, used_funcs = self.select_cards_to_play(cur)
        if played_cards is None:
            print(f"{cur.name} 未能出牌，视为失败。")
            cur.alive = False
            self.check_game_over()
            return

        guess = self.form_number_from_cards(played_cards, cur)
        if guess is None:
            print(f"{cur.name} 出牌无效（无数字牌），失败。")
            cur.alive = False
            self.check_game_over()
            return

        self.rev_comp(cur, guess)

        if guess == self.secret:
            print(f"🎉 {cur.name} 猜中了秘密数字 {self.secret}，游戏结束！")
            self.game_over()
            return

        if "加牌" in used_funcs:
            drawn = self.draw_cards(cur, 2)
            print(f"{cur.name} 使用了 加牌，额外摸到: {[c.name for c in drawn]}")

        # TODO: declare

        self.advce_turn()

    def run(self):
        print(f'游戏开始！\n共有{self.n}位玩家，秘密数字已生成！')
        self.show_public_state()
        cur = self.players[self.curplayer_idx]
        self.show_hand(cur)
        # TODO