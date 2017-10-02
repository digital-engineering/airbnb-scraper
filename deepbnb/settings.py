# -*- coding: utf-8 -*-

# Scrapy settings for deepbnb project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#     http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
#     http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'deepbnb'

SPIDER_MODULES = ['deepbnb.spiders']
NEWSPIDER_MODULE = 'deepbnb.spiders'

#
# Splash config (https://github.com/scrapy-plugins/scrapy-splash)
#

# Add the Splash server address
SPLASH_URL = 'http://localhost:8050'

# Enable the Splash middleware by adding it and changing HttpCompressionMiddleware priority
# Order 723 is just before HttpProxyMiddleware (750) in default scrapy settings.
# HttpCompressionMiddleware priority should be changed in order to allow advanced response processing;
# see https://github.com/scrapy/scrapy/issues/1895 for details
DOWNLOADER_MIDDLEWARES = {
    'scrapy_splash.SplashCookiesMiddleware': 723,
    'scrapy_splash.SplashMiddleware': 725,
    'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
}

# These 2 lines are necessary because Scrapy doesn't provide a way to override request fingerprints calculation
# algorithm globally; this could change in future.
DUPEFILTER_CLASS = 'scrapy_splash.SplashAwareDupeFilter'
HTTPCACHE_STORAGE = 'scrapy_splash.SplashAwareFSCacheStorage'

#
# Scraper config
#

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = 'deepbnb (+https://www.bashedev.com)'

# Obey robots.txt rules
ROBOTSTXT_OBEY = True
WEB_BROWSER = 'chromium'
# Configure maximum concurrent requests performed by Scrapy (default: 16)
# CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See http://scrapy.readthedocs.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
# DOWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
CONCURRENT_REQUESTS_PER_DOMAIN = 10
# CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
# COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED = False

# Override the default request headers:
# DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
# }

# Enable or disable spider middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html
# SPIDER_MIDDLEWARES = {
#    'deepbnb.middlewares.MyCustomSpiderMiddleware': 543,
# }

# Enable or disable extensions
# See http://scrapy.readthedocs.org/en/latest/topics/extensions.html
# EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
# }

# Configure item pipelines
# See http://scrapy.readthedocs.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    'deepbnb.pipelines.AirbnbScraperPipeline': 300,
}

FEED_EXPORTERS = {
    'xlsx': 'deepbnb.exporter.AirbnbExcelItemExporter',
}
FIELDS_TO_EXPORT = [
    'name',
    'price',
    'nightly_price',
    #    'calendar_updated_at',
    #    'min_nights',
    #    'url',
    'summary',
    'description',
    'space',
    'satisfaction_guest',
    'accuracy_rating',
    #    'amenities',
    'access',
    'house_rules',
    'response_rate',
    'response_time',
    'notes',
    #    'cancel_policy',
    #    'host_id',
    #    'hosting_id',
    #    'instant_book',
    #    'interaction',
    'neighborhood_overview',
    #    'rating_checkin',
    #    'rating_cleanliness',
    #    'rating_communication',
    #    'review_count',
    #    'reviews',
    #    'room_type',
    #    'person_capacity',
    #    'transit',
    #    'bed_type',
]

MINIMUM_MONTHLY_DISCOUNT = 0  # percent
MINIMUM_WEEKLY_DISCOUNT = 0  # percent

# Enable and configure the AutoThrottle extension (disabled by default)
# See http://doc.scrapy.org/en/latest/topics/autothrottle.html
AUTOTHROTTLE_ENABLED = True
# The initial download delay
AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
# AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = 'httpcache'
# HTTPCACHE_IGNORE_HTTP_CODES = []
# HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'
