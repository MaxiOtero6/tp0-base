from common.utils import Bet

BET_HEADER = "bet"


def deserialize(data: bytes) -> Bet:
    """
    Deserialize a Bet object from a byte string.
    """
    split = data.decode("utf-8").split(" ")

    if len(split) != 7 or split.pop(0) != BET_HEADER:
        raise ValueError("Invalid message format")

    agency: str = split.pop(0)
    first_name: str = split.pop(0).replace("-", " ")
    last_name: str = split.pop(0).replace("-", " ")
    document: str = split.pop(0)
    birthday: str = split.pop(0)
    number: str = split.pop(0)

    return Bet(agency, first_name, last_name, document, birthday, number)


def serialize(bet: Bet) -> bytes:
    """
    Serialize a Bet object to a byte string.
    """
    return f"{BET_HEADER} {bet.document} {bet.number}\n".encode("utf-8")
