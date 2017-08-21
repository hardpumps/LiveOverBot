from twisted.internet import defer, endpoints, protocol, reactor, task, ssl
from twisted.words.protocols import irc
from twisted.python import log
import random
import json
import sys
import re
import os
import time
import requests

class IRCBotProtocol(irc.IRCClient):
    nickname = 'LiveOverBot'
    optkey = "~"
    magasin=6
    msg_stack=[]
    logo=unicode(u'\u25CF').encode('utf-8')
    last_vid_file=".lo_last_vid"

    def signedOn(self):
        for channel in self.factory.channels:
            self.join(channel)
            time.sleep(1)
            l=task.LoopingCall(self.check_new_lo_vid, channel)
            l.start(300)

    # Called when a PRIVMSG is received.
    def privmsg(self, user, channel, message):
        nick, _, host = user.partition('!')
        message = message.strip()
        if len(self.msg_stack) > 1000:
            self.msg_stack = self.msg_stack[500:]
        if message[:2] == 's/':
            self.doregex(nick, channel, message)
        elif message[:2].lower() == "hi":
            self.msg(channel, "hi!")
        elif message[0] == self.optkey:
            self.handle_cmd(nick, channel, message)

        if message.find("http://")!=-1 or message.find("https://")!=-1 or message.find("www.")!=-1:
            self.handle_url(channel, message)
        self.msg_stack.append("<"+nick+"> "+message)
        return

    def handle_cmd(self, user, channel, message):
        cmd=message[1:]
        if cmd.find(' ')!=-1:
            argv=cmd.split(' ')
        else:
            argv = [cmd]
        if argv[0] == "rand":
            self.msg(channel, "\x035%s\x030%s: \x034%s" % (self.logo, user, self.dorand(argv)))
        elif argv[0] == "roulette":
            if self.doroulette():
                self.msg(channel, "\x035%s\x030%s: \x034BOOM! \x033You're dead." % (self.logo, user))
                self.magasin=6
            else:
                self.magasin-=1
                self.msg(channel, "\x035%s\x030%s: \x035*click* \x033(%d shots left)" % (self.logo, user, self.magasin))
    
    def check_new_lo_vid(self, channel):
        channelId="UClcE-kVhqyiHCcjYwcpfj9w"
        apiKey="Get one"
        ret = requests.get("https://www.googleapis.com/youtube/v3/search?order=date&part=snippet&channelId=%s&key=%s" % (channelId, apiKey) )
        json_data = json.loads(ret.text)
        last_vid = str(json_data['items'][0]['id']['videoId'])

        if not os.path.exists(".lo_last_vid"):
            with open(self.last_vid_file, "w") as f:
                f.write(last_vid)
                self.msg(channel, "\x035%s\x030LiveOverflow new video! - \x033https://youtube.com/watch?v=%s" % (self.logo, last_vid))
                self.handle_url(channel, "https://youtube.com/watch?v=%s" % last_vid)
                return
        with open(self.last_vid_file, "r") as f:
            saved_last_vid = f.read().strip()
        if saved_last_vid == last_vid:
            return
        else:
            with open(self.last_vid_file, "w") as f:
                f.write(last_vid)
            self.msg(channel, "\x035%s\x030LiveOverflow new video! - \x033https://youtube.com/watch?v=%s" % (self.logo, last_vid))
            self.handle_url(channel, "https://youtube.com/watch?v=%s" % last_vid)
            return

    def doregex(self, user, channel, message):
        message = message.split()[0]
        if message[len(message)-1] != '/':
            message += '/'
        message = self.sectxt(message)
        (search, replace) = message.split('/')[1:3]
        for i in range(len(self.msg_stack)-1, 0, -1):
            if re.search(search, self.msg_stack[i]):
                replaced = re.sub(search, replace, self.msg_stack[i])
                self.msg(channel, "\x037"+user+": \x033" + replaced)
                break

    def handle_url(self, channel, message):
        try:
            url=message[message.index('http'):]
            if url.find(' ') != -1:
                url=url[:url.index(' ')]
        except:
            url=message[message.index('www.'):]
            if url.find(' ') != -1:
                url=url[:url.index(' ')]


        r = requests.get(url.strip())
        if r.status_code != 200:
            return

        try:
            c_type=r.headers["content-type"]
        except:
            c_type=""
            pass
        try:
            c_length=r.headers["content-length"]
        except:
            c_length=0
            pass
         

        try:
                title=r.content[r.content.find("<title>"):]
                title=title[:title.find("</title>")]
                title=title.replace("<title>","")
        except:
                title=""
        
        title = self.sectxt(title)
        if c_type != "" and c_length != 0:
            self.msg(channel, "\x035%s\x030Title: %s \x033 > %s | %s Bytes" % (self.logo, title, c_type, c_length))
        elif c_type != "" and c_length == 0:
            self.msg(channel, "\x035%s\x030Title: %s \x033 > %s" % (self.logo, title, c_type))
        else:
            self.msg(channel, "\x035%s\x030Title: %s" % (self.logo, title))

    
    def sectxt(self,txt):
        while txt.find('\n')!=-1:
            txt=txt.replace("\n", "")
        while txt.find('\r')!=-1:
            txt=txt.replace("\r","")
        return txt

    def dorand(self, argv):
        if len(argv) == 1:
            return str(random.randint(0,100))
        elif len(argv) == 2:
            return str(random.randint(0, int(argv[1])))

    def doroulette(self):
        return ((100 /self.magasin) > random.randint(0,100))


class IRCBotFactory(protocol.ReconnectingClientFactory):
    protocol = IRCBotProtocol
    channels = ["#liveoverflow"]


if __name__ == '__main__':
    hostname = "irc.freenode.net"
    port = 6697 #port

    log.startLogging(sys.stderr)

    factory = IRCBotFactory()
    reactor.connectSSL(hostname, port, factory, ssl.ClientContextFactory())
    reactor.run()
