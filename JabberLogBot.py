#!/usr/bin/python
# -*- coding: utf-8 -*-

from jabberbot import JabberBot, botcmd
from datetime import datetime
import os
import ConfigParser
import sys
import codecs
import time
import re
import urllib
import simplejson
from shutil import copy
from subprocess import Popen, PIPE, STDOUT
import twitter # from http://code.google.com/p/python-twitter/
import threading
# used for expanding short urls
import urllib2

import logging

mem_path = '/usr/share/screen/scripts/mem'
swap_path = '/usr/share/screen/scripts/swap'

configfile = 'jabberlogbot.conf'

maxofflinemessages = 1000
twittercheckinterval = 10.0

class JabberLogBot(JabberBot):

	def __init__(self):
		# Read config
		self.config = ConfigParser.RawConfigParser()
		self.config.read(configfile)
		
		jid = self.config.get('general','jid')
		password = self.config.get('general','password')
		debug = self.config.getboolean('general','debug')

		self.admins = self.config.get('general','admins').split(',')

		self.channels = self.config.get('general','channels').split(',')

		self.isLogging = self.config.getboolean('log','log')
		
		self.logFolder = self.config.get('log','folder')

		self.googleApiKey = self.config.get('general', 'googleapikey')

		# all the users that want to be notified if they got offline messages
		self.offlineUsers = self.config._sections['offlinemessages']
		
		# Spawn bot
		super( JabberLogBot, self).__init__(jid, password, debug=debug)
		# create console handler
		chandler = logging.StreamHandler()
		# create formatter
		formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
		# add formatter to handler
		chandler.setFormatter(formatter)
		# add handler to logger
		self.log.addHandler(chandler)
		# set level to INFO
		self.log.setLevel(logging.DEBUG)

		self.offlineMessages = []
		self.nickRegex = re.compile(r'(\S+):')
		self.stripHTMLTagsRegex = re.compile(r'<.*?>')

		#initialize twitter api
		consumer_key = self.config.get('twitter', 'consumer_key');
		consumer_secret = self.config.get('twitter', 'consumer_secret');
		access_token_key = self.config.get('twitter', 'access_token_key');
		access_token_secret = self.config.get('twitter', 'access_token_secret');
		self.twitter = twitter.Api(consumer_key=consumer_key, consumer_secret=consumer_secret,access_token_key=access_token_key, access_token_secret=access_token_secret);
		self.twitterChannels = self.config.get('twitter', 'channels').split(',');
		self.twitterTimer = threading.Timer(twittercheckinterval, self.twitterLoop);
		self.match_urls = re.compile(r"""((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|(([^\s()<>]+|(([^\s()<>]+)))*))+(?:(([^\s()<>]+|(([^\s()<>]+)))*)|[^\s`!()[]{};:'".,<>?«»“”‘’]))""", re.DOTALL);

	# Save parameters to config
	def save_config(self):
		# Join the channels to a string
		self.config.set('twitter', 'channels', ','.join(self.twitterChannels));
		self.config.set('general', 'channels', ','.join(self.channels))
		try:
			f = open(configfile,'wb')
			self.config.write(f)
			f.close()
		except:
			self.log.warning('Could not write configfile: '+configfile)

	# Every unknown command is a line we want to log
	def unknown_command(self, mess, cmd, args):
		self.logMessage(mess)
	
	def top_of_help_message(self):
		return "This is the skweez.net jabber bot.\nThis channel is logged so watch your mouth."

	def saveOfflineMessage(self, uniqueKey, messageTime, senderUsername, rawMessage):
		offlineMessage = '<b>'+messageTime.strftime('%H:%M')+' '+senderUsername+':</b> '+ rawMessage
		self.offlineMessages.append((uniqueKey, offlineMessage))
		if len(self.offlineMessages) >= maxofflinemessages:
			self.offlineMessages.remove(0);

	def logMessage(self, mess):
		if not self.isLogging:
			return
		
		channel = mess.getFrom().getStripped()

		if mess.getType() != 'groupchat':
			return

		if channel not in self.channels:
			return

		folder = '%s/%s/' % (self.logFolder, channel)
		file = '%s%s.log' % (folder, datetime.now().strftime('%Y-%m-%d'))
		if not os.path.exists(folder):
			try:
				os.mkdir(folder)
			except:
				self.log.warning('Can not create log folder: '+folder)
				broadcast('WARNING: Can not create log folder')
				return
			try:
				copy('index.php',folder)
			except:
				self.log.warning('Can not copy index.php to log folder')
				return
		messageTime = datetime.now()
		senderUsername = self.get_sender_username(mess)
		output = '<tr><td class="date">%s</td><td class="nick" id="%s">%s:</td> <td class="message">%s</td></tr>\n' % (messageTime.strftime('%H:%M'), senderUsername, senderUsername, mess.getBody())
		try:
			f = codecs.open(file, 'a', 'utf-8')
			f.write(output)
			f.close()
		except:
			self.log.warning('Can no write log file: '+file)
			broadcast('WARNING: Can not write log file')

		# We want to store messages for users that are not here right now
		rawMessage = self.stripHTMLTagsRegex.sub('', mess.getBody())
		nick = self.nickRegex.match(rawMessage)
		if nick is not None:
			nick = nick.group(1)
			uniqueKey = nick+' '+channel
			if uniqueKey in self.offlineUsers and channel+'/'+nick not in self._JabberBot__seen:
				self.log.debug('Got a offline message for %s: "%s %s: %s' % ( nick, messageTime.strftime('%H:%M'), senderUsername, rawMessage, ))
				self.saveOfflineMessage(uniqueKey, messageTime, senderUsername, rawMessage)

	def join( self):
		for c in self.channels:
			self.join_room(c)
		self.twitterTimer.start();

	def callback_presence(self, conn, presence):
		channel = presence.getFrom().getStripped()
		if channel in self.channels:
			if presence.getStatusCode() == '307':
				self.log.info('I was kicked from '+channel)
				self.channels.remove(channel)
				self.save_config()
			elif presence.getType() is None:
				jid = presence.getFrom()
				old_show, old_status = self._JabberBot__seen.get(jid, (self.OFFLINE, None))
				if old_show is self.OFFLINE:
					uniqueKey = jid.getResource()+' '+jid.getStripped()
					self.log.debug('User %s came online.'%uniqueKey)
					print self.offlineMessages
					message = 'Hey, %s. Someone left a message for you:' % jid.getResource()
					foundone = False
					entriesToDelete = []
					for (key, offlineMessage) in self.offlineMessages:
						print key+' '+offlineMessage
						if key == uniqueKey:
							foundone = True
							message = message + '<br />\n' + offlineMessage
							entriesToDelete.append((key, offlineMessage))
					if foundone == True:
						for item in entriesToDelete:
							self.offlineMessages.remove(item)
						entriesToDelete = []
						self.send(jid.getStripped(), message, None, 'groupchat')
		
		super(JabberLogBot, self).callback_presence(conn, presence)

	def callback_message(self, conn, mess):
		type = mess.getType()
		# If the message is a 'normal' maybe we were invited
		if type == 'normal':
			# Check for an invite tag
			mess_tag_x = mess.getTag('x')
			if mess_tag_x != None:
				invitation = mess_tag_x.getTag('invite')
				if invitation != None:
					in_channel = mess.getFrom().getStripped()
					in_from = invitation.getAttr('from').split('/')[0]
					# Check if an admin invited me
					if in_from in self.admins:
						self.log.info('I was invited to '+in_channel+' by '+in_from)
						
						self.channels.append(in_channel)
						self.save_config()
		
						self.join()

		super(JabberLogBot, self).callback_message(conn, mess)

	@botcmd(hidden=True)
        def _getin(self, mess, args):
		'''Make me join all channels I am invited'''
		self.join()

	def uptime(self):
		"""Display skweez.net's uptime"""
		try:
			f = open("/proc/uptime")
			contents = f.read().split()
			f.close()
		except:
			return "Cannot read uptime"

		total_seconds = float(contents[0])

		MINUTE = 60
		HOUR = MINUTE * 60
		DAY = HOUR * 24

		days    = int( total_seconds / DAY )
		hours   = int( ( total_seconds % DAY ) / HOUR )
		minutes = int( ( total_seconds % HOUR ) / MINUTE )
		seconds = int( total_seconds % MINUTE )

		string = ""
		if days> 0:
			string += str(days) + " " + (days == 1 and "day" or "days" ) + ", "
		if len(string)> 0 or hours> 0:
			string += str(hours) + " " + (hours == 1 and "hour" or "hours" ) + ", "
		if len(string)> 0 or minutes> 0:
			string += str(minutes) + " " + (minutes == 1 and "minute" or "minutes" ) + ", "
		string += str(seconds) + " " + (seconds == 1 and "second" or "seconds" )

		return string

	@botcmd
	def _serverinfo( self, mess, args):
		"""Displays information about the server"""
		self.logMessage(mess);

		version = open('/proc/version').read().strip()
		loadavg = open('/proc/loadavg').read().strip()

		try:
			p = Popen(mem_path , stdout=PIPE, stderr=PIPE)
			stdout, stderr = p.communicate()
			mem = stdout.rstrip('\n')
		except:
			mem = '%s not found' % mem_path

		try:
			p = Popen('/usr/share/screen/scripts/swap', stdout=PIPE, stderr=PIPE)
			stdout, stderr = p.communicate()
			swap = stdout.rstrip('\n')
		except:
			swap = '%s not found' % swap_path

		uptime = self.uptime()

		return '%s\n\nRAM: %s - SWAP: %s - LOAD: %s\nUPTIME: %s' % ( version, mem, swap, loadavg, uptime, )

	@botcmd
	def _fortune( self, mess, args):
		"""Returns a random quote"""

		self.logMessage(mess)

		cmd = ['/usr/games/fortune']
		cmd.extend(args.split())
		try:
			p = Popen(cmd, stdout=PIPE, stderr=STDOUT)
			stdout, stderr = p.communicate()
			stdout = str(stdout)
			try:
				stdout = stdout.decode('utf-8')
			except UnicodeError:
				self.log.warning('Decode with utf-8 did not work. Using latin_1')
				try:
					stdout = stdout.decode('latin_1')
				except UnicodeError:
					self.log.warning('Decode with latin_1 did not work. Using utf-8 and ignore errors')
					stdout = stdout.decode('utf-8', 'replace')
			stdout = stdout.encode('utf-8')
			self.log.info(stdout.rstrip('\n'))
			return stdout.rstrip('\n')
		except Exception, error:
			return 'An error occured: %s' % error
	
	# offline message handling
	@botcmd
	def _addofflinenick( self, mess, args):
		"""Saves offline messages for you that are send to the specified nick in a MUC while you are away. This is a per nick and per channel setting. You have to register your nick in every channel whereyou want to receive offline messages. You can register as many nicks as you like."""
		if mess.getType() != 'groupchat':
			return 'This feature is only available in group chats'
		if len(args) == 0:
			return 'Please supply a nick as argument'
		nick = args.split(' ')[0]
		user = mess.getFrom()
		channel = user.getStripped()
		uniqueKey = nick+' '+channel
		if uniqueKey in self.offlineUsers:
			return 'This nick is already in use.'
		else:
			self.offlineUsers[uniqueKey] = user
			self.config.set('offlinemessages', uniqueKey, user)
			self.save_config()
			self.log.info('Messages for %s will be stored for %s' % (nick, user, ))
			return 'Messages for %s will be stored for %s' % (nick, user, )

	@botcmd
	def _deleteofflinenick( self, mess, args):
		"""Deletes the specified nick from the offline message system. You will no longer receive offline messages in this channel"""
		if mess.getType() != 'groupchat':
			return 'This feature is only available in group chats'
		if len(args) == 0:
			return 'Please supply a nick as argument'
		nick = args.split(' ')[0]
		user = mess.getFrom()
		channel = user.getStripped()
		uniqueKey = nick+' '+channel
		if uniqueKey in self.offlineUsers:
			if self.offlineUsers[uniqueKey] == user:
				del self.offlineUsers[uniqueKey]
				self.config.remove_option('offlinemessages', uniqueKey)
				self.save_config()
				self.log.info('Deleted %s from the offline message system' % nick)
				return 'Deleted %s from the offline message system' % nick
		else:
			return 'Nick %s not found' % nick

	@botcmd
	def google( self, mess, args ):
		"""Returns the first google result for your query"""
		self.logMessage(mess)
		query = urllib.urlencode({'key' : self.googleApiKey, 'q' : args.encode('utf-8')})
		url = 'https://www.googleapis.com/customsearch/v1?cx=004970785222078633189:xanzqd-yq7w&googlehost=google.de&num=1&%s' % (query)
		search_results = urllib.urlopen(url)
		if search_results.getcode() is not 200:
			return "Sorry, an error occurred. Status code was: %s" % str(search_results.getcode())
		json = simplejson.loads(search_results.read())
		try:
			results = json['items']
		except:
			return "Sorry, nothing found."
		if len(results) == 0:
			return "Sorry, nothing found."
		return results[0]['link']

	@botcmd(hidden=True)
	def g ( self, mess, args ):
		return self.google(mess, args)

	def expandLinksInText(self, text):
		return self.match_urls.sub(lambda x: urllib2.urlopen(x.group()).url, text);
		

	def getLatestTweets( self ):
		latestTweetID = self.config.get('twitter', 'latestTweetID');

		tweets = self.twitter.GetFriendsTimeline(retweets=True, since_id=latestTweetID, count=10);
		if tweets:
			latestTweet = next(iter(tweets), None);
			if latestTweet:
				self.config.set('twitter','latestTweetID', latestTweet.id);
				self.save_config();
		return tweets;

	def twitterLoop(self):
		self.log.debug('Looking for new tweets');
		if len(self.twitterChannels) == 0:
			return;
		tweets = self.getLatestTweets();
		if len(tweets) == 0:
			return;
		for channel in self.twitterChannels:
			if channel == '':
				continue;
			self.log.info('Sending tweets to channel '+channel);
			message = 'New tweets:\n';
			for tweet in tweets:
				message += tweet.user.screen_name + ': ' + self.expandLinksInText(tweet.text) + '\n';
			self.send(channel, message, None, 'groupchat')
		#look for new tweets every 5 minutes
		self.twitterTimer = threading.Timer(twittercheckinterval, self.twitterLoop);
		self.twitterTimer.start();

	@botcmd
	def _enabletwitter(self, mess, args):
		"""Display twitter messages in this channel"""
		if mess.getType() != 'groupchat':
			return 'This command is only avaliable in group chats';
		channel = mess.getFrom().getStripped();
		if not channel in self.twitterChannels:
			self.twitterChannels.append(channel);
			self.save_config();
			self.log.info('Enabled twitter for channel '+channel);
			return 'Enabled Twitter in channel '+channel;
		else:
			return 'Twitter is already enabled for '+channel;
	
	@botcmd
	def _disabletwitter(self, mess, agrs):
		"""Stop displaying twitter messages in this channel"""
		if mess.getType() != 'groupchat':
			return 'This command is only avaliable in group chats';
		channel = mess.getFrom().getStripped();
		if channel in self.twitterChannels:
			self.twitterChannels.remove(channel);
			self.save_config();
			self.log.info('Disabled twitter for channel '+channel);
			return 'Disabled Twitter in channel '+channel;
		else:
			return 'Twitter is not enabled for '+channel;

	def shutdown(self):
		self.twitterTimer.cancel();

bot = JabberLogBot()

bot.serve_forever( connect_callback = bot.join() )
