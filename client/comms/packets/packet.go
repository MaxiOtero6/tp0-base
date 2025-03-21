package packets

import (
	"fmt"
	"strings"
)

type PacketType string

// Packet types enum
const (
	Bet PacketType = "bet"
)

// Error returned when an unknown packet is received
type unknownPacket struct {
	Header PacketType
}

func (e *unknownPacket) Error() string {
	return "Unknown packet: " + string(e.Header)
}

// Deserialize Deserializes a message into a packet struct
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
	default:
		return "", &unknownPacket{Header: packetType}
	}
}
