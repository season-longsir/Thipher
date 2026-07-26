# To create object Card.


from constants import FUNCTION_NAMES


class Card:
    def __init__(self, card_type, value):
        if card_type == 'digit':
            if not isinstance(value, int) or not (0 <= value <= 9):
                raise ValueError(f'The value of the digit card({value}) is illegal!')
            self.type = 'digit'
            self.value = value
            self.name = str(value)
        elif card_type == 'func':
            if value not in FUNCTION_NAMES:
                raise ValueError(f'Unknown functiong card name: {value}!')
            self.type = 'func'
            self.value = value
            self.name = value
        else:
            raise ValueError(f'Unknown card type: {card_type}!')

    def is_digit(self):
        return self.type == 'digit'

    def is_func(self):
        return self.type == 'func'

    def __repr__(self):
        if self.is_digit():
            return f'Digit({self.value})'
        else:
            return f'Func({self.value})'

    def __str__(self):
        return self.name


def mk_card(id):
    if id in FUNCTION_NAMES:
        return Card('func', id)
    else:
        try:
            val = int(id)
            if 0 <= val <= 9:
                return Card('digit', val)
            else:
                raise ValueError(f'Unknown digit card mark: {val}')
        except:
            raise ValueError(f'Unknown card mark: {id}')