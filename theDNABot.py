import re
import smtplib
from datetime import datetime, timedelta
from multiprocessing import Process
from subprocess import check_output
from time import sleep, strftime

import WordOfTheDay
import tweepy
from keys import key, email_key

# Will tweet in response to people who tweet/retweet #genetics
# if someone tweets at bot, translate their handle, or if they ask for a custom 
# translation, their message
consumer_key = key["consumer_key"]
consumer_secret = key["consumer_secret"]
access_token = key["access_token"]
access_token_secret = key["access_token_secret"]

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
PURPLE = "\033[35m"


def words_to_dna(string):
    string = re.sub("'", "", string)  # remove single quotes
    return check_output(["Rscript wordsToDNA.r " + string], shell=True)


def dna_to_words(string):
    return check_output(["Rscript dnaToWords.r " + string], shell=True)


def double_stranded_dna(string):
    string = re.sub("'", "", string)  # remove single quotes
    return check_output(["Rscript doubleStrandedDNA.r " + string], shell=True)


def get_date(date_string):
    date_values = re.split("-", date_string)
    date_values = [int(i) for i in date_values]
    return datetime(date_values[0], date_values[1], date_values[2])


def is_tweeted_wotd():
    current_day = get_date(strftime("%Y-%m-%d"))
    for status in tweepy.Cursor(api.user_timeline).items():
        tweeted_at = status.created_at - timedelta(hours=5)  # twitter is ahead
        creation_day_raw = str(tweeted_at)[:len(strftime("%Y-%m-%d"))]
        creation_day = get_date(creation_day_raw)

        if "Daily #DNA: " in status.text and current_day == creation_day:
            return True
        elif creation_day < current_day:  # passed through relevant timeframe
            return False
    return False


def is_waking_hours():
    current_time = datetime.now().hour
    early = 9  # 9 o'clock in the morning
    return current_time >= early


def clear_tweets():
    for status in tweepy.Cursor(api.user_timeline).items():
        try:
            api.destroy_status(status.id)
            print "deleted successfully"
        except tweepy.TweepError:
            print "Failed to delete:", status.id


def is_replied(tweet):  # check if replied. if not, add to list and reply
    with open("repliedTweets.txt", "rb") as replied_tweets:
        replies = replied_tweets.readlines()
    replied = (str(tweet.id) + "\n") in replies
    if not replied:
        with open("repliedTweets.txt", "ab") as replied_tweets:
            replied_tweets.write(str(tweet.id) + "\n")
    return replied


def respond(tweet):  # provide translation of custom message or username
    username = tweet.user.screen_name
    text = tweet.full_text
    if username != "theDNABot":  # don't respond to self
        if not is_replied(tweet):
            if "translate" in text:
                # grab everything after the "translate:"
                expr = re.compile(".+translate")
                start = expr.search(text).end()
                translated = words_to_dna(text[start:len(text)])
                if len(translated) < 3:
                    response = "@{0} Sorry @{0}, ".format(username)
                    response += "the translation was too short. Try avoiding "
                    response += "the letters B,J,O,U,X,Z, or any emoji!"
                    error_msg = RED + "Translation for "
                    error_msg += "@%s failed - too short\n" % username + RESET
                    with open("bot_log.txt", "ab") as bot_log:
                        bot_log.write(error_msg)
                    print error_msg
                    return api.update_status(response, tweet.id)

                # translated can be up 3 tweets of text... break apart and reply
                to_tweet = divide_tweet(translated, username)
                if to_tweet == -1:
                    response = "@{0} Sorry @{0}, ".format(username)
                    response += "the translation was too long. But congrats on "
                    response += "figuring out how to fit so many characters in!"
                    error_msg = RED + "Translation for "
                    error_msg += "@%s failed - too long\n" % username + RESET
                    with open("bot_log.txt", "ab") as bot_log:
                        bot_log.write(error_msg)
                    print error_msg
                    return api.update_status(response, tweet.id)

                recent = None
                for new_tweet in to_tweet:
                    with open("bot_log.txt", "ab") as bot_log:
                        bot_log.write("translated " + new_tweet + "\n")
                    print YELLOW + "translated " + BOLDWHITE + new_tweet + RESET
                    recent = api.update_status(status=new_tweet,
                                               in_reply_to_status_id=(tweet.id
                                                                      if recent is None
                                                                      else recent.id))
            else:  # do a full convert of their handle + translate back
                response = "@%s\n" % username
                response += double_stranded_dna(username)
                response += "\n(%s)" % dna_to_words(words_to_dna(username))
                if len(response) <= TWEET_MAX_LENGTH:
                    with open("bot_log.txt", "ab") as bot_log:
                        bot_log.write("responded  " + response + "\n")
                    print YELLOW + "responded " + BOLDWHITE + response + RESET
                else:
                    response = "@%s, your handle is too long!\n" % username
                    response += "Try doing a custom translation instead, by tw"
                    response += "eeting at me using the keyword \"translate\"?"
                    error_msg = RED + "Translation for "
                    error_msg += "@%s failed - handle too long\n" % username + RESET
                    with open("bot_log.txt", "ab") as bot_log:
                        bot_log.write(error_msg)
                    print error_msg
                return api.update_status(response, tweet.id)


def divide_tweet(long_tweet, username):
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
    if len(long_tweet) <= single_tweet_length:
        return [handle + long_tweet]
    # too many characters (edge case)
    elif len(long_tweet) >= three_tweets_length:
        return -1
        # 3 tweets
    elif len(long_tweet) > two_tweets_length:
        return [handle + "(1/3) "
                + long_tweet[:first_tweet_length],
                my_handle + "(2/3) "
                + long_tweet[first_tweet_length: two_tweets_length],
                my_handle + "(3/3) "
                + long_tweet[two_tweets_length: len(long_tweet)]]
    # 2 tweets
    else:
        return [handle + "(1/2) "
                + long_tweet[: first_tweet_length],
                my_handle + "(2/2) "
                + long_tweet[first_tweet_length: len(long_tweet)]]


def alert(subject="Error Occurred", text="TheDNABot has encountered an error."):
    content = 'Subject: %s\n\n%s' % (subject, text)
    mail = smtplib.SMTP('smtp.gmail.com', 587)
    mail.ehlo()
    mail.starttls()
    mail.login(email_key["username"], email_key["password"])
    mail.sendmail(email_key["username"], email_key["destination"], content)
    mail.close()
    print(RED + "ERROR OCCURRED, EMAIL SENT" + RESET)


def daily_tweet():
    """daily tweet multi-processing method"""
    print(CYAN + "Checking for daily tweet..." + RESET)
    while 1:
        if not is_tweeted_wotd() and is_waking_hours():
            tweet = WordOfTheDay.get_tweet()
            if tweet == -1:
                content = "Unable to print daily words "
                alert(subject="Daily Words were too long", text=content)
            else:
                try:
                    api.update_status(status=tweet)
                except tweepy.TweepError as e:
                    print(RED + "Duplicate Word of Day ERROR" + RESET)
                    content = "Could not tweet:\n" + e.api_code + "\n" + tweet
                    alert(Subject="Duplicate Daily Word?", text=content)

        sleep(14400)  # 4 hour wait


def check_tweets():
    """tweet upkeep multi-processing method"""
    print(CYAN + "Beginning polling...\n" + RESET)
    while 1:
        try:
            for tweet in tweepy.Cursor(api.search, q='@theDNABot -filter:retweets',
                                       tweet_mode="extended").items():
                respond(tweet)
        except tweepy.TweepError as e:
            print RED + e.api_code + RESET

        sleep(30)


if __name__ == '__main__':
    wotd = Process(target=daily_tweet)
    wotd.start()
    tweet_poll = Process(target=check_tweets)
    tweet_poll.start()






# sudo apt-get install tcsh
# tcsh
# sudo apt-get install r-base &
# sudo pip install tweepy &
# sudo pip install urllib2 &
# sudo pip install beautifulsoup4 &
# #
#
# matthewsftp
# put *.py *.txt *.r
# exit
# #
#
# nohup python theDNABot.py >>& bot_log.out &  ((tcsh specific))
# tail -f bot_log.txt
