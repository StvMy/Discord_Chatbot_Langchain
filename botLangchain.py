import discord
from discord.ext import commands
from langchain_ollama.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.messages import AIMessage, SystemMessage, HumanMessage
import logging
from dotenv import load_dotenv
import os
import asyncio
from vector import retriever

members = [] #hold member list    

systemMessage = open("sysPrompt.txt","r",encoding='utf8').read()
memories = open("memories.txt","r",encoding='utf8')

line = memories.read()
if (len(line)>0):
    systemMessage+=f"this is summary of your last chat session \n{line}"  # Handle open memories file in read or overwrite mode
memories.close()
memories = open("memories.txt","a", encoding='utf8')         # Change back mode to overwrite



# print(systemMessage)   #DEBUG---------------------------
model= "gemma4:e2b"  # model used
chat = ChatOllama(
    model=model,
    temperature=1,
    )
template = ChatPromptTemplate.from_messages([
    MessagesPlaceholder(variable_name="convo"),
    MessagesPlaceholder(variable_name="context")
])
messages= [ 
    SystemMessage(content=systemMessage)         # to contain the messages
    ]
memory = [
    
    ]                                    # to contain chat history without system prompt

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

            
# ON EVENT FUNCTION ----------------------------       
@bot.event
async def on_member_join(member):
    await member.send(f"welcome to the server {member.name}")

@bot.event
async def on_message(message):
    if message.content.lower() == "/exit":
        if len(memory)>0:
            memory.append(SystemMessage("you are being shutted down, now summarize this chat for you so you can easily remember this chat session in the next session!. remember important points (names, event, story, name, specific topics), also give your opinion for each member you interacted with so you will remember how to get the conversation going with them, make sure in the next session you remember you have been shutted down before."))
            summary = chat.invoke(memory)  # the summarize is forced to the model the data is raw and not structured.
            print(summary.content)
            memories.write("\n"+str(summary.content)+ f"\nabove is memories created at {message.created_at} -- END OF MEMORY --")
            memories.close()
            await bot.close()
            return
        else:
            memories.close()
            await bot.close()


    if not message.content.startswith(bot.command_prefix):
        if message.author == bot.user:return                              # Do not response the bot message
        
        humanMSG = HumanMessage(content=f"{message.author.display_name}:{message.content}")
        messages.append(humanMSG)     # append user input to the message sent
        memory.append(humanMSG)
        # message.author.username+" say: "+


        # CHAIN 
        chain = template | chat
        result = chain.invoke({"convo":messages,
                               "context":[SystemMessage(f"here is some information you can use: {retriever.invoke(humanMSG.content)}")]
                               }) 

        # # CONVENTIONAL
        # response = chat.invoke(messages) # this should change to chain 

        aiMSG = AIMessage(content=result.content)
        messages.append(aiMSG) # append bot response
        memory.append(aiMSG)
        
        os.system('cls' if os.name == 'nt' else 'clear')   # DEBUG - TO PRINT CONVO !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        print("\n\n\n-----------------CHAT-----------------------\n")
        for i in messages:          
            print(i.content)
        

        await message.channel.send(result.content)   # SEND model reply to discord

        # Crucial line: allows the bot to process other commands
    await bot.process_commands(message)


# ----- ON CALL FUNCTION -----
async def warn(message):
    await message.channel.send(f"dont say that {message.author.mention}")


bot.run(token=token,log_handler=handler,log_level=logging.DEBUG) # RUN BOT


### TO FIX!!! add chain to this bot