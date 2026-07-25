"""
Thipher: Digit Bluff - CLI single-file implementation (初版)

运行: python thipher.py
"""

import random
import sys
import textwrap

# -----------------------
# 配置与常量
# -----------------------
MIN_PLAYERS = 2
MAX_PLAYERS = 4
INITIAL_HAND_SIZE = 10
MIN_DIGITS_INITIAL = 5
SECRET_MIN = 1
SECRET_MAX = 1000

# Function card names (internal keys)
FUNC_PROHIBIT = "禁止"
FUNC_ADDCARD = "加牌"
FUNC_DOUBLE = "双出"
FUNC_WILD = "万能"
FUNC_SWAP = "交换"
FUNC_BOMB = "炸弹"
FUNC_CUNNING = "狡猾"

ALL_FUNCTIONS = [FUNC_PROHIBIT, FUNC_ADDCARD, FUNC_DOUBLE, FUNC_WILD, FUNC_SWAP, FUNC_BOMB, FUNC_CUNNING]

# When drawing random cards from infinite pile, use probabilities:
# higher chance for digits than function cards; bombs are rarer.
FUNC_PROB = 0.22  # prob to draw a function card vs digit
BOMB_PROB = 0.06  # part of function-prob that is bomb
# normalize: when function chosen, choose specific function with weights
FUNC_WEIGHTS = {
    FUNC_PROHIBIT: 1,
    FUNC_ADDCARD: 1,
    FUNC_DOUBLE: 1,
    FUNC_WILD: 1,
    FUNC_SWAP: 1,
    FUNC_BOMB: 0.6,     # slightly rarer
    FUNC_CUNNING: 1
}

# Bomb pass limit: number of passes until it becomes "weakened". Spec:
# "传递两次后（2人局为传递一次后）炸弹牌自动爆炸实效，此时炸弹爆炸需要爆炸的人丢弃2张手牌."
# We'll interpret: passes_needed = 2 for games with >=3 players, 1 for 2-player games.
def bomb_pass_limit_for_players(n_players):
    return 1 if n_players == 2 else 2

# -----------------------
# Card and Player models
# -----------------------
class Card:
    # type: 'digit' or 'func'
    def __init__(self, type_, value=None):
        self.type = type_
        if type_ == 'digit':
            assert isinstance(value, int) and 0 <= value <= 9
            self.value = value
            self.name = str(value)
        else:
            assert value in ALL_FUNCTIONS
            self.value = value
            self.name = value

    def is_digit(self):
        return self.type == 'digit'

    def is_func(self, fname):
        return self.type == 'func' and self.value == fname

    def __repr__(self):
        if self.type == 'digit':
            return f"Digit({self.value})"
        else:
            return f"Func({self.value})"

class Player:
    def __init__(self, pid, name, is_human=True):
        self.id = pid
        self.name = name
        self.is_human = is_human
        self.hand = []  # list of Card
        self.skip_rounds = 0  # due to 禁止
        self.double_last_used_round = -999  # for 双出 cooldown tracking (round index when used)
        self.has_bomb_flag = False  # whether currently holding bomb (for convenience)
        # dynamic flags for effects applying to this player:
        self.cunning_effect_active = False  # previous player used 狡猾 -> affects this player's next compare display (only for first of double)
        # bookkeeping
        self.alive = True

    def count(self):
        return len(self.hand)

    def count_digits(self):
        return sum(1 for c in self.hand if c.type == 'digit' or (c.type == 'func' and c.value == FUNC_WILD))

    def func_list(self):
        # show function cards as names and counts
        funcs = {}
        for c in self.hand:
            if c.type == 'func':
                funcs[c.value] = funcs.get(c.value, 0) + 1
        return funcs

    def remove_cards_by_indices(self, indices):
        # indices is list of indices (unique) referring to self.hand
        indices = sorted(indices, reverse=True)
        removed = []
        for i in indices:
            removed.append(self.hand.pop(i))
        removed.reverse()
        return removed

    def remove_cards_objects(self, objs):
        # remove specific Card objects from hand (first occurrence)
        removed = []
        for o in objs:
            for i, c in enumerate(self.hand):
                if c is o:
                    removed.append(self.hand.pop(i))
                    break
        return removed

    def add_cards(self, cards):
        self.hand.extend(cards)
        self.has_bomb_flag = any(c.type == 'func' and c.value == FUNC_BOMB for c in self.hand)

    def discard_random(self, n):
        # discard n random cards; returns list of discarded
        discarded = []
        for _ in range(n):
            if not self.hand:
                break
            idx = random.randrange(len(self.hand))
            discarded.append(self.hand.pop(idx))
        self.has_bomb_flag = any(c.type == 'func' and c.value == FUNC_BOMB for c in self.hand)
        return discarded

    def find_func_indices(self, fname):
        return [i for i, c in enumerate(self.hand) if c.type == 'func' and c.value == fname]

    def find_digit_indices(self):
        return [i for i, c in enumerate(self.hand) if c.type == 'digit' or (c.type == 'func' and c.value == FUNC_WILD)]

# -----------------------
# Utility: drawing infinite deck
# -----------------------
def draw_random_card():
    # returns Card object
    if random.random() < FUNC_PROB:
        # draw function card
        func = random.choices(list(FUNC_WEIGHTS.keys()), weights=list(FUNC_WEIGHTS.values()), k=1)[0]
        return Card('func', func)
    else:
        return Card('digit', random.randint(0, 9))

def draw_initial_hand(exclude_bomb=True):
    # draw initial hand of size INITIAL_HAND_SIZE with at least MIN_DIGITS_INITIAL digit cards,
    # and if exclude_bomb True, do not include bombs in initial hand
    hand = []
    # ensure required digits
    for _ in range(MIN_DIGITS_INITIAL):
        hand.append(Card('digit', random.randint(0, 9)))
    while len(hand) < INITIAL_HAND_SIZE:
        c = draw_random_card()
        if exclude_bomb and c.type == 'func' and c.value == FUNC_BOMB:
            continue
        hand.append(c)
    random.shuffle(hand)
    return hand

# -----------------------
# Game engine
# -----------------------
class Game:
    def __init__(self, num_players, human_players):
        self.n = num_players
        self.players = []
        for i in range(num_players):
            is_human = i < human_players
            p = Player(i, f"P{i+1}", is_human=is_human)
            p.hand = draw_initial_hand(exclude_bomb=True)
            p.has_bomb_flag = any(c.type == 'func' and c.value == FUNC_BOMB for c in p.hand)
            self.players.append(p)

        self.secret = random.randint(SECRET_MIN, SECRET_MAX)
        self.round_index = 0  # increments each full turn passed to next player (for double cooldown)
        self.current_player_idx = 0
        # bomb in play tracking: when a bomb is played it is passed to next player. There can be at most one bomb in play.
        # We'll track bomb_passes count and whether a bomb is currently active and which player currently holds it.
        self.bomb_active = False
        self.bomb_holder_idx = None
        self.bomb_passes = 0  # how many times passed so far since original played
        self.pass_limit = bomb_pass_limit_for_players(self.n)
        # challenged boundaries history: set of numbers that have been declared AND were challenged at some point (cannot be reused)
        self.challenged_boundaries = set()
        # For logging and transparency
        self.verbose = False

    def show_public_state(self):
        print("\n---- 当前公开信息 ----")
        for p in self.players:
            funcs = p.func_list()
            func_str = ", ".join(f"{k}x{v}" for k, v in funcs.items()) if funcs else "无"
            print(f"{p.name}: 手牌数={p.count()} (数字牌数={p.count_digits()} 隐藏)，功能牌: {func_str}，跳过回合剩余={p.skip_rounds}")
        if self.bomb_active and self.bomb_holder_idx is not None:
            print(f"场上有炸弹，当前持有者: {self.players[self.bomb_holder_idx].name} (已传递 {self.bomb_passes} 次，阈值 {self.pass_limit})")
        else:
            print("场上无炸弹")
        print("----------------------\n")

    def show_player_hand(self, p: Player):
        # For current player only: show full hand
        s = []
        for i, c in enumerate(p.hand):
            s.append(f"[{i}] {c.name}")
        print("你的手牌:")
        print("  " + "  ".join(s))

    def next_player_index(self, idx):
        return (idx + 1) % self.n

    def previous_player_index(self, idx):
        return (idx - 1) % self.n

    def draw_cards_for(self, p: Player, count):
        cards = [draw_random_card() for _ in range(count)]
        p.add_cards(cards)
        return cards

    def enforce_bomb_holding_rule(self, p: Player):
        # At the start of player's turn, if they hold a bomb (i.e., there's a bomb in their hand),
        # and fail to play it this turn, it explodes and they must discard 4 cards.
        # We'll check and apply explosion if they don't play bomb when their turn ends.
        # The explosion effect severity depends on bomb_passes so far (if >= pass_limit, explosion cost = 2, otherwise 4).
        # Return explosion_cost if explosion occurs; we handle it externally after the choice is known.
        if any(c.type == 'func' and c.value == FUNC_BOMB for c in p.hand):
            return True
        return False

    def play(self):
        print("欢迎来到 千数谎牌 Thipher: Digit Bluff（简体中文）")
        print("游戏开始，系统已在 1-1000 中随机选取目标数字（仅系统与提示器知道）。")
        print("按回车开始。")
        input()
        # main loop
        while True:
            cur = self.players[self.current_player_idx]
            # skip if eliminated
            if not cur.alive:
                self.current_player_idx = self.next_player_index(self.current_player_idx)
                continue
            print(f"\n======== 回合 {self.round_index+1} - 当前玩家: {cur.name} {'(人类)' if cur.is_human else '(电脑)'} ========")
            # show public state and player's hand (if human)
            self.show_public_state()
            if cur.is_human:
                self.show_player_hand(cur)
            else:
                # for bot, also print summary
                print(f"{cur.name} 的手牌数: {cur.count()}（显示功能牌）: {cur.func_list()}")

            # Handle skip due to 禁止
            if cur.skip_rounds > 0:
                print(f"{cur.name} 被禁止，跳过本回合（剩余 {cur.skip_rounds} 回合）。")
                cur.skip_rounds -= 1
                # if holds bomb and doesn't play (they didn't), bomb explosion applies
                if self.enforce_bomb_holding_rule(cur):
                    # they didn't play bomb (since skipped), explosion happens:
                    # explosion severity depends if bomb_passes >= pass_limit: then cost=2 else cost=4
                    cost = 2 if self.bomb_passes >= self.pass_limit else 4
                    discarded = cur.discard_random(cost)
                    print(f"由于未打出炸弹，炸弹爆炸！{cur.name} 弃置 {len(discarded)} 张牌：{[c.name for c in discarded]}")
                    # remove bomb if it was in their hand (explosion consumes it)
                    new_has_bomb = any(c.type == 'func' and c.value == FUNC_BOMB for c in cur.hand)
                    if not new_has_bomb:
                        # bomb removed from their hand => no active bomb
                        self.bomb_active = False
                        self.bomb_holder_idx = None
                        self.bomb_passes = 0
                # advance
                self.advance_turn()
                continue

            # At start of turn, if bomb_active and bomb holder is this player (bomb passed to them), they have to play it or it may explode
            if self.bomb_active and self.bomb_holder_idx == self.current_player_idx:
                # they hold the bomb already in hand (since bomb passed to them)
                print(f"注意: 你当前持有炸弹（已传递 {self.bomb_passes} 次，阈值 {self.pass_limit}）。若本回合不打出炸弹将发生爆炸。")
                if cur.is_human:
                    pass  # human will decide
                else:
                    pass  # bot will decide

            # Offer option: if hand <=5, can choose to draw 3 cards instead of playing
            drew_for_choice = False
            if cur.count() <= 5:
                can_draw3 = True
            else:
                can_draw3 = False

            # Determine allowed action for current player: either draw3 (if eligible) or play
            # For human, interactive. For bot, choose according to simple heuristic.
            played_cards = []
            used_functions_in_play = []  # list of function card names used during the play (consumed)
            played_digit_values = []  # the numeric guesses (one or two values if double)
            used_wild_positions = []  # positions where wild used and its substitution digit if human choose
            did_double_play = False
            double_used_this_round = False
            addcard_used = False
            swap_used = False
            prohibit_used = False
            cunning_used = False
            bomb_played_this_move = False

            # For bots: a simplistic strategy: if have digit(s), play 1-2 digits; randomly use function cards sometimes.
            if not cur.is_human:
                # Decide draw3?
                if can_draw3 and random.random() < 0.25:
                    # choose to draw 3
                    print(f"{cur.name} 选择在本回合摸 3 张牌（因手牌数<=5）。")
                    new_cards = self.draw_cards_for(cur, 3)
                    print(f"{cur.name} 摸到: {[c.name for c in new_cards]}")
                    drew_for_choice = True
                    # After drawing, turn ends (rule said "你也可以选择在这一回合抽取3张牌" — ambiguous whether they can still play same turn;
                    # interpreting as choosing to draw instead of playing this turn.)
                    self.advance_turn()
                    continue
                # else plan to play
                # Decide to use 双出 if has and not used recently
                double_idx = cur.find_func_indices(FUNC_DOUBLE)
                want_double = False
                if double_idx and (self.round_index - cur.double_last_used_round) >= 2 and random.random() < 0.35:
                    want_double = True
                # choose number of cards to play (counting bomb=2)
                play_count_target = random.choice([1, 1, 2])  # bias to 1
                if want_double:
                    # we'll plan to use a double card
                    pass
                # Build play indices: prefer using digit cards with possibly a wild
                digits_idx = cur.find_digit_indices()
                if not digits_idx:
                    # must include at least one digit; else cannot play -> lose
                    print(f"{cur.name} 无法出牌（无数字牌），失败。")
                    cur.alive = False
                    print(f"{cur.name} 失败，游戏结束。")
                    return
                # prepare indices to play
                chosen_indices = []
                # pick first digit index as required
                chosen_indices.append(digits_idx[0])
                # maybe add another digit if available and within limit
                for di in digits_idx[1:]:
                    if len(chosen_indices) >= play_count_target:
                        break
                    chosen_indices.append(di)
                # if want double and have double function, add its index
                if want_double:
                    chosen_indices.extend(double_idx[:1])
                # maybe add addcard function
                add_idx = cur.find_func_indices(FUNC_ADDCARD)
                if add_idx and random.random() < 0.2 and len(chosen_indices) < 5:
                    chosen_indices.extend(add_idx[:1])
                # ensure unique and within bounds
                chosen_indices = sorted(set(chosen_indices))
                # enforce limit counting bomb as 2
                total_count = 0
                final_choice = []
                for i in chosen_indices:
                    c = cur.hand[i]
                    if c.type == 'func' and c.value == FUNC_BOMB:
                        # bomb counts as two
                        if total_count + 2 > 5:
                            continue
                        final_choice.append(i)
                        total_count += 2
                    else:
                        if total_count + 1 > 5:
                            continue
                        final_choice.append(i)
                        total_count += 1
                chosen_indices = final_choice
                # if no chosen indices -> just choose one digit
                if not chosen_indices:
                    chosen_indices = [digits_idx[0]]
                # perform the play
                played_cards = cur.remove_cards_by_indices(chosen_indices)
                print(f"{cur.name} 出了 {len(played_cards)} 张牌（对方只看到张数和功能牌，数字牌隐藏）")
                # record used function cards
                for c in played_cards:
                    if c.type == 'func':
                        used_functions_in_play.append(c.value)
                # process digits to form number(s)
                # For bots, treat digits in order of played_cards (left to right)
                # build numeric string from digit cards and wilds replaced randomly
                digits_in_play = [c for c in played_cards if c.type == 'digit' or (c.type == 'func' and c.value == FUNC_WILD)]
                # if no digits -> invalid
                if not digits_in_play:
                    print(f"{cur.name} 本次出牌中没有数字（或万能），违反规则，失败。")
                    cur.alive = False
                    print(f"{cur.name} 失败，游戏结束。")
                    return
                # build number
                # choose wild replacements randomly
                num_str = ""
                for c in digits_in_play:
                    if c.type == 'digit':
                        num_str += str(c.value)
                    else:
                        # wild
                        rep = str(random.randint(1, 9))  # avoid leading zero for first maybe
                        num_str += rep
                # enforce no leading zero:
                if len(num_str) > 1 and num_str[0] == '0':
                    # try to fix by replacing first digit if wild available else invalid -> pick replacement
                    num_str = num_str.lstrip('0') or "0"
                # turn into int
                guess_val = int(num_str)
                played_digit_values.append(guess_val)
                # handle function uses effects now (bomb, double etc.)
                if FUNC_BOMB in used_functions_in_play:
                    bomb_played_this_move = True
                if FUNC_DOUBLE in used_functions_in_play:
                    did_double_play = True
                    double_used_this_round = True
                if FUNC_ADDCARD in used_functions_in_play:
                    addcard_used = True
                if FUNC_CUNNING in used_functions_in_play:
                    cunning_used = True
                if FUNC_SWAP in used_functions_in_play:
                    swap_used = True
                if FUNC_PROHIBIT in used_functions_in_play:
                    prohibit_used = True
                # show to current player only the comparison result(s)
                # apply cunning_effect_active if present (affects display of first compare only)
                self.reveal_comparisons_to_player(cur, played_digit_values, cunning_effect_active=cur.cunning_effect_active)
                cur.cunning_effect_active = False
                # handle immediate win
                if any(v == self.secret for v in played_digit_values):
                    print(f"恭喜 {cur.name} 猜中目标数字 {self.secret}，取得胜利！")
                    return
                # process addcard draw
                if addcard_used:
                    new_cards = self.draw_cards_for(cur, 2)
                    print(f"{cur.name} 使用 加牌，额外摸到: {[c.name for c in new_cards]}")
                # process bomb played: pass bomb to next player
                if bomb_played_this_move:
                    # find bomb card among used_functions_in_play
                    # we removed it from current player's hand already and it's considered played: pass to next alive player (skip prohibited?), rule: "传递给下家。传递两次后（2人局为传递一次后）炸弹牌自动爆炸实效，此时爆炸需要爆炸的人丢弃2张手牌。若传递的下家同时被禁止，则传递给下家的下家。场上最多有一张炸弹牌。初始手牌不含有炸弹牌。"
                    next_idx = self.next_player_index(self.current_player_idx)
                    # if target is prohibited for this coming turn, skip to their next
                    # but prohibition refers to skipping a player's turn; here if the next player is currently with skip>0, pass to next next
                    loops = 0
                    while self.players[next_idx].skip_rounds > 0 and loops < self.n:
                        next_idx = self.next_player_index(next_idx)
                        loops += 1
                    # place bomb into next player's hand
                    bomb_card = Card('func', FUNC_BOMB)
                    self.players[next_idx].add_cards([bomb_card])
                    self.bomb_active = True
                    self.bomb_holder_idx = next_idx
                    self.bomb_passes += 1
                    print(f"炸弹被打出并传递给 {self.players[next_idx].name}（已传递 {self.bomb_passes} 次）")
                # process double: if used, allow an immediate next play by same player (subject to rule about cooldown)
                if did_double_play:
                    cur.double_last_used_round = self.round_index
                    # allow another play immediately by current player (we'll implement a simple immediate second play for bot)
                    # For bots: perform second random play similar to above but obey "上一回合使用后，则当前回合不能使用（即在过一圈后才能重新使用）" - we set last used round so they cannot use again next round
                    # For bot: second play choose 1 digit
                    digits_idx2 = cur.find_digit_indices()
                    if not digits_idx2:
                        print(f"{cur.name} 双出第二回合无法出牌（无数字牌），跳过第二回合。")
                    else:
                        idx2 = [digits_idx2[0]]
                        played_cards2 = cur.remove_cards_by_indices(idx2)
                        digits_in_play2 = [c for c in played_cards2 if c.type == 'digit' or (c.type == 'func' and c.value == FUNC_WILD)]
                        num_str2 = "".join(str(c.value) if c.type == 'digit' else str(random.randint(0,9)) for c in digits_in_play2)
                        if len(num_str2) > 1 and num_str2[0] == '0':
                            num_str2 = num_str2.lstrip('0') or "0"
                        guess2 = int(num_str2)
                        played_digit_values.append(guess2)
                        self.reveal_comparisons_to_player(cur, [guess2], cunning_effect_active=False)  # cunning only affects first of double
                        if guess2 == self.secret:
                            print(f"恭喜 {cur.name} 在双出第二次出牌中猜中目标数字 {self.secret}，取得胜利！")
                            return
                # After playing, perform mandatory declaration
                declared_correctly = self.declaration_phase(cur, played_digit_values)
                # After declaration and possible challenge, advance turn
                self.advance_turn()
                continue

            # Human player's interactive flow
            # present options: draw3 (if can), or play cards (must include at least one digit), view function cards known, etc.
            if cur.is_human:
                # Before human chooses, warn them about bomb in hand that will explode if not played
                if any(c.type == 'func' and c.value == FUNC_BOMB for c in cur.hand):
                    print("注意：你手中包含炸弹。如果本回合不打出炸弹，则炸弹会爆炸（会弃置若干牌）。")
                # Show function cards in hand explicitly (they're public, but help user)
                funcs = cur.func_list()
                if funcs:
                    print("你拥有的功能牌（本信息公开）：")
                    for k, v in funcs.items():
                        print(f"  {k} x{v}")
                # Prompt for action: draw3 or play
                while True:
                    choices = []
                    if can_draw3:
                        choices.append("1")
                        print("选项 1: 抽取 3 张牌（仅当手牌数<=5时可选，本回合不出牌）")
                    print("选项 2: 出牌")
                    print("选项 3: 查看规则摘要")
                    choice = input("请输入选项编号: ").strip()
                    if choice == "1" and can_draw3:
                        new_cards = self.draw_cards_for(cur, 3)
                        print(f"你摸到: {[c.name for c in new_cards]}")
                        drew_for_choice = True
                        break
                    elif choice == "2":
                        # Proceed to play: ask user to select indices up to 5 (bomb counts as 2)
                        while True:
                            print("请选择要出的牌（输入空格分隔的索引，例如: 0 2 3）。每次出牌必须包含至少一张数字牌（数字或万能）。炸弹计作两张。最多计数为5。")
                            self.show_player_hand(cur)
                            sel = input("输入要出的牌索引（或输入 cancel 返回）：").strip()
                            if sel.lower() in ("cancel", "c"):
                                break
                            try:
                                idxs = list(map(int, sel.split()))
                                if not idxs:
                                    print("必须选择至少一张牌。")
                                    continue
                                if any(i < 0 or i >= len(cur.hand) for i in idxs):
                                    print("索引越界，请重新选择。")
                                    continue
                                # compute count with bomb counting as 2
                                total_count = 0
                                has_digit = False
                                for i in idxs:
                                    c = cur.hand[i]
                                    if c.type == 'digit' or (c.type == 'func' and c.value == FUNC_WILD):
                                        has_digit = True
                                    if c.type == 'func' and c.value == FUNC_BOMB:
                                        total_count += 2
                                    else:
                                        total_count += 1
                                if not has_digit:
                                    print("出牌必须至少包含一张数字牌（数字或万能）。")
                                    continue
                                if total_count > 5:
                                    print(f"计数超出 5（当前计数 {total_count}），请减少选择。")
                                    continue
                                # If all good, remove selected cards
                                played_cards = cur.remove_cards_by_indices(sorted(idxs))
                                # record used functions
                                for c in played_cards:
                                    if c.type == 'func':
                                        used_functions_in_play.append(c.value)
                                # build digits for number formation
                                digits_in_play = [c for c in played_cards if c.type == 'digit' or (c.type == 'func' and c.value == FUNC_WILD)]
                                if not digits_in_play:
                                    print("意外：没有数字牌（包含万能）被选中，按规则应包含至少一张数字牌。你出牌失败。")
                                    cur.alive = False
                                    return
                                # For human, allow specifying order for digits and wild substitutions
                                print("你出的数字牌将按你提供的顺序组成一个数字（不允许前导零）。")
                                print("当前你出的数字/万能卡顺序如下（按位置编号）:")
                                for j, c in enumerate(digits_in_play):
                                    print(f"  pos{j}: {c.name}")
                                # Ask to provide order as permutation of positions
                                while True:
                                    order_input = input("输入顺序（pos 索引的空格序列），例如 '0 1 2'：").strip()
                                    try:
                                        order = list(map(int, order_input.split()))
                                        if sorted(order) != list(range(len(digits_in_play))):
                                            print("顺序索引无效，请按所有位置一次性提供排列。")
                                            continue
                                        break
                                    except Exception:
                                        print("输入无效，请重新输入。")
                                # Ask for wild replacements
                                wild_values = {}
                                for j, c in enumerate(digits_in_play):
                                    if c.type == 'func' and c.value == FUNC_WILD:
                                        while True:
                                            val = input(f"万能卡 pos{j} 要替代的数字（0-9）：").strip()
                                            if val.isdigit() and 0 <= int(val) <= 9:
                                                wild_values[j] = int(val)
                                                break
                                            else:
                                                print("请输入 0-9 的数字。")
                                # build the numeric string
                                num_chars = []
                                for pos in order:
                                    c = digits_in_play[pos]
                                    if c.type == 'digit':
                                        num_chars.append(str(c.value))
                                    else:
                                        num_chars.append(str(wild_values[pos]))
                                # check leading zero
                                if len(num_chars) > 1 and num_chars[0] == '0':
                                    print("不允许前导零。请重新组牌或调整替换。")
                                    # put cards back to player's hand in same order as removed
                                    cur.add_cards(played_cards)
                                    break  # to selection loop
                                num_str = "".join(num_chars)
                                guess_val = int(num_str)
                                played_digit_values.append(guess_val)
                                # process function cards used
                                if FUNC_ADDCARD in used_functions_in_play:
                                    addcard_used = True
                                if FUNC_DOUBLE in used_functions_in_play:
                                    # enforce cooldown: if used last round, cannot use now
                                    if (self.round_index - cur.double_last_used_round) < 2:
                                        print("双出本回合无法使用（上一回合使用过），请重新选择牌或移除双出卡。")
                                        # return cards
                                        cur.add_cards(played_cards)
                                        used_functions_in_play.clear()
                                        played_digit_values.clear()
                                        break
                                    else:
                                        did_double_play = True
                                        double_used_this_round = True
                                if FUNC_CUNNING in used_functions_in_play:
                                    cunning_used = True
                                if FUNC_SWAP in used_functions_in_play:
                                    swap_used = True
                                if FUNC_PROHIBIT in used_functions_in_play:
                                    prohibit_used = True
                                if FUNC_BOMB in used_functions_in_play:
                                    bomb_played_this_move = True
                                # Show comparison result to current player only
                                self.reveal_comparisons_to_player(cur, [guess_val], cunning_effect_active=cur.cunning_effect_active)
                                cur.cunning_effect_active = False
                                if guess_val == self.secret:
                                    print(f"恭喜 {cur.name} 猜中目标数字 {self.secret}，取得胜利！")
                                    return
                                # handle addcard draw
                                if addcard_used:
                                    new_cards = self.draw_cards_for(cur, 2)
                                    print(f"你使用了 加牌，额外摸到: {[c.name for c in new_cards]}")
                                # handle bomb played: pass bomb to next eligible player
                                if bomb_played_this_move:
                                    next_idx = self.next_player_index(self.current_player_idx)
                                    loops = 0
                                    while self.players[next_idx].skip_rounds > 0 and loops < self.n:
                                        next_idx = self.next_player_index(next_idx)
                                        loops += 1
                                    bomb_card = Card('func', FUNC_BOMB)
                                    self.players[next_idx].add_cards([bomb_card])
                                    self.bomb_active = True
                                    self.bomb_holder_idx = next_idx
                                    self.bomb_passes += 1
                                    print(f"炸弹被打出并传递给 {self.players[next_idx].name}（已传递 {self.bomb_passes} 次）")
                                # handle 双出: allow immediate second play
                                if did_double_play:
                                    cur.double_last_used_round = self.round_index
                                    # ask human if they want to perform second play now (they must, 因为双出使你可以再进行一回合)
                                    print("你使用了 双出，可以再进行一次出牌（第二次出牌）。")
                                    # For second play, allow similar but simpler process: choose indices, at least one digit, up to 5 count.
                                    while True:
                                        self.show_player_hand(cur)
                                        sel2 = input("第二次出牌 - 选择牌索引 (或输入 skip 取消第二次出牌): ").strip()
                                        if sel2.lower() in ("skip", "s"):
                                            print("取消第二次出牌。")
                                            break
                                        try:
                                            idxs2 = list(map(int, sel2.split()))
                                            if not idxs2:
                                                print("请至少选择一张牌或输入 skip。")
                                                continue
                                            if any(i < 0 or i >= len(cur.hand) for i in idxs2):
                                                print("索引越界，请重新选择。")
                                                continue
                                            total_count2 = 0
                                            has_digit2 = False
                                            for i in idxs2:
                                                c = cur.hand[i]
                                                if c.type == 'digit' or (c.type == 'func' and c.value == FUNC_WILD):
                                                    has_digit2 = True
                                                if c.type == 'func' and c.value == FUNC_BOMB:
                                                    total_count2 += 2
                                                else:
                                                    total_count2 += 1
                                            if not has_digit2:
                                                print("出牌必须至少包含一张数字牌（数字或万能）。")
                                                continue
                                            if total_count2 > 5:
                                                print("计数超出 5，请减少选择。")
                                                continue
                                            played_cards2 = cur.remove_cards_by_indices(sorted(idxs2))
                                            digits_in_play2 = [c for c in played_cards2 if c.type == 'digit' or (c.type == 'func' and c.value == FUNC_WILD)]
                                            if not digits_in_play2:
                                                print("意外：第二次出牌没有数字牌，取消第二次出牌并把牌放回。")
                                                cur.add_cards(played_cards2)
                                                break
                                            # allow order and wild replacement simpler: order as given, wild replacement prompts
                                            num_chars2 = []
                                            for j, c in enumerate(digits_in_play2):
                                                if c.type == 'digit':
                                                    num_chars2.append(str(c.value))
                                                else:
                                                    # wild
                                                    while True:
                                                        v = input(f"第二次出牌的 万能卡 pos{j} 替代数字 (0-9)：").strip()
                                                        if v.isdigit() and 0 <= int(v) <= 9:
                                                            num_chars2.append(v)
                                                            break
                                                        else:
                                                            print("请输入 0-9。")
                                            if len(num_chars2) > 1 and num_chars2[0] == '0':
                                                print("第二次出牌不允许前导零，取消第二次出牌并把牌放回。")
                                                cur.add_cards(played_cards2)
                                                break
                                            guess2 = int("".join(num_chars2))
                                            played_digit_values.append(guess2)
                                            # reveal only to player
                                            self.reveal_comparisons_to_player(cur, [guess2], cunning_effect_active=False)
                                            if guess2 == self.secret:
                                                print(f"恭喜 {cur.name} 在双出第二次出牌中猜中目标数字 {self.secret}，取得胜利！")
                                                return
                                            # note: the rule says 两次出牌仅需一次声明 -> we will collect both guesses into declaration later
                                            break
                                        except Exception as e:
                                            print("输入无效，请重试。", e)
                                # After playing, handle other function immediate effects if any (交换、禁止、狡猾)
                                # handle 交换: choose target and cards to swap
                                if swap_used:
                                    # select target player
                                    while True:
                                        try:
                                            t = int(input("请选择要与之交换的玩家编号 (例如 1 表示 P1): ")) - 1
                                            if t < 0 or t >= self.n or t == cur.id:
                                                print("无效玩家，请重试。")
                                                continue
                                            # choose 1-5 cards from own hand to exchange (bomb不可交换)
                                            self.show_player_hand(cur)
                                            selswap = input("选择要交换的自己手牌索引（空格分隔，1-5 张，炸弹不可交换）：").strip()
                                            idxs_swap = list(map(int, selswap.split()))
                                            if not (1 <= len(idxs_swap) <= 5):
                                                print("请选择 1-5 张牌。")
                                                continue
                                            # check none is bomb
                                            if any(cur.hand[i].type == 'func' and cur.hand[i].value == FUNC_BOMB for i in idxs_swap):
                                                print("炸弹不能被交换，请重新选择。")
                                                continue
                                            # now choose: remove these from cur and randomly pick same number from target's hand to transfer
                                            give_cards = cur.remove_cards_by_indices(sorted(idxs_swap))
                                            # from target pick random selections (bombs cannot be given)
                                            target = self.players[t]
                                            available_target_indices = [i for i, c in enumerate(target.hand) if not (c.type == 'func' and c.value == FUNC_BOMB)]
                                            if len(available_target_indices) < len(give_cards):
                                                # if insufficient non-bomb cards, then choose as many as possible
                                                take_indices = available_target_indices
                                            else:
                                                take_indices = random.sample(available_target_indices, len(give_cards))
                                            taken = target.remove_cards_by_indices(sorted(take_indices))
                                            # exchange
                                            cur.add_cards(taken)
                                            target.add_cards(give_cards)
                                            print(f"你与 {target.name} 交换了 {len(give_cards)} 张牌。对方随机交给了你 {[c.name for c in taken]}")
                                            break
                                        except Exception as e:
                                            print("输入无效，请重试。", e)
                                # handle 禁止: select target and set skip_rounds +=1
                                if prohibit_used:
                                    while True:
                                        try:
                                            t = int(input("请选择要禁止的玩家编号 (例如 1 表示 P1): ")) - 1
                                            if t < 0 or t >= self.n or t == cur.id:
                                                print("无效玩家，请重试。")
                                                continue
                                            self.players[t].skip_rounds += 1
                                            print(f"{self.players[t].name} 将被禁止一回合（下次轮到其时跳过）。")
                                            break
                                        except Exception:
                                            print("输入无效，请重试。")
                                # handle 狡猾: next player will have cunning effect (only affects next comparison; if next player double-plays, only first round affected)
                                if cunning_used:
                                    next_idx = self.next_player_index(self.current_player_idx)
                                    self.players[next_idx].cunning_effect_active = True
                                    print(f"狡猾已使用，下一位玩家 ({self.players[next_idx].name}) 的第一次比对会受到特殊显示效果影响。")
                                # After all immediate function effects, process add/draw already done, bomb pass done earlier
                                # Now mandatory declaration (covering all played_digit_values from this player's plays in this turn)
                                declared_correctly = self.declaration_phase(cur, played_digit_values)
                                break  # exit play selection loop
                            except Exception as e:
                                print("输入异常，请重试。", e)
                        # leave selection loop to either drew_for_choice or played
                        break
                    elif choice == "3":
                        self.print_rules_brief()
                    else:
                        print("输入无效，请重试。")

                if drew_for_choice:
                    # player drew 3 and their turn ends
                    self.advance_turn()
                    continue
                else:
                    # After playing and declaration already handled, advance turn
                    self.advance_turn()
                    continue

    def reveal_comparisons_to_player(self, player: Player, guesses, cunning_effect_active=False):
        # Reveal comparison results (only to that player). For each guess in guesses:
        # normally display: guess < a / guess > a / guess == a
        # if cunning_effect_active: display "与目标数字相差超过/不超过 某数字" as per rule,
        # i.e., display whether abs(a - guess) > guess (大于算超过，小于等于算不超过).
        for idx, g in enumerate(guesses):
            if cunning_effect_active and idx == 0:
                diff = abs(self.secret - g)
                if diff > g:
                    print(f"[私人] 对你出的 {g} 的显示: {g} 与目标数字相差超过 {g}")
                else:
                    print(f"[私人] 对你出的 {g} 的显示: {g} 与目标数字相差不超过 {g}")
            else:
                if g == self.secret:
                    print(f"[私人] 你的出牌 {g} 与目标数字相等！")
                elif g < self.secret:
                    print(f"[私人] 你的出牌 {g} 小于目标数字。")
                else:
                    print(f"[私人] 你的出牌 {g} 大于目标数字。")

    def declaration_phase(self, player: Player, guesses):
        # After a player (maybe with 双出 producing multiple guesses) has played, they must向全部人声明
        # 格式: “目标数字大于/小于 某数字”。可以撒谎，但与自己所猜测的数据不能相差20以上（双出时只需与其中一次的猜测差不超过20）。
        # 但不能与曾经所有玩家声明过且被质疑的边界数字相同（即 challenged_boundaries）。
        # If the previous effect was 狡猾 and the display format is different, the declaration format must be "目标数字与某数字相差超过/不超过 某数字" — implemented by passing a flag.
        # After declaration, next player can choose 质疑 or 相信. If 质疑:
        # - 若声明的范围是错的 -> challenger +2 cards, declarer 丢弃3张。
        # - 若声明的范围是正确 -> challenger 丢弃2张，declarer +1张。
        # 质疑的信息公布全员（比如揭示所出的猜测与目标的实际比较结果）。
        # returns True if declaration stands (not necessarily truthful), but used for internal logging.
        # Implementation:
        # Determine allowed boundary numbers: must be within 20 of at least one of the guesses.
        # For human player: prompt for declaration text. For bot: choose randomly consistent boundary.
        print(f"\n{player.name} 现在需要向所有人声明信息（你必须声明：目标数字 大于/小于 某数字）")
        # Determine whether cunning display was used on player previously: that changed only what they saw, not declaration format.
        # The special declaration format (相差超过/不超过) is used only when player was shown cunning? The rule says:
        # 狡猾: 可以使下家获得的数据变为该数字与随机数a相差是否超过该数字的值 ... 此时声明格式为目标数字与某数字相差超过/不超过某数字。
        # So if the player's displayed info was changed by 狡猾, they must declare using that format.
        format_cunning = False  # default
        # We can know if prior player used 狡猾 targeting this player by checking player.cunning_effect_active was used earlier; but we cleared that when revealing.
        # To enforce: if the player was affected by cunning at the time of reveal, they should have known. For simplicity, if they previously had cunning_effect_active True at start of play we used that in reveal and then cleared it.
        # We cannot detect here; so we won't change format except if player had earlier 'cunning_flag_decl_required'—not stored.
        # For safety, skip special format enforcement unless there's a reason; but we will give players choice to declare in either standard or cunning format.
        # Determine allowed boundaries
        allowed_boundaries = set()
        for g in guesses:
            for delta in range(-20, 21):
                candidate = g + delta
                if candidate >= 0:  # allow zero boundary though secret is >=1
                    allowed_boundaries.add(candidate)
        # remove any boundary numbers that are in challenged_boundaries (cannot reuse)
        allowed_boundaries = allowed_boundaries - self.challenged_boundaries
        if not allowed_boundaries:
            print("竟然没有合法可声明的边界（被历史质疑边界全部占用），你自动失败。")
            player.alive = False
            return False
        # For human: prompt input; for bot: pick randomly from allowed set and choose greater/less or cunning format if affected.
        declared = None  # tuple (kind, boundary, format_cunning_bool) where kind in {'>', '<'} or {'diff>','diff<'}
        if player.is_human:
            print("声明限制：你声明的边界数字必须与本回合你实际出的某一次数字相差不超过 20，且不能与曾被质疑过的边界数字相同。")
            while True:
                print("声明格式选项：")
                print("  1) 标准：'目标数字 大于/小于 N'（例如：大于 500）")
                print("  2) 狡猾格式：'目标数字 与 N 相差超过/不超过 N'（当你在比对时曾被狡猾影响，可使用/也可使用标准）")
                fmt_choice = input("请选择格式 1 或 2（按回车默认 1）: ").strip() or "1"
                if fmt_choice not in ("1", "2"):
                    print("请输入 1 或 2。")
                    continue
                if fmt_choice == "2":
                    format_cunning = True
                # Now ask for direction and boundary
                if format_cunning:
                    print("请选择： 1) 相差超过  2) 相差不超过")
                    dir_choice = input("输入 1 或 2: ").strip()
                    if dir_choice not in ("1", "2"):
                        print("无效输入")
                        continue
                    dir_sym = 'diff>' if dir_choice == "1" else 'diff<'
                else:
                    print("请选择： 1) 大于  2) 小于")
                    dir_choice = input("输入 1 或 2: ").strip()
                    if dir_choice not in ("1", "2"):
                        print("无效输入")
                        continue
                    dir_sym = '>' if dir_choice == "1" else '<'
                bound_str = input("请输入边界数字 N（整数，例如 500）: ").strip()
                if not bound_str.lstrip('-').isdigit():
                    print("请输入整数。")
                    continue
                bound = int(bound_str)
                if bound not in allowed_boundaries:
                    print("所选边界不被允许（须与本回合某一次猜测相差 ≤20，且不能与曾被质疑过的边界数字相同）。")
                    # let player choose again
                    continue
                declared = (dir_sym, bound, format_cunning)
                break
        else:
            # bot picks a boundary near one of its guesses
            chosen_guess = random.choice(guesses)
            # pick a delta within [-20,20]
            delta = random.randint(-20, 20)
            bound = chosen_guess + delta
            if bound in self.challenged_boundaries:
                # adjust by searching nearby allowed boundary
                found = None
                for d in range(0, 21):
                    for s in (-1, 1):
                        cand = bound + s * d
                        if cand in allowed_boundaries:
                            found = cand
                            break
                    if found is not None:
                        break
                if found is None:
                    # fallback
                    found = random.choice(list(allowed_boundaries))
                bound = found
            dir_sym = random.choice(['>', '<'])
            format_cunning = False
            declared = (dir_sym, bound, format_cunning)
            print(f"{player.name} 声明: {'目标数字 大于' if dir_sym=='>' else '目标数字 小于'} {bound}")

        # Broadcast declaration
        if declared[2]:
            # cunning format
            stmt = f"目标数字与 {declared[1]} 相差 {'超过' if declared[0]=='diff>' else '不超过'} {declared[1]}"
        else:
            stmt = f"目标数字 {'大于' if declared[0]=='>' else '小于'} {declared[1]}"
        print(f"{player.name} 向所有人声明：{stmt} （该声明可为真可为假）")

        # Next player can choose to challenge or believe
        next_idx = self.next_player_index(player.id)
        next_player = self.players[next_idx]
        if next_player.is_human:
            # prompt human
            while True:
                ch = input(f"{next_player.name}：是否质疑? 输入 y 质疑，n 相信（默认 n）: ").strip().lower() or "n"
                if ch not in ('y', 'n'):
                    print("请输入 y 或 n。")
                    continue
                challenge = (ch == 'y')
                break
        else:
            # simple bot logic: random challenge based on probability influenced by hand size
            # bots more likely to challenge if opponent has few cards (to punish) or if their own hand big.
            prob_challenge = 0.25 + 0.02 * (next_player.count() - player.count())
            prob_challenge = max(0.05, min(0.6, prob_challenge))
            challenge = random.random() < prob_challenge
            print(f"{next_player.name} {'选择质疑' if challenge else '选择相信'}（由 AI 决定）。")

        if challenge:
            print(f"{next_player.name} 发起质疑，揭示相关信息……")
            # Reveal the actual information (comparisons) to all: show for each guess whether >/</= target (or for cunning-format reveal appropriate)
            for g in guesses:
                if g == self.secret:
                    comp = "等于"
                elif g < self.secret:
                    comp = "小于"
                else:
                    comp = "大于"
                print(f"公开信息: 玩家 {player.name} 的出牌 {g} 与目标数字比较结果: {g} {comp} 目标数字")
            # Evaluate whether the declaration was correct.
            dir_sym, bound, fmt_c = declared
            if fmt_c:
                # declaration was about difference exceeding or not
                diff = abs(self.secret - bound)
                declared_truth = (diff > bound) if dir_sym == 'diff>' else (diff <= bound)
            else:
                if dir_sym == '>':
                    declared_truth = (self.secret > bound)
                else:
                    declared_truth = (self.secret < bound)
            if declared_truth:
                # challenger loses 2 cards, declarer gets +1 card
                print(f"声明为真：{next_player.name} 弃置 2 张牌，{player.name} 抽取 1 张牌作为奖励。")
                lost = next_player.discard_random(2)
                print(f"{next_player.name} 弃置: {[c.name for c in lost]}")
                new_draw = self.draw_cards_for(player, 1)
                print(f"{player.name} 获得: {[c.name for c in new_draw]}")
                # Since challenge happened, this boundary is considered "被质疑过的边界"，需要加入 challenged_boundaries
                self.challenged_boundaries.add(bound)
            else:
                # challenger gets +2, declarer discards 3
                print(f"声明为假：{next_player.name} 获得 2 张牌，{player.name} 弃置 3 张牌。")
                gained = self.draw_cards_for(next_player, 2)
                print(f"{next_player.name} 获得: {[c.name for c in gained]}")
                lost = player.discard_random(3)
                print(f"{player.name} 弃置: {[c.name for c in lost]}")
                self.challenged_boundaries.add(bound)
            # return True for having been processed
            return declared_truth
        else:
            # no challenge: declaration stands (but not verified)
            print(f"{next_player.name} 选择相信声明。声明未被质疑，不影响牌数。")
            return True

    def print_rules_brief(self):
        print(textwrap.dedent("""
        规则摘要（简要）：
        - 系统在 1-1000 中选取秘密数字 a（仅系统知道）。
        - 每人初始牌 10 张（至少 5 张数字牌）。2-4 人游玩。
        - 回合按顺序进行。每人可出 1-5 张牌（炸弹计为两张），必须至少含一张数字牌（数字或万能）。
        - 多张数字牌按出牌的顺序组成一个数字（不允许前导零），与秘密数字比较，比较结果仅对出牌者可见；若相等则该玩家胜利。
        - 出牌时向所有人显示出牌数，并且所有玩家的功能牌公开（数字牌隐藏）。
        - 当手牌数 <= 5 时，可选择本回合抽取 3 张牌（代替出牌）。
        - 出牌后需向所有人声明“目标数字大于/小于 N”（可撒谎），声明必须与本回合自己所出的某一次猜测相差不超过 20（双出时满足其中一次即可），且不得与曾被质疑过的边界数字相同。
        - 下家可以质疑或相信。质疑后若声明为假，质疑者 +2 张，上家弃 3 张；若声明为真，质疑者弃 2 张，上家 +1 张。质疑信息公开。
        - 牌堆无限。若某玩家牌数 < 0 或违反出牌规则，则该玩家失败。
        功能牌：
        - 禁止：指定玩家停止一回合（skip_rounds += 1）。
        - 加牌：本回合出牌同时摸 2 张牌。
        - 双出：使用后本回合可以再进行一次出牌（使用后需过一圈才能再用）。
        - 万能：可代替任意数字牌。
        - 交换：选择 1-5 张牌与某玩家交换（自己选出，目标随机交给你相同数量的牌），炸弹不可交换。
        - 炸弹：出牌时计为 2 张。若手中持有炸弹且当回合不打出，则炸弹爆炸并弃牌（爆炸弃牌数依传递次数而定）。打出后炸弹传递给下家；传递次数达到阈值后下一次爆炸损失变小（见实现）。
        - 狡猾：使下家获得的数据变为“该数字与目标相差是否超过该数字”（只影响对方看到的显示；若对方双出仅影响第一次显示）。
        """))

    def advance_turn(self):
        # advance the current player index; increment round if we've completed a cycle?
        # We'll increment round_index only when moving from last player to player 0
        prev_idx = self.current_player_idx
        self.current_player_idx = self.next_player_index(self.current_player_idx)
        if self.current_player_idx == 0:
            self.round_index += 1
        # Check bomb holder tracking: if bomb is active and we moved to bomb holder, everything okay.
        # If bomb is active and some player's hand got bomb by being passed, bomb_holder_idx updated at time of pass.
        # Also if any player's hand contains bomb due to draws, we set bomb_active and bomb_holder appropriately.
        # Clean up dead players and check loss conditions
        for p in self.players:
            if p.count() < 0:
                p.alive = False
        # Endgame check: only one alive or any player lost by negative count triggers game end.
        alive_players = [p for p in self.players if p.alive and p.count() >= 0]
        if len(alive_players) <= 1:
            if alive_players:
                print(f"游戏结束，最终胜利者: {alive_players[0].name}")
            else:
                print("游戏结束，未剩下玩家。")
            sys.exit(0)

# -----------------------
# Entrypoint and CLI
# -----------------------
def main():
    print("Thipher: Digit Bluff（千数谎牌） - 单文件命令行初版")
    while True:
        try:
            num_players = int(input(f"请输入玩家总人数（{MIN_PLAYERS}-{MAX_PLAYERS}）：").strip())
            if num_players < MIN_PLAYERS or num_players > MAX_PLAYERS:
                print("玩家人数不合法。")
                continue
            break
        except Exception:
            print("请输入整数。")
    while True:
        try:
            human_players = int(input(f"其中多少为人类玩家（1-{num_players}）：").strip())
            if human_players < 1 or human_players > num_players:
                print("人数不合法。")
                continue
            break
        except Exception:
            print("请输入整数。")
    # create game
    game = Game(num_players, human_players)
    # For debug: allow showing secret (comment out normally)
    # print(f"[DEBUG] secret = {game.secret}")
    game.play()

if __name__ == "__main__":
    main()