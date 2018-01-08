#!/usr/bin/env zsh
source ~/.zshrc

cd "${0%/*}"
source env/bin/activate

./stop_storescraper_workers.sh
sleep 5
./stop_storescraper_workers.sh
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
./start_storescraper_workers.sh