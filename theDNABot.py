import tweepy
import io
import smtplib
import WordOfTheDay 
import re 
import urllib2  # for querying data to scrape
from bs4 import BeautifulSoup  # for WebScraping
from time import strftime
from datetime import datetime
from subprocess import check_output
from time import sleep
from multiprocessing import Process
from keys import key, email_key


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

RED = "\033[31m"      
RESET = "\033[0m"
BOLDWHITE = "\033[1m\033[37m"      
YELLOW = "\033[33m"
CLEAR = "\033[2J"  # clears the terminal screen
CYAN = "\033[36m"

def wordsToDNA(string):
    string = re.sub("'", "", string)  # remove single quotes
    return check_output(["Rscript wordsToDNA.r " + string], shell=True)

def dnaToWords(string):
    return check_output(["Rscript dnaToWords.r " + string], shell=True)

def doubleStrandedDNA(string):
    string = re.sub("'", "", string)  # remove single quotes
    return check_output(["Rscript doubleStrandedDNA.r " + string], shell=True)

def getDate(date_string):
    date_values = re.split("-", date_string)
    date_values = [int(i) for i in date_values]
    return datetime(date_values[0], date_values[1], date_values[2])

def isTweetedWOTD():
    current_day = getDate(strftime("%Y-%m-%d"))
    for status in tweepy.Cursor(api.user_timeline).items():
        creation_day_raw = str(status.created_at)[:len(strftime("%Y-%m-%d"))]
        creation_day = getDate(creation_day_raw)
        if "Daily DNA: " in status.text and current_day == creation_day:
            return True
        elif creation_day < current_day:  # passed through relevant timeframe
            return False
    return False

def clearTweets():
    for status in tweepy.Cursor(api.user_timeline).items():
        try:
            api.destroy_status(status.id)
            print "deleted successfully"
        except:
            print "Failed to delete:", status.id

def isReplied(tweet):  # check if replied. if not, add to list and reply
    with open("repliedTweets.txt", "rb") as replied_tweets:
        replies = replied_tweets.readlines()
    is_replied = (str(tweet.id) + "\n") in replies
    if(not is_replied):
        with open("repliedTweets.txt", "ab") as replied_tweets:
            replied_tweets.write(str(tweet.id) + "\n")
    return is_replied

def respond(tweet):  # provide translation of custom message or username
    username = tweet.user.screen_name
    text = tweet.full_text
    if(username != "theDNABot"):  # don't respond to self
        if(not isReplied(tweet)):
            if("translate" in text):
                # grab everything after the "translate:"
                expr = re.compile(".+translate")
                start = expr.search(text).end()
                translated = wordsToDNA(text[start:len(text)]) 
                if len(translated) < 3:
                    response = "@{0} Sorry @{0}, ".format(username)
                    response += "the translation was too short. Try avoiding "
                    response += "the letters B,J,O,U,X,Z, or any emoji!"
                    error_msg = RED + "Translation for "
                    error_msg += "@%s failed - too short\n" % username + RESET
                    print error_msg
                    return api.update_status(response, tweet.id)
                
                # translated can be up 3 tweets of text... break apart and reply
                to_tweet = divideTweet(translated, username)
                if to_tweet == -1:
                    response = "@{0} Sorry @{0}, ".format(username)
                    response += "the translation was too long. Congrats on "
                    response += "figuring out how to fit so many characters in"
                    response += ", though!"
                    error_msg = RED + "Translation for "
                    error_msg += "@%s failed - too long\n" % username + RESET
                    print error_msg
                    return api.update_status(response, tweet.id)
                
                recent = None
                for new_tweet in to_tweet:
                    print YELLOW + "translated " + BOLDWHITE + new_tweet + RESET
                    recent = api.update_status(status=new_tweet,
                                    in_reply_to_status_id=(tweet.id 
                                                           if recent is None
                                                           else recent.id))
            else:  # do a full convert of their handle + translate back
                response = "@%s\n" % username
                response += doubleStrandedDNA(username)
                response += "\n(%s)" % dnaToWords(wordsToDNA(username))
                if len(response) <= TWEET_MAX_LENGTH:
                    print YELLOW + "responded " + BOLDWHITE + response + RESET
                else:
                    response = "@%s, your handle is too long!\n" % username
                    response += "Try doing a custom translation instead, by tw"
                    response += "eeting at me using the keyword \"translate\"?"
                return api.update_status(response, tweet.id)
        
def divideTweet(long_tweet, username):
    # 1 tweet
    handle = "@" + username + " "
    my_handle = "@theDNABot "
    numbered = len("(x/y) ")
    
    single_tweet_length = (TWEET_MAX_LENGTH - len(handle))
    first_tweet_length = (TWEET_MAX_LENGTH - len(handle) - numbered)
    self_tweet_length = (TWEET_MAX_LENGTH - len(my_handle) - numbered)
    two_tweets_length = first_tweet_length + self_tweet_length
    three_tweets_length = two_tweets_length + self_tweet_length
    
    # 1 tweet
    if(len(long_tweet) <= single_tweet_length):
        return [handle + long_tweet]
    # too many characters (edge case)
    elif(len(long_tweet) >= three_tweets_length):
        return -1 
    # 3 tweets
    elif(len(long_tweet) > two_tweets_length):
        return [handle + "(1/3) "
                + long_tweet[ :first_tweet_length],
                my_handle + "(2/3) " 
                + long_tweet[first_tweet_length : two_tweets_length],
                my_handle + "(3/3) " 
                + long_tweet[two_tweets_length : len(long_tweet)]]
    # 2 tweets
    else:
        return [handle + "(1/2) " 
                + long_tweet[ : first_tweet_length],
                my_handle + "(2/2) " 
                + long_tweet[first_tweet_length : len(long_tweet)]] 
        
def alert(subject="Error Occurred", text="TheDNABot has encountered an error."):
    content = 'Subject: %s\n\n%s' % (subject, text)
    mail = smtplib.SMTP('smtp.gmail.com', 587)
    mail.ehlo()
    mail.starttls()
    mail.login(email_key["username"], email_key["password"])
    mail.sendmail(email_key["username"], email_key["destination"], content) 
    mail.close()
    print(BOLDWHITE + "ERROR OCCURRED, EMAIL SENT" + RESET)       

def dailyTweet():
    '''daily tweet multi-processing method'''
    print(CYAN + "Checking for daily tweet..." + RESET)
    while(1):
        if not isTweetedWOTD():
            daily_tweet = WordOfTheDay.getTweet()
            if(daily_tweet == -1):
                content = "On %s, was unable to print daily words " % date
                alert(subject="Daily Words were too long", text=content)
            else:
                api.update_status(status=daily_tweet)
        sleep(14400)  # 4 hour wait
        
def checkTweets():
    '''tweet upkeep multi-processing method'''
    print(CYAN + "Beginning polling..." + RESET)
    while(1):
        for tweet in tweepy.Cursor(api.search, q='@theDNABot -filter:retweets',
                                   tweet_mode="extended").items(25):
            respond(tweet)
        sleep(30)
        
if __name__ == '__main__': 
    
    wotd = Process(target=dailyTweet)
    wotd.start()
    tweet_poll = Process(target=checkTweets)
    tweet_poll.start()

    
        # nohup python theDNABot.py &
        # tail -f nohup.out 
        
        
        
        
        
        
        
        
