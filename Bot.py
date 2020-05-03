import os

from tweepy import StreamListener, Stream, OAuthHandler, API

import util


class Bot:
	def __init__(self):
		self.api_key = util.api_key
		self.api_secret_key = util.api_secret_key
		self.access_token = util.access_token
		self.access_token_secret = util.access_token_secret
		self.master_user = "2472010408"
		self.auth = OAuthHandler(self.api_key, self.api_secret_key)
		self.auth.set_access_token(self.access_token, self.access_token_secret)
		self.api = API(self.auth)
		self.stream_listener = Streamer()
		self.streaming = Stream(auth=self.api.auth, listener=self.stream_listener)
		self.tracked_word = ['samiambot']

	def listen(self):
		# set stream to follow only me and listen for my tweets
		self.streaming.filter(follow=[self.master_user], is_async=True, track=self.tracked_word)


class Log:
	def __init__(self, text):
		# Set location for getting absolute path
		self.location = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
		self.log_name = "log.txt"

		# See if log exists in same folder and set appropriate file access mode
		if os.path.exists(os.path.join(self.location, 'log.txt')):
			mode = 'a'
		else:
			mode = 'w'

		# open and write to log file
		with open(os.path.join(self.location, 'log.txt'), mode) as log_file:
			log_file.write(f'{text}\n')


class Streamer(StreamListener):
	def on_status(self, status):
		if hasattr(status, 'retweeted_status'):
			pass
		else:
			print(status.text)

	def on_error(self, status_code):
		if status_code == 420:
			Log(f'Status {status_code}')
			return False
		elif status_code == 429:
			Log(f'Status {status_code}')
			return False


class Processor:
	def __init__(self):
		pass

	def process_text(self, text):
		print(list(text))


Processor().process_text("Test")
