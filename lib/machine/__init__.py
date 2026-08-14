import asyncio

from .cpu import CPU
from .memory import Memory
from .storage import Storage
from .network import Network
from .host import Host
from .minecraft import Minecraft


class Machine:

	def __init__(self):
		self.cpu = CPU()
		self.memory = Memory()
		self.storage = Storage()
		self.network = Network()
		self.host = Host()
		self.minecraft = Minecraft()

	async def get_full_info(self):
		cpu, minecraft = await asyncio.gather(
			self.cpu.get_full_info(),
			self.minecraft.get_status()
		)
		return {
			"cpu": cpu,
			"memory": self.memory.get_usage(),
			"storage": self.storage.get_usage(),
			"network": self.network.get_net(),
			"host": self.host.get_host(),
			"minecraft": minecraft
		}
