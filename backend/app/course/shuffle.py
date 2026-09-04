import random


def shuffled_order(seed: str, count: int) -> list[int]:
    """Return a permutation of range(count) that is reproducible from the seed."""
    order = list(range(count))
    random.Random(seed).shuffle(order)
    return order
