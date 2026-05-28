import discord
from discord.ext import commands
from langchain_core.documents import Document
from langchain_ollama.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.messages import AIMessage, SystemMessage, HumanMessage
import logging
import pandas as pd
from dotenv import load_dotenv
import os
import asyncio
import json
import time
from vector import retriever


members = [] #hold member list    

with open("sysPrompt.txt","r",encoding='utf8') as s:
    systemMessage = s.read()
with open("memories.txt","r",encoding='utf8') as memories:
    line = memories.read()
    if (len(line)>0):
        systemMessage+=f"this is summary of your last chat session \n{line}"  # Handle open memories file in read or overwrite mode
memories = open("memories.txt","a", encoding='utf8')         # Change back mode to overwrite

# Create json for guild list with bot
try:
    with open(f"json\\guild channel\\guild_list.json", "x"):  
        print("create file guild list")
except:
    print("guild list exist")

if os.path.getsize("json\\guild channel\\guild_list.json")>0:
    with open(f"json\\guild channel\\guild_list.json", "r") as f:
        guild_list = json.load(f)
        print(guild_list)
else:
    guild_list = []
    print("---NO GUILD---")




# print(systemMessage)   #DEBUG---------------------------
active = None
model= "gemma4:e4b"  # model used
chat = ChatOllama(
    model=model,
    temperature=1,
    )
template =  ChatPromptTemplate.from_messages([
                MessagesPlaceholder(variable_name="convo"),
                MessagesPlaceholder(variable_name="context")
            ])
messages= [SystemMessage(content=systemMessage)]         # to contain the messages

memory = []                                    # to contain chat history without system prompt

dfMain = pd.DataFrame()
# tools=[{
#     'type': 'function',
#     'function': {
#     'name': 'warn',
#     'description': 'to warn member when they say the word "shit"',
#     'parameters': {
#         'type': 'object',
#         'required': ['message'],
#     },
#     },
# },
# ]


load_dotenv()
token = os.getenv("DISCORD_TOKEN")

handler = logging.FileHandler(filename="discordbot.log",encoding='utf-8',mode='w')
intents = discord.Intents.default()
intents.message_content = True     # Set intents to true in code
intents.members = True
intents.presences = True


# ---------------------------------------------------
bot = commands.Bot(command_prefix="!", intents=intents) # set prefix so every bot command will start with "!" (in discord server)
# ---------------------------------------------------


# ON BOT READY -------------------------------
@bot.event
async def on_ready(): 
    #// LIST MEMBERS IN GUILD
    for guild in bot.guilds:
        for member in guild.members:
            members.append(member.id)

    print(f"HI, I'am {bot.user.name}")


# BOT COMMAND FUNCTION -----------------------
@bot.command()  
async def list_servers(ctx):
    for guild in bot.guilds:
        await ctx.send(f"{ctx.author.mention} bot joined in {guild}")

@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author.mention}!")

@bot.command()
async def mention(ctx):
    for i in range (len(members)):
        await ctx.send(f"{i} - {ctx.guild.get_member(members[i]).display_name}")
    
    def check(m):
        return (m.author == ctx.author and m.channel == ctx.channel)
    
    try:
        await ctx.send("choose which member you wanna mention: ")
        message = await bot.wait_for("message",timeout=15.0,check=check)
    except asyncio.TimeoutError:
        await ctx.send("time ran out")
    else:
        mentioned = str(members[int(message.content)])
        await ctx.send(f"HELLO {mention(ctx.guild.get_member(members[int(message.content)]))}")#<-something wrong here

@bot.command
async def add_channel(ctx):
    if ctx.message in guild_list:
        ctx.send("YES?")
    ctx.send(ctx.message)


# ON EVENT FUNCTION ----------------------------       
@bot.event
async def on_guild_join(guild):
    global active
    global guild_list
    channel_names = [channel.name for channel in guild.text_cchannels]
    print(channel_names)
    integrations = await guild.integrations()
    for integration in integrations:
        if isinstance(integration, discord.BotIntegration):
            if integration.application.user.name == bot.user.name:
                inviter = integration.user
                if inviter:
                    try:
                        global send_options
                        if not(guild.name in guild_list): 
                            guild_list.append(guild.name)

                            send_options = DropdownView(channel_names)
                            await inviter.send(view=send_options)
                            await send_options.wait()
                            active = [send_options.choose]
                            with open(f"json\\guild channel\\guild_{guild.name}.json", "w") as f:  # dump channel in active guild
                                json.dump(active,f)   
                            with open(f"json\\guild channel\\guild_list.json", "w") as f:   # dump guild list
                                json.dump(guild_list,f)
                            print(f"active: {active}")
                        else:
                            try:
                                with open(f"json\\guild channel\\guild_{guild.name}.json", "r") as f:
                                    channel = json.load(f)
                                await inviter.send(f"This bot is already in {guild.name}, {channel} channel ----- You can always add more channel with command !add_channel")
                            except Exception:
                                await inviter.send(f"This guild have invite the bot at some point but got deleted !")
                                send_options = DropdownView(channel_names)
                                await inviter.send(view=send_options)
                                await send_options.wait()
                                active = [send_options.choose]
                                with open(f"json\\guild channel\\guild_{guild.name}.json", "w") as f:  # dump channel in active guild
                                    json.dump(active,f)               
                              
                    except discord.Forbidden:
                        # User may have DMs closed
                        print(f"Could not DM {inviter.name}")
                break

@bot.event
async def on_message(message): #ADD open json to check if channel listed
    global dfMain 
    global active
    if not isinstance(message.channel, discord.DMChannel):
        print(f"{message.channel}, {active}") 
        if message.content.lower() == "/exit":
            if len(messages)>0:
                date = message.created_at
                for i in range(len(messages)-1):  #remove sysprompt from list
                    messages[i] = messages[i+1]
            

                # Create summerize of previous interation
                messages.append(SystemMessage(content="you are being shutted down, now summarize this chat in english so you can easily know important details in the next session!. remember important points (names, event, story, name, specific topics, language of each member), also give your opinion for each member you interacted with so you will remember how to get the conversation going with them, make sure in the next session you remember you have been shutted down before."))
                summary = chat.invoke(messages)  # the summarize is forced to the model the data is raw and not structured.
                # print(summary.content)
                memories.write("\n"+str(summary.content)+ f"\n MEMORY CREATED AT {date} -- END OF MEMORY --")
                memories.close()
                print("memory created")

                # Kill connection to discord bot
                await bot.close()

                # PLACE TO SAVE CHAT as Json locally
                for i,row in dfMain.iterrows():
                    print(f"ITERATION: {i}")
                    doc = Document(
                        page_content=row["subject"]+" "+row["content"],  # Turn Dataframe into Document
                        metadata={"Date":row["date"]}   
                    )
                    print(f"Construct: {i}")
                    try:
                        with open(f"json\\chat_{i}.json", "w") as f:      # Dump document to Json
                            json.dump(doc.model_dump(), f)       
                            print("Dump")
                    except Exception as e:
                        print(f"failed to dump jason: {e}")            
                

                return
            else:
                memories.close()
                await bot.close()


        if (not message.content.startswith(bot.command_prefix) and message.channel.name == active): # function to ask inviter for the channel still on progress
            if message.author == bot.user:return                              # Do not response the bot message
            date = message.created_at
            # catch all chat or images
            allmsg = ""
            try:
                msgContent = (f"{message.author.display_name}:{message.content}") 
                allmsg+=msgContent
                print(f"MSG CONTENT: {msgContent}")
            except Exception as e:
                attachContent = None
                print(f"No Text:{e}")       
            try:
                for attachment in message.attachments:           
                    attachContent = (f"image_url: {str(attachment.url)}")
                allmsg+=attachContent
                print(f"ATTCH CONTENT: {attachContent}")
            except Exception as e:
                msgContent = None
                print(f"No Image:{e}")
            humanMSG = HumanMessage(content=(allmsg))   
            
            messages.append(humanMSG)     # append user input to the message sent-----------------------
            print(f"HUMAN MSG: {humanMSG.content}")
            dftemp = pd.DataFrame({
                "subject":[humanMSG.content.split(":")[0]],
                "content":[humanMSG.content.split(":")[:1]],
                "date":[str(date)]
            })
            dfMain = pd.concat([dftemp,dfMain],ignore_index=True)


            async with message.channel.typing():
                # CHAIN -------------------------------------------------------------------------------------
                if (retriever==None):#if no data in collection then return nothing to retrive
                    ctx = "nothing to retrive"  
                else:
                    ctx = retriever.invoke(humanMSG.content)
                chain = template | chat
                result = chain.invoke({"convo":messages,
                                    "context":[SystemMessage(content=f"here is some information you can use, ignore if the information does not realte to the conversation : {ctx}")] # [] is needed for the template require list
                                    }) 
                # print(f"retrieved: {retriever.invoke(humanMSG.content)}") # DEBUG PRINT RETRIEVED


            aiMSG = AIMessage(content=f"{result.content}")
            messages.append(aiMSG)                           # append bot response----------------------
            dftemp = pd.DataFrame({
                "subject":["BOT"],
                "content":[result.content],
                "date":[str(date)]
            })
            dfMain = pd.concat([dftemp,dfMain],ignore_index=True)
            
            # os.system('cls' if os.name == 'nt' else 'clear')   # DEBUG - TO PRINT CONVO !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            print("\n\n\n-----------------CHAT-----------------------\n")
            for i in messages:          
                print(f"->{i.content}")
            

            await message.channel.send(result.content)   # SEND model reply to discord

        # Crucial line: allows the bot to process other commands
        await bot.process_commands(message)


# ----- ON CALL FUNCTION -----
async def warn(message):
    await message.channel.send(f"dont say that {message.author.mention}")


# ----- Classes -----
class MultipleChoice(discord.ui.Select):
    def __init__(self,channelCount:list,parent_view):   
        self.parent_view = parent_view                                                                                          
        options = []   
        for i in channelCount:
            options.append(discord.SelectOption(label=i, description = i))
            super().__init__(placeholder='Choose your channel for rocky to chat...', min_values=1, max_values=1, options=options)
          
    async def callback(self, interaction: discord.Interaction):
        choose = self.values[0]
        self.parent_view.choose = choose
        self.parent_view.stop()
        await interaction.response.send_message(f'active at: {choose}!')
             
class DropdownView(discord.ui.View):
    def __init__(self, channelcount):
        super().__init__()
        self.choose = None
        self.add_item(MultipleChoice(channelcount,self)) 


bot.run(token=token,log_handler=handler,log_level=logging.DEBUG) # RUN BOT
