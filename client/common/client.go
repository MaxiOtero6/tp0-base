package common

import (
	"fmt"
	"io"
	"time"

	"github.com/7574-sistemas-distribuidos/docker-compose-init/client/comms"
	"github.com/7574-sistemas-distribuidos/docker-compose-init/client/comms/packets"
	"github.com/op/go-logging"
)

var log = logging.MustGetLogger("log")

// ClientConfig Configuration used by the client
type ClientConfig struct {
	ID            int
	ServerAddress string
	LoopAmount    int
	LoopPeriod    time.Duration
}

// Client Entity that encapsulates how
type Client struct {
	config ClientConfig
	conn   comms.Socket
	done   chan bool
}

// NewClient Initializes a new client receiving the configuration
// as a parameter
func NewClient(config ClientConfig) *Client {
	client := &Client{
		config: config,
		done:   make(chan bool, 1),
	}
	return client
}

// CreateClientSocket Initializes client socket. In case of
// failure, error is printed in stdout/stderr and
// is returned
func (c *Client) createClientSocket() error {
	conn, err := comms.NewSocket(c.config.ServerAddress)

	if err != nil {
		log.Criticalf(
			"action: connect | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
		return err
	}

	c.conn = conn
	return nil
}

// NotifyAllBetsSent Notifies the server that all bets have been sent
func (c *Client) NotifyAllBetsSent() (ret bool) {
	select {
	case <-c.done:
		return
	default:
		msgToSend := []byte(fmt.Sprintf("betdraw %v\n", c.config.ID))

		response, err := c.stopAndWait(msgToSend)

		if err != nil {
			return
		}

		if response == "fail" {
			log.Errorf("action: notificar_sorteo | result: fail | client_id: %v", c.config.ID)
			return
		}

		log.Infof("action: notificar_sorteo | result: success | client_id: %v", c.config.ID)

		ret = true
		return
	}
}


// stopAndWait Sends a message to the server and waits for the response
// to return it. In case of error, it is returned
func (c *Client) stopAndWait(msgToSend []byte) (response string, err error) {
	err = c.createClientSocket()

	if err != nil {
		return
	}

	err = c.conn.SendAll(msgToSend)

	if err != nil {
		log.Errorf("action: send_message | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
		c.conn.Close()
		return
	}

	msgRecv, err := c.conn.ReadAll()
	c.conn.Close()

	if err != nil {
		log.Errorf("action: receive_message | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
		return
	}

	response, err = packets.Deserialize(msgRecv)

	if err != nil {
		log.Errorf("action: receive_message | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
		return
	}

	return
}

// SendAllBets Send bets to the server until all bets are sent
// or the file ends. The client will wait a time between sending
// one message and the next one. If an error occurs, it is returned
func (c *Client) SendAllBets(maxBatchAmount int) (ret bool) {
	parser, err := newParser(c.config.ID, maxBatchAmount)

	if err != nil {
		log.Criticalf("action: create_parser | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
	}

	defer parser.close()

	var fileErr error
	var batch []packets.BetPacket

outer:
	for fileErr != io.EOF {
		select {
		case <-c.done:
			return
		default:
			batch, fileErr = parser.newBets()

			if len(batch) == 0 {
				break outer
			}

			if err != nil {
				log.Errorf("action: create_bet | result: fail | client_id: %v | error: %v",
					c.config.ID,
					err,
				)
				return
			}

			response, err := c.stopAndWait(packets.SerializeBets(batch))

			if err != nil {
				return
			}

			log.Infof("action: receive_message | result: success | client_id: %v | msg: %v",
				c.config.ID,
				response,
			)

			log.Infof("action: apuesta_enviada | result: %v | client_id: %v", response, c.config.ID)

			// Wait a time between sending one message and the next one
			time.Sleep(c.config.LoopPeriod)
		}
	}

	ret = true

	log.Infof("action: loop_finished | result: success | client_id: %v", c.config.ID)
	return
}

// Shutdown Closes the client connection and sends a signal
// to the client to finish its execution gracefully
func (c *Client) Shutdown() {
	c.done <- true
	c.conn.Close()
}
