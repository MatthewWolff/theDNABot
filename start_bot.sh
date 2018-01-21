#!/bin/tcsh
cd /home/matthew/theDNABot/
nohup python theDNABot.py >>& bot_log.out &
cd ..
exit
done

