#!/bin/bash
# System Information Script
# Prints basic system info, takes user input, and saves running processes to a file.

# Store data in variables
RUN_STAMP=$(date)
MACHINE_ID=$(hostname)
ACTIVE_USER=$(whoami)

echo "=============================="
echo " SYSTEM INFORMATION"
echo "=============================="

echo "Current Date : $RUN_STAMP"
echo "Hostname     : $MACHINE_ID"
echo "Username     : $ACTIVE_USER"

echo ""
echo "----- Disk Usage -----"
df -h

echo ""
echo "----- Running Processes -----"
ps aux

# Take input from the user
echo ""
read -p "Enter a name for the report directory: " REPORT_DIR
read -p "Enter a name for the report file: " REPORT_FILE

# Create directory and file
mkdir -p "$REPORT_DIR"
touch "$REPORT_DIR/$REPORT_FILE"

# Store running processes in the file using output redirection
ps aux > "$REPORT_DIR/$REPORT_FILE"

echo ""
echo "Running processes saved to: $REPORT_DIR/$REPORT_FILE"
