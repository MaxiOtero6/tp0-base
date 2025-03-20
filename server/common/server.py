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
                client_sock = self.__accept_new_connection()
                self.__handle_client_connection(client_sock)
                
                if len(self._agencies_ready_to_draw) == clients_amount:
                    self.__draw_bets()

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

    def __handle_bet(self, client_sock: Socket, msg: str) -> None:
        """
        Store the bets received from the client
        If the bets are not correctly deserialized, a fail message is sent
        """
        try:
            bet_batch: list[Bet] = deserialize_bets(msg)
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

    def __handle_draw(self, client_sock: Socket, msg: str) -> None:
        """
        Confirm the draw of a specific agency
        If the agency id is not a number, a fail message is sent
        """
        try:
            client_id: int = int(msg)

            self._agencies_ready_to_draw.add(client_id)

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

            winners: list[Bet] = self._bet_winners_by_agency.pop(agency_id)
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

        Function that closes the server socket and stops the server loop
        """
        self._running = False
        self._server_socket.close()
        signal_name: str = signal.Signals(signum).name
        logging.info(
            f'action: exit | result: success | signal: {signal_name}')
