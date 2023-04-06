#!/usr/bin/env bash

if [ -z ${1+x} ]; then
  echo -e "Wrong execute command\n"
  echo -e "Usage: \n\t$0 USER@HOST:DEST_DIR_DB\n"
  echo "Where:"
  echo -e "  - USER@HOST\t Connection options (address) in 'rsync'"
  echo -e "  - DEST_DIR_DB\t Path to database folder on remote server (sqlite in Grafana)";
else
  RSYNC_DEST_PATH=$1
  PATH_TO_SSH_KEY=".ssh/notif.key"

  # Run script
  python3 update-load_table.py &&

  # Get path of new database
  NEW_DB=$(python3 update-load_table.py --get-db-path) &&
  
  # Copy database to Grafana-server
  rsync --rsh="ssh -i $PATH_TO_SSH_KEY -o 'StrictHostKeyChecking=no'" \
        -a "$NEW_DB" "$RSYNC_DEST_PATH"
fi
