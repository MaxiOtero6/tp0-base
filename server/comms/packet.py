from common.utils import Bet

BET_HEADER = "bet"


class BetDeserializationError(ValueError):
    """
    Exception raised when a deserialization error occurs.
    """
    bets_len: int

    def __init__(self, len: int):
        self.bets_len = len
        super().__init__("Invalid message format, expected 6 fields")


def __deserialize(data: str) -> Bet:
    """
    Deserialize a Bet object from a byte string.
    """
    split = data.split(" ")

    if len(split) != 6:
        raise ValueError()

    agency: str = split.pop(0)
    first_name: str = split.pop(0).replace("-", " ")
    last_name: str = split.pop(0).replace("-", " ")
    document: str = split.pop(0)
    birthday: str = split.pop(0)
    number: str = split.pop(0)

    return Bet(agency, first_name, last_name, document, birthday, number)


def deserialize(data: bytes) -> list[Bet]:
    """
    Deserialize a list of Bet objects from a byte string.
    """

    split = data.decode("utf-8").split(" ", maxsplit=1)

    if split.pop(0) != BET_HEADER:
        raise ValueError(
            f"Invalid message format, expected '{BET_HEADER}' keyword"
        )

    bets_raw: list[str] = split.pop(0).split("&")

    try:
        return [__deserialize(i) for i in bets_raw]
    except ValueError as e:
        raise BetDeserializationError(len(bets_raw)) from e
