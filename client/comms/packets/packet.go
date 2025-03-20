package packets

import (
	"strings"
)

type PacketType string

// Packet types enum
const (
	Bet         PacketType = "bet"
	BetDraw     PacketType = "betdraw"
	DrawResults PacketType = "betdrawresults"
)

// Error returned when an unknown packet is received
type unknownPacket struct {
	Header PacketType
}

func (e *unknownPacket) Error() string {
	return "Unknown packet: " + string(e.Header)
}

// Deserialize Deserializes a message into a string by packetType
// in case of unknown packet an error is returned
func Deserialize(msg []byte) (string, error) {
	data := string(msg)

	split := strings.SplitN(data, " ", 2)

	packetType := PacketType(split[0])

	switch packetType {
	case Bet:
		return split[1], nil
	case BetDraw:
		return split[1], nil
	case DrawResults:
		return split[1], nil
	default:
		return "", &unknownPacket{Header: packetType}
	}
}
