#!/usr/bin/python
# Program for BAIR/AI4ALL Camp Slack bot @bairbot
# Teela Huff, thuff@berkeley.edu, Summer 2017
# last updated 07/28/2017

from datetime import datetime, timedelta
from time import sleep, time
from slackclient import SlackClient
from unicodedata import normalize
import pygsheets
import string

BOT_NAME = 'bairbot'

# bot token taken from slack api 
# TODO token goes here
SLACK_BOT_TOKEN = ''

sc = SlackClient(SLACK_BOT_TOKEN)

# getting uid 
if __name__ == "__main__":
    api_call = sc.api_call("users.list")
    if api_call.get('ok'):
        # retrieve all users so we can find our bot
        users = api_call.get('members')
        for user in users:
            if 'name' in user and user.get('name') == BOT_NAME:
                print("Bot ID for '" + user['name'] + "' is " + user.get('id'))
                BOT_ID = user.get('id')
    else:
        print("ERROR could not find bot user with the name " + BOT_NAME)

# bot id
print BOT_ID

def eventdict():
    # TODO {"Name":"UID"} but with members other than myself
    uids = {"Teela":"U6FSQUJSK","Teela":"U6FSQUJSK","Teela":"U6FSQUJSK","Teela":"U6FSQUJSK"}

    print "...reading spreadsheet"
    gc = pygsheets.authorize()
    # TODO spreadsheet url goes here
    sh = gc.open_by_url('')
    wks = sh.sheet1

    print "...preparing column letters"
    # column letters A:S
    letters = list(string.uppercase[:19])
    lettercolumns = {}
    for letter in letters:
        lettercolumns[letter] = wks.range(letter+'1:'+letter+'98')

    print "...getting list of times and volunteers"
    studentletters = ["B", "C", "K", "L"]
    timecolumn = []
    volunteers = {}
    for letter in letters[0:19]:
        if letter not in studentletters:
            columnlist = []
            column = (lettercolumns[letter])
            for i in range(len(column)):
                if "u'" in str(column[i]):
                    tmp = (str(column[i]).split("u'")[1]) 
                    tmp = (str(tmp).split("'>")[0])
                    columnlist.append(tmp)
                else:
                    columnlist.append('')
            if letter == "A":
                timecolumn = columnlist
            volunteers[letter] = columnlist


    print "...getting event times"
    timeval = ""
    for j in range(1,len(timecolumn)):
        current = timecolumn[j]
        if ":" in current:
            timeval = current
        else:
            timecolumn[j] = timeval

    addtimes = {}
    header = ""
    for letter in letters:
        if letter not in studentletters:
            tmpdict = {}
            for i in range(len(volunteers[letter])):
                event = (volunteers[letter])[i]
                if event:
                    time = timecolumn[i]
                    if ":" not in time:
                            header = event
                    else:
                        tmpdict[time] = event
            if header != "":
                print "processing column...",header
                addtimes[header] = tmpdict

    print "...final list of person,uid,timestamp,task tuples"
    am = ["8:","9:","10:","11:"]
    events = []
    for titlekey in addtimes.keys():
        usertimes = (addtimes[titlekey]).keys()
        for k in range(len(usertimes)):
            timestamp = usertimes[k]
            task = addtimes[titlekey][timestamp]
            person = titlekey.split(" - ")[1]

            if "saturday" in titlekey.lower():
                timestamp = "07/29/2017 " + timestamp
            else:
                timestamp = "07/30/2017 " + timestamp
            if any(substring in timestamp for substring in am):
                timestamp = timestamp + "AM"
            else:
                timestamp = timestamp + "PM"

            timestamp = str(timestamp)
            timestamp = datetime.strptime(timestamp, "%m/%d/%Y %I:%M%p")

            if person in uids.keys():
                uid = uids[person]
            events.append((person,uid,timestamp,task))

    print "...making dictionary of time:(event,event,etc.)"
    timetask = {}
    for usertask in events:
        if usertask[2] not in timetask:
            timetask[usertask[2]] = ((usertask[0],usertask[1],usertask[3]),)
        else:
            timetask[usertask[2]] = timetask[usertask[2]] + ((usertask[0],usertask[1],usertask[3]),)
    
    return timetask

schedule = eventdict()

print "@bairbot connecting to Slack..."
print "..."

# connection stuff
if sc.rtm_connect():
    print "@bairbot connected and listening to Slack!"
    while True:
        try:
            # five minute warnings
            now = datetime.now()
            sleep(3)
            new_evts = sc.rtm_read()
            for tasktime in schedule.keys():
                fiveminwarning = tasktime - timedelta(minutes = 5)
                if fiveminwarning < now:
                    for taskmoment in schedule[tasktime]:
                        hourtask = int(str(tasktime.hour))
                        if hourtask > 12:
                            hourtask = hourtask - 12
                        hourtask = str(hourtask)
                        text = (":bear: `5 MINUTE WARNING FOR " + (str(taskmoment[0])).upper() + ": "+
                                hourtask + ":" + str(tasktime.minute) + " - " +str(taskmoment[2])+"` :bear:")
                        print text
                        sc.api_call("chat.postMessage", as_user="true:", channel=str(taskmoment[1]), text=text)
                    schedule.pop(tasktime, None)

            response_flag = False
            for evt in new_evts:
                if "type" in evt:
                    if evt["type"] == "message" and "text" in evt:    
                        command = evt["text"]
                        # get user id of command
                        try:
                            user = str(evt).split("user': u'")[1].split("', u'")[0]
                        except IndexError:
                            continue
                        # get channel of command
                        #print evt
                        channel = str(evt).split("channel': u'")[1].split("'")[0]
                        if (BOT_ID in command) and (user != str(BOT_ID)):
                            command = normalize('NFKD', command).encode('ascii','ignore')

                            print "Parsing command...", str(command)

                            if "updateschedule" in command:
                                text = "<@"+ user + ">, updating event schedule based on spreadsheet..."
                                sc.api_call("chat.postMessage", as_user="true:", channel=channel, text= text)
                                response_flag = True
                                schedule = eventdict()
                                text = "<@"+ user + ">, event schedule updated!"
                                sc.api_call("chat.postMessage", as_user="true:", channel=channel, text= text)
                                response_flag == True

                            elif response_flag == False:
                                text = ("Hello <@"+ user + "> :wave:\n"+
                                       "I hope you're having a :bear:-y nice day!")
                                sc.api_call("chat.postMessage", as_user="true:", channel=channel, text= text)

        except Exception as e:
            print e
            continue
