# KashKlik Instagram Crawler Public Version
This crawler was completed as part of a Summer 2019 internship at [KashKlik](https://www.kashklik.com/). It is an Instagram web crawler written in Python designed to find potential social media influencers to reach out based on the hashtags they post under.

Created by [David Kocen](https://github.com/dkocen) and [Luis Rivas](https://github.com/Rivas142)

## Dependencies
 - [Python3](https://www.python.org/downloads/)
 - [Pandas](https://pypi.org/project/pandas/)
 - [NumPy](https://pypi.org/project/numpy/)
 - [Requests](https://pypi.org/project/requests/)
 - [BeautifulSoup4](https://pypi.org/project/beautifulsoup4/)
 - [Selenium](https://pypi.org/project/selenium/)
 - [Objectpath](https://pypi.org/project/objectpath/)
 - [Google Chrome](https://www.google.com/chrome/)
 - [Chromedriver](https://chromedriver.chromium.org/)

## Content

### `main.py`
`main.py` is the main Python script for the crawler. This script calls `instagrambot.py` with the parameters set in`configmain.py` saving each result to a Pandas dataframe. It then saves this dataframe to a csv and if desired saves the csv to either AWS S3 services or the local directory

### `instagrambot.py`
`instagrambot.py` contains the instagrambot class. It is here that the crawler is created and performs its functions

### `config/configmain.json`
`configmain.json` contains all the various parameters for personalizing how you want the crawler to run including what hashtags to crawl, how many pictures to get, and minimum number of followers to be considered an influencer.

 - `"hashtags"`: list of hashtags that you want the crawler to search. Do not include the # symbol. Should take the form of a list i.e. `["nyc", "ad"]`.
 - `"num_pictures"`: number of pictures you want to go through per hashtag. Note: as of right now the largest successful crawl has been 2000 pictures. Recommended size for now is 1000 but may change if we switch to residential IPs.
 - `"threads"`: number of threads to run the crawler with. Somewhere between 5 and 8 seems to be the sweet spot depending on the system.
 - `"folder_path"`: path to folder to save outputs to.
 - `"headless"`: boolean that tells crawler to run Chrome in headless mode.
 - `"proxy"`: boolean that tells crawler to run with Luminati proxy services.
 - `"min_followers"`: minimum required followers to be considered an influencer.
 - `"max_followers"`: maximum number of followers to be considered an influencer.

### `config/configbot.json`
`configbot.json` contains specific parameters that apply to the crawler including proxy IPs, xpaths to various page elements, and the location of the chromedriver for Selenium.

-`"proxy_http`: string containing the proxy IP address if applicable
- `"proxy_https"`: should be the same as `"proxy_http"`
- `"webpage_hashtags"`: string containing URL for a generic Instagram hashtag that the specific hashtag is then appended to.
- `"webpage_profile"`: string containing URL for a generic Instagram profile that the specific profile name is then appended to.
- `"pic_link_xpath"`: Xpath to picture link for a given post for a hashtag.
- `"chromedriver_path"`: File path to chromedriver installation. This should be the same folder as `main.py`. Make sure to include `\\chromedriver.exe` at the end if using Windows or `/chromedriver` if using Linux

Note: Unless something stops working do not edit `"webpage_hashtags"`, `"webpage_profile"`, or `"pic_link_xpath"` as these are variables set by Instagram. 

## How To Use
 1. Install all required dependencies.
 3. Open `configmain.json` and enter desired values (see `configmain.json` content section).
 4. Open `configbot.json` and enter desired values (see `configbot.json` content section). For `"chromedriver_path"` make sure to include the chromedriver itself. This means for Windows the path should end in "chromedriver.exe" and for Linux/MacOS the path should end in "chromedriver".
 6. Run `main.py` in the command line.
 5. The resulting CSV files will appear in the corresponding `folder_path` variable/

## Known Issues
- Crawler will get caught when initially collecting pictures especially if told to collect a lot. If caught restart the crawler or request fewer pictures. The largets successful crawl so far is 10,000 pictures but it is recommended to keep it under 3,000. Note that this crawl was done using a proxy service.
- Running crawler for extended period results in some failure to collect some profile address (about 10 per 1000 pictures). It is speculated that this is Instagram rejecting the requests so take a break and crawl again later.
- Running crawler with too many threads results in a slowdown. This is believed to be a hardware-based problem and so one should test optimal number of threads on a per machine basis. Somewhere between 5 and 8 seems to work best.

Instagram's policy is not to provide support for web crawlers so please make sure to crawl respectfully. Do not make too many requests at once and break between each successive crawl.
