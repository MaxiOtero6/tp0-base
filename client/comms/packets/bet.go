package packets

import (
	"fmt"
	"strconv"
	"strings"
)

// BetPacket Struct that encapsulates the bet packet data
type BetPacket struct {
	Agency    int
	FirstName string
	LastName  string
	Document  string
	Birthdate string
	Number    int
}

// Error returned when unknown fields for a BetPacket are received
type deserializationError struct {
	Data string
}

func (e *deserializationError) Error() string {
	return "Deserialization error, expected <document> <bet-number>, got: " + e.Data
}

// NewBetResponse Deserializes a message into a BetPacket struct
func NewBetResponse(data string) (*BetPacket, error) {
	split := strings.Split(data, " ")

	if len(split) != 2 {
		return nil, &deserializationError{Data: data}
	}

	agency_raw := split[0]
	number_raw := split[1]

	agency, err := strconv.Atoi(agency_raw)
	if err != nil {
		return nil, err
	}

	number, err := strconv.Atoi(number_raw)
	if err != nil {
		return nil, err
	}

	return &BetPacket{
		Agency: agency,
		Number: number,
	}, nil
}

// Serialize Serializes a BetPacket into a byte array
func (p *BetPacket) Serialize() []byte {
	header := "bet "

	msg := header +
		fmt.Sprint(p.Agency) + " " +
		strings.ReplaceAll(p.FirstName, " ", "-") + " " +
		strings.ReplaceAll(p.LastName, " ", "-") + " " +
		p.Document + " " +
		p.Birthdate + " " +
		fmt.Sprint(p.Number) + "\n"

	return []byte(msg)
}
