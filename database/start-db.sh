#!/bin/bash

if [ ! -f docker.env ]; then
    echo "Error: docker.env file not found. Please create one."
    exit 1
fi

export $(grep -v '^#' docker.env | xargs)

if [ -z "$USER_PREFIX" ] || [ -z "$HOST_PORT" ]; then
    echo "Error: USER_PREFIX or HOST_PORT is missing in docker.env file."
    exit 1
fi

VOLUME_NAME="${USER_PREFIX}-data-dev"

if ! docker volume inspect "$Volume_Name" > /dev/null 2>&1; then
    echo "Creating external docker volume: $VOLUME_NAME..."
    docker volume create "$VOLUME_NAME"
else
    echo "Volume '$VOLUME_NAME' already exists."
fi

echo "Starting database container for user '$USER_PREFIX' on port '$HOST_PORT'"

docker compose -f docker-compose.dev.yml up -d

echo "Check logs with command docker logs pol-postgres-dev-$USER_PREFIX"