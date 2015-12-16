#!/bin/bash

touch -f $KAFKA_DIR/logs/controller.log
#touch -f $KAFKA_DIR/logs/server.log
touch -f $KAFKA_DIR/logs/kafkaServer-gc.log 
touch -f $KAFKA_DIR/logs/log-cleaner.log
touch -f $KAFKA_DIR/logs/kafka-request.log
touch -f $KAFKA_DIR/logs/state-change.log

tail -f $KAFKA_DIR/logs/controller.log &
#tail -f $KAFKA_DIR/logs/server.log &
tail -f $KAFKA_DIR/logs/kafkaServer-gc.log &
tail -f $KAFKA_DIR/logs/log-cleaner.log &
tail -f $KAFKA_DIR/logs/kafka-request.log &
tail -f $KAFKA_DIR/logs/state-change.log &

exec /usr/bin/env python3 -u /tmp/start_kafka_and_reassign_partitions.py
