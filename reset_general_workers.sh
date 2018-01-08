#!/usr/bin/env zsh
source ~/.zshrc

cd "${0%/*}"
source env/bin/activate

./stop_general_workers.sh
sleep 5
./stop_general_workers.sh
sleep 5
killall phantomjs
killall chrome
killall chromedriver
killall google-chrome
sleep 5
killall phantomjs
killall chrome
killall chromedriver
killall google-chrome
sleep 5
./start_general_workers.sh