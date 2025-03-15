#!/bin/bash

MESSAGE="tp0-health-check"
PORT=12345

RESPONSE=$( \
    echo -n "$MESSAGE" | \
    docker run -i --network tp0_testing_net alpine nc server "$PORT" \
)

if [ "$MESSAGE" = "$RESPONSE" ]; then
    echo "action: test_echo_server | result: success"
else
    echo "action: test_echo_server | result: fail"
fi
