#!/usr/bin/env bash
cd ..

scrapy crawl airbnb_spider \
    -a city=Rio-de-Janeiro \
    -a country=Brazil \
    -a check_in=02/23/2017 \
    -a check_out=03/02/2017 \
    -a max_price=150 \
    -a min_price=30 \
    -a neighborhoods="Ipanema,Leblon" \
    -s WEB_BROWSER="/usr/bin/chromium" \
    -s MINIMUM_WEEKLY_DISCOUNT=15 \
    -o rio.xlsx

#    -s MUST_HAVE="(atico|attic|balcon|terr?a|patio|outdoor|roof|varanda|view|vista)" \
#    -s SKIP_LIST="14317244,13900224,13810673,6121326,7138669" \
cd examples
