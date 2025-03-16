package comms

import (
	"bufio"
	"io"
	"net"

	"github.com/op/go-logging"
)

var log = logging.MustGetLogger("log")

// Socket Struct that encapsulates the socket connection
type Socket struct {
	conn net.Conn
}

// NewSocket Initiliazes a new socket connection
func NewSocket(address string) (Socket, error) {
	conn, err := net.Dial("tcp", address)

	if err != nil {
		return Socket{}, err
	}

	return Socket{conn: conn}, nil
}

// Close Closes the socket connection
func (s *Socket) Close() {
	s.conn.Close()
}

// ReadAll Reads all the data from the socket connection avoiding short reads
// when EOF or '\n' is found in the data stream it stops reading
func (s *Socket) ReadAll() ([]byte, error) {
	var result []byte
	reader := bufio.NewReader(s.conn)

	for {
		part, err := reader.ReadBytes('\n')
		result = append(result, part...)

		if err == io.EOF {
			break
		}

		if err != nil {
			return nil, err
		}

		if len(part) > 0 && part[len(part)-1] == '\n' {
			break
		}
	}

	return result, nil
}

// SendAll Sends all the data to the socket connection avoiding short writes
func (s *Socket) SendAll(msg []byte) {
	for len(msg) > 0 {
		n, err := s.conn.Write(msg)

		if err != nil {
			log.Criticalf(
				"action: send_message | result: fail | error: %v",
				err,
			)
			return
		}

		msg = msg[n:]
	}
}
