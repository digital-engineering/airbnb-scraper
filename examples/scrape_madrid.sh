#!/usr/bin/env bash
cd ..

scrapy crawl bnb \
    -a city=Madrid \
    -a country=Spain \
    -a check_in=05/21/2017 \
    -a check_out=06/22/2017 \
    -a max_price=2200 \
    -s WEB_BROWSER="/usr/bin/chromium" \
    -s MINIMUM_WEEKLY_DISCOUNT=0 \
    -o madrid.xlsx \
    -s MUST_HAVE="(atico|attic|balcon|terr?a|patio|outdoor|roof|varanda|view|vista)"
#    -s SKIP_LIST="14317244,13900224,13810673,6121326,7138669" \
cd examples
