#!/usr/bin/env python3
from multiprocessing import Process
from theDNABot import daily_tweet, check_tweets

if __name__ == "__main__":
    wotd = Process(target=daily_tweet)
    wotd.start()
    tweet_poll = Process(target=check_tweets)
    tweet_poll.start()
