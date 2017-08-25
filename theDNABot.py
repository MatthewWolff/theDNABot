# -*- coding: utf-8 -*-
import tweepy
import io
from keys import key, email_key
from subprocess import check_output
import random
from responses import response
from time import sleep
import re 
import urllib2  # for querying data to scrape
from bs4 import BeautifulSoup  # for WebScraping
from time import strftime
from date_list import dates
from datetime import datetime
import smtplib

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

TWEET_MAX_LENGTH = 140
RESET = "\033[0m"
RED = "\033[31m"      
BOLDWHITE = "\033[1m\033[37m"      
CLEAR = "\033[2J"  # clears the terminal screen
CYAN = "\033[36m"
YELLOW = "\033[33m"
# TODO: add more colors?

def wordsToDNA(string):
    return check_output(["Rscript wordsToDNA.r " + string], shell=True)

def dnaToWords(string):
    return check_output(["Rscript dnaToWords.r " + string], shell=True)

def doubleStrandedDNA(string):
    return check_output(["Rscript doubleStrandedDNA.r " + string], shell=True)

def getDate(date_string):
    date_values = re.split("-",date_string)
    date_values = [int(i) for i in date_values]
    return datetime(date_values[0],date_values[1],date_values[2])

def isTweetedWOTD():
    current_day = getDate(strftime("%Y-%m-%d"))
    for status in tweepy.Cursor(api.user_timeline).items():
        creation_day_raw = str(status.created_at)[:len(strftime("%Y-%m-%d"))]
        creation_day = getDate(creation_day_raw)
        if "Daily DNA: " in status.text and current_day == creation_day:
            return True
        elif creation_day < current_day: # passed through relevant timeframe
            return False
    return False

def scrubDefinitions(date):
    # NOTE: Definitions are shelved due to lack of space in tweet
    #     only implemented for Merriam-Webster (primary WOTD)
    # format into proper, small strings
    merriam_word_of_day_URL = "https://www.merriam-webster.com/word-of-the-day/" + date    
    page = urllib2.urlopen(merriam_word_of_day_URL)
    soup = BeautifulSoup(page, "html.parser")
    definitions_raw = str(soup.find("div", class_="wod-definition-container").p)
    definition_entry = re.sub("(?!</?strong>)<.+?>", "", definition_entry)  # remove formatting, ignoring strongs
    definition_entry = re.sub("(?<=<strong>) ?\w ?", "", definition_entry)  # remove letters inside of strongs
    definition_entry = re.sub("<.+?>", "", definition_entry)  # remove remaining strongs
    definition_entry = re.sub(":|;", ";:", definition_entry)  # create beginning and end indicators
    error_check = re.sub("[\xc2\xa0b\xc2\xa0]", "%ABORT%", definition_entry)  # IN CASE WONKY ENCODINGS?
#     if("%ABORT%" in error_check):
#         error_report = "For the " + date + " word of the day, invalid characters were encoded:\n" + definition_entry
#         alert(subject="Invalid Character Encodings", text=error_report)
    short_definitions = re.findall(":.+?(?:$|;)", definition_entry)  # split apart
    for i in range(0, len(short_definitions)):
        short_definitions[i] = re.sub(":|;", "", short_definitions[i]).strip()  # remove indicators and trim
    for x in short_definitions:
        print(x)
    return(short_definitions)

def getWOTD(date):
    merriam_word_of_day_URL = "https://www.merriam-webster.com/word-of-the-day/" + date    
    page = urllib2.urlopen(merriam_word_of_day_URL)
    soup = BeautifulSoup(page, "html.parser")
    return soup.find("div", class_="word-and-pronunciation").h1.string
    
def getBackupWOTD(date):
    date_backup = re.sub("-", "/", date)
    dictionary_word_of_day_URL = "http://www.dictionary.com/wordoftheday/" + date_backup
    page_backup = urllib2.urlopen(dictionary_word_of_day_URL)
    soup_backup = BeautifulSoup(page_backup, "html.parser")
    word_of_the_day_backup_raw = soup_backup.find("div", class_="origin-header")
    return re.findall("(?<=<strong>).+?(?=</strong>)", str(word_of_the_day_backup_raw))[0]

def prepareWOTD(word_of_the_day):
    daily_DNA = "Daily DNA: %s\n" % word_of_the_day
    daily_DNA += doubleStrandedDNA(word_of_the_day)
    daily_DNA += "\n(%s)" % dnaToWords(wordsToDNA(word_of_the_day))
    return(daily_DNA)

def wordOfTheDay(date="today"):
    if(date is "today"):
        date = strftime("%Y-%m-%d")
    
    # retrieve data & clean word and back up word (in case main is too long)
    word_of_the_day = getWOTD(date)
    word_of_the_day_backup = getBackupWOTD(date)
    daily_DNA = prepareWOTD(word_of_the_day)
    daily_DNA_backup = prepareWOTD(word_of_the_day_backup)

    if(len(daily_DNA) <= TWEET_MAX_LENGTH):
        api.update_status(status = daily_DNA)
        print YELLOW + "defined " + BOLDWHITE + daily_DNA + RESET
    elif(len(daily_DNA_backup) <= TWEET_MAX_LENGTH):
        api.update_status(status = daily_DNA_backup)
        print YELLOW + "defined " + BOLDWHITE + daily_DNA_backup + RESET
    else:
        content = "On %s, was unable to print daily words %s or %s due to length..." % (date, daily_DNA, daily_DNA_backup)
        alert(subject="Daily Words were too long", text=content)

def getResponse(username, user_DNA, specific="random"):
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

def isReplied(tweet):  # check if replied. if not, add to list and proceed to reply
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
        print(YELLOW + "found tweet and tweeted at " + BOLDWHITE + username + RESET)

def respond(tweet):  # provide custom translation or a full translation of their username
    username = tweet.user.screen_name
    if(not isReplied(tweet)):
        if("translate" in tweet.full_text):
            # grab everything after the "translate:"
            expr = re.compile(".+translate")
            start = expr.search(tweet.full_text).end()
            translated = wordsToDNA(tweet.full_text[start : len(tweet.full_text)]) 
            
            # translated can be up 3 tweets of text... break apart and reply
            to_tweet = divideTweet(translated, username)
            most_recent = None
            for new_tweet in to_tweet:
                print(YELLOW + "translated " + BOLDWHITE + new_tweet + RESET + "\n")
#                 most_recent = api.update_status(status=new_tweet,
#                                   in_reply_to_status_id=(tweet.id if most_recent is None else most_recent.id))
        else:  # do a full convert of their handle, and then translate back the template strand
            response = doubleStrandedDNA(username)
            response += "\n(%s)" % dnaToWords(wordsToDNA(username))
            print(YELLOW + "responded " + BOLDWHITE + response + RESET + "\n")
#             api.update_status(response, in_reply_to_status_id=tweet.id)
        
def divideTweet(long_tweet, username):
    # 1 tweet
    handle = "@" + username + " "
    my_handle = "@theDNABot "
    numbered = len("(x/y) ")
    
    single_tweet_length = (TWEET_MAX_LENGTH - len(handle))
    first_tweet_length = (TWEET_MAX_LENGTH - len(handle) - numbered)
    self_tweet_length = (TWEET_MAX_LENGTH - len(my_handle) - numbered)
    two_tweets_length = first_tweet_length + self_tweet_length
    
    if(len(long_tweet) <= single_tweet_length):
        return [handle + long_tweet]
    # 3 tweets
    elif(len(long_tweet) > two_tweets_length):
        return [handle + "(1/3) " + long_tweet[ :first_tweet_length],
                my_handle + "(2/3) " + long_tweet[first_tweet_length : two_tweets_length],
                my_handle + "(3/3) " + long_tweet[two_tweets_length : len(long_tweet)]]
    # 2 tweets
    else:
        return [handle + "(1/2) " + long_tweet[ : first_tweet_length],
                my_handle + "(2/2) " + long_tweet[first_tweet_length : len(long_tweet)]] 
        
def alert(subject="Error Occurred", text="TheDNABot has encountered an error during execution."):
    content = 'Subject: %s\n\n%s' % (subject, text)
    mail = smtplib.SMTP('smtp.gmail.com', 587)
    mail.ehlo()
    mail.starttls()
    mail.login(email_key["username"], email_key["password"])
    mail.sendmail(email_key["username"], email_key["destination"], content) 
    mail.close()
    print(BOLDWHITE + "ERROR OCCURRED, EMAIL SENT" + RESET)       

def main():
    for tweet in tweepy.Cursor(api.search, q='@theDNABot -filter:retweets', tweet_mode="extended").items(25):
        respond(tweet)
        
if __name__ == '__main__': 
#     for date in dates:
    while(1):  # run every 15 minutes
        if not isTweetedWOTD():
            wordOfTheDay()
        main()  
        sleep(900)
        # nohup python theDNABot.py &
        # tail -f nohup.out 
        
