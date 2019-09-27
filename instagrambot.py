import re
import time
import threading
import concurrent.futures
import numpy
import json
import requests
import objectpath
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.proxy import *

with open('config//configbot.json') as config_file:
    parameters = json.load(config_file)

PROXIES = {
    'http': parameters["proxy_http"],
    'https': parameters["proxy_https"]}
WEBPAGE_HASHTAGS = parameters['webpage_hashtags']
WEBPAGE_PROFILE = parameters['webpage_profile']
PIC_LINKS_XPATH = parameters['pic_link_xpath']
CHROMEDRIVER_PATH = parameters['chromedriver_path']


class InstagramBot:
    """Class defining the Instagram bot

    Methods
    ---------
    get_users(self, num_pictures=10, hashtag='ad')
        Goes through num_pictures pictures in a provided hashtag and collects user urls associated with each post

    get_user_url(self, pic_urls = None)
        Helper function for get_users that gets the profile url from a list of posts (called when working in parallel)

    get_user_info(self, urls = None)
        Collects profile info for each profile in a list of valid urls. For each profile collects and structures data as
        a list with the structure [username, num_followers, num_following, num_posts, email, profile_url]. If it is
        unable to access the provided url then returns a list where each value is null.

    get_hashtag_post_count(self, url)
        Helper function to get number of posts in a given hashtag. Used to ensure not looking for 1000 posts in a
        hashtag with only 100 posts

    get_email(self, soup)
        Helper function to find a valid email from an account description

    convert_to_int(num)
         Helper function that converts profile statistics to int ifn ot already (i.e. 100m followers to 100000000)

    get_username_from_soup(soup)
        Helper function to get username from profile page
    """

    def __init__(self, headless=False, proxy=False, threads=1):
        """
        Initializes bot

        :param headless: boolean that decides if bot runs in headless mode
        :param proxy: boolean that decides if bot runs using a proxy
        :param threads: int that gives number of concurrent threads to use when going through picture and account links
        """
        self.headless = headless
        self.proxy = proxy
        self.threads = threads
        self.capabilities = webdriver.DesiredCapabilities.CHROME
        self.options = webdriver.ChromeOptions()

        if self.proxy:
            proxy = Proxy({
            'proxyType': ProxyType.MANUAL,
            'httpProxy': PROXIES['http'],
            'ftp_proxy': PROXIES['http'],
            'sslProxy': PROXIES['http'],
            'noProxy': ''
            })

            proxy.add_to_capabilities(self.capabilities)

        if self.headless:
            self.options.add_argument('--headless')
            self.options.add_argument('--no-sandbox')
            self.options.add_argument('--disable-browser-side-navigation')
            self.options.add_argument('--disable-infobars')
            self.options.add_argument('--disable-dev-shm-usage')
            self.options.add_argument('--disable-gpu')

        self.browser = webdriver.Chrome(executable_path=CHROMEDRIVER_PATH, chrome_options=self.options,
                                        desired_capabilities=self.capabilities)

    def get_users(self, num_pictures=10, hashtag='ad'):
        """
        Goes through num_pictures pictures in a provided hashtag and collects user urls associated with each post

        :param num_pictures: int that decides number of pictures to look through for a hashtag
        :param hashtag: string that decides what hashtag to search through
        :return: list of user urls who post under a given hashtag
        """

        webpage = WEBPAGE_HASHTAGS + hashtag + '/'
        self.browser.get(webpage)

        # check total number of posts in hashtag and adjust accordingly
        posts_count = self.get_hashtag_post_count(webpage)
        if posts_count < num_pictures:
            num_pictures = posts_count

        # Using sets instead of lists to avoid duplicates
        pic_urls = set()
        current_num = -1
        current_num_counter = 0

        while len(pic_urls) < num_pictures:
            if len(pic_urls) != current_num:
                current_num_counter = 0
            current_num = len(pic_urls)
            print(
                "Getting pictures for #" + str(hashtag) + ". Currently have " + str(len(pic_urls)) + " of " + str(
                    num_pictures) + " pictures")

            pic_links_elements = self.browser.find_elements_by_xpath(PIC_LINKS_XPATH)
            pic_urls = pic_urls | {element.get_attribute("href") for element in pic_links_elements}

            self.browser.execute_script("window.scrollTo(0,document.body.scrollHeight);")

            # Automatically ends crawl if unable to load more pictures after 20 attempts at scrolling down
            if len(pic_urls) == current_num:
                current_num_counter += 1
                if current_num_counter == 20:
                    break

            time.sleep(1)  # Sleep to prevent making too many requests at once

        self.browser.close()

        # Splits pic_urls into self.threads evenly split lists
        pic_urls_divided = list(numpy.array_split(numpy.array(list(pic_urls)), self.threads))
        pic_urls_divided = [numpy_arr.tolist() for numpy_arr in pic_urls_divided]

        # Runs threads returning list of future objects
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.threads) as executor:
            user_urls_future = {executor.submit(self.get_user_url, url_list) for url_list in pic_urls_divided}

        # Converts list of future objects into list of user urls
        user_urls_divided = [future.result() for future in user_urls_future]
        user_urls = [url for sublist in user_urls_divided for url in sublist]

        return user_urls

    def get_user_url(self, pic_urls = None):
        """
        Helper function for get_users that gets the profile url from a list of posts (called when working in parallel)

        :param pic_urls: list of post urls
        :return: list of urls to accounts associated with the provided list of post urls
        """

        user_urls = set()

        counter = 1
        for url in pic_urls:
            print("Getting link to profile for picture " + str(counter) + " of " + str(len(pic_urls)) + ": " + str(url)
                  + " {}".format(threading.current_thread()))
            try:
                if self.proxy:
                    r = requests.get(url, verify='ca.crt.txt', proxies=PROXIES)
                else:
                    r = requests.get(url)

                soup = BeautifulSoup(r.content, 'html.parser')
                username = self.get_username_from_soup(soup)
                profile_url = WEBPAGE_PROFILE + username + '/'
                user_urls = user_urls | {profile_url}
            except Exception as e:
                print("No user url received for: ", url)
                print(e)

            counter += 1

        return user_urls

    def get_user_info(self, urls=None):
        """
        Collects profile info for each profile in a list of valid urls. For each profile collects and structures data as
        a list with the structure [username, num_followers, num_following, num_posts, email, profile_url]. If it is
        unable to access the provided url then returns a list where each value is null.

        :param urls: list of profile urls
        :return: list of lists containing individual profile information
        """

        users_info = []
        counter = 1
        for url in urls:
            print('Getting user profile info {0} of {1}{2}'.format(str(counter), str(len(urls)),
                                                                   ' {}'.format(threading.current_thread())))
            counter += 1
            try:
                if self.proxy:
                    r = requests.get(url, verify='ca.crt.txt', proxies=PROXIES)
                else:
                    r = requests.get(url)

                soup = BeautifulSoup(r.content, 'html.parser')
                data = soup.find_all('meta', attrs={'property': 'og:description'})
                text = data[0].get('content').split()
                user = '%s %s %s' % (text[-3], text[-2], text[-1])
                followers = self.convert_to_int(text[0])
                following = self.convert_to_int(text[2])
                posts = self.convert_to_int(text[4])

                # Convert to dict and back to list removes duplicates
                email_list = list(dict.fromkeys(self.get_email(soup)))
                email_str = ','.join(email_list)

                user_info = [user, followers, following, posts, email_str, url]

                users_info.append(user_info)

            except Exception as e:
                print("Unable to get account information for " + url)
                print(e)
                users_info.append(['null', 'null', 'null', 'null', 'null', 'null'])

        return users_info

    def get_hashtag_post_count(self, url):
        """
        Helper function to get number of posts in a given hashtag. Used to ensure not looking for 1000 posts in a
        hashtag with only 100 posts

        :param url: string containing link to hashtag
        :return: int with number of posts in a given hashtag
        """

        if self.proxy:
            r = requests.get(url, verify='ca.crt.txt', proxies=PROXIES)
        else:
            r = requests.get(url)

        soup = BeautifulSoup(r.content, 'html.parser')
        body = soup.find('body')
        script = body.find('script')
        raw = script.text.strip().replace('window._sharedData =', '').replace(';', '')
        json_data = json.loads(raw)

        posts_count = json_data['entry_data']['TagPage'][0]['graphql']['hashtag']['edge_hashtag_to_media']['count']

        return posts_count

    @staticmethod
    def get_email(soup):
        """
        Helper function to find a valid email from an account description

        :param soup: BeautifulSoup object of a profile page
        :return: list of all valid emails found in account description
        """

        script_data = soup.find_all("script")
        description = script_data[3].getText()
        description = re.sub(r"(?<=\w)(\\)", r" \1", description)

        email_pattern = r'[\w\\][\w._%+-]+@[\w.-]+\.[a-zA-z]{2,4}'

        emails = re.findall(email_pattern, description)

        clean_emails = []

        for email in emails:

            # removes error code that appears with an emoji near the email
            if email.startswith('\\u'):
                pattern = r'[\\]+[\w]{5}'
                email = re.sub(pattern, '', email)

            # removes new line before email
            if email.startswith('\\n'):
                pattern = r'[\\]+[\w]'
                email = re.sub(pattern, '', email)

            # removes starting hyphen if there was one after emoji or newline char was removed
            if email.startswith('-'):
                email.replace('-', '', 1)

            # ensures after removing emoji or new line character we don't just have a username
            if not email.startswith('@'):
                clean_emails.append(email)

        return clean_emails

    @staticmethod
    def convert_to_int(num):
        """
        Helper function that converts profile statistics to int ifn ot already (i.e. 100m followers to 100000000)

        :param num: int or sting containing value to be converted.
        :return: float containing converted value (note: if a string with 'k' or 'm' the value has been rounded)
        """

        num = str(num)
        if 'k' in num:
            mult = 1000
        elif 'm' in num:
            mult = 1000000
        else:
            mult = 1

        num = re.sub("[^\d.]", "", num)
        return float(num) * mult

    @staticmethod
    def get_username_from_soup(soup):
        """
        Helper function to get username from profile page

        :param soup: BeautifulSoup object of profile page
        :return: string containing username associated with profile page
        """
        body = soup.find('body')
        script = body.find('script')
        raw = script.text.strip().replace('window._sharedData =', '').replace(';', '')
        json_data = json.loads(raw)
        posts = json_data['entry_data']['PostPage'][0]['graphql']
        posts = json.dumps(posts)
        posts = json.loads(posts)
        json_tree = objectpath.Tree(posts)
        result_list = list(json_tree.execute('$..owner["username"]'))

        return str(result_list[0])