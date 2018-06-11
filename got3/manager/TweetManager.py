import urllib.request, urllib.parse, urllib.error, urllib.request, urllib.error, urllib.parse, json, re, datetime, sys, \
    http.cookiejar
from .. import models
from pyquery import PyQuery
from lxml import html
import requests
from bs4 import BeautifulSoup
from termcolor import colored

class TweetManager:
    def __init__(self):
        pass

    @staticmethod
    def getTweets(tweetCriteria, receiveBuffer=None, bufferLength=100):
        refreshCursor = ''

        results = []
        resultsAux = []
        cookieJar = http.cookiejar.CookieJar()

        active = True

        while active:
            json = TweetManager.getJsonReponse(tweetCriteria, refreshCursor, cookieJar)
            if len(json['items_html'].strip()) == 0:
                break

            refreshCursor = json['min_position']
            tweets = PyQuery(json['items_html'])('div.js-stream-tweet')

            if len(tweets) == 0:
                break

            for tweetHTML in tweets:
                try:
                    tweetPQ = PyQuery(tweetHTML)
                    tweet = models.Tweet()

                    usernameTweet = tweetPQ("b").html();

                    txt = re.sub(r"\s+", " ", tweetPQ("p.js-tweet-text").text().replace('# ', '#').replace('@ ', '@'));

                    print(colored("@","red") + colored(usernameTweet,"red")+colored(": ","red")+txt+"\n")
                    retweets = int(tweetPQ("span.ProfileTweet-action--retweet span.ProfileTweet-actionCount").attr(
                        "data-tweet-stat-count").replace(",", ""));
                    favorites = int(tweetPQ("span.ProfileTweet-action--favorite span.ProfileTweet-actionCount").attr(
                        "data-tweet-stat-count").replace(",", ""));
                    dateSec = int(tweetPQ("small.time span.js-short-timestamp").attr("data-time"));
                    id = tweetPQ.attr("data-tweet-id");
                    permalink = tweetPQ.attr("data-permalink-path");
                    user_id = int(tweetPQ("a.js-user-profile-link").attr("data-user-id"))

                    page = requests.get('https://twitter.com/tubiity/status/'+id)
                    script_geo =html.fromstring(page.content)
                    location = script_geo.xpath('//a[@class="u-textUserColor js-nav js-geo-pivot-link"]/text()')
                    sp_location = ','.join(location)
                    geo = ''

                    geoSpan = tweetPQ('span.Tweet-geo')
                    if len(geoSpan) > 0:
                        geo = geoSpan.attr('title')
                    urls = []

                    #userInformation

                    result = requests.get("https://twitter.com/"+usernameTweet)
                    c = result.content

                    soup = BeautifulSoup(c, "html.parser")
                    liste = []
                    samples = soup.find_all("a",
                                            "ProfileNav-stat ProfileNav-stat--link u-borderUserColor u-textCenter js-tooltip js-openSignupDialog js-nonNavigable u-textUserColor")
                    #Follower, Follow and number of likes in list
                    for a in samples:
                        liste.append(a.attrs['title'])

                    for link in tweetPQ("a"):
                        try:
                            urls.append((link.attrib["data-expanded-url"]))
                        except KeyError:
                            pass
                    tweet.id = id
                    tweet.permalink = 'https://twitter.com' + permalink
                    tweet.username = usernameTweet
                    tweet.user_id = user_id
                    tweet.text = txt
                    tweet.date = datetime.datetime.fromtimestamp(dateSec)+datetime.timedelta(hours=2)
                    tweet.formatted_date = datetime.datetime.fromtimestamp(dateSec).strftime("%a %b %d %X +0000 %Y")
                    tweet.retweets = retweets
                    tweet.favorites = favorites
                    tweet.mentions = " ".join(re.compile('(@\\w*)').findall(tweet.text))
                    tweet.hashtags = " ".join(re.compile('(#\\w*)').findall(tweet.text))
                    tweet.geo = sp_location
                    tweet.urls = ",".join(urls)
                    tweet.author_id = user_id

                    results.append(tweet)
                    resultsAux.append(tweet)

                    if receiveBuffer and len(resultsAux) >= bufferLength:
                        receiveBuffer(resultsAux)
                        resultsAux = []

                    if tweetCriteria.maxTweets > 0 and len(results) >= tweetCriteria.maxTweets:
                        active = False
                        break
                except:
                    receiveBuffer(resultsAux)
                    return

        if receiveBuffer and len(resultsAux) > 0:
            receiveBuffer(resultsAux)

        return results

    @staticmethod
    def getJsonReponse(tweetCriteria, refreshCursor, cookieJar):
        url = "https://twitter.com/i/search/timeline?f=realtime&q=%s&src=typd&%smax_position=%s"
        #url = "https://twitter.com/search?l?&q=%s "

        urlGetData = ''
        if hasattr(tweetCriteria, 'username'):
            urlGetData += ' from:' + tweetCriteria.username



        if hasattr(tweetCriteria, 'querySearch'):
            urlGetData += ' '+ tweetCriteria.querySearch
        if hasattr(tweetCriteria, 'since'):
            urlGetData += ' since:' + tweetCriteria.since

        if hasattr(tweetCriteria, 'until'):
            urlGetData += ' until:' + tweetCriteria.until
        if hasattr(tweetCriteria, 'lang'):
            urlLang = 'lang=' + tweetCriteria.lang + '&'
        else:
            urlLang = ''
        url = url % (urllib.parse.quote(urlGetData), urlLang, refreshCursor)

        headers = [
            ('Host', "twitter.com"),
            ('User-Agent', "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"),
            ('Accept', "application/json, text/javascript, */*; q=0.01"),
            ('Accept-Language', "de,en-US;q=0.7,en;q=0.3"),
            ('X-Requested-With', "XMLHttpRequest"),
            ('Referer', url),
            ('Connection', "keep-alive")
        ]

        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookieJar))
        opener.addheaders = headers

        try:
            response = opener.open(url)
            jsonResponse = response.read()
        except:
            # print("Twitter weird response. Try to see on browser: ", url)
            print(
                "Twitter weird response. Try to see on browser: https://twitter.com/search?q=%s&src=typd" % urllib.parse.quote(
                    urlGetData))
            print("Unexpected error:", sys.exc_info()[0])
            sys.exit()
            return

        dataJson = json.loads(jsonResponse.decode())

        return dataJson