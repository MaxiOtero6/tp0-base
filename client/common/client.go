package common

import (
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

// SendAllBets Send bets to the server until all bets are sent
// or the file ends. The client will wait a time between sending
// one message and the next one
func (c *Client) SendAllBets(maxBatchAmount int) {
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

			// Create the connection the server in every loop iteration. Send an array of bets
			// and wait for the response
			c.createClientSocket()

			err = c.conn.SendAll(packets.SerializeBets(batch))

			if err != nil {
				log.Errorf("action: send_message | result: fail | client_id: %v | error: %v",
					c.config.ID,
					err,
				)
				c.conn.Close()
				return
			}

			msg, err := c.conn.ReadAll()
			c.conn.Close()

			if err != nil {
				log.Errorf("action: receive_message | result: fail | client_id: %v | error: %v",
					c.config.ID,
					err,
				)
				return
			}

			response, err := packets.Deserialize(msg)

			if err != nil {
				log.Errorf("action: receive_message | result: fail | client_id: %v | error: %v",
					c.config.ID,
					err,
				)
				return
			}

			log.Infof("action: receive_message | result: success | client_id: %v | msg: %v",
				c.config.ID,
				msg,
			)

			log.Infof("action: apuesta_enviada | result: %v | client_id: %v", response, c.config.ID)

			// Wait a time between sending one message and the next one
			time.Sleep(c.config.LoopPeriod)
		}
	}

	log.Infof("action: loop_finished | result: success | client_id: %v", c.config.ID)
}

// Shutdown Closes the client connection and sends a signal
// to the client to finish its execution gracefully
func (c *Client) Shutdown() {
	c.done <- true
	c.conn.Close()
}
