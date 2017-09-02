import re
import urllib2  # for querying data to scrape
from time import strftime

from bs4 import BeautifulSoup  # for WebScraping
from theDNABot import words_to_dna, dna_to_words, double_stranded_dna

RED = "\033[31m"
RESET = "\033[0m"
BOLDWHITE = "\033[1m\033[37m"
PURPLE = "\033[35m"
YELLOW = "\033[33m"

TWEET_MAX_LENGTH = 140


def get_wotd(date):
    merriam_word_url = "https://www.merriam-webster.com/word-of-the-day/"
    merriam_word_url += date
    page = urllib2.urlopen(merriam_word_url)
    soup = BeautifulSoup(page, "html.parser")
    return soup.find("div", class_="word-and-pronunciation").h1.string


def get_backup_wotd(date):
    dictionary_word_url = "http://www.dictionary.com/wordoftheday/"
    dictionary_word_url += re.sub("-", "/", date)
    page = urllib2.urlopen(dictionary_word_url)
    soup = BeautifulSoup(page, "html.parser")
    word_raw = soup.find("div", class_="origin-header")
    return re.findall("(?<=<strong>).+?(?=</strong>)", str(word_raw))[0]


def get_backup_wotd2():
    wordthink_word_url = "http://www.wordthink.com/"
    page = urllib2.urlopen(wordthink_word_url)
    soup = BeautifulSoup(page, "html.parser")
    word_raw = soup.find("h1").next_sibling.next_sibling
    return re.findall("(?<=<b>).+?(?=</b>.?<i>)", str(word_raw))[0].lower()


def prepare_wotd(word_of_the_day):
    daily_dna = "Daily #DNA: %s\n" % word_of_the_day
    daily_dna += double_stranded_dna(word_of_the_day)
    daily_dna += "\n(%s)" % dna_to_words(words_to_dna(word_of_the_day))
    return daily_dna


def get_tweet(date="today"):
    if date is "today":
        date = strftime("%Y-%m-%d")

    # retrieve data & clean word and back up word (in case main is too long)
    word_of_the_day = get_wotd(date)
    daily_dna = prepare_wotd(word_of_the_day)
    if len(daily_dna) <= TWEET_MAX_LENGTH:
        print PURPLE + "Source: Merriam-Webster" + RESET
        print YELLOW + "defined " + BOLDWHITE + daily_dna + RESET + "\n"
        return daily_dna

    wotd_backup = get_backup_wotd(date)
    daily_dna_backup = prepare_wotd(wotd_backup)
    if len(daily_dna_backup) <= TWEET_MAX_LENGTH:
        print PURPLE + "Source: Dictionary.com" + RESET
        print YELLOW + "defined " + BOLDWHITE + daily_dna_backup + RESET + "\n"
        return daily_dna_backup

    wotd_backup2 = get_backup_wotd2(date)
    daily_dna_backup2 = prepare_wotd(wotd_backup2)
    if len(daily_dna_backup2) <= TWEET_MAX_LENGTH:
        print("Source: Wordthink")
        print YELLOW + "defined " + BOLDWHITE + daily_dna_backup2 + RESET + "\n"
        return daily_dna_backup2

    return -1
