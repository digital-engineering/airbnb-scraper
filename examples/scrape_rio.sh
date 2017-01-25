#!/usr/bin/env bash
cd ..
#-s SKIP_LIST="7456783,1718701,16400665,13810673,3736953,528558,13900224,11774680,7138669,6121326,15477191"
scrapy crawl airbnb_spider \
    -a city=Rio-de-Janeiro \
    -a country=Brazil \
    -a check_in=02/01/2017 \
    -a check_out=03/02/2017 \
    -a max_price=3200 \
    -a min_price=1700 \
    -a neighborhoods="Ipanema,Leblon" \
    -s MUST_HAVE="(atico|attic|balcon|terr?a|patio|outdoor|roof|varanda|view|vista)" \
    -s WEB_BROWSER="/usr/bin/chromium" \
    -s SKIP_LIST="14317244,13900224,13810673,6121326,7138669" \
    -o rio.xlsx

cd examples
