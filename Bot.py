import os
import re
import sys

from tweepy import StreamListener, Stream, OAuthHandler, API

import util


class Bot:
	def __init__(self):
		self.logger = Logger()
		self.logger.log('Logging in...')
		self.api_key = util.api_key
		self.api_secret_key = util.api_secret_key
		self.access_token = util.access_token
		self.access_token_secret = util.access_token_secret
		self.tracked_word = ['samiambot']
		self.auth = OAuthHandler(self.api_key, self.api_secret_key)
		self.auth.set_access_token(self.access_token, self.access_token_secret)
		self.api = API(self.auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
		self.stream_listener = Streamer(api=self.api, tracked_word=self.tracked_word[0])
		self.streaming = Stream(auth=self.api.auth, listener=self.stream_listener)
		self.logger.log('Login successful\n')

	# Function to start listening.
	# returns a status object which gets passed to the on_status function in our Streamer subclass
	def listen(self, follow=util.user_to_follow):
		self.logger.log('Listening...')
		# set stream to follow only me and listen for my tweets
		self.streaming.filter(follow=[follow], is_async=True, track=self.tracked_word)

	# # Function for tweeting
	# def tweet(self, tweet):
	# 	self.api.update_status(status=tweet)
	#
	# # Function for replying
	# def reply(self, status_id, reply):
	# 	self.api.update_status(in_reply_to_status_id=status_id, status=reply)


class Streamer(StreamListener):
	def __init__(self, api=None, tracked_word=None):
		# Call StreamListener superclass and set out API to the already authenticated one from Bot()
		super().__init__(api=api)
		self.logger = Logger()
		self.api = api
		self.tracked_word = tracked_word

	def on_status(self, status):
		# Check if @samiambot was mentioned. I.E, bot will not respond to just "samiambot" but "@samiambot"
		if status.entities['user_mentions']['screen_name'] == self.tracked_word:
			original_tweet_id = self.parse_reply(status)
			if original_tweet_id is not None:
				media = self.get_media(original_tweet_id)
				if media is not None:
					pass
			else:
				return

	def parse_reply(self, reply, video=False, reminder=False):
		# Check if it's a retweet
		if hasattr(reply, 'retweeted_status'):
			return
		else:
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

				# Fix dashing for datetime parsing
				tweet_string = tweet_string.replace('-', '/')
				# Get Remind Me message
				reminder_time = re.sub('(["].{0,9000}["])', '', tweet_string)[9:]

				if reminder_time is not None:
					self.logger.log("No time found\n")
					return  # Return something here
			# We get this error when we hit tweet_string = reply[match.start():] which means there are not words we need
			# (remindme, !RemindMe, RemindMe!, remindme!, etc) so we can go ahead and check if its a reply and process
			except AttributeError:
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

	# Function for downloading media
	def get_media(self, extended_tweet_id):
		self.logger.log("Downloading media")
		original_tweet_object = self.api.get_status(extended_tweet_id)
		media_url = None
		video_variants = original_tweet_object.extended_entities['media'][0]['video_info']['variants']

		for variant in video_variants:
			if variant['content_type'] == 'video/mp4':
				media_url = variant['url']

		# wget.download(media_url, os.path.join(sys.path[0], 'media'))
		self.logger.log("Media link obtained\n")
		print("Media link obtained\n")
		return media_url

	def on_error(self, status_code):
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

	def log(self, text):
		# See if log exists in same folder and set appropriate file access mode
		if os.path.exists(os.path.join(sys.path[0], 'log.txt')):
			mode = 'a'
		else:
			mode = 'w'

		# open and write to log file
		with open(os.path.join(sys.path[0], 'log.txt'), mode) as log_file:
			log_file.write(f'{text}\n')


Bot().listen(follow=util.throw_away)
# print(Processor().process_text("samiambot"))
# Logger("Test")
