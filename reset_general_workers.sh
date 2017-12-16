#!/usr/bin/env bash
cd ~/projects/solotodo_core/

sh stop_general_workers.sh
sleep 5
sh stop_general_workers.sh
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
sh start_general_workers.sh