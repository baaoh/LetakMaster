#!/bin/bash

# --- LetakMaster Hub Setup Script for Synology NAS ---
# Usage: bash setup_hub.sh <YOUR_GITHUB_REPO_URL>

REPO_URL=$1

if [ -z "$REPO_URL" ]; then
    echo "Usage: bash setup_hub.sh <YOUR_GITHUB_REPO_URL>"
    exit 1
fi

# 1. Clone or Pull
if [ -d ".git" ]; then
    echo "Project exists. Pulling latest updates..."
    git pull
else
    echo "Cloning LetakMaster from GitHub..."
    git clone $REPO_URL .
fi

# 2. Setup the Shared Network Folder (if it doesn't exist)
# This is where the actual Excel/PSD files will be stored.
mkdir -p /volume1/LetakMaster_Assets

# 3. Build & Launch the Containers (Linux Hub + Postgres)
# Synology's 'docker-compose' is often 'docker compose' or 'docker-compose'
echo "Starting LetakMaster Hub Containers..."
docker-compose up -d --build

echo "-------------------------------------------------------"
echo "Hub is now running at: http://$(hostname -I | awk '{print $1}'):8000"
echo "Database is running at: 5432"
echo "-------------------------------------------------------"
