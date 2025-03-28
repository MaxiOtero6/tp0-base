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

// Run Starts the client. It sends all bets to the server
// and then waits for the draw results
func (c *Client) Run(maxBatchAmount int) {
	err := c.createClientSocket()
	defer c.conn.Close()

	if err != nil {
		return
	}

	ret := c.SendAllBets(maxBatchAmount)

	if !ret {
		return
	}

	ret = c.NotifyAllBetsSent()

	if !ret {
		return
	}

	ret = c.RequestDrawResults()

	if !ret {
		return
	}

	c.shutdownConnection()
	// Wait docker to flush stdout/stderr before exiting
	time.Sleep(c.config.LoopPeriod)
}

// NotifyAllBetsSent Notifies the server that all bets have been sent
func (c *Client) NotifyAllBetsSent() (ret bool) {
	select {
	case <-c.done:
		return
	default:
		for {
			msgToSend := []byte(fmt.Sprintf("%v %v\n", packets.BetDraw, c.config.ID))

			response, err := c.stopAndWait(msgToSend)

			if err != nil {
				return
			}

			if response == packets.FAIL_RESULT {
				log.Errorf("action: notificar_sorteo | result: fail | client_id: %v", c.config.ID)
				continue
			}

			log.Infof("action: notificar_sorteo | result: success | client_id: %v", c.config.ID)

			ret = true
			return
		}
	}
}

// RequestDrawResults Requests the draw results to the server
// until the server responds with the results or an error occurs
func (c *Client) RequestDrawResults() (ret bool) {
	var winners []string

	select {
	case <-c.done:
		return
	default:
		for winners == nil {
			msgToSend := []byte(fmt.Sprintf("%v %v\n", packets.DrawResults, c.config.ID))
			response, err := c.stopAndWait(msgToSend)

			if err != nil {
				log.Infof("action: consulta_ganadores | result: fail")
				return
			}

			results := packets.GetDrawResults(response)

			if results == nil {
				// Wait a time between sending one message and the next one
				time.Sleep(c.config.LoopPeriod)
				continue
			}

			winners = results
		}

		log.Infof("action: consulta_ganadores | result: success | cant_ganadores: %v", len(winners))
	}

	ret = true
	return
}

// stopAndWait Sends a message to the server and waits for the response
// to return it. In case of error, it is returned
func (c *Client) stopAndWait(msgToSend []byte) (response string, err error) {
	err = c.conn.SendAll(msgToSend)

	if err != nil {
		log.Errorf("action: send_message | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
		return
	}

	msgRecv, err := c.conn.ReadAll()

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

// shutdownConnection Sends a message to the server to close the connection
// and waits for the response.
func (c *Client) shutdownConnection() {
	select {
	case <-c.done:
		return
	default:
		msg := []byte(fmt.Sprintf("%v success\n", packets.ShutdownConnection))
		_, err := c.stopAndWait(msg)

		if err != nil {
			log.Errorf("action: cerrar_conexion | result: fail | client_id: %v", c.config.ID)
			return
		}

		log.Infof("action: cerrar_conexion | result: success | client_id: %v", c.config.ID)
	}
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
		}
	}

	ret = true

	log.Infof("action: loop_finished | result: success | client_id: %v", c.config.ID)
	return
}

// Shutdown Closes the client connection and sends a signal
// to the client to finish its execution gracefully
func (c *Client) Shutdown() {
	close(c.done)
	c.conn.Close()
}
