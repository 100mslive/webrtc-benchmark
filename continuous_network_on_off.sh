for n in {1..50000}; 
do
    ./throttle_network.sh 100000 12121     
    sleep 1
	./block_all_network.sh
	sleep 1

done


