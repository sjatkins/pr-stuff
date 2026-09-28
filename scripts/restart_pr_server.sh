#!/bin/bash

SERVER_LIVE_DIR="$HOME/live"
SERVER_LIB_DIR="$SERVER_LIVE_DIR/lib"
WORLD_SAVE_DIR="$SERVER_LIB_DIR/WorldSave"
WORLD_SAVE_MISC_DIR="$SERVER_LIB_DIR/WorldSave/Misc"
ROOM_SAVE_DIR="$SERVER_LIB_DIR/RoomSave"
SERVER_SCRIPT="$SERVER_LIVE_DIR/PR_SERVER_SCRIPT"
MAX_AUTO_RESTART_RETRIES=20
AUTO_RESTART_RETRIES_BEFORE_TRY_CLEAN=15

# Define the array of server ports to check
SERVER_PORTS=(5024 2150)  # Add the ports you want to check

# Path to the attempt file
ATTEMPT_FILE="/tmp/pr_server_restart_attempts"

# Path to the lock file
LOCK_FILE="/tmp/restart_pr_server.lock"

# Path to auto check restart lock file
AUTO_CHECK_RESTART_LOCK_FILE="/tmp/check_and_restart_pr_server.lock"

# Default values for optional flags
clear_files=false
max_retries=3
dry_run=false
silent=false

# Function to display usage information
usage() {
  echo "Usage: $0 [-c] [-m max-retries] [-d] [-i] [-h]"
  echo ""
  echo "Options:"
  echo "  -c        Clear world and save files before starting the server. (Clean reboot)"
  echo "  -m        Set the maximum number of retry attempts for killing processes (default: 3)."
  echo "  -d        Dry-run mode. Display actions without executing them."
  echo "  -i        Silent mode. Suppress output except for errors."
  echo "  -h        Display this help message."
  exit 1
}

# Function to parse arguments using getopts
parse_args() {
  while getopts ":cim:dh" opt; do
    case $opt in
      c) clear_files=true ;;
      m)
        if [[ $OPTARG =~ ^[0-9]+$ ]] && [[ $OPTARG -ge 1 ]]; then
          max_retries=$OPTARG
        else
          echo "Error: -m must be a positive integer."
          exit 1
        fi
        ;;
      d) dry_run=true ;;
      i) silent=true ;;  # Silent mode option
      h) usage ;;
      \?) echo "Invalid option: -$OPTARG" >&2; usage ;;
      :) echo "Option -$OPTARG requires an argument." >&2; usage ;;
    esac
  done
}

# Function to log messages
log() {
  if ! $silent; then
    echo "$(date +'%Y-%m-%d %H:%M:%S') - $1"
  fi
}

# Function to perform a countdown
countdown() {
  local seconds=$1
  local message=$2
  if ! $silent; then
    echo "$message"

    if (( seconds > 5 )); then
      local step=5
      local decrement_steps=$(((seconds - step) / step + 1))  # Number of steps for decrements
      local total_decrement_time=$((decrement_steps - 1))  # Time spent in decrement phase
      local interval
      interval=$(echo "scale=2; ($seconds - 5) / $total_decrement_time" | bc)  # Interval for decrement phase

      # Display countdown in decrements of 5
      for ((i = seconds; i > step; i -= step)); do
        echo "  ${i}s"
        sleep "$interval"
      done

      # Display the final countdown from 5 to 1
      for ((i = step; i >= 1; i--)); do
        echo "  ${i}s"
        sleep 1
      done
    else
      # Display countdown for 5 or fewer seconds
      for ((i = seconds; i >= 1; i--)); do
        echo "  ${i}s"
        sleep 1
      done
    fi
  else
    sleep "$seconds"
  fi
}

# Function to retry a given command
retry_command() {
  local command=$1
  local retries=$2
  local attempt=1

  while (( attempt <= retries )); do
    if (( attempt > 1 )); then
      log "Retrying command: '$command' (Attempt $attempt of $retries)..."
    fi

    if $dry_run; then
      echo "Dry-run: $command"
      return 0
    elif eval "$command >/dev/null 2>&1"; then
      return 0
    fi

    attempt=$((attempt + 1))
    sleep 1
  done

  return 1
}

# Function to handle process termination with graceful kill, followed by forced kill if necessary
handle_process() {
  local process_name=$1
  local command_to_kill=$2
  local pid

  # Match exactly: -x on the process name for a binary, or an anchored full
  # command line for the bash wrapper script. A bare "pgrep -f pr3" matched any
  # process whose command line merely contained "pr3" and could kill it.
  if [[ $process_name == */* ]]; then
    pid=$(pgrep -f "^(/bin/)?bash $process_name( |\$)" | tail -n 1)
  else
    pid=$(pgrep -x "$process_name" | tail -n 1)
  fi

  if [[ -n $pid ]]; then
    log "Attempting to gracefully kill $process_name (PID: $pid)"
    if retry_command "kill $pid" 3; then
      retry_command "killall $command_to_kill" 1
      log "$process_name (PID: $pid) killed successfully."
    else
      log "Graceful kill failed. Forcibly killing $process_name (PID: $pid)"
      retry_command "kill -9 $pid" 1
      log "$process_name (PID: $pid) forcefully terminated."

      log "Attempting to forcefully kill all $command_to_kill processes with killall -9"
      retry_command "killall -9 $command_to_kill" 1
      log "All $command_to_kill processes forcefully terminated with killall -9."
    fi
  # else
  #   log "$process_name is not running."
  fi
}

# Function to locate and kill the processes in order with fallback to forceful kill
kill_processes() {
  handle_process "$SERVER_SCRIPT" "PR_SERVER_SCRIPT"
  handle_process "pr3" "pr3"

  if ! $dry_run; then
    # Check for active screen sessions
    if screen -ls | grep -i -q "attached\|detached"; then
      log "Wiping screen sessions."
      retry_command "screen -wipe" 1
      log "Killing all 'screen' sessions."
      retry_command "killall -9 screen" 1
    else
      log "No active screen sessions found."
    fi
  else
    echo "Dry-run: screen -wipe"
    echo "Dry-run: killall screen"
  fi
}

# Function to clear specific files (based on the option)
clear_files_before_restart() {
  if $clear_files; then
    log "Clearing save and cache files before restarting the server..."
    for dir in "$WORLD_SAVE_DIR" "$WORLD_SAVE_MISC_DIR" "$ROOM_SAVE_DIR"; do
      if [[ -d "$dir" ]]; then
        log "Clearing files in $dir"
        if $dry_run; then
          echo "Dry-run: rm -f $dir/*"
        else
          rm -f "$dir"/* >/dev/null 2>&1
        fi
      fi
    done
    echo -n "." > "$SERVER_LIB_DIR"/BOOT_CLEAN
    log "All save files and cache have been cleared. Staging for a CLEAN server restart."
  fi
}

# Function to start the PR_SERVER_SCRIPT in a new screen session
start_server() {
  log "Starting PR_SERVER_SCRIPT in a new screen session"
  if $dry_run; then
    echo "Dry-run: screen -dmS PR_SERVER_SESSION /bin/bash $SERVER_SCRIPT"
  else
    screen -dmS PR_SERVER_SESSION /bin/bash "$SERVER_SCRIPT"
  fi
}

# Function to validate server restart with retries on multiple ports
validate_server_restart() {
  log "Validating restart..."

  if $clear_files; then
    countdown 25 "Validating restart in:"
  else
    countdown 15 "Validating restart in:"
  fi

  local new_pr_server_pid
  local attempt=1
  local max_attempts=3
  local port
  local valid_port_found=false

  while (( attempt <= max_attempts )); do
    if (( attempt > 1 )); then
      log "Attempt $attempt of $max_attempts to validate restart..."
    fi

    new_pr_server_pid=$(pgrep -x pr3 | tail -n 1)

    if [[ -n $new_pr_server_pid ]]; then
      # Loop through the ports and check connection for each
      for port in "${SERVER_PORTS[@]}"; do
        log "Checking connection to localhost on port $port..."
        if echo "QUIT" | nc -w 1 localhost "$port" | grep -q "Welcome to"; then
          log "Connection to localhost:$port successful."
          valid_port_found=true
          break  # Exit the loop once a valid port is found
        else
          log "Error: Unable to connect to localhost:$port or unexpected response."
        fi
      done

      # If any port was successfully validated
      if $valid_port_found; then
        if $clear_files; then
          log "MUD server restarted CLEAN successfully (PID: $new_pr_server_pid)."
        else
          log "MUD server restarted successfully (PID: $new_pr_server_pid)."
        fi
        reset_attempt_count  # Reset the attempt count on success
        return 0
      fi
    else
      log "Error: MUD server failed to start."
    fi

    attempt=$((attempt + 1))
    if (( attempt <= max_attempts )); then
      countdown 5 "Retrying validation in:"
    fi
  done

  log "All validation attempts failed."
  return 1
}

# Function to retrieve the current attempt count from the attempt file
get_current_attempt() {
  if [[ -f $ATTEMPT_FILE ]]; then
    cat "$ATTEMPT_FILE"
  else
    echo 0
  fi
}

# Function to reset the attempt count
reset_attempt_count() {
  echo "0" > "$ATTEMPT_FILE"
}

# Function to handle exceeding maximum retries
handle_max_retries_exceeded() {
  log "Maximum retry attempts exceeded!"
  local current_attempt=$1
  log "Current attempt count: $current_attempt (maximum allowed: $max_retries)."
  log "Do you want to reset the attempt count and proceed? (Y/n)"

  read -r -t 5 -n 1 answer
  answer=${answer:-y}  # Default to 'y' if no input

  if [[ $answer =~ ^[Yy]$ ]]; then
    reset_attempt_count
    return 0
  fi
  return 1
}

# Helper function to handle running processes
handle_running_instance() {
  local pid=$1
  local process_name=$2
  local custom_message=$3
  local answer

  # Check if the process is running
  if kill -0 "$pid" >/dev/null 2>&1; then
    if ! $silent; then
      log "$custom_message with PID: $pid."

      # Ask the user if they want to kill the running process
      log "Do you want to kill the $process_name? (y/N)"
      read -r -t 5 -n 1 answer
      answer=${answer:-n}

      if [[ $answer =~ ^[Yy]$ ]]; then
        log "Killing process $pid..."
        kill -9 "$pid" >/dev/null 2>&1
        # Remove the associated lock file
        if [[ "$process_name" == "automatic restart process" ]]; then
          rm -f "$AUTO_CHECK_RESTART_LOCK_FILE" >/dev/null 2>&1
          # Reset attempt counter on manual cancellation of the auto check restart process
          reset_attempt_count
        else
          rm -f "$LOCK_FILE" >/dev/null 2>&1
        fi
      else
        log "Exiting. The $process_name continues to run."
        exit 1
      fi
    else
      exit 1
    fi
  else
    log "Stale lock file found with PID: $pid. Removing it."
    if [[ "$process_name" == "automatic restart process" ]]; then
      rm -f "$AUTO_CHECK_RESTART_LOCK_FILE" >/dev/null 2>&1
    else
      rm -f "$LOCK_FILE" >/dev/null 2>&1
    fi
  fi
}

# Function to ensure only one instance of the script runs at a time
check_running_instance() {
  local current_pid
  local auto_check_restart_pid

  # Check for the automatic check restart lock file
  if ! $silent && [[ -e "$AUTO_CHECK_RESTART_LOCK_FILE" ]]; then
    auto_check_restart_pid=$(cat "$AUTO_CHECK_RESTART_LOCK_FILE")
    handle_running_instance "$auto_check_restart_pid" "automatic restart process" \
                           "Automatic check and restart process is running"
  fi

  # Check if the lock file exists
  if [[ -e "$LOCK_FILE" ]]; then
    current_pid=$(cat "$LOCK_FILE")
    handle_running_instance "$current_pid" "other instance of the script" \
                           "Another instance of the script is running"
  fi
}

# Function to attempt to restart the server with retries
attempt_server_restart() {
  local attempt
  attempt=$(get_current_attempt)
  attempt=$((attempt + 1))

  # Handle max retries exceeded
  if (( attempt > max_retries )) && ! $silent; then
    if ! handle_max_retries_exceeded "$attempt"; then
      log "Maximum attempts ($max_retries) exceeded. Exiting..."
      exit 1  # Exit if the user chooses not to reset the attempt count
    fi
    attempt=1  # Reset the attempt count if the user chose to do so
  elif (( attempt > MAX_AUTO_RESTART_RETRIES )) && $silent; then
    exit 1
  fi

  # Loop while attempt is within max_retries, or the total cap of $MAX_AUTO_RESTART_RETRIES in silent mode
  while (( attempt <= max_retries )) || { $silent && (( attempt <= MAX_AUTO_RESTART_RETRIES )) && [[ -e "$AUTO_CHECK_RESTART_LOCK_FILE" ]]; }; do
    if (( attempt > 1 )); then
      log "Attempt $attempt of $max_retries to restart the MUD server..."
    fi

    # Check if we need to use the clean reboot option
    if (( attempt >= AUTO_RESTART_RETRIES_BEFORE_TRY_CLEAN )) && $silent && ! $clear_files; then
      if [[ -e "$AUTO_CHECK_RESTART_LOCK_FILE" ]]; then
        clear_files=true
      fi
    fi

    kill_processes
    clear_files_before_restart
    countdown 3 "Restarting in:"
    start_server

    if validate_server_restart; then
      return 0
    fi

    attempt=$((attempt + 1))
    echo "$attempt" > "$ATTEMPT_FILE"  # Update the attempt counter
    [[ $attempt -le $max_retries ]] && log "Retrying restart..."
  done

  log "All attempts to restart the MUD server failed."
  log "Killing all related processes..."
  kill_processes
  log "Please check the server manually."
  exit 1
}

# Main script execution
parse_args "$@"
check_running_instance

# Create the lock file
touch "$LOCK_FILE"

# Write the PID of the current instance to the lock file
echo $$ > "$LOCK_FILE"

# Ensure the lock file is removed on exit
trap 'rm -f "$LOCK_FILE"; exit' EXIT SIGINT SIGTERM

# Main script execution
attempt_server_restart

