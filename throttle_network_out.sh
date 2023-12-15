#!/bin/bash
speed=$1
port=$2
echo "throttling network to ${speed}Kbit/s"
sudo dnctl pipe 1 config bw ${speed}Kbit/s delay 0 plr 0 noerror
echo "dummynet out proto {udp} from any  to any port ${port} pipe 1" | sudo pfctl -f -
sudo pfctl -e
