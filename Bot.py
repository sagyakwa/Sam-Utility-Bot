import os
import sys

import wget
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
		self.auth = OAuthHandler(self.api_key, self.api_secret_key)
		self.auth.set_access_token(self.access_token, self.access_token_secret)
		self.api = API(self.auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
		self.stream_listener = Streamer(api=self.api)
		self.streaming = Stream(auth=self.api.auth, listener=self.stream_listener)
		self.tracked_word = ['samiambot']
		self.logger.log('Login successful\n')

	# Function to start listening.
	# returns a status object which gets passed to the on_status function in our Streamer subclass
	def listen(self, follow=util.user_to_follow):
		self.logger.log('Listening...')
		# set stream to follow only me and listen for my tweets
		self.streaming.filter(follow=[follow], is_async=True, track=self.tracked_word)

	# Function for tweeting
	def tweet(self, tweet):
		self.api.update_status(status=tweet)

	# Function for replying
	def reply(self, reply, status_id):
		self.api.update_status(in_reply_to_status_id=status_id, status=reply)


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


class Streamer(StreamListener):
	def __init__(self, api=None):
		# Call StreamListener superclass and set out API to the already authenticated one from Bot()
		super().__init__(api=api)
		self.logger = Logger()
		self.api = api

	def on_status(self, status):
		# Check if it's a retweet
		if hasattr(status, 'retweeted_status'):
			pass
		else:
			self.logger.log("Found reply with @samiambot")
			original_tweet_id = status.in_reply_to_status_id_str
			# Check to see if tweet is a reply. We want a reply under a video
			if original_tweet_id is not None:
				self.logger.log("Found Media")
				# Store reply attributes for processing wha
				status_attributes = {
					'status_text': status.text,
					'status_id': status.id
				}
				# Get the media of the original tweet
				return self.get_media(original_tweet_id)
			# If tweet is not a reply just move on and log it
			else:
				self.logger.log("No media found\n")
				print("Not a reply")

	# Function for downloading media
	def get_media(self, extended_tweet_id):
		self.logger.log("Downloading media")
		media_files = []
		original_tweet_media = self.api.statuses_lookup(extended_tweet_id, include_entities='media')
		media_files.append(original_tweet_media)
		print(original_tweet_media)

		for media in media_files:
			wget.download(media, os.path.join(sys.path[0], 'media'))

		self.logger.log("Media downloaded\n")
		print("Media downloaded\n")

	def on_error(self, status_code):
		if status_code == 420:
			self.logger.log(f'Status {status_code}')
			return False
		elif status_code == 429:
			self.logger.log(f'Status {status_code}')
			return False


Bot().listen()
# print(Processor().process_text("samiambot"))
# Logger("Test")