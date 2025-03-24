package common

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"

	"github.com/7574-sistemas-distribuidos/docker-compose-init/client/comms/packets"
)

// Parser Struct that encapsulates the opened file and the max batch amount
type Parser struct {
	file           *os.File
	maxBatchAmount int
	agency         int
	reader         *bufio.Reader
}

// newParser Initializes a new parser with the client id and the max batch amount
// opening the file with the agency data
func newParser(clientId int, maxBatchAmount int) (*Parser, error) {
	path := fmt.Sprintf("./data/agency-%v.csv", clientId)
	file, err := os.OpenFile(path, os.O_RDONLY, 0644)

	if err != nil {
		return nil, err
	}

	reader := bufio.NewReader(file)

	return &Parser{file: file, maxBatchAmount: maxBatchAmount, agency: clientId, reader: reader}, nil
}

// close Closes the file
func (p *Parser) close() {
	if p.file != nil {
		p.file.Close()
	}
}

// newBet Creates a new bet batch reading data from the agency csv file
// until the max batch amount is reached or the file ends, each line is
// expected to have the following format: <first-name>,<last-name>,<document>,<birthdate>,<number>
func (p *Parser) newBets() ([]packets.BetPacket, error) {
	var batch []packets.BetPacket

	for i := 0; i < p.maxBatchAmount; i++ {
		line, err := p.reader.ReadString('\n')
		line = strings.TrimRight(line, "\r\t\n") // Remove '\r\n'

		if err == io.EOF {
			return batch, err
		}

		if err != nil {
			log.Warningf("action: read_line | result: fail | error: %v", err)
			return nil, err
		}

		split := strings.Split(line, ",")

		if len(split) != 5 {
			log.Warningf("action: split_line | result: fail | line: %v", line)
			continue
		}

		number, err := strconv.Atoi(split[4])

		if err != nil {
			log.Warningf("action: parse_number | result: fail | number: %v", split[4])
			continue
		}

		bet := packets.BetPacket{
			Agency:    p.agency,
			FirstName: split[0],
			LastName:  split[1],
			Document:  split[2],
			Birthdate: split[3],
			Number:    number,
		}

		batch = append(batch, bet)
	}

	return batch, nil
}
