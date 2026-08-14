import asyncio
import json
import re
import struct

from ..config import config


class Minecraft:

	async def get_status(self):
		if not config.get("minecraft", "enabled"):
			return None

		address = config.get("minecraft", "address")
		port = int(config.get("minecraft", "port"))

		try:
			status = await asyncio.wait_for(ping(address, port), timeout=1)
		except (OSError, asyncio.TimeoutError, EOFError, ValueError):
			return {"online": False}

		players = status.get("players", {})
		return {
			"online": True,
			"players": players.get("online", 0),
			"max_players": players.get("max", 0),
			"player_names": [p["name"] for p in players.get("sample", []) if "name" in p],
			"version": status.get("version", {}).get("name"),
			"motd": parse_motd(status.get("description"))
		}


# Server List Ping - the status handshake every vanilla-compatible server answers
# https://minecraft.wiki/w/Java_Edition_protocol#Status_Request

async def ping(address: str, port: int):
	reader, writer = await asyncio.open_connection(address, port)
	try:
		# Handshake (id 0, protocol -1 = "just asking", next state 1 = status)
		handshake = pack_varint(0) + pack_varint(-1) + pack_string(address) + struct.pack(">H", port) + pack_varint(1)
		writer.write(pack_packet(handshake) + pack_packet(pack_varint(0)))
		await writer.drain()

		await read_varint(reader)	# packet length
		await read_varint(reader)	# packet id
		length = await read_varint(reader)
		data = await reader.readexactly(length)
		return json.loads(data)

	finally:
		writer.close()


def pack_varint(value: int):
	value &= 0xFFFFFFFF
	data = b""
	while True:
		byte = value & 0x7F
		value >>= 7
		data += bytes([byte | (0x80 if value else 0)])
		if not value:
			return data


def pack_string(value: str):
	encoded = value.encode("utf-8")
	return pack_varint(len(encoded)) + encoded


def pack_packet(payload: bytes):
	return pack_varint(len(payload)) + payload


async def read_varint(reader):
	value = 0
	for i in range(5):
		byte = (await reader.readexactly(1))[0]
		value |= (byte & 0x7F) << (7 * i)
		if not byte & 0x80:
			break
	return value


# MOTD may be a plain string or nested chat components
def flatten_chat(part):
	if isinstance(part, str):
		return part
	if isinstance(part, list):
		return "".join(flatten_chat(p) for p in part)
	if isinstance(part, dict):
		return part.get("text", "") + flatten_chat(part.get("extra", []))
	return ""


def parse_motd(description):
	if description is None:
		return None
	text = re.sub("§.", "", flatten_chat(description))
	return text.replace("\n", " ").strip()
