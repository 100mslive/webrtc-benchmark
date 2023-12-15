#!/bin/bash
port=$1
echo "throttling network to ${speed}Kbit/s with in bursts"

delay=10
increment=10

for i in {1..100}
do
    sudo dnctl pipe 1 config bw 100000Kbit/s delay 0 plr 0 noerror
    echo "dummynet out proto {udp} from any to any port ${port}  pipe 1" | sudo pfctl -f -
    sudo pfctl -e
    sleep ${delay}

    echo "start burst loss for 3 seconds.."
    sudo dnctl pipe 1 config bw 100000Kbit/s delay 2000 plr 0 noerror
    echo "dummynet out proto {udp} from any to any port ${port} pipe 1" | sudo pfctl -f -
    sudo pfctl -e
    sleep 2
    echo "stop burst loss for 3 seconds.."
done


