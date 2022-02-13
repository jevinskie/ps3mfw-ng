
def round_up(n: int, mul: int) -> int:
    return n + -n % mul

def round_down(n: int, mul: int) -> int:
    return n - n % mul

