# Nomad Airbnb: Airbnb advanced search for digital nomads using Scrapy 

## Intro

Airbnb's search is pretty good, but sometimes I find it lacking. For instance, you 
can't do a full text search, and they limit you to 300 results per search which means 
it is a chore to see their entire inventory. 

Luckily, they make it easy by storing most of their listing data (i.e. "state") in big
JSON objects at the bottom of the page in the content attribute of meta HTML tags.

## Example Usage

Minimal scraper usage:

    scrapy crawl bnb
    
### Edit *AirbnbSpider.py* to configure `_query_parts`
    
Advanced command line options:

```
scrapy crawl bnb \
    -a city=Madrid \
    -a country=Spain \
    -a check_in=10/04/2016 \
    -a check_out=11/01/2016 \
    -a max_price=1900 \
    -a min_price=1800 \
    -a neighborhoods="Acacias,Almagro,Arganzuela,Argüelles,Centro,Cortes,Embajadores,Imperial,Jerónimos,La Latina,Malasaña,Moncloa,Palacio,Recoletos,Retiro,Salamanca,Sol" \
    -s MUST_HAVE="(atico|attic|balcon|terra|patio|outdoor|roof|view)" \
    -s CANNOT_HAVE="studio" \
    -s MINIMUM_WEEKLY_DISCOUNT=20 \
    -s WEB_BROWSER="/usr/bin/chromium" \
    -o madrid.xlsx
```

## Scraping Description

After running the above command, the scraper will start. It will first run the 
search query, then determine the quantity of result pages, and finally iterate 
through each of those, scraping each of the property listings on each page.

Scraped items (listings) will be passed to the default item pipeline, where, 
optionally, the `description`, `name`, `summary`, and `reviews` fields will be
filtered using either or both of the `CANNOT_HAVE` and `MUST_HAVE` regexes. 
Filtered items will be dropped. Accepted items can be optionally opened in a 
given web browser, so that you can easily view your search results.

Finally, the output can be saved to an xlsx format file for additional 
filtering, sorting, and inspection.

## Parameters

You can find the values for these by first doing a search manually on the 
Airbnb site. 

* `city`, `state`: City and State to search. **(required)** 
* `check_in`, `check_out`: Check-in and Check-out dates. **(required)** 
* `min_price`, `max_price`: Minimum and maximum price for the period. **(required)**  
  *The Airbnb search algorithm seems to scale this based upon search length. So 
  it will be either the daily or monthly price, depending on the length of the 
  stay.*
* `neighborhoods`: Comma-separated list of neighborhoods within the city
  to filter for. **(optional)**
* `output`: Name of output file. Only xlsx output is tested. 
  **(optional)**

## Settings

These settings can be edited in the `settings.py` file, or appended to the 
command line using the `-s` flag as in the example above.

* `CANNOT_HAVE="<cannot-have-regex>"`  
  Don't accept listings that match the given regex pattern. 
  **(optional)**
  
* `FIELDS_TO_EXPORT=['field1', 'field2', ...]`  
  Can be found in settings.py. Contains a list of all possible fields to 
  export, i.e. all fields of `AirbnbScraperItem`. Comment items to 
  remove undesired fields from output.
  
* `MINIMUM_MONTHLY_DISCOUNT=30`  
  Minimum monthly discount. 
  **(optional)**

* `MINIMUM_WEEKLY_DISCOUNT=25`  
  Minimum weekly discount. 
  **(optional)**

* `MUST_HAVE="(<must-have-regex>)"`  
  Only accept listings that match the given regex pattern. 
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


## Requirements

* [Scrapy](http://scrapy.org/)
* [openpyxl](https://openpyxl.readthedocs.io/en/default/#installation)


## Credits

This project was originally inspired by 
[this excellent blog post](http://www.verginer.eu/blog/web-scraping-airbnb/) 
by Luca Verginer.
