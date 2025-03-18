import signal
import logging
from comms.socket import Socket
from common.utils import Bet, store_bets
from comms.packet import BetDeserializationError, deserialize, serialize


class Server:
    def __init__(self, port: int, listen_backlog: int):
        # Initialize server socket
        self._server_socket = Socket(
            address=('', port), listen_backlog=listen_backlog
        )

        self._running = False

        signal.signal(signal.SIGTERM, self.__shutdown)

    def run(self) -> None:
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        self._running = True

        while self._running:
            try:
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

            bet_batch: list[Bet] = deserialize(msg)
            store_bets(bet_batch)

            logging.info(
                f"action: apuesta_recibida | result: success | cantidad: {len(bet_batch)}"
            )

            success_msg: bytes = "bet success\n".encode("utf-8")
            client_sock.send_all(success_msg)
        except BetDeserializationError as e:
            logging.error(
                f"action: apuesta_recibida | result: fail | cantidad: {e.bets_len}"
            )

            fail_msg: bytes = "bet fail\n".encode("utf-8")
            client_sock.send_all(fail_msg)
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
