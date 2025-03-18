package packets

import (
	"fmt"
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

// SerializeBets Serializes BetPackets into a byte array
func SerializeBets(batch []BetPacket) []byte {
	msg := "bet "

	for idx, p := range batch {
		if idx > 0 {
			msg += "&"
		}

		msg += fmt.Sprint(p.Agency) + " " +
			strings.ReplaceAll(p.FirstName, " ", "-") + " " +
			strings.ReplaceAll(p.LastName, " ", "-") + " " +
			p.Document + " " +
			p.Birthdate + " " +
			fmt.Sprint(p.Number)
	}

	msg += "\n"
	return []byte(msg)
}
