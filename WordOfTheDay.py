import re
from time import strftime
from subprocess import check_output

from bs4 import BeautifulSoup
from requests import get

RED = "\033[31m"
RESET = "\033[0m"
BOLDWHITE = "\033[1m\033[37m"
PURPLE = "\033[35m"
YELLOW = "\033[33m"

TWEET_MAX_LENGTH = 280


# wasn't importing properly...?
def words_to_dna(string):
    return check_output(["Rscript wordsToDNA.r " + string.replace("'", "")],
                        shell=True).decode("utf-8")


def dna_to_words(string):
    return check_output(["Rscript dnaToWords.r " + string.replace("'", "")],
                        shell=True).decode("utf-8")


def double_stranded_dna(string):
    return check_output(["Rscript doubleStrandedDNA.r " + string.replace("'", "")],
                        shell=True).decode("utf-8")


def get_wotd(date):
    merriam_word_url = f"https://www.merriam-webster.com/word-of-the-day/{date}"
    page = get(merriam_word_url).text
    soup = BeautifulSoup(page, "html.parser")
    word = soup.find("div", class_="word-and-pronunciation").h1.string
    raw_def = soup.find("div", class_="wod-definition-container").p.text
    definition = raw_def[raw_def.find(":") + 2:]  # skip colon and the space after it
    return word, definition


def get_backup_wotd(date):
    dictionary_word_url = f"http://www.dictionary.com/wordoftheday/{date.replace('-','/')}"
    page = get(dictionary_word_url).text
    soup = BeautifulSoup(page, "html.parser")
    word = soup.find("div", class_="origin-header").text.split()[-1]
    definition = soup.find("li", class_="first").span.text
    return word, definition


def get_backup_wotd2(date):
    wordthink_word_url = f"http://www.wordthink.com/{date.replace('-','/')}"
    page = get(wordthink_word_url).text
    soup = BeautifulSoup(page, "html.parser")
    word = soup.find("h2").text.strip()
    # wow this is a pain in the ass
    raw_def = soup.find("div", "postmeta").next_sibling.next_sibling.i.next_sibling
    definition = re.sub(":? ?“", "", re.findall("[A-Z].+?[.“]", raw_def)[0])
    if definition[-1] != ".":
        definition += "."
    return word, definition


def prepare_wotd(word_of_the_day, definition):
    daily_dna = f"Daily #DNA: {word_of_the_day}\n"
    daily_dna += double_stranded_dna(word_of_the_day)
    daily_dna += "\n(%s)\n" % dna_to_words(words_to_dna(word_of_the_day))
    daily_dna += definition.capitalize()
    return daily_dna


def get_tweet(date=strftime("%Y-%m-%d")):  # ex: 2019-01-01
    # retrieve data & clean word and back up word (in case main is too long)
    word_of_the_day, definition = get_wotd(date)
    daily_dna = prepare_wotd(word_of_the_day, definition)
    if len(daily_dna) <= TWEET_MAX_LENGTH:
        source = PURPLE + "Source: Merriam-Webster" + RESET
        print(PURPLE + source,
              YELLOW + "defined",
              BOLDWHITE + daily_dna + RESET, sep="\n")
        return daily_dna, source

    wotd_backup, definition = get_backup_wotd(date)
    daily_dna = prepare_wotd(wotd_backup, definition)
    if len(daily_dna) <= TWEET_MAX_LENGTH:
        source = PURPLE + "Source: Dictionary.com" + RESET
        print(PURPLE + source,
              YELLOW + "defined",
              BOLDWHITE + daily_dna + RESET, sep="\n")
        return daily_dna, source

    wotd_backup2, definition = get_backup_wotd2(date)
    daily_dna = prepare_wotd(wotd_backup2, definition)
    if len(daily_dna) <= TWEET_MAX_LENGTH:
        source = PURPLE + "Source: WordThink" + RESET
        print(PURPLE + source,
              YELLOW + "defined",
              BOLDWHITE + daily_dna + RESET, sep="\n")
        return daily_dna, source

    return -1


if __name__ == "__main__":
    get_tweet()
