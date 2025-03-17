package common

import (
	"fmt"
	"os"
	"strconv"

	"github.com/7574-sistemas-distribuidos/docker-compose-init/client/comms/packets"
)

// newBet Creates a new bet packet with the data from the environment variables
func newBet() (packets.BetPacket, error) {
	firstname := os.Getenv("NOMBRE")
	lastname := os.Getenv("APELLIDO")
	document := os.Getenv("DOCUMENTO")
	birthdate := os.Getenv("NACIMIENTO")

	if firstname == "" || lastname == "" || document == "" || birthdate == "" {
		return packets.BetPacket{}, fmt.Errorf("missing required fields")
	}

	agency, err := strconv.Atoi(os.Getenv("CLI_ID"))

	if err != nil {
		return packets.BetPacket{}, fmt.Errorf("missing required fields")
	}

	number, err := strconv.Atoi(os.Getenv("NUMERO"))
	if err != nil {
		return packets.BetPacket{}, fmt.Errorf("missing required fields")
	}

	return packets.BetPacket{
		Agency:    agency,
		FirstName: firstname,
		LastName:  lastname,
		Document:  document,
		Birthdate: birthdate,
		Number:    number,
	}, nil
}
