import tweepy
import io
from keys import key
from subprocess import call, check_output
import random
from responses import response

# Will tweet in response to people who tweet/retweet #genetics
# if anyone responds to generated tweet, will convert their DNA back into words

consumer_key = key['consumer_key']
consumer_secret = key['consumer_secret']
access_token = key['access_token']
access_token_secret = key['access_token_secret']

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

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
               
clearTweets()
api.update_status(status=(doubleStrandedDNA("Hello, World!")))
 
for tweet in tweepy.Cursor(api.search,q='#genetics').items(10):
        username = tweet.user.screen_name
        with open("tweetedNames.txt") as prevTweeted:
            usedNames = prevTweeted.readlines()
        if( (username + "\n") not in usedNames):
            user_DNA = wordsToDNA(username)
            reverse_DNA = dnaToWords(user_DNA)
            if(user_DNA == ""): # if username can't be translated
                print("ERROR: could not translate", username)
                continue
            with open("tweetedNames.txt", "ab") as usedNames:
                usedNames.write(username + "\n")
            tweetResponse = formulateResponse(username, user_DNA)
            api.update_status(tweetResponse, in_reply_to_status_id=tweet.id).in_reply_to_user_id
            print(username)
          
         
         
         
         
        
        
        
        
        
        