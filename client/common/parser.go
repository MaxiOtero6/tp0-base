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
}

// newParser Initializes a new parser with the client id and the max batch amount
// opening the file with the agency data
func newParser(clientId int, maxBatchAmount int) (*Parser, error) {
	path := fmt.Sprintf("./data/agency-%v.csv", clientId)
	file, err := os.OpenFile(path, os.O_RDONLY, 0644)

	if err != nil {
		return nil, err
	}

	return &Parser{file: file, maxBatchAmount: maxBatchAmount, agency: clientId}, nil
}

// close Closes the file
func (p *Parser) close() {
	p.file.Close()
}

// newBet Creates a new bet batch reading data from the agency csv file
// until the max batch amount is reached or the file ends, each line is
// expected to have the following format: <first-name>,<last-name>,<document>,<birthdate>,<number>
func (p *Parser) newBets() ([]packets.BetPacket, error) {
	reader := bufio.NewReader(p.file)

	var batch []packets.BetPacket

	for i := 0; i < p.maxBatchAmount; i++ {
		line, err := reader.ReadString('\n')
		line = strings.TrimSpace(line) // Remove '\r\n'

		if err == io.EOF {
			return batch, err
		}

		if err != nil {
			// TODO
			fmt.Println("err")
			continue
		}

		split := strings.Split(line, ",")

		if len(split) != 5 {
			// TODO
			fmt.Println("len err")
			continue
		}

		number, err := strconv.Atoi(split[4])

		if err != nil {
			// TODO
			fmt.Println("num err")
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
