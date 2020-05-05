import os
import re
import sys
import configparser
import threading
import queue
from datetime import datetime

from pytz import timezone

import dateparser
from tweepy import StreamListener, Stream, OAuthHandler, API

import ReminderBot


class Bot:
	def __init__(self):
		self.logger = Logger()
		self.logger.log('Logging in...')
		self.config_parser = configparser.ConfigParser()
		self.config_parser.read(os.path.join(sys.path[0], 'config.ini'))
		self.api_key = self.config_parser.get('Keys', 'api_key')
		self.api_secret_key = self.config_parser.get('Keys', 'api_secret_key')
		self.access_token = self.config_parser.get('Keys', 'access_token')
		self.access_token_secret = self.config_parser.get('Keys', 'access_token_secret')
		self.user_to_follow = self.config_parser.get('UserInfo', 'user_to_follow')
		self.tracked_word = ['@samiambot']
		self.auth = OAuthHandler(self.api_key, self.api_secret_key)
		self.auth.set_access_token(self.access_token, self.access_token_secret)
		self.api = API(self.auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
		self.stream_listener = BotStreamer(api=self.api, tracked_word=self.tracked_word[0])
		self.streaming = Stream(auth=self.api.auth, listener=self.stream_listener)
		self.logger.log('Login successful\n')

	# Function to start listening.
	# returns a status object which gets passed to the on_status function in our BotStreamer subclass
	def listen(self, follow: object = None) -> None:
		"""
		This function starts our BotStreamer subclass

		:rtype: None
		:param follow: ID of user to follow
		"""
		if follow is None:
			follow = self.user_to_follow
		self.logger.log('Listening...')
		# Set stream to follow only me and listen for specific tweets
		self.streaming.filter(follow=[follow], is_async=True, track=self.tracked_word)

	# Function for tweeting
	def tweet(self, tweet: object) -> None:
		"""
		In case we need to manually tweet for some reason in the future

		:rtype: None
		:param tweet: String object to tweet
		"""
		self.api.update_status(tweet)

	# Function for replying
	def reply(self, reply: object, status_id: object) -> None:
		"""
		In case we want to reply manually for some reason

		:rtype: None
		:param reply: String object to reply with
		:param status_id:  Tweet ID to reply to
		"""
		self.api.update_status(reply, in_reply_to_status_id=status_id, auto_populate_reply_metadata=True)


class BotStreamer(StreamListener):
	def __init__(self, api=None, tracked_word=None):
		# Call StreamListener superclass and set our API to the already authenticated one from Bot()
		super().__init__(api=api)
		self.logger = Logger()
		self.api = api
		self.tracked_word = tracked_word
		self.is_reminder_attempt = False
		self.time_travel_requested = False

	def on_status(self, status: object):
		"""
		This function is activated whenever we find our tracked word (which is @samiambot)

		:rtype: None
		:param status:
		:return: None
		"""
		# Check if @samiambot was mentioned. I.E, bot will not respond to just "samiambot" but "@samiambot"
		if self.tracked_word in status.text.lower():
			# Check that it's not a test message
			if '/test/' not in status.text.lower():
				self.logger.log(f"[{datetime.now(tz=timezone('EST'))}]")
				self.logger.log('Found @samiambot mention')
				original_tweet_id = self.parse_reply(status, video=True)
				# If tweet is a reply
				if original_tweet_id is not None:
					tweet_media_link = self.get_media_url(original_tweet_id)
					# If there's a video
					if tweet_media_link is not None:
						# Reply with video link
						self.api.update_status(f'Here\'s your video link below!\n{tweet_media_link}',
						                       in_reply_to_status_id=status.id,
						                       auto_populate_reply_metadata=True)  # auto populate needs to be set to true
						# or a new tweet is made and not a reply
						self.logger.log('Replied with link\n')
					# Simply do nothing if there's no video (for now)
					else:
						self.logger.log('Couldn\'t find extended entities')
						return
				# Simply do nothing if tweet is not a reply (will always hold true as bot should only work for comments/replies)
				else:
					return

			# TODO: Implement reminder class...someday
			# If the mention of our bot contains any extra text rather than simply "@samiambot".
			elif 'remindme' in status.text.lower():
				# Parse reply to determine that it's in fact a reminder request
				date_time_object = self.parse_reply(status.text, reminder=True)
				# If we successfully parse and get our desired word (!RemindMe) and a time (eg. 1 hour)
				if date_time_object is not None:
					# Schedule our reminder
					reminder_bot = ReminderBot.Scheduler()
					reminder_bot.schedule(status.id, date_time_object)
				else:
					# Check if it's a failed attempt for a reminder and send a reply
					if self.is_reminder_attempt:
						self.api.update_status(f'No time found. Please use either  (Case insenitive) !Remindme, RemindMe!, '
						                       f'or remindme followed by a time\nExample: RemindMe in 5 hours (don\'t '
						                       f'put anything else after the tweet) in_reply_to_status_id=status.id, '
						                       f'auto_populate_reply_metadata=True)')
						self.logger.log('User failed reminder attempt. Correct format replied.\n')
						return
					# Check if reminder time is in the past. We always want a future time
					elif self.time_travel_requested:
						self.api.update_status('Can\'t remind you in the future sir. We\'re just not there yet :/. '
						                       'Please pick a valid time')
			# For testing purposes!
			elif '/test/' in status.text.lower():
				self.logger.log(f"[{datetime.now(tz=timezone('EST'))}]")
				self.logger.log('Found Test Statement')
				self.api.update_status('Hello creator\nReady whenever, just let me know what video you want to download!', in_reply_to_status_id=status.id, auto_populate_reply_metadata=True)
				self.logger.log('Reply sent to test message\n')

	def parse_reply(self, reply: object, video: object = False, reminder: object = False) -> object:
		"""
		Function to parse our user's reply and perform the necessary operations based on bool values passed in

		:rtype: object
		:param reply: String object to parse
		:param video: Boolean for if we should parse with knowledge that we want a video
		:param reminder: Boolean for if we should parse and set a reminder
		:return: Either a datetime object for a reminder, A string object of the tweet to reply video link under, or None
		"""
		# Check if it's a retweet
		if hasattr(reply, 'retweeted_status'):
			return
		else:
			# If we need to parse a reminder
			if reminder:
				try:
					# Search for our desired words case insensitive
					word_to_match = re.search(r'(?i)(!*)RemindMe(!*)', reply)
					# Get everything before our desired match
					tweet_string = reply[word_to_match.start():]
					self.logger.log("Found reply with just @samiambot")
					# Remove characters that break our format
					tweet_string = tweet_string.split('\n')[0]
					if tweet_string.count('"') == 1:
						tweet_string = tweet_string + '"'

					# Fix dashing for datetime format
					tweet_string = tweet_string.replace('-', '/')
					# Get Remind Me message time
					reminder_time = re.sub('(["].{0,9000}["])', '', tweet_string)[9:]

					# Check that there's a time format that we want. Eg ("in 5 days" or "in 1 hour", "on August 5th, 2020")
					if reminder_time is not None:
						self.logger.log("No time found for reminder attempt\n")
						datetime_object = dateparser.parse(reminder_time)
						# Can't remind in the past so we compare that time to now
						if datetime_object < datetime.now():
							self.time_travel_requested = True
							return
						else:
							return dateparser.parse(reminder_time)  # which will look something like -> 2020-08-25 00:00:00
					# Return None if we dont have a time but we have the desired words so we can reply to user with
					# the correct reminder format
					else:
						# Here, we want to see if it's an attempt for a reminder and reply with  the appropriate reminder format
						self.is_reminder_attempt = True
						return
				# We get this error when we hit tweet_string = reply[match.start():] which means there are not words we need
				# (remindme, !RemindMe, RemindMe!, remindme!, etc) so we can go ahead and return None
				except AttributeError:
					return
			elif video:
				# Get original tweet's ID for processing
				original_tweet_id = reply.in_reply_to_status_id_str
				# Check to see if tweet is a reply. We want a reply under a video (which we'll check for later)
				if original_tweet_id is not None:
					self.logger.log("Tweet is a reply!")
					# Return original tweet ID and status attributes
					return original_tweet_id
				# If tweet is not a reply just move on and log it
				else:
					# Store reply attributes for when bot replies
					self.logger.log("No media found\n")
					return

	# Function for getting media url
	def get_media_url(self, extended_tweet_id: object) -> object:
		"""
		Function to get video url

		:rtype: object
		:param extended_tweet_id: String object of the original tweet that posted a video
		:return: Media url or None
		"""
		self.logger.log("Downloading media")
		original_tweet_object = self.api.get_status(extended_tweet_id)
		media_url = None
		try:
			video_variants = original_tweet_object.extended_entities['media'][0]['video_info']['variants']
		except AttributeError:
			return

		for variant in video_variants:
			if variant['content_type'] == 'video/mp4':
				media_url = variant['url']

		# wget.download(media_url, os.path.join(sys.path[0], 'media'))
		self.logger.log("Media link obtained")
		return media_url

	def on_error(self, status_code: object) -> object:
		"""
		Overriding StreamListener's on_error function

		:rtype: object
		:param status_code: Integer object of whatever status code we get
		:return: False for our errors
		"""
		if status_code == 420:
			self.logger.log(f'Status {status_code}')
			return False
		elif status_code == 429:
			self.logger.log(f'Status {status_code}')
			return False


class Logger:
	def __init__(self):
		# Set location for getting absolute path
		self.log_name = "log.txt"

	def log(self, text: object) -> None:
		"""
		For logging. A bit unnecessary but whatever

		:rtype: None
		:param text: String object to log
		"""
		# See if log exists in same folder and set appropriate file access mode, Append to file if it exists and create
		# new file if it doesn't exist
		if os.path.exists(os.path.join(sys.path[0], self.log_name)):
			mode = 'a'
		else:
			mode = 'w'

		# open and write to log file
		with open(os.path.join(sys.path[0], 'log.txt'), mode) as log_file:
			log_file.write(f'{text}\n')


if __name__ == '__main__':
	twitter_bot = Bot()
	twitter_bot.listen()
