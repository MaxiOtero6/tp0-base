package packets

import (
	"fmt"
	"strings"
)

type PacketType string

// Packet types enum
const (
	Bet                PacketType = "bet"
	BetDraw            PacketType = "betdraw"
	DrawResults        PacketType = "betdrawresults"
	ShutdownConnection PacketType = "shutdown-connection"
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

	if len(split) != 2 {
		return "", fmt.Errorf("invalid message: %v", data)
	}

	packetType := PacketType(split[0])

	switch packetType {
	case Bet:
		return split[1], nil
	case BetDraw:
		return split[1], nil
	case DrawResults:
		return split[1], nil
	case ShutdownConnection:
		return split[1], nil
	default:
		return "", &unknownPacket{Header: packetType}
	}
}

// GetDrawResults Returns the draw results from a message
// in case of error returns nil
func GetDrawResults(data string) []string {
	split := strings.SplitN(data, " ", 2)

	if split[0] == "fail" {
		return nil
	}

	if len(split[1]) == 0 {
		return []string{}
	}

	return strings.Split(split[1], "&")
}
