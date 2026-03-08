#!/bin/bash
set -ex

cat <<EOF >> ~/.bashrc

source ${PROJECT_DIR}/.devcontainer/.bashrc_private
EOF