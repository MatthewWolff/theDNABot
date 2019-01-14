import WordOfTheDay
import re
import smtplib
import tweepy
from datetime import datetime, timedelta
from keys import key, email_key
from subprocess import check_output
from time import sleep, strftime
from tweepy import TweepError

# if someone tweets at bot, translate their handle, or if they ask for a custom
# translation, their message

consumer_key = key["consumer_key"]
consumer_secret = key["consumer_secret"]
access_token = key["access_token"]
access_token_secret = key["access_token_secret"]

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

TWEET_MAX_LENGTH = 280
LOGGING_FILE = "dnabot.log"

RED = "\033[31m"
RESET = "\033[0m"
BOLDWHITE = "\033[1m\033[37m"
YELLOW = "\033[33m"
CLEAR = "\033[2J"  # clears the terminal screen
CYAN = "\033[36m"
PURPLE = "\033[35m"


def words_to_dna(string):
    return check_output(["Rscript auxiliary/wordsToDNA.r " + string.replace("'", "")],
                        shell=True).decode("utf-8")


def dna_to_words(string):
    return check_output(["Rscript auxiliary/dnaToWords.r " + string.replace("'", "")],
                        shell=True).decode("utf-8")


def double_stranded_dna(string):
    return check_output(["Rscript auxiliary/doubleStrandedDNA.r " + string.replace("'", "")],
                        shell=True).decode("utf-8")


def get_date(date_string):
    date_values = re.split("-", date_string)
    date_values = [int(i) for i in date_values]
    return datetime(date_values[0], date_values[1], date_values[2])


def is_tweeted_wotd():
    current_day = get_date(strftime("%Y-%m-%d"))
    for status in tweepy.Cursor(api.user_timeline).items():
        creation_day = get_twitter_time(status)
        if "Daily #DNA: " in status.text and current_day == creation_day:
            return True
        elif creation_day < current_day:  # passed through relevant time frame
            return False
    return False


def get_twitter_time(status):
    tweeted_at = status.created_at - timedelta(hours=5)  # twitter is ahead
    creation_day_raw = str(tweeted_at)[:len(strftime("%Y-%m-%d"))]
    creation_day = get_date(creation_day_raw)
    return creation_day


def is_waking_hours():
    current_time = datetime.now().hour
    early = 9  # 9 o'clock in the morning
    return current_time >= early


def clear_tweets():
    response = None
    while response != "y":
        response = input(colors.red("ARE YOU SURE YOU WANT TO ERASE ALL TWEETS? (y/n)"))

    for status in tweepy.Cursor(api.user_timeline).items():
        try:
            api.destroy_status(status.id)
            print("deleted successfully")
        except TweepError:
            print("Failed to delete:", status.id)


def is_replied(tweet):  # check if a tweet or tweet id has been replied to (favorited)
    tweet_id = tweet if type(tweet) is int else tweet.id
    favorites = [x.id for x in api.favorites()]
    return tweet_id in favorites


def respond(tweet):  # provide translation of custom message or username
    """
    makes a response to a tweet
    :param tweet: the tweet that was directed at @theDNABot
    :return: the tweet that was made, if any
    """
    username = tweet.user.screen_name
    text = tweet.full_text
    if username != "theDNABot" and not is_replied(tweet):  # don't respond to self
        try:
            if "translate" in text:
                # grab everything after the "translate:"
                expr = re.compile(".+translate")
                start = expr.search(text).end()
                translated = words_to_dna(text[start:len(text)])
                if len(translated) < 3:
                    response = too_short_err(username)
                    return api.update_status(response, tweet.id)

                # translated can be up 3 tweets of text... break apart and reply
                to_tweet = divide_tweet(translated, username)
                if to_tweet == -1:
                    response = too_long_err(username)
                    return api.update_status(response, tweet.id)

                # make a response
                last_tweet = None
                for new_tweet in to_tweet:
                    last_tweet = api.update_status(status=new_tweet,
                                                   in_reply_to_status_id=(
                                                       tweet.id if last_tweet is None else last_tweet.id
                                                   ))
                return to_tweet[0]
            else:  # do a full convert of their handle + translate back
                response = get_response(username)
                return api.update_status(response, tweet.id)
        except TweepError as err:
            log_error(tweepy_error_message(err))


def mark_replied(tweet_id):
    api.create_favorite(tweet_id)


def get_response(username):
    response = formulate_response(username)
    if len(response) <= TWEET_MAX_LENGTH:
        log(f"responded {response}")
    else:
        response = name_err(username)
    return response


def formulate_response(username):
    response = f"@%s{username}\n" + double_stranded_dna(username) + \
               "\n(%s)\n" % dna_to_words(words_to_dna(username))
    return response


def name_err(username):
    response = f"@{username}, your handle is too long!\n" \
               "Try doing a custom translation instead, by " \
               "tweeting at me using the keyword \"translate\"?"
    error_msg = RED + f"Translation for @{username} failed - handle too long\n" + RESET
    log_error(error_msg)
    return response


def too_long_err(username):  # defunct -- impossible to have a username too long now
    response = f"@{username} Sorry @{username}, " \
               "the translation was too long. But congrats on " \
               "figuring out how to fit so many characters in!"
    error_msg = RED + f"Translation for @{username} failed - too long" + RESET
    log_error(error_msg)
    return response


def too_short_err(username):
    response = "@{0} Sorry @{0}, ".format(username) + \
               "the translation was too short. Try avoiding " \
               "the letters B,J,O,U,X,Z, or any emoji!"
    error_msg = RED + f"Translation for @{username} failed - too short" + RESET
    log_error(error_msg)
    return response


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
    content = f"Subject: {subject}\n\n{text}"
    mail = smtplib.SMTP("smtp.gmail.com", 587)
    mail.ehlo()
    mail.starttls()
    mail.login(email_key["username"], email_key["password"])
    mail.sendmail(email_key["username"], email_key["destination"], content)
    mail.close()
    print(RED + "ERROR OCCURRED, EMAIL SENT" + RESET)


def daily_tweet():
    print(CYAN + "Checking for daily tweet..." + RESET)
    while 1:
        if not is_tweeted_wotd() and is_waking_hours():
            attempt_tweet()
        sleep(60 * 60 * 4)  # 4 hour wait


def attempt_tweet():
    """attempt to tweet the Word of the Day"""
    tweet, source = WordOfTheDay.get_tweet()
    date = strftime("%Y-%m-%d")
    if tweet is -1:
        msg = "Unable to print daily words."
        log_error(msg)
        alert(subject="Daily Words were too long", text=f"{date} -- {msg}")
    else:
        try:
            api.update_status(status=tweet)
            word = tweet.split("\n")[0].split()[-1]
            log(f"word: {word} from source: {source}")
        except TweepError as e:
            msg = f"Duplicate Word of Day ERROR\n" + \
                  f"Could not tweet:\n{e.api_code}\n{tweet}"
            log_error(msg)
            alert(subject="Duplicate Daily Word?", text=f"{date} -- {msg}")


def check_tweets():
    """polls for tweets at self and tries to respond to them"""
    print(CYAN + "Beginning polling...\n" + RESET)
    while True:
        poll()
        sleep(60)


def poll():
    try:
        for tweet in tweepy.Cursor(api.search, q="@theDNABot -filter:retweets", tweet_mode="extended").items():
            if not is_replied(tweet):
                mark_replied(tweet.id)  # mark replied no matter what
                respond(tweet)
    except TweepError as err:
        log_error(tweepy_error_message(err))


def tweepy_error_message(e):
    return e.response.reason


def log_error(err):
    print(RED + err + RESET)
    log(f"\n{RED}ERR: {err}{RESET}\n")


def log(message):
    with open(LOGGING_FILE, "a") as log_file:
        log_file.write(f"{strftime('[%Y-%m-%d] @ %H:%M:%S')} {message}\n")

