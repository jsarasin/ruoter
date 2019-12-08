from scapy.all import *
from scapy.layers.inet import *


class ExistingInstance(Exception):
	"""Only one instance of MultiTraceroute is allowed to avoid other instances stealing eachothers replies."""
class TargetExists(Exception):
	"""Can only run one traceroute on a single target at a time"""
class TracerouteException(Exception):
	"""An unhandled error occured"""
class UnhandledNetworkResponse(Exception):
	"""The traceroute engine received a response it was not expecting"""

class TracerouteTarget:
	def __init__(self, target_ip, frequency=500, max_hop_search=1):
		self.target_ip = target_ip
		self.frequency = frequency
		self.max_hop_search = max_hop_search
		self.hop_timeout = 15

class MultiTraceroute:
	def __init__(self, config):
		self.config = config

		# answered, unanswered_sent = sr(
		# 	IP(	dst=self.config.target, ttl=(self.config.configcttl), id=self.config.configcustom_id) /
		# 	UDP(dport=self.config.configcork) /
		# 	Raw(self.config.configDATA),
		# 	verbose=False, timeout=MultiTraceroute.TIMEOUT, filter=myfilter
		# )

		send(   IP( dst=self.config.target_ip, ttl=(self.config.max_hop_search), id=0) /
				UDP(dport=1000),
				verbose=False)

		# sniff(	filter="tcp",
		# 		prn = lambda x: x.summary())

		t = AsyncSniffer(filter="tcp",
				prn = lambda x: x.summary())
		t.start()
		time.sleep(10)
		print("nice weather today")
		t.stop()
