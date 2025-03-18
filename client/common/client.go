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
// failure, error is printed in stdout/stderr and exit 1
// is returned
func (c *Client) createClientSocket() error {
	conn, err := comms.NewSocket(c.config.ServerAddress)

	if err != nil {
		log.Criticalf(
			"action: connect | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
	}

	c.conn = conn
	return nil
}

// StartClientLoop Send messages to the client until some time threshold is met
func (c *Client) StartClientLoop(maxBatchAmount int) {
	parser, err := newParser(c.config.ID, maxBatchAmount)

	if err != nil {
		log.Criticalf("action: create_parser | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
	}

	var fileErr error
	var batch []packets.BetPacket

	// There is an autoincremental msgID to identify every message sent
	// Messages if the message amount threshold has not been surpassed
	for fileErr != io.EOF {
		select {
		case <-c.done:
			parser.close()
			return
		default:
			batch, fileErr = parser.newBets()

			if err != nil {
				log.Errorf("action: create_bet | result: fail | client_id: %v | error: %v",
					c.config.ID,
					err,
				)
				parser.close()
				return
			}

			// Create the connection the server in every loop iteration. Send an
			c.createClientSocket()

			err = c.conn.SendAll(packets.SerializeBets(batch))

			if err != nil {
				log.Errorf("action: send_message | result: fail | client_id: %v | error: %v",
					c.config.ID,
					err,
				)
				c.conn.Close()
				parser.close()
				return
			}

			msg, err := c.conn.ReadAll()
			c.conn.Close()

			if err != nil {
				log.Errorf("action: receive_message | result: fail | client_id: %v | error: %v",
					c.config.ID,
					err,
				)
				parser.close()
				return
			}

			response, err := packets.Deserialize(msg)

			if err != nil {
				log.Errorf("action: receive_message | result: fail | client_id: %v | error: %v",
					c.config.ID,
					err,
				)
				parser.close()
				return
			}

			log.Infof("action: receive_message | result: success | client_id: %v | msg: %v",
				c.config.ID,
				msg,
			)

			log.Infof("action: apuesta_enviada | result: success | dni: %v | numero: %v",
				response.Document,
				response.Number,
			)

			// Wait a time between sending one message and the next one
			time.Sleep(c.config.LoopPeriod)
		}
	}

	parser.close()
	log.Infof("action: loop_finished | result: success | client_id: %v", c.config.ID)
}

func (c *Client) Shutdown() {
	c.done <- true
	c.conn.Close()
}
