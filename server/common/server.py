import signal
import logging
from comms.socket import Socket
from common.utils import Bet, has_won, load_bets, store_bets
from comms.packet import BetDeserializationError, deserialize_bets, deserialize_header


class Server:
    def __init__(self, port: int, listen_backlog: int):
        # Initialize server socket
        self._server_socket = Socket(
            address=('', port), listen_backlog=listen_backlog
        )

        self._running = False
        self._agencies_ready_to_draw: set = set()
        self._bet_winners_by_agency: dict[int, list[Bet]] = dict()

        signal.signal(signal.SIGTERM, self.__shutdown)

    def run(self, clients_amount: int) -> None:
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again.
        If {clients_amount} clients have notified that they are ready to draw
        the server will draw the bets and store the winners by agency
        """

        self._running = True

        while self._running:
            try:
                if len(self._agencies_ready_to_draw) == clients_amount:
                    self.__draw_bets()

                client_sock = self.__accept_new_connection()
                self.__handle_client_connection(client_sock)

            except OSError as e:
                if self._running:
                    logging.error(
                        f"action: accept_connections | result: fail | error: {str(e)}")

    def __handle_client_connection(self, client_sock: Socket) -> None:
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        try:
            msg: bytes = client_sock.recv_all()
            addr: tuple[str, int] = client_sock.address

            logging.info(
                f'action: receive_message | result: success | ip: {addr[0]} | msg: {msg}'
            )

            header, body = deserialize_header(msg)

            if header == "bet":
                self.__handle_bet(client_sock, body)
            elif header == "betdraw":
                self.__handle_draw(client_sock, body)
            elif header == "betdrawresults":
                self.__handle_bet_results(client_sock, body)
            else:
                logging.error(
                    f"action: receive_message | result: fail | error: invalid header"
                )

        except (ValueError, OSError) as e:
            logging.error(
                f"action: receive_message | result: fail | error: {str(e)}"
            )
        finally:
            client_sock.close()
            
    def __draw_bets(self) -> None:
        """
        Draw bets and store winners by agency
        """
        bets: list[Bet] = load_bets()
        winners: list[Bet] = [bet for bet in bets if has_won(bet)]

        for agency_id in self._agencies_ready_to_draw:
            self._bet_winners_by_agency[agency_id] = [
                bet for bet in winners if bet.agency == agency_id
            ]

        self._agencies_ready_to_draw.clear()
        logging.info("action: sorteo | result: success")

        except ValueError as e:
            logging.error(
                f"action: receive_message | result: fail | error: {str(e)}"
            )
        except OSError as e:
            logging.error(
                f"action: receive_message | result: fail | error: {str(e)}"
            )
        finally:
            client_sock.close()

    def __accept_new_connection(self) -> Socket:
        """
        Accept new connections

        Function blocks until a connection to a client is made.
        Then connection created is printed and returned
        """

        # Connection arrived
        logging.info('action: accept_connections | result: in_progress')
        return self._server_socket.accept()

    def __shutdown(self, signum, frame):
        """
        Shutdown server

        Function that closes the server socket and stops the server loop
        """
        self._running = False
        self._server_socket.close()
        signal_name: str = signal.Signals(signum).name
        logging.info(
            f'action: exit | result: success | signal: {signal_name}')
