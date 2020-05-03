import os
import sys

import wget
from tweepy import StreamListener, Stream, OAuthHandler, API

import util

__file__ = 'Bot.py'


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
		self.api = API(self.auth)
		self.stream_listener = Streamer(api=self.api)
		self.streaming = Stream(auth=self.api.auth, listener=self.stream_listener)
		self.tracked_word = ['samiambot']
		self.logger.log('Login successful\n')

	def listen(self, follow=util.user_to_follow):
		self.logger.log('Listening...')
		# set stream to follow only me and listen for my tweets
		self.streaming.filter(follow=[follow], is_async=True, track=self.tracked_word)

	def tweet(self, tweet):
		self.api.update_status(status=tweet)

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
		super().__init__(api=api)
		self.logger = Logger()
		self.api = api

	def on_status(self, status):
		bot = Bot()
		if hasattr(status, 'retweeted_status'):
			pass
		else:
			self.logger.log("Found reply with @samiambot")
			original_tweet_id = status.in_reply_to_status_id_str
			if original_tweet_id is not None:
				self.logger.log("Found Media")
				status_attributes = {
					'status_text': status.text,
					'status_id': status.id
				}
				return self.get_media(original_tweet_id)

			else:
				self.logger.log("No media found\n")
				print("Not a reply")

	def get_media(self, extended_tweet_id):
		self.logger.log("Downloading media")
		media_file = set()
		original_tweet_media = self.api.statuses_lookup(extended_tweet_id, include_entities='media')
		print(original_tweet_media)

		for media in media_file:
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