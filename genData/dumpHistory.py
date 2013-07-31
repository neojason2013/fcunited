from basedata import *
import urllib
import os, codecs
import re, json
import time

def removeTag(text):
    p = re.compile(r"<([\s\S]*?)>")
    text = p.sub("",text)
    return text

def getVenue(text):
    text = removeTag(text).split(',')[0]
    return text

def getOpponent(text):
    text = removeTag(text)
    text = "<abbr title='%s'>%s</abbr>" % (dicOpponent[text], text)
    return text

def getResult(text):
    s = text[-1:]
    (u,v) = text[:-1].split("-")
    (u,v) = (u,v) if u > v else (v,u)
    if s == "L":
        result = "%s-%s" % (v,u)
    else:
        result = "%s-%s" % (u,v)
    return result

def getAtt(text):
    text = text.replace(",","")
    if text.isdigit():
        return int(text)
    else:
        return null
    
def readHtml(filename, url):
    if os.path.exists(filename):
        fr = open(filename)
        rawdata = fr.read()
        fr.close()
    else:
        rawdata = urllib.urlopen(url).read() 
        fw = open(filename,'w')
        fw.write(rawdata)
        fw.close()
    return rawdata

def getGoal(text):
    json = []
    text = text.replace("<br>","<br />")
    goals = text.split("<br />")
    for goal in goals:
        if goal == "": break

        goal = goal.replace(",","")
        tokens =goal.split("&nbsp;") 
        
        for i in range(1,len(tokens)):
            if tokens[i].isdigit():
                g = {}
                g["player"] = tokens[0]
                g["time"] = int(tokens[i])
                json.append(g)
            else:
                json[-1]["memo"] = tokens[i]

    return json

def getPlayer(text):
    # 892 capt + sub/yellow
    # 826 yellow -> red
    json = []
    text = text.replace("\r","")
    text = text.replace("\n","")
    text = text.replace("<br />","<br>")
    text = text.replace("&nbsp;"," ")
    players = text.split("<br>")

    for player in players:
        (n,p,m) = re.findall(r"(^[0-9]*)([\s\S]*?)([<(][\s\S]*)?$", player.strip())[0]
        if n == '': continue
        token = {}
        token["no"] = n
        token["player"] = p.strip()
        if len(re.findall(r"capt", m)) > 0:
            token["captain"] = 0
        if len(re.findall(r"yellow.JPG", m)) > 0:
            token["yellow"] = 0
        if len(re.findall(r"red.JPG", m)) > 0:
            token["red"] = 0
        
        sub = re.findall(r"\(for ([0-9]+?), ([0-9]?[0-9]?)[\s\S]*$", m)
        if len(sub) > 0: 
            (suboff, subtime) = sub[0]
            token["subon"] = int(subtime)
            
            for d in json:
                if d["no"] == suboff:
                    d["suboff"] = int(subtime)
                    break
        json.append(token)
            
            
        
        
        token["memo"] = m
        
    #text = text
    return json

def getDetail(text):
    text = re.findall(r"Match Details([\s\S]*?)Match Report", text)[0]
    rows = text.split("<hr>")
    
    json = {}
    # date, competition, venue
    firstRow = re.findall(r"<font size=\"\+1\">([\s\S]*?)</font>", rows[0])
    json["date"] = firstRow[0]
    json["comp"] = firstRow[1]
    json["venue"] = firstRow[2]
    
    # hometeam, score, awayteam, goals, att
    secondRow = re.findall(r"<span class=\"mediumtitle\">([\s\S]*?)</span>", rows[1])
    
    goals = re.findall(r"<span class=\"text\">([\s\S]*?)</span>", rows[1])
    json["homegoal"] = getGoal(goals[0])
    json["awaygoal"] = getGoal(goals[1])

    json["hometeam"] = secondRow[0]
    json["score"] = secondRow[1]
    json["awayteam"] = secondRow[2]
    json["att"] = re.findall(r"Attendance: ([\s\S]*?)</span>", rows[1])[0]
    
    # teamsheet
    thirdRow = re.findall(r"<span class=\"mediumtitle\">([\s\S]*?)</span>", rows[2])
    #print rows[2]
    sheets = re.findall(r"</font><br>([\s\S]*?)</td>", rows[2])
    json["homeplayer"] = getPlayer(sheets[0])
    json["awayplayer"] = getPlayer(sheets[1])
    
    # fourthRow contains report
    
    return json

def dumpSeason(season, team=1):
    filename = "./data/%s_%s.txt" % (season, team)
    url = "http://www.fc-utd.co.uk/m_fixtures.php?year=%s&team=%s" % (season, team)
    rawdata = readHtml(filename, url) 
    
    jsondata = []
    leagueTeam = []    
    
    tables = re.findall(r"<table width=\"100%\" border=\"0\" bordercolor=\"#CCCCCC\">([\s\S]*?)</table>", rawdata)
    tables = re.findall(r"<tbody>([\s\S]*?)</tbody>", tables[0])
    games = re.findall(r"<tr>([\s\S]*?)</tr>", tables[0])
    for game in games:
        dict = {}
        cells = re.findall(r"<td.*?>(.*?)</td>", game)
        dict["comp"] = dictComp[cells[0]]
        dict["weekday"] = dictWeekday[cells[1]]
        dict["date"] = cells[2][6:]+"."+cells[2][3:5]+"."+cells[2][0:2]
        dict["time"] = cells[3]
        dict["opponent"] = getOpponent(cells[4])
        dict["venue"] = getVenue(cells[5])
        dict["hoa"] = dicHoa[cells[6]]
        try:
            dict["report"] = re.findall(r"<a href=\"([\s\S]*?)\">", cells[7])[0]
        except:
            pass
        try:
            dict["result"] = getResult(re.findall(r"<strong>([\s\S]*?)</strong>", cells[7])[0])
        except:
            pass
        # 2013.07.25 data source have bug , lost </td> in cells[7], so that att is in cells[7] either
        try:
            dict["att"] = getAtt(re.findall(r"<td align=\"left\"> ([\s\S]*?)$", cells[7])[0])
        except:
            pass
        
        try:
            reportfile = "./data/report/%s_%s.txt" % (season, dict["report"].split("=")[1])
        except:
            reportfile = "" 
        
        if "report" in dict.keys():    
            url = "http://www.fc-utd.co.uk/" + dict["report"]
            reportdata = readHtml(reportfile, url)
            detail =  getDetail(reportdata)
            print detail
            return
                    
        jsondata.append(dict)
        
    print jsondata[39]
    print reportdata
    return
        
    uptime =  time.strftime('%Y-%m-%d',time.localtime(time.time()))
    output = {"modified":uptime,"rawdata":jsondata}
    
    fw = codecs.open("./data/%s_%s.html" % (season, team),"w","utf-8")
    text = json.dumps(output, encoding='utf-8', ensure_ascii=False)
    
    fw.write(text)
    fw.close()

dumpSeason(2013)
