# game.py
# 游戏主逻辑，包含所有功能牌

import sys
import random
import constants
from player import Player
from deck import draw_random_card, generate_initial_hand

class Game:
    def __init__(self, num_players, human_players):
        self.n = num_players
        self.players = []
        for i in range(num_players):
            is_human = (i < human_players)
            p = Player(i, f"P{i+1}", is_human=is_human)
            p.hand = generate_initial_hand()
            self.players.append(p)

        self.secret = random.randint(constants.SECRET_MIN, constants.SECRET_MAX)

        self.round_index = 0
        self.current_player_idx = 0

        # 炸弹追踪
        self.bomb_active = False
        self.bomb_holder_idx = None
        self.bomb_passes = 0
        self.pass_limit = 1 if num_players == 2 else 2

        self.challenged_boundaries = set()

        # 调试（可注释掉）
        # print(f"[DEBUG] secret = {self.secret}")

    # ---------- 辅助方法 ----------
    def next_player_index(self, idx):
        return (idx + 1) % self.n

    def previous_player_index(self, idx):
        return (idx - 1) % self.n

    def draw_cards_for(self, player, count):
        cards = [draw_random_card() for _ in range(count)]
        player.add_cards(cards)
        return cards

    def show_public_state(self):
        print("\n---- 公开信息 ----")
        for p in self.players:
            funcs = p.func_list()
            func_str = ", ".join(f"{k}x{v}" for k, v in funcs.items()) if funcs else "无"
            print(f"{p.name}: 手牌数={p.count()} (数字牌数={p.count_digits()} 隐藏), 功能牌: {func_str}, 跳过剩余={p.skip_rounds}")
        if self.bomb_active and self.bomb_holder_idx is not None:
            print(f"场上有炸弹，持有者: {self.players[self.bomb_holder_idx].name} (已传递 {self.bomb_passes} 次，阈值 {self.pass_limit})")
        else:
            print("场上无炸弹")
        print("------------------")

    def show_player_hand(self, player):
        print(f"{player.name} 的手牌:")
        for i, c in enumerate(player.hand):
            print(f"  [{i}] {c.name}")

    def reveal_comparison_to_player(self, player, guess, cunning=False):
        """
        向玩家显示比较结果，若 cunning=True 则使用狡猾格式。
        """
        if cunning:
            diff = abs(self.secret - guess)
            if diff > guess:
                print(f"[私人] {player.name}，你的出牌 {guess} 与目标数字相差超过 {guess}")
            else:
                print(f"[私人] {player.name}，你的出牌 {guess} 与目标数字相差不超过 {guess}")
        else:
            if guess == self.secret:
                print(f"[私人] {player.name}，你的出牌 {guess} 与目标数字相等！")
            elif guess < self.secret:
                print(f"[私人] {player.name}，你的出牌 {guess} 小于目标数字。")
            else:
                print(f"[私人] {player.name}，你的出牌 {guess} 大于目标数字。")

    def check_game_over(self):
        alive = [p for p in self.players if p.alive]
        if len(alive) <= 1:
            winner = alive[0] if alive else None
            self.game_over(winner)

    def game_over(self, winner=None):
        if winner:
            print(f"\n🏆 游戏结束，胜利者是 {winner.name}！")
        else:
            print("\n游戏结束，无人生还。")
        sys.exit(0)

    def advance_turn(self):
        # 检查死亡
        self.check_game_over()
        # 移动到下一位
        self.current_player_idx = self.next_player_index(self.current_player_idx)
        if self.current_player_idx == 0:
            self.round_index += 1

    # ---------- 核心玩法方法 ----------
    def select_cards_to_play(self, player):
        """
        让玩家选择要出的牌，返回 (牌列表, 使用的功能名列表)
        若取消/无法出牌，返回 (None, None)
        """
        if player.is_human:
            while True:
                print("\n请选择要出的牌（输入索引，空格分隔）。")
                self.show_player_hand(player)
                print("提示：必须包含至少一张数字牌（数字或万能），最多5张（炸弹计2张）。")
                sel = input("输入索引（或 'cancel' 取消）：").strip()
                if sel.lower() == "cancel":
                    return None, None
                try:
                    indices = list(map(int, sel.split()))
                    if not indices:
                        print("至少选择一张牌。")
                        continue
                    if any(i < 0 or i >= len(player.hand) for i in indices):
                        print("索引越界。")
                        continue
                    # 检查包含数字牌
                    has_digit = any(
                        player.hand[i].is_digit() or
                        (player.hand[i].type == 'func' and player.hand[i].value == "万能")
                        for i in indices
                    )
                    if not has_digit:
                        print("必须包含至少一张数字牌（数字或万能）。")
                        continue
                    # 计算计数（炸弹计2）
                    total = 0
                    for i in indices:
                        if player.hand[i].type == 'func' and player.hand[i].value == "炸弹":
                            total += 2
                        else:
                            total += 1
                    if total > 5:
                        print(f"总计数 {total} 超过5，请减少牌数。")
                        continue
                    # 移除牌
                    played = player.remove_cards_by_indices(indices)
                    used_funcs = [c.value for c in played if c.type == 'func']
                    return played, used_funcs
                except ValueError:
                    print("请输入整数索引。")
        else:
            # AI策略
            digit_indices = player.find_digit_indices()
            if not digit_indices:
                return None, None
            # 随机选1-2张数字牌，可能附加功能牌（如加牌）
            num_digits = random.randint(1, min(2, len(digit_indices)))
            chosen = random.sample(digit_indices, num_digits)
            # 尝试添加一张功能牌（概率）
            func_indices = [i for i in range(len(player.hand)) if player.hand[i].type == 'func']
            if func_indices and random.random() < 0.3:
                # 选一个功能牌，但检查是否会造成超限
                extra = random.choice(func_indices)
                # 计算总计数
                temp_indices = chosen + [extra]
                total = 0
                for i in temp_indices:
                    if player.hand[i].type == 'func' and player.hand[i].value == "炸弹":
                        total += 2
                    else:
                        total += 1
                if total <= 5:
                    chosen.append(extra)
            # 移除
            played = player.remove_cards_by_indices(chosen)
            used_funcs = [c.value for c in played if c.type == 'func']
            print(f"{player.name} 出了 {len(played)} 张牌。")
            return played, used_funcs

    def form_number_from_cards(self, cards, player):
        """
        从出牌列表中组合数字，返回整数，若失败返回 None
        """
        digit_cards = [c for c in cards if c.is_digit() or (c.type == 'func' and c.value == "万能")]
        if not digit_cards:
            return None

        # 如果只有一张
        if len(digit_cards) == 1:
            c = digit_cards[0]
            if c.is_digit():
                return c.value
            else:
                if player.is_human:
                    while True:
                        val = input("万能牌替代数字（0-9）：").strip()
                        if val.isdigit() and 0 <= int(val) <= 9:
                            return int(val)
                        print("请输入0-9。")
                else:
                    return random.randint(0, 9)

        # 多张牌：需要指定顺序
        if player.is_human:
            print("\n你出的数字牌（含万能）如下：")
            for idx, c in enumerate(digit_cards):
                print(f"  pos {idx}: {c.name}")
            while True:
                order_input = input("请输入这些牌的顺序（空格分隔的索引，如 '0 1 2'）：").strip()
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
                print("数字不允许前导零。")
                return None
            return int(num_str)
        else:
            # AI：随机排列，避免前导零
            random.shuffle(digit_cards)
            num_str = ""
            for idx, c in enumerate(digit_cards):
                if c.is_digit():
                    num_str += str(c.value)
                else:
                    # 万能
                    if idx == 0 and len(digit_cards) > 1:
                        num_str += str(random.randint(1, 9))
                    else:
                        num_str += str(random.randint(0, 9))
            if len(num_str) > 1 and num_str[0] == '0':
                num_str = '1' + num_str[1:]
            return int(num_str)

    def declaration_phase(self, player, guesses):
        """
        声明与质疑阶段，guesses 是一个列表（可能包含多个猜测，双出时有两个）
        返回是否通过
        """
        print("\n--- 声明阶段 ---")
        # 计算所有允许的边界（基于所有猜测）
        allowed = set()
        for g in guesses:
            for delta in range(-20, 21):
                cand = g + delta
                if cand >= 0:
                    allowed.add(cand)
        allowed = allowed - self.challenged_boundaries
        if not allowed:
            print(f"没有可声明的合法边界，{player.name} 自动失败。")
            player.alive = False
            self.check_game_over()
            return False

        if player.is_human:
            print("声明要求：边界数字必须与本回合某一次出牌数字相差≤20，且未被质疑过。")
            print(f"本回合出牌数字: {guesses}")
            print(f"可用边界示例: {sorted(list(allowed))[:10]}... (共{len(allowed)}个)")
            while True:
                dir_choice = input("请选择方向：1) 大于  2) 小于：").strip()
                if dir_choice not in ("1", "2"):
                    print("请输入1或2。")
                    continue
                dir_sym = ">" if dir_choice == "1" else "<"
                bound_str = input("请输入边界数字（整数）：").strip()
                if not bound_str.lstrip('-').isdigit():
                    print("请输入有效整数。")
                    continue
                bound = int(bound_str)
                if bound not in allowed:
                    print("边界数字不合法（须与某次猜测相差≤20且未被质疑）。")
                    continue
                break
        else:
            bound = random.choice(list(allowed))
            dir_sym = random.choice([">", "<"])
            print(f"{player.name} 声明: 目标数字 {'大于' if dir_sym=='>' else '小于'} {bound}")

        stmt = f"目标数字 {'大于' if dir_sym=='>' else '小于'} {bound}"
        print(f"\n{player.name} 向所有人声明：{stmt}")

        # 下家质疑
        next_idx = self.next_player_index(player.id)
        next_player = self.players[next_idx]
        if next_player.is_human:
            while True:
                ch = input(f"{next_player.name}，是否质疑？(y/n，默认n)：").strip().lower()
                if ch in ("y", "yes"):
                    challenge = True
                    break
                elif ch in ("n", "no", ""):
                    challenge = False
                    break
                else:
                    print("请输入 y 或 n。")
        else:
            prob = 0.25 + 0.02 * (next_player.count() - player.count())
            prob = max(0.05, min(0.6, prob))
            challenge = random.random() < prob
            print(f"{next_player.name} 决定 {'质疑' if challenge else '相信'}（AI）。")

        if challenge:
            print(f"\n{next_player.name} 发起质疑！")
            # 公开比较结果（对所有猜测）
            for g in guesses:
                if g == self.secret:
                    comp = "等于"
                elif g < self.secret:
                    comp = "小于"
                else:
                    comp = "大于"
                print(f"公开信息：{player.name} 的出牌 {g} 与目标数字比较结果为 {g} {comp} 目标数字。")
            # 判断声明真假
            if dir_sym == ">":
                declared_true = (self.secret > bound)
            else:
                declared_true = (self.secret < bound)
            if declared_true:
                print(f"声明为真！{next_player.name} 弃置2张牌，{player.name} 获得1张牌。")
                lost = next_player.discard_random(2)
                print(f"{next_player.name} 弃置: {[c.name for c in lost]}")
                drawn = self.draw_cards_for(player, 1)
                print(f"{player.name} 获得: {[c.name for c in drawn]}")
            else:
                print(f"声明为假！{next_player.name} 获得2张牌，{player.name} 弃置3张牌。")
                drawn = self.draw_cards_for(next_player, 2)
                print(f"{next_player.name} 获得: {[c.name for c in drawn]}")
                lost = player.discard_random(3)
                print(f"{player.name} 弃置: {[c.name for c in lost]}")
            self.challenged_boundaries.add(bound)
            return declared_true
        else:
            print(f"{next_player.name} 选择相信声明。")
            return True

    # ---------- 回合主流程 ----------
    def play_turn(self):
        player = self.players[self.current_player_idx]
        print(f"\n========== {player.name} 的回合 ==========")
        self.show_public_state()
        if player.is_human:
            self.show_player_hand(player)

        # 跳过处理
        if player.skip_rounds > 0:
            print(f"{player.name} 被禁止，跳过本回合（剩余 {player.skip_rounds} 回合）。")
            player.skip_rounds -= 1
            # 检查炸弹（如果手中有炸弹且跳过，则爆炸）
            self.check_bomb_explosion(player)
            self.advance_turn()
            return

        # 检查炸弹持有（需要打出或爆炸）
        has_bomb = any(c.type == 'func' and c.value == "炸弹" for c in player.hand)
        if has_bomb:
            print("你手中有炸弹！本回合若不打出则会爆炸。")

        # 抽牌选项
        can_draw = (player.count() <= 5)
        action = None
        if player.is_human:
            while True:
                if can_draw:
                    print("选项1: 抽取3张牌（本回合不出牌）")
                print("选项2: 出牌")
                choice = input("请选择（输入1或2）：").strip()
                if choice == "1" and can_draw:
                    action = "draw"
                    break
                elif choice == "2":
                    action = "play"
                    break
                else:
                    print("无效输入。")
        else:
            if can_draw and random.random() < 0.2:
                action = "draw"
            else:
                action = "play"
            print(f"{player.name} 决定: {'抽3张' if action=='draw' else '出牌'}")

        if action == "draw":
            drawn = self.draw_cards_for(player, 3)
            print(f"{player.name} 抽到: {[c.name for c in drawn]}")
            # 抽牌后若手中有炸弹，不会爆炸，但已警告过。
            self.advance_turn()
            return

        # 出牌流程
        played_cards, used_funcs = self.select_cards_to_play(player)
        if played_cards is None:
            print(f"{player.name} 无法出牌，失败。")
            player.alive = False
            self.check_game_over()
            return

        # 组合数字（可能多个，双出会多次）
        guesses = []
        # 第一次出牌
        guess1 = self.form_number_from_cards(played_cards, player)
        if guess1 is None:
            print(f"{player.name} 出牌无效（无数字或前导零），失败。")
            player.alive = False
            self.check_game_over()
            return
        guesses.append(guess1)

        # 判断是否使用了双出
        double_used = ("双出" in used_funcs)
        if double_used:
            # 检查冷却：上一回合是否使用过
            if (self.round_index - player.double_last_used_round) < 2:
                print("双出冷却中（需过一圈才能再用），本次双出无效，将忽略。")
                double_used = False
            else:
                print("使用了双出，可以进行第二次出牌。")
                player.double_last_used_round = self.round_index
                # 第二次出牌
                if player.is_human:
                    print("请进行第二次出牌：")
                played2, funcs2 = self.select_cards_to_play(player)
                if played2 is None:
                    print("取消第二次出牌。")
                else:
                    guess2 = self.form_number_from_cards(played2, player)
                    if guess2 is not None:
                        guesses.append(guess2)
                        # 第二次出牌的功能牌也处理（加牌等）
                        used_funcs.extend(funcs2)

        # 显示比较结果（仅玩家可见）
        # 检查是否受到狡猾影响（仅影响第一次显示）
        cunning_effect = player.cunning_effect_active
        for idx, g in enumerate(guesses):
            cunning = cunning_effect and idx == 0
            self.reveal_comparison_to_player(player, g, cunning=cunning)
        player.cunning_effect_active = False   # 只影响一次

        # 判断胜利（任何一次猜测等于秘密数字）
        for g in guesses:
            if g == self.secret:
                print(f"🎉 {player.name} 猜中目标数字 {self.secret}，取得胜利！")
                self.game_over(winner=player)
                return

        # 处理功能牌效果（加牌、交换、禁止、狡猾、炸弹）
        # 加牌
        if "加牌" in used_funcs:
            drawn = self.draw_cards_for(player, 2)
            print(f"{player.name} 使用加牌，额外摸到: {[c.name for c in drawn]}")

        # 交换
        if "交换" in used_funcs:
            self.handle_swap(player)

        # 禁止
        if "禁止" in used_funcs:
            self.handle_prohibit(player)

        # 狡猾
        if "狡猾" in used_funcs:
            self.handle_cunning(player)

        # 炸弹：打出后传递给下家
        if "炸弹" in used_funcs:
            self.handle_bomb_played(player)

        # 声明阶段（仅需一次，不管是否双出）
        self.declaration_phase(player, guesses)

        # 检查玩家是否因声明失败而死亡
        if not player.alive:
            self.check_game_over()
            return

        # 前进到下一位
        self.advance_turn()

    # ---------- 功能牌处理方法 ----------
    def handle_swap(self, player):
        """交换功能：选择1-5张牌与某玩家交换，炸弹不可交换"""
        print("\n--- 使用交换 ---")
        if player.is_human:
            while True:
                try:
                    target_idx = int(input("请输入要交换的玩家编号（例如 2 表示 P2）：")) - 1
                    if target_idx < 0 or target_idx >= self.n or target_idx == player.id:
                        print("无效玩家。")
                        continue
                    target = self.players[target_idx]
                    self.show_player_hand(player)
                    sel = input("选择要交换的自己手牌索引（1-5张，空格分隔）：").strip()
                    indices = list(map(int, sel.split()))
                    if not (1 <= len(indices) <= 5):
                        print("请选择1-5张。")
                        continue
                    if any(player.hand[i].type == 'func' and player.hand[i].value == "炸弹" for i in indices):
                        print("炸弹不可交换。")
                        continue
                    # 移除自己的牌
                    give_cards = player.remove_cards_by_indices(indices)
                    # 从目标随机选相同数量非炸弹牌
                    avail = [i for i, c in enumerate(target.hand) if not (c.type == 'func' and c.value == "炸弹")]
                    if len(avail) < len(give_cards):
                        print("目标可交换牌不足，将交换尽可能多的牌。")
                        take_indices = avail
                    else:
                        take_indices = random.sample(avail, len(give_cards))
                    taken = target.remove_cards_by_indices(take_indices)
                    player.add_cards(taken)
                    target.add_cards(give_cards)
                    print(f"交换完成！你得到: {[c.name for c in taken]}")
                    break
                except Exception:
                    print("输入无效，请重试。")
        else:
            # AI简单处理：随机选一个玩家，交换1张
            targets = [p for p in self.players if p.id != player.id and p.alive]
            if not targets:
                return
            target = random.choice(targets)
            # 选自己的非炸弹牌
            my_indices = [i for i, c in enumerate(player.hand) if not (c.type == 'func' and c.value == "炸弹")]
            if not my_indices:
                return
            give_idx = random.sample(my_indices, 1)
            give_cards = player.remove_cards_by_indices(give_idx)
            # 目标随机给一张非炸弹
            avail = [i for i, c in enumerate(target.hand) if not (c.type == 'func' and c.value == "炸弹")]
            if avail:
                take_idx = random.sample(avail, min(1, len(avail)))
                taken = target.remove_cards_by_indices(take_idx)
                player.add_cards(taken)
                target.add_cards(give_cards)
                print(f"{player.name} 与 {target.name} 交换了1张牌。")

    def handle_prohibit(self, player):
        """禁止：指定一名其他玩家，使其跳过下一回合"""
        print("\n--- 使用禁止 ---")
        if player.is_human:
            while True:
                try:
                    target_idx = int(input("请输入要禁止的玩家编号（例如 2 表示 P2）：")) - 1
                    if target_idx < 0 or target_idx >= self.n or target_idx == player.id:
                        print("无效玩家。")
                        continue
                    self.players[target_idx].skip_rounds += 1
                    print(f"{self.players[target_idx].name} 将被禁止一回合。")
                    break
                except Exception:
                    print("输入无效。")
        else:
            targets = [p for p in self.players if p.id != player.id and p.alive]
            if targets:
                target = random.choice(targets)
                target.skip_rounds += 1
                print(f"{player.name} 禁止了 {target.name}。")

    def handle_cunning(self, player):
        """狡猾：下家的下一次比较显示为“相差超过/不超过”格式"""
        print("\n--- 使用狡猾 ---")
        next_idx = self.next_player_index(player.id)
        next_player = self.players[next_idx]
        next_player.cunning_effect_active = True
        print(f"{next_player.name} 的下一次比较将被狡猾影响。")

    def handle_bomb_played(self, player):
        """炸弹打出：传递给下家（跳过被禁止的）"""
        print("\n--- 炸弹被打出 ---")
        next_idx = self.next_player_index(player.id)
        # 跳过被禁止的玩家（如果其skip_rounds>0）
        loops = 0
        while self.players[next_idx].skip_rounds > 0 and loops < self.n:
            next_idx = self.next_player_index(next_idx)
            loops += 1
        # 将炸弹放入下家手牌
        bomb_card = Card('func', "炸弹")
        self.players[next_idx].add_cards([bomb_card])
        self.bomb_active = True
        self.bomb_holder_idx = next_idx
        self.bomb_passes += 1
        print(f"炸弹传递给 {self.players[next_idx].name}（已传递 {self.bomb_passes} 次）")

    def check_bomb_explosion(self, player):
        """检查玩家手中是否有炸弹，若有且未打出则爆炸（在回合开始时调用）"""
        if any(c.type == 'func' and c.value == "炸弹" for c in player.hand):
            # 爆炸
            cost = 2 if self.bomb_passes >= self.pass_limit else 4
            print(f"💥 {player.name} 手中的炸弹爆炸！弃置 {cost} 张牌。")
            discarded = player.discard_random(cost)
            print(f"弃置: {[c.name for c in discarded]}")
            # 移除炸弹（可能已被弃置）
            # 但炸弹可能还在手牌中（如果弃置的牌没有炸弹？但爆炸会消耗炸弹，我们强制移除）
            # 直接移除手牌中的炸弹
            bomb_indices = [i for i, c in enumerate(player.hand) if c.type == 'func' and c.value == "炸弹"]
            if bomb_indices:
                player.remove_cards_by_indices(bomb_indices)
                print("炸弹已从手牌中移除。")
            # 清除炸弹状态
            self.bomb_active = False
            self.bomb_holder_idx = None
            self.bomb_passes = 0

    # ---------- 主循环 ----------
    def run(self):
        print(f"游戏开始！共有 {self.n} 位玩家，秘密数字已生成。")
        # 调试（可注释）
        # print(f"[DEBUG] secret = {self.secret}")
        while True:
            self.play_turn()


# ---------- 启动 ----------
if __name__ == "__main__":
    print("=== 千数谎牌 Thipher: Digit Bluff ===")
    while True:
        try:
            num = int(input(f"请输入玩家总人数（{constants.MIN_PLAYERS}-{constants.MAX_PLAYERS}）："))
            if constants.MIN_PLAYERS <= num <= constants.MAX_PLAYERS:
                break
            print("人数不合法。")
        except ValueError:
            print("请输入整数。")
    while True:
        try:
            human = int(input(f"请输入人类玩家数量（1-{num}）："))
            if 1 <= human <= num:
                break
            print("数量不合法。")
        except ValueError:
            print("请输入整数。")
    game = Game(num, human)
    game.run()