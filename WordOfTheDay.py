import re 
import urllib2  # for querying data to scrape
from bs4 import BeautifulSoup  # for WebScraping
from time import strftime
from datetime import datetime
from subprocess import check_output
from theDNABot import wordsToDNA, dnaToWords, doubleStrandedDNA


RED = "\033[31m"      
RESET = "\033[0m"
BOLDWHITE = "\033[1m\033[37m"      
YELLOW = "\033[33m"

TWEET_MAX_LENGTH = 140

def getWOTD(date):
    merriam_word_URL = "https://www.merriam-webster.com/word-of-the-day/"
    merriam_word_URL += date    
    page = urllib2.urlopen(merriam_word_URL)
    soup = BeautifulSoup(page, "html.parser")
    return soup.find("div", class_="word-and-pronunciation").h1.string

def getBackupWOTD(date):
    dictionary_word_URL = "http://www.dictionary.com/wordoftheday/"
    dictionary_word_URL += re.sub("-", "/", date)
    page = urllib2.urlopen(dictionary_word_of_day_URL)
    soup = BeautifulSoup(page, "html.parser")
    word_raw = soup.find("div", class_="origin-header")
    return re.findall("(?<=<strong>).+?(?=</strong>)", str(word_raw))[0]

def getBackupWOTD2(date):
    wordthink_word_URL = "http://www.wordthink.com/"
    page = urllib2.urlopen(wordthink_word_URL)
    soup = BeautifulSoup(page, "html.parser")
    word_raw = soup.find("h1").next_sibling.next_sibling  # start at 
    return re.findall("(?<=<b>).+?(?=</b>.?<i>)", str(word_raw))[0].lower()

def prepareWOTD(word_of_the_day):
    daily_DNA = "Daily DNA: %s\n" % word_of_the_day
    daily_DNA += doubleStrandedDNA(word_of_the_day)
    daily_DNA += "\n(%s)" % dnaToWords(wordsToDNA(word_of_the_day))
    return(daily_DNA)

def getTweet(date="today"):
    if(date is "today"):
        date = strftime("%Y-%m-%d")
    
    # retrieve data & clean word and back up word (in case main is too long)
    word_of_the_day = getWOTD(date)
    daily_DNA = prepareWOTD(word_of_the_day)
    if(len(daily_DNA) <= TWEET_MAX_LENGTH):
        print("Source: Merriam-Webster")
        print YELLOW + "defined " + BOLDWHITE + daily_DNA + RESET + "\n"
        return daily_DNA

    wotd_backup = getBackupWOTD(date)
    daily_DNA_backup = prepareWOTD(wotd_backup)
    if(len(daily_DNA_backup) <= TWEET_MAX_LENGTH):
        print("Source: Dictionary.com")
        print YELLOW + "defined " + BOLDWHITE + daily_DNA_backup + RESET + "\n"
        return daily_DNA_backup
    
    wotd_backup2 = getBackupWOTD2(date)
    daily_DNA_backup2 = prepareWOTD(wotd_backup2)
    if(len(daily_DNA_backup2) <= TWEET_MAX_LENGTH):
        print("Source: Wordthink")
        print YELLOW + "defined " + BOLDWHITE + daily_DNA_backup2 + RESET + "\n" 
        return daily_DNA_backup2
    
    return -1

