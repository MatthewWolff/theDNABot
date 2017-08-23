import tweepy
import io
from keys import key
from subprocess import check_output
import random
from responses import response
from time import sleep
import re

# Will tweet in response to people who tweet/retweet #genetics
# if someone tweets at bot, translate their handle, or if they ask for a custom 
# translation, their message
consumer_key = key['consumer_key']
consumer_secret = key['consumer_secret']
access_token = key['access_token']
access_token_secret = key['access_token_secret']

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

TWEET_MAX_LENGTH = 180

def wordsToDNA(string):
    return check_output(["Rscript wordsToDNA.r " + string], shell=True)

def dnaToWords(string):
    return check_output(["Rscript dnaToWords.r " + string], shell=True)

def doubleStrandedDNA(string):
    return check_output(["Rscript doubleStrandedDNA.r " + string], shell=True)

def getResponse(username, user_DNA, specific = "random"):
    if(specific != "random"):
        return response[specific].format(handle=username, DNA=user_DNA)
    base_response = random.choice(response)
    return base_response.format(handle=username, DNA=user_DNA)

def clearTweets():
    for status in tweepy.Cursor(api.user_timeline).items():
           try:
            api.destroy_status(status.id)
           except:
               print "Failed to delete:", status.id
               
def isNew(username):  # check if name is new, if not, ret false, else, add + ret true
    with open("tweetedNames.txt", "rb") as used_names:
        prev_tweeted = used_names.readlines()
    is_not_present = (username + "\n") not in prev_tweeted
    if(is_not_present):
        with open("tweetedNames.txt", "ab") as used_names:
            used_names.write(username + "\n")
    return is_not_present

def isReplied(tweet): # check if replied. if not, add to list and proceed to reply
    with open("repliedTweets.txt", "rb") as replied_tweets:
        replies = replied_tweets.readlines()
    is_replied = (str(tweet.id) + "\n") in replies
    if(not is_replied):
        with open("repliedTweets.txt", "ab") as replied_tweets:
            replied_tweets.write(str(tweet.id) + "\n")
    return is_replied
    
def filterAndTweet(tweet):
    username = tweet.user.screen_name
    if(isNew(username) and not tweet.retweeted):  # try and ignore retweets
        # make R calls
        user_DNA = wordsToDNA(username)
        reverse_DNA = dnaToWords(user_DNA)
        # Prevent errors
        if(user_DNA == "" or len(user_DNA) <= 6):  # if username can't be translated
            print("ERROR: could not translate " + username)
            return
        tweet_response = getResponse(username, user_DNA)
        try:
            api.update_status(status=tweet_response, in_reply_to_status_id=tweet.id)
        except TweepError as inst:  # TODO: figure out how to catch error reasons?
            print("ERROR: ", inst.message[0]['code'], tweet_response)
            return
        print("found tweet and tweeted at " + username)

def respond(tweet):  # provide custom translation or a full translation of their username
    username = tweet.user.screen_name
    if(not isReplied(tweet)):
        if("translate:" in tweet.full_text):
            # grab everything after the "translate:"
            expr = re.compile(".+translate:")
            start = expr.search(tweet.full_text).end()
            translated = wordsToDNA(tweet.full_text[start:len(tweet.full_text)]) 
            # can be up to 477 characters... break apart and reply
            for new_tweet in divideTweet(translated, username):
                print("translated " + new_tweet + "\n")
                #api.update_status(status=new_tweet, in_reply_to_status_id=tweet.id)
        else: # do a full convert of their handle, and then translate back the template strand
            response = doubleStrandedDNA(username)
            response += "\n(%s)" % dnaToWords(wordsToDNA(username))
            print("responded " + response + "\n")
            #api.update_status(response, in_reply_to_status_id=tweet.id)
        
def divideTweet(long_tweet, username):
    # 1 tweet
    handle = "@" + username + " "
    numbered = len("(x/y) ")
    one_tweet_length = (TWEET_MAX_LENGTH - len(handle) - numbered)
    if(len(long_tweet) <= (TWEET_MAX_LENGTH - len(handle))):
        return [handle + long_tweet]
    # 3 tweets
    elif(len(long_tweet)/float(one_tweet_length) > 2):
        return [handle + "(1/3) " + long_tweet[:(one_tweet_length + 1)],
                handle + "(2/3) " + long_tweet[(one_tweet_length + 1) :(2 * one_tweet_length + 1)],
                handle + "(3/3) " + long_tweet[(2 * one_tweet_length + 1):len(long_tweet)]]
    # 2 tweets
    else:
        return [handle + "(1/2) " + long_tweet[:(one_tweet_length + 1)],
                handle + "(2/2) " + long_tweet[(one_tweet_length + 1):len(long_tweet)]]        

def main():
    for tweet in tweepy.Cursor(api.search, q='@theDNABot -filter:retweets', tweet_mode="extended").items():
        respond(tweet)
#     for tweet in tweepy.Cursor(api.search, q='#genetics -filter:retweets').items(50):
#         filterAndTweet(tweet) 
#     for tweet in tweepy.Cursor(api.search, q='#DNA -filter:retweets').items(50):
#         filterAndTweet(tweet)
if __name__ == '__main__': 
#   api.update_status(status=(doubleStrandedDNA("Hello, World!")))
#     while(1):  # run every 15 minutes
    main()  
#         sleep(900)
        # nohup python theDNABot.py &
        # tail -f nohup.out 
        
