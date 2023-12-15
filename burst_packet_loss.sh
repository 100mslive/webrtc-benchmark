    sudo dnctl pipe 1 config bw 100000Kbit/s delay 0 plr 0.5 noerror
    echo "dummynet out proto {tcp} from any to any pipe 1" | sudo pfctl -f -
    sudo pfctl -e

    sleep 20
    
    sudo dnctl pipe 1 config bw 100000Kbit/s delay 0 plr 0 noerror
    echo "dummynet out proto {tcp} from any to any pipe 1" | sudo pfctl -f -
    sudo pfctl -e
