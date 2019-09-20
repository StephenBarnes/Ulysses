#!/bin/bash

rm -rf /root/ulysses
cp /home/j/proj/ulysses /root/ulysses -r
chown root.root -R /root/ulysses
sed /root/ulysses/src/precommitment/configuration.py -e "s/JUST_TESTING = True/JUST_TESTING = False/" --in-place

date_str=`date +'%Y-%m-%dT%H:%M:%S.%N'`
FILE=/home/j/Traxis/DATA.db
sqlite3 $FILE <<EOF
INSERT INTO UlyssesShips (date) values ('$date_str');
EOF

