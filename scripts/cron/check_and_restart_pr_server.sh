#!/bin/bash

# PR_HOME is the directory that holds live/, scripts/ and Backups/.
# Defaults to the current directory, so run from that directory or export it.
PR_HOME="${PR_HOME:-$(pwd)}"; export PR_HOME

# Path to your restart script
RESTART_SCRIPT="$PR_HOME/scripts/restart_pr_server.sh"

# Path to the lock file
LOCK_FILE="/tmp/check_and_restart_pr_server.lock"

# Function to check if the game server is online with dynamic port input
check_server_online() {
  local ports=("$@")  # Use function arguments as the list of ports
  for port in "${ports[@]}"; do
    if echo "QUIT" | nc -w 1 localhost "$port" | grep -q "Welcome to"; then
      return 0
    fi
  done
  return 1
}

# Function to check for the lock file and ensure only one instance runs
check_lock_file() {
  if [ -e "$LOCK_FILE" ]; then
    local pid
    pid=$(cat "$LOCK_FILE")
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      rm -f "$LOCK_FILE" >/dev/null 2>&1
    else
      exit 1
    fi
  fi
}

# Call the lock file check function
check_lock_file

# Create the lock file
touch "$LOCK_FILE"

# Write the PID of the current instance to the lock file
echo $$ > "$LOCK_FILE"

# Ensure the lock file is removed on exit
trap 'rm -f "$LOCK_FILE"; exit' EXIT SIGINT SIGTERM

# Retry logic
retry_count=0
max_retries=3
retry_interval=30

while (( retry_count < max_retries )); do
  if check_server_online "5024" "2150"; then
    exit 0
  else
    sleep "$retry_interval"
    (( retry_count++ ))
  fi
done

# If server is still offline after retries, run the restart script
bash "$RESTART_SCRIPT" -i

