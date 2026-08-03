# card.py
# 牌类定义

class Card:
    def __init__(self, card_type, value=None):
        self.type = card_type   # 'digit' 或 'func'
        self.value = value
        if card_type == 'digit':
            self.name = str(value)
        else:
            self.name = value

    def is_digit(self):
        return self.type == 'digit'

    def is_func(self, func_name):
        return self.type == 'func' and self.value == func_name

    def __repr__(self):
        return f"Card({self.name})"