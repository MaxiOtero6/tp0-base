from enum import Enum
import logging
from queue import Queue
from typing import Any
from server.common.utils import Bet, has_won, store_bets as store_bets_in_file, load_bets
from threading import Lock, Thread


class Action(Enum):
    """
    Enum class that represents the possible actions that the BetMonitor can
    receive
    """
    STORE_BETS = "store_bets"
    REGISTER_READY_AGENCY = "register_ready_agency"
    SHUTDOWN = "shutdown"


class BetMonitor:
    """
    Class that represents the BetMonitor component of the server
    it consumes actions from a queue and stores the winners of the bets
    """
    __queue: Queue[tuple[Action, Any]] = Queue()
    __winners_lock: Lock = Lock()
    __bet_winners_by_agency: dict[int, list[Bet]] = dict()
    __worker: Thread
    __running: bool
    __clients_amount: int

    def __init__(self, clients_amount: int):
        self.__worker = Thread(target=self.__run)
        self.__worker.start()
        self.__clients_amount = clients_amount

    def push_action(self, action: tuple[Action, Any]) -> None:
        """
        Push an action to the queue
        """
        self.__queue.put(action, block=True)

    def request_winners(self, agency_id: int) -> list[Bet]:
        """
        Request the winners of a specific agency thread-safely
        """
        with self.__winners_lock:
            return self.__bet_winners_by_agency.pop(agency_id)

    def shutdown(self) -> None:
        """
        Shutdown the BetMonitor and wait for the worker to join
        """
        self.push_action((Action.SHUTDOWN, None))
        self.__queue.join()
        self.__worker.join()

    def __run(self) -> None:
        """
        Main loop of the BetMonitor that waits blocking for actions in the queue
        """
        agencies_ready_to_draw: set = set()
        self.__running = True

        while self.__running:
            action, data = self.__queue.get(block=True)

            if action == Action.STORE_BETS:
                store_bets_in_file(data)

            elif action == Action.REGISTER_READY_AGENCY:
                agencies_ready_to_draw.add(data)
                if len(agencies_ready_to_draw) == self.__clients_amount:
                    self.__draw_bets(agencies_ready_to_draw)

            elif action == Action.SHUTDOWN:
                self.__running = False

            self.__queue.task_done()

    def __draw_bets(self, agencies_ready_to_draw: set[int]) -> None:
        """
        Draw the bets and store the winners
        """
        bets: list[Bet] = load_bets()
        winners: list[Bet] = [bet for bet in bets if has_won(bet)]

        with self.__winners_lock:
            for agency_id in agencies_ready_to_draw:
                self.__bet_winners_by_agency[agency_id] = [
                    bet for bet in winners if bet.agency == agency_id
                ]

            logging.info("action: sorteo | result: success")

        agencies_ready_to_draw.clear()
