import tweepy
import io
from keys import key
from subprocess import call, check_output
import random
from responses import response
from time import sleep
import json

# Will tweet in response to people who tweet/retweet #genetics
# if anyone responds to generated tweet, will convert their DNA back into words

consumer_key = key['consumer_key']
consumer_secret = key['consumer_secret']
access_token = key['access_token']
access_token_secret = key['access_token_secret']

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

class StdOutListener(tweepy.StreamListener):
    def on_data(self, data):
        # Twitter returns data in JSON format - we need to decode it first
        decoded = json.loads(data)

        # Also, we convert UTF-8 to ASCII ignoring all bad characters sent by users
        print '@%s: %s' % (decoded['user']['screen_name'], decoded['text'].encode('ascii', 'ignore'))
        print ''
        return True

    def on_error(self, status):
        print status

def wordsToDNA(string):
    return check_output(["Rscript wordsToDNA.r "  + string], shell=True)

def dnaToWords(string):
    return check_output(["Rscript dnaToWords.r "  + string], shell=True)

def doubleStrandedDNA(string):
    return (check_output(["Rscript doubleStrandedDNA.r "  + string], shell=True)
        + "\n(" + string + ")")

def formulateResponse(username, user_DNA, specific = "random"):
    if(specific != "random"):
        return response[specific].format(handle=username, DNA = user_DNA)
    base_response = random.choice(response)
    return base_response.format(handle=username, DNA = user_DNA)

def clearTweets():
    for status in tweepy.Cursor(api.user_timeline).items():
           try:
            api.destroy_status(status.id)
           except:
               print "Failed to delete:", status.id
               
def filterAndTweet(tweet):
    username = tweet.user.screen_name
    with open("tweetedNames.txt") as prevTweeted:
        usedNames = prevTweeted.readlines()
    if( (username + "\n") not in usedNames and not tweet.retweeted):
        user_DNA = wordsToDNA(username)
        reverse_DNA = dnaToWords(user_DNA)
        if(user_DNA == ""): # if username can't be translated
            print("ERROR: could not translate", username)
            return
        with open("tweetedNames.txt", "ab") as usedNames:
            usedNames.write(username + "\n")
        tweetResponse = formulateResponse(username, user_DNA)
        try:
            api.update_status(tweetResponse, in_reply_to_status_id=tweet.id).in_reply_to_user_id
        except:
            print(tweetResponse)
            return
        print(username)
# api.update_status(status=(doubleStrandedDNA("Hello, World!")))
def main():
    for tweet in tweepy.Cursor(api.search,q='#genetics').items(20):
        filterAndTweet(tweet) 
    for tweet in tweepy.Cursor(api.search,q='#DNA').items(20):
        filterAndTweet(tweet)
                
    
if __name__ == '__main__': 
    while(1): # run every 15 minutes
        main()  
        sleep(900)
        # nohup python theDNABot.py &
        # tail -f nohup.out 
          
         
         
         
         
        
        
        
        
        
        