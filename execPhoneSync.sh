#!/bin/bash

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
EXEC_SCRIPT_NAME=$(basename "$SOURCE")
EXEC_SCRIPT_NAME_WO_EXT=${EXEC_SCRIPT_NAME%%.sh}
SCRIPT_FULL_PATH=$(find "${DIR}" -maxdepth 1 | grep "\/${EXEC_SCRIPT_NAME_WO_EXT##exec}\.")

if [ $? -ne 0 -o $(echo "${SCRIPT_FULL_PATH}" | wc -l) -ne 1 ]
then
    /usr/bin/gnome-terminal --geometry=120x50+250+150 -e "bash -c \"echo ERROR! Can not find script to execute. ; read -p 'Press ENTER.'\""
    exit 1
fi

/usr/bin/gnome-terminal --geometry=120x50+250+150 -e "bash -c \"${SCRIPT_FULL_PATH} ; read -p 'Done. Press ENTER.'\""
