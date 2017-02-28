import discord
import os
import aiohttp
import re
import requests
import json

from discord.ext import commands
from email.utils import parseaddr
# from .utils.dataIO import fileIO


class Mailgun:
    """ Send messages from your channel as emails to your friends! """

    def __init__(self, bot):
        self.bot = bot
        with open("data/mailgun/config.json", "r", encoding="utf-8") as cfile:
            self.config = json.load(cfile)

    @commands.command(pass_context=True, no_pm=True)
    async def mailgun(self, ctx, address: str, count: int=1):
        # Make sure config.json is set up properly
        if self.config["key"] == "":
            await self.bot.say("ERROR: Your API key isn't valid! Enter it in `data/config.json`")
            return
        elif self.config["domain"] == "":
            await self.bot.say("ERROR: Your domain isn't valid! Enter it in `data/config.json`")
            return

        # Now our basic setup check is done, let's make sure the address is valid
        # parseaddr returns a tuple, so we want the second element
        recipient = parseaddr(address)[1]
        if '@' not in recipient:
            await self.bot.say("That doesn't look like a valid email address!")
            return

        # Make sure 'count' is a sane number for our context
        if count < 1:
            await self.bot.say("Please specify 1 or more messages.")
            return

        # TODO: Check the address against our banned recipient list

        # Get our previous message(s)
        prev_msgs = []
        msgct = 0
        async for msg in self.bot.logs_from(ctx.message.channel, count, before=ctx.message):
            # Each entry in prev_msg is a tuple - the message body, and the URL
            # of the attachment (if there was one)
            content = msg.clean_content
            attachment = extract_attachment(msg.attachments, self.config["allowed_extensions"])

            prev_msgs.append((content, attachment))

        # Make sure we have some messages to send
        if (prev_msgs == []) or (prev_msgs[0] == ('', '')):
            await self.bot.say("There's nothing for me to send!")
            return

        # Format our message body HTML
        htmlMessage = ''
        for msg in prev_msgs.reverse():  # order prev_msgs chronologically
            if msg[0] is not '':
                htmlMessage += '<p>{}</p>'.format(msg[0])
            if msg[1] is not '':
                htmlMessage += '<img src="{0}">'.format(msg[1])

            if msg is not ('', ''):
                htmlMessage += '<hr>'

        # Set up our variables for sending the email
        sender = 'Discord Automailer <discord@{}>' .format(self.config["domain"])
        subject = 'Discord automatic mail from {}'.format(ctx.message.author.name)
        request_url = 'https://api.mailgun.net/v3/{}/messages'.format(self.config["domain"])

        # Send the email
        email = requests.post(request_url, auth=('api', self.config["key"]), data={
            'from': sender,
            'to': recipient,
            'subject': subject,
            'html': htmlMessage
        })

        # Check the response from Mailgun
        # TODO: Add support for more response codes
        if 'Forbidden' in email.text:
            await self.bot.say("ERROR: Access denied. Is your API key valid?")
            return
        elif 'Queued' in email.text:
            await self.bot.say("Your message is on the way!")
            return

    @commands.command(pass_context=True)
    async def banaddress(self, ctx, address: str):
        if not address:
            await self.bot.say("Please specify an address")
            return
        else:
            self.config[address].push(address)  # TODO: Check to see if this is the right way to do this
            await self.bot.say("Address banned.")
            return


def extract_attachment(attachList, extensions):
    if (attachList):
        attachment = attachList[0]
        if any(ext in attachment['url'] for ext in extensions):
            return attachment['url']
    else:
        return ''

"""
 I shamelessly stole the code for check_folders() from 26-Cogs
 Credit where credit is due: https://github.com/Twentysix26/26-Cogs
"""


def check_folders():
    folders = ("data", "data/mailgun/")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)


def check_files():
    defaultConfig = {"key": "", "domain": "", "banned_domains": ["discordapp.com", "whitehouse.gov"]}

    if not os.path.isfile("data/mailgun/config-example.json"):
        print("Creating default config file...")
        dc = open('data/config-example.json', 'w+')
        json.dump(defaultConfig, dc)
        # fileIO("data/config-example.json", "save", defaultConfig)

    if not os.path.isfile("data/mailgun/config.json"):
        print("Creating config file, please fill it out!")
        cf = open('data/config.json', 'w+')
        json.dump(defaultConfig, cf)
        # fileIO("data/config.json", "save", defaultConfig)


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Mailgun(bot))
