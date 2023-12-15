#!/bin/bash
speed=$1
port=$2
echo "throttling network to ${speed}Kbit/s with increasing delay"

delay=20
increment=10

for i in {1..20}
do
    sudo dnctl pipe 1 config bw ${speed}Kbit/s delay ${delay} plr 0.02 noerror
    echo "dummynet in proto {udp} from any port ${port} to any pipe 1" | sudo pfctl -f -
    sudo pfctl -e
    delay=$((delay+increment))
    echo "delay=${delay}"
    sleep 0.2

done


