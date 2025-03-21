package comms

import (
	"bufio"
	"io"
	"net"
)

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

	if len(result) == 0 {
		return nil, io.EOF
	}

	return result[:len(result)-1], nil // Remove '\n'
}

// SendAll Sends all the data to the socket connection avoiding short writes
func (s *Socket) SendAll(msg []byte) error {
	for len(msg) > 0 {
		n, err := s.conn.Write(msg)

		if err != nil {
			return err
		}

		msg = msg[n:]
	}

	return nil
}
