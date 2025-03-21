import signal
import logging
from comms.socket import Socket
from common.utils import Bet, has_won, load_bets, store_bets
from comms.packet import BetDeserializationError, deserialize_bets, deserialize_header
from server.common.bet_monitor import Action, BetMonitor


class Server:
    def __init__(self, port: int, listen_backlog: int, clients_amount: int):
        # Initialize server socket
        self._server_socket = Socket(
            address=('', port), listen_backlog=listen_backlog
        )

        self.__bet_monitor: BetMonitor = BetMonitor(clients_amount)
        self._running = False

        signal.signal(signal.SIGTERM, self.__shutdown)

    def run(self) -> None:
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

    def __handle_bet(self, client_sock: Socket, msg: str) -> None:
        """
        Store the bets received from the client
        If the bets are not correctly deserialized, a fail message is sent
        """
        try:
            bet_batch: list[Bet] = deserialize_bets(msg)

            self.__bet_monitor.push_action(
                (Action.STORE_BETS, bet_batch)
            )

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

    def __handle_draw(self, client_sock: Socket, msg: str) -> None:
        """
        Confirm the draw of a specific agency
        If the agency id is not a number, a fail message is sent
        """
        try:
            client_id: int = int(msg)

            self.__bet_monitor.push_action(
                (Action.REGISTER_READY_AGENCY, client_id)
            )

            logging.info(
                f"action: confirmacion_sorteo | result: success | id: {client_id}"
            )

            success_msg: bytes = "betdraw success\n".encode("utf-8")
            client_sock.send_all(success_msg)
        except ValueError as e:
            logging.error(
                f"action: confirmacion_sorteo | result: fail"
            )

            fail_msg: bytes = "betdraw fail\n".encode("utf-8")
            client_sock.send_all(fail_msg)

    def __handle_bet_results(self, client_sock: Socket, msg: str) -> None:
        """
        Send the results of the bet draw to the client
        If the agency id is not found because it has not drawn yet, a fail message is sent
        If the agency id is not found because it has already been sent, a fail message is sent
        If the agency id is not a number, a fail message is sent
        """
        try:
            agency_id: int = int(msg)

            winners: list[Bet] = self.__bet_monitor.request_winners(agency_id)
            winners_documents: str = "&".join([i.document for i in winners])

            winners_msg: bytes = f"betdrawresults success {winners_documents}\n".encode(
                "utf-8")

            logging.info(
                f"action: resultados_apuestas | result: success | id: {agency_id} | cantidad: {len(winners)}"
            )

            client_sock.send_all(winners_msg)
        except (ValueError, KeyError) as e:
            fail_msg: bytes = "betdrawresults fail\n".encode("utf-8")
            client_sock.send_all(fail_msg)

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

        Function that closes the server socket, stops the server loop
        and waits for the bet monitor to join
        """
        self._running = False
        self._server_socket.close()
        self.__bet_monitor.shutdown()

        signal_name: str = signal.Signals(signum).name
        logging.info(
            f'action: exit | result: success | signal: {signal_name}')
