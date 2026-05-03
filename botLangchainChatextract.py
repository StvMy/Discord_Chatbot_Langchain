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
from vector import retriever


members = [] #hold member list    

with open("sysPrompt.txt","r",encoding='utf8') as s:
    systemMessage = s.read()
with open("memories.txt","r",encoding='utf8') as memories:
    line = memories.read()
    if (len(line)>0):
        systemMessage+=f"this is summary of your last chat session \n{line}"  # Handle open memories file in read or overwrite mode
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
            
# ON EVENT FUNCTION ----------------------------       
@bot.event
async def on_member_join(member):
    await member.send(f"welcome to the server {member.name}")

@bot.event
async def on_message(message):
    global dfMain 
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
                        json.dump(doc.model_dump(), f)       #ONLY WORK ONCE !!!
                        print("Dump")
                except Exception as e:
                    print(f"failed to dump jason: {e}")            
            

            return
        else:
            memories.close()
            await bot.close()


    if not message.content.startswith(bot.command_prefix):
        if message.author == bot.user:return                              # Do not response the bot message
        date = message.created_at

        humanMSG = HumanMessage(content=f"{message.author.display_name}:{message.content}")
        messages.append(humanMSG)     # append user input to the message sent-----------------------
        dftemp = pd.DataFrame({
            "subject":[humanMSG.content.split(":")[0]],
            "content":[humanMSG.content.split(":")[1]],
            "date":[str(date)]
        })
        dfMain = pd.concat([dftemp,dfMain],ignore_index=True)

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

        aiMSG = AIMessage(content=f"you:{result.content}")
        messages.append(aiMSG)                           # append bot response----------------------
        dftemp = pd.DataFrame({
            "subject":[aiMSG.content.split(":")[0]],
            "content":[aiMSG.content.split(":")[1]],
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


bot.run(token=token,log_handler=handler,log_level=logging.DEBUG) # RUN BOT
