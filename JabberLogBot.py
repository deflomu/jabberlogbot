#!/usr/bin/python
# -*- coding: utf-8 -*-

from jabberbot import JabberBot, botcmd
from datetime import datetime
import os
import ConfigParser
import sys
import codecs
import time
from shutil import copy
from subprocess import Popen, PIPE, STDOUT

#import wikipedia

mem_path = '/usr/share/screen/scripts/mem'
swap_path = '/usr/share/screen/scripts/swap'

configfile = 'jabberlogbot.conf'

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

		self.logging = self.config.getboolean('log','log')
		
		self.logFolder = self.config.get('log','folder')

		# Spawn bot
		super( JabberLogBot, self).__init__(jid, password, debug=debug)

	# Save parameters to config
	def save_config(self):
		# Join the channels to a string
		channels = ','.join(self.channels)
		self.config.set('general','channels',channels)
		try:
			f = open(configfile,'wb')
			self.config.write(f)
			f.close()
		except:
			self.log.warning('Could not write configfile: '+configfile)

	# Every unknown command is a line we want to log
	def unknown_command(self, mess, cmd, args):
		self.logger(mess)
	
	def top_of_help_message(self):
		return "This is the skweez.net jabber bot.\nThis channel is logged so watch your mouth."

	def logger(self, mess):
		if not self.logging:
			return
		
		channel = mess.getFrom().getStripped()
		folder = '%s/%s/' % (self.logFolder, channel)
		file = '%s%s.log' % (folder, datetime.now().strftime('%Y-%m-%d'))
		output = '<tr><td class="date">%s</td><td class="nick" id="%s">%s:</td> <td class="message">%s</td></tr>\n' % (datetime.now().strftime('%H:%M'), self.get_sender_username(mess), self.get_sender_username(mess), mess.getBody())

		if mess.getType() != 'groupchat':
			return

		if channel not in self.channels:
			return


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
			
		try:
			f = codecs.open(file, 'a', 'utf-8')
			f.write(output)
			f.close()
		except:
			self.log.warning('Can no write log file: '+file)
			broadcast('WARNING: Can not write log file')

	def join( self):
		for c in self.channels:
			self.join_room(c)

	def callback_presence(self, conn, presence):
		channel = presence.getFrom().getStripped()
		if channel in self.channels:
			if presence.getStatusCode() == '307':
				self.log.info('I was kicked from '+channel)

				self.channels.remove(channel)
				self.save_config()
			
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
		self.logger(mess);

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

		self.logger(mess)

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
	
	#@botcmd(hidden=True)
	#def _wiki( self, mess, args):
	#	"""Return the wikipedia site to arg"""
	#	site = wikipedia.getSite() # Taking the default site
	#	page = wikipedia.Page(site, args)
	#	wikipedia.stopme()
	#	return page.get()

bot = JabberLogBot()

bot.serve_forever( connect_callback = bot.join() )
#wikipedia.stopme()
