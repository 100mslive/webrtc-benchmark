    #sudo dnctl pipe 1 config bw 0Kbit/s delay 0 plr 0 noerror
    echo "block out quick proto {udp } from any to any " | sudo pfctl -f -
    sudo pfctl -e

    