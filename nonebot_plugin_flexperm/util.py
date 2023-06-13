from typing import Union


def try_int(s: str) -> Union[str, int]:
    try:
        return int(s)
    except ValueError:
        return s
