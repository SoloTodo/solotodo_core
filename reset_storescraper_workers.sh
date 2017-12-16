#!/usr/bin/env bash
cd ~/projects/solotodo_core/

sh stop_storescraper_workers.sh
sleep 5
sh stop_storescraper_workers.sh
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
sh start_storescraper_workers.sh