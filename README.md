# Airbnb Scraper: Advanced Airbnb Search using Scrapy

## Disclaimer: No longer maintained

### This project is not currently maintained, due to difficulty in using scrapy to make requests to the Airbnb API. Project is on hold until further notice. Currently exploring a simpler approach here: https://github.com/JoeBashe/stl-scraper

Use Airbnb's unofficial API to efficiently search for rental properties.
Regex matching, ranged search, open matched properties in a browser, save to CSV, xlsx, or ElasticSearch (alpha).

## Notes

- Airbnb's API is subject to change at any moment, which would break this scraper. They've already changed it several
  times in the past. Also, using this probably violates their TOS. Please only use for educational or research purposes.
- The scraper was recently updated to work with Airbnb's new v3 GraphQL API. Some features are still being updated.
- If you get 403 Forbidden errors when running this scraper, try browsing the Airbnb site in your web browser from the
  same computer first, then try running the script again.

## Requirements

* **Python 3.10+**
* [Scrapy](http://scrapy.org/)
* [openpyxl](https://openpyxl.readthedocs.io/en/default/#installation)
* ElasticSearch 7+ if using elasticsearch pipeline
* see [requirements.txt](requirements.txt) for details

## Installation (nix)

```bash
# Create venv
python3.10 -m venv env

# Enable venv
. env/bin/activate

# Install required packages
pip install -Ur requirements.txt

# Create settings.py
cp deepbnb/settings.py.dist deepbnb/settings.py

# @NOTE: Don't forget to set AIRBNB_API_KEY in settings.py. To find your API key, 
# search Airbnb using Chrome, open dev tools, and look for to the url parameter  
# named "key" in async requests to /api/v2/explore_tabs under the Network tab.
```

## Configuration

Edit `deepbnb/settings.py` for settings. I've created some custom settings which are
documented [below](https://github.com/digital-engineering/airbnb-scraper#settings). The rest are documented
in https://docs.scrapy.org/en/latest/topics/settings.html.

## Example Usage

#### Minimal scraper usage:

    scrapy crawl airbnb -a query="Colorado Springs, CO" -o colorado_springs.csv

#### Advanced examples:

##### Madrid, fixed dates

```
scrapy crawl airbnb \
    -a query="Madrid, Spain" \
    -a checkin=2023-10-01 \
    -a checkout=2023-11-30 \
    -a max_price=1900 \
    -a min_price=1800 \
    -a neighborhoods="Acacias,Almagro,Arganzuela,Argüelles,Centro,Cortes,Embajadores,Imperial,Jerónimos,La Latina,Malasaña,Moncloa,Palacio,Recoletos,Retiro,Salamanca,Sol" \
    -s MUST_HAVE="(atico|attic|balcon|terra|patio|outdoor|roof|view)" \
    -s CANNOT_HAVE="studio" \
    -s MINIMUM_WEEKLY_DISCOUNT=20 \
    -s WEB_BROWSER="/usr/bin/chromium" \
    -o madrid.xlsx
```

##### New York ranged date search

```
scrapy crawl airbnb \
    -a query="New York, NY" \
    -a checkin="2023-01-22+7-0" \
    -a checkout="2023-02-22+14-3" \
    -a max_price=1800 \
    -s CANNOT_HAVE="guest suite" \
    -s MUST_HAVE="(walking distance|short walk|no car needed|walk everywhere|metro close|public transport)" \
    -o newyork.csv
```

## Ranged date queries

If you have flexible checkin / checkout dates, use the ranged search feature to search a range of checkin / checkout
dates.

### Search checkin date range +5 days -2 days

    scrapy crawl airbnb \
        -a query="Minneapolis, MN" \
        -a checkin="2023-10-15+5-2" \
        -a checkout="2023-11-15" \
        -o minneapolis.csv

This search would look for rentals in Minneapolis using Oct 15 2023 as base check-in date, and also searching for
rentals available for check-in 2 days before, up to 5 days after. In other words, check-ins from Oct 13 to Oct 20. This
is specified by the string `+5-2` appended to the checkin date `2023-10-15+5-2`. The string must always follow the
pattern`+[days_after]-[days_before]` unless `[days_after]` and `[days_before]` are equal, in which case you can
use `+-[days]`. The numbers may be any integer 0 or greater (large numbers untested).

### Search checkin date +5 days -2 days, checkout date + or - 3 days

    scrapy crawl airbnb \
        -a query="Florence, Italy" \
        -a checkin="2023-10-15+5-2" \
        -a checkout="2023-11-15+-3" \
        -o firenze.csv

## Scraping Description

After running the crawl command, the scraper will start. It will first run the
search query, then determine the quantity of result pages, and finally iterate
through each of those, scraping each of the property listings on each page.

Scraped items (listings) will be passed to the default item pipeline, where,
optionally, the `description`, `name`, and `reviews.description` fields will
be filtered using either or both of the `CANNOT_HAVE` and `MUST_HAVE` regexes.
Filtered items will be dropped. Accepted items can be optionally opened in a
given web browser, so that you can easily view your search results.

Finally, the output can be saved to an xlsx format file for additional
filtering, sorting, and inspection.

## Parameters

You can find the values for these by first doing a search manually on the
Airbnb site.

* `query`: City and State to search. **(required)**
* `checkin`, `checkout`: Check-in and Check-out dates.
* `min_price`, `max_price`: Minimum and maximum price for the period.
  *The Airbnb search algorithm calculates this based upon search length.
  It will be either the daily or monthly price, depending on the length
  of the stay.*
* `neighborhoods`: Comma-separated list of neighborhoods within the city
  to filter for.
* `output`: Name of output file. Only `xlsx` output is tested.

## Settings

These settings can be edited in the `settings.py` file, or appended to the
command line using the `-s` flag as in the example above.

* `CANNOT_HAVE="<cannot-have-regex>"`  
  Don't accept listings that match the given regex pattern.
  **(optional)**


* `FIELDS_TO_EXPORT="['field1', 'field2', ...]"`  
  Can be found in settings.py. Contains a list of all possible fields to
  export, i.e. all fields of `AirbnbScraperItem`. Comment items to
  remove undesired fields from output. Applies only to `xlsx` output.


* `MINIMUM_MONTHLY_DISCOUNT=30`  
  Minimum monthly discount.
  **(optional)**


* `MINIMUM_WEEKLY_DISCOUNT=25`  
  Minimum weekly discount.
  **(optional)**


* `MUST_HAVE="(<must-have-regex>)"`  
  Only accept listings that match the given regex pattern.
  **(optional)**


* `ROOM_TYPES="['Camper/RV', 'Campsite', 'Entire guest suite']"`  
  Room Types to filter.
  **(optional)**


* `SKIP_LIST="['12345678', '12345679', '12345680']"`  
  Property IDs to filter.
  **(optional)**


* `WEB_BROWSER="/path/to/browser %s"`  
  Web browser executable command. **(optional)**

  *Examples*:
    - MacOS  
      `WEB_BROWSER="open -a /Applications/Google\ Chrome.app"`

    - Windows  
      `WEB_BROWSER="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"`

    - Linux  
      `WEB_BROWSER="/usr/bin/google-chrome"`

## Elasticsearch

Enable `deepbnb.pipelines.ElasticBnbPipeline` in `settings.py`

## Credits

- This project was originally inspired by [this excellent blog post](http://www.verginer.eu/blog/web-scraping-airbnb/)
  by Luca Verginer.
- In converting this to use the unofficial API, https://stevesie.com/apps/airbnb-api was very helpful.
- [This analysis of Bali Airbnbs](https://github.com/daben/m2851-prac1) provided inspiration for more eloquent code.
