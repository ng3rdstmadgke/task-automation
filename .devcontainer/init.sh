#!/bin/bash

mkdir -p ~/.ssh
mkdir -p ~/.aws
mkdir -p ~/.task-automation/.claude
[ ! -f ~/.task-automation/.claude.json ] && echo '{}' > ~/.task-automation/.claude.json
mkdir -p ~/.task-automation/.gemini
mkdir -p ~/.task-automation/.kube
mkdir -p ~/.task-automation/.config/helm

DOCKER_NETWORK=br-task-automation-${USER}
NETWORK_EXISTS=$(docker network ls --filter name=$DOCKER_NETWORK --format '{{.Name}}')

if [ -z "$NETWORK_EXISTS" ]; then
  docker network create $DOCKER_NETWORK
fi