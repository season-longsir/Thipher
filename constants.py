# To save some constants.


MIN_PLAYERS = 2
MAX_PLAYERS = 4

INITIAL_HAND_SIZE = 10
MIN_DIGITS_INITIAL = 5

SECRET_MIN = 1
SECRET_MAX = 1000

FUNCTION_NAMES = {'禁止', '加牌', '双出', '万能', '交换', '炸弹', '狡猾'}
FUNC_PROB = 0.25
FUNC_WEIGHTS = {
    '禁止': 1.0,
    '加牌': 1.0,
    '双出': 0.9,
    '万能': 0.9,
    '交换': 1.0,
    '炸弹': 0.6,
    '狡猾': 0.8
}