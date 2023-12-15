#!/bin/bash
speed=$1
plr=$2
port=$3
echo "throttling network to ${speed}Kbit/s, plr to ${plr}"
sudo dnctl pipe 1 config bw ${speed}Kbit/s delay 0 plr ${plr} noerror
echo "dummynet out proto {udp} from any  to any port ${port}  pipe 1" | sudo pfctl -f -
sudo pfctl -e
