import asyncio

import discord
from loguru import logger

from agent.framework.agent import get_agent

_agent = get_agent("nanobot")


async def run(token: str, bot_id: str, role: str):
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    agent_loop = _agent.get_agent_loop()

    @client.event
    async def on_ready():
        logger.info(f"Discord bot connected as {client.user}")

    @client.event
    async def on_message(message: discord.Message):
        if message.author == client.user:
            return
        if not (client.user in message.mentions or isinstance(message.channel, discord.DMChannel)):
            return
        text = message.content.replace(f"<@{client.user.id}>", "").strip()
        if not text:
            return

        from agent.models import ChatSession, ChatMessage
        session_label = f"discord:{message.author.id}"
        session, _ = await ChatSession.objects.aget_or_create(
            bot_id=bot_id,
            label=session_label,
        )

        await ChatMessage.objects.acreate(
            session=session, user=None, role=ChatMessage.Role.USER, content=text, artifacts=[],
        )

        _agent._user_role.set(role)
        _agent._user_id.set(None)
        _agent._source.set("discord")
        _agent._bot_id.set(bot_id)

        async with message.channel.typing():
            try:
                response = await agent_loop.process_direct(content=text, session_key=str(session.id))
            except Exception as e:
                logger.error(f"[discord bot] agent error: {e}")
                response = "An error occurred. Please try again."

        await ChatMessage.objects.acreate(
            session=session, user=None, role=ChatMessage.Role.ASSISTANT, content=response[:2000], artifacts=[],
        )

        await message.reply(response[:2000])

    try:
        await client.start(token)
    except asyncio.CancelledError:
        await client.close()
        logger.info("Discord bot stopped.")
