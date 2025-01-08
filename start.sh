#!/bin/bash

# Ensure /data directory exists
mkdir -p /data

# Copy cookies.txt to /data
cp ./cookies.txt /data/cookies.txt

# Start the Gunicorn server
gunicorn app:app
