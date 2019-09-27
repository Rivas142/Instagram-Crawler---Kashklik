import pandas as pd
import concurrent.futures
import numpy
import os
import time
import json
from instagrambot import InstagramBot

with open('config/configmain.json') as config_file:
    parameters = json.load(config_file)

HASHTAGS = parameters["hashtags"]
NUM_PICTURES = parameters["num_pictures"]
THREADS = parameters["threads"]
FOLDER_PATH = parameters["folder_path"]
HEADLESS = parameters["headless"]
PROXY = parameters["proxy"]
MIN_FOLLOWERS = parameters["min_followers"]
MAX_FOLLOWERS = parameters["max_followers"]

def get_influencer_csv(csv):
    """
    Creates and saves CSV of influencers (users with valid email and within followers threshold)

    :param csv: string containing file path to CSV containing profile information
    :return: None
    """

    df = pd.read_csv(csv)
    df = df[(df.Followers > MIN_FOLLOWERS) & (df.Followers < MAX_FOLLOWERS)]
    df = df.dropna(subset=['Email'])

    csv_name = csv.replace('.csv', '') + '_influencers.csv'
    df.to_csv(csv_name, index=False)

def main():
    """
    Main function for collecting profile and influencer information from a provided hashtag.

    For each hashtag in HASHTAGS go through NUM_PICTURES pictures and extract the profile information associated with
    them. Save the user information to a CSV and then of those user find the influencers and copy them to an additional
    separate CSv. CSV has the following column names:
        User (the profile username),
        Followers (number of followers),
        Following (number of profiles the account is following),
        Posts (number of posts),
        Email (profile's email if publicly available),
        URL (link to profile URL).

    :return: None
    """

    for hashtag in HASHTAGS:
        start = time.time()
        print("Getting profile info for #" + hashtag)
        bot = InstagramBot(headless=HEADLESS, proxy=PROXY, threads=THREADS)
        profile_links = bot.get_users(num_pictures=NUM_PICTURES, hashtag=hashtag)

        profile_links_divided = list(numpy.array_split(numpy.array(list(profile_links)), THREADS))
        profile_links_divided = [numpy_arr.tolist() for numpy_arr in profile_links_divided]

        with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as executor:
            user_info_future = {executor.submit(bot.get_user_info, profile_links) for profile_links in
                                profile_links_divided}

        user_info_divided = [future.result() for future in user_info_future]
        user_info = [info for sublist in user_info_divided for info in sublist]
        for info in user_info:
            info.append(hashtag)

        users_df = pd.DataFrame(user_info,
                                columns=['User', 'Followers', 'Following', 'Posts', 'Email', 'URL', 'Hashtag'])
        end = time.time()
        users_df.loc[len(users_df)] = ['RUNTIME', str(end-start), 0, 0, 0, 0, 0]

        csv_name = FOLDER_PATH + '/users_' + hashtag + '.csv'
        try:
            users_df.to_csv(csv_name, index=False)
        except Exception as e:
            print('Unable to save to csv. It is probably open on your machine')
            print(e)

        get_influencer_csv(csv_name)

        print("#" + hashtag + " took " + str(end-start) + "s to run")


if __name__ == '__main__':
    main()
