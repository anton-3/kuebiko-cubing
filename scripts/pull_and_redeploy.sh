#!/usr/bin/env bash

# pull the latest code
git pull

# rebuild the docker image
docker compose up --build -d