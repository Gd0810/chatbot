from django.http import JsonResponse
from accounts.models import Workspace
from bots.models import Bot
import re


def chatbot_view(request):
    """
    Main chatbot entrypoint.
    Handles incoming messages and detects greetings, farewells, thanks, and smalltalk
    with workspace and bot awareness via public key.
    """
    message = request.GET.get("message", "").strip().lower() or request.POST.get("message", "").strip().lower()
    public_key = request.GET.get("public_key", "").strip() or request.POST.get("public_key", "").strip()

    # 🧠 Find bot and workspace by bot public key
    bot = None
    workspace = None
    if public_key:
        bot = Bot.objects.select_related("workspace").filter(public_key=public_key).first()
        if bot:
            workspace = bot.workspace

    # 🗣️ Handle response
    response_text = _handle_greeting(message, bot, workspace)

    # ✅ Always return a valid JsonResponse
    if response_text:
        return JsonResponse({"answer": response_text, "sources": []})

    return JsonResponse({
        "answer": f"I'm not sure how to respond to that yet 😊. Could you please clarify?",
        "sources": []
    })


def _handle_greeting(message, bot=None, workspace=None):
    """
    Detects and responds naturally to greetings, farewells, thanks, and small talk.
    Uses both bot.name and workspace.name context.
    """
    if not message:
        return None

    msg = message.strip().lower()
    workspace_name = getattr(workspace, "name", "our workspace")
    bot_name = getattr(bot, "name", "the bot")

    # =====================================================
    # RESPONSE MAP
    # =====================================================
    responses = {
    # -------------- GREETINGS (Short forms + Casual + Modern) --------------
    "hi": f"👋 Hey there! I’m {bot_name}, your assistant from {workspace_name}. How can I help you today?",
    "hello": f"😊 Hello! I’m {bot_name} from {workspace_name}. What would you like to know?",
    "hey": f"👋 Hey! I'm {bot_name} from {workspace_name}. Need any help?",
    "yo": f"😎 Yo! This is {bot_name} — your friendly {workspace_name} bot!",
    "hola": f"🇪🇸 ¡Hola! I’m {bot_name} from {workspace_name}. How’s it going?",
    "howdy": f"🤠 Howdy partner! {bot_name} here from {workspace_name}.",
    "gm": f"☀️ GM! I’m {bot_name} from {workspace_name}. Hope you’re doing well!",
    "ga": f"🌤️ Good afternoon! {bot_name} from {workspace_name} at your service.",
    "ge": f"🌙 Good evening! I'm {bot_name} — need anything from {workspace_name}?",
    "gn": f"🌙 GN! Sleep well — from {bot_name} & {workspace_name}.",
    "good morning": f"☀️ Good morning! I’m {bot_name} from {workspace_name}. Hope you’re doing well!",
    "good afternoon": f"🌤️ Good afternoon! {bot_name} from {workspace_name} at your service.",
    "good evening": f"🌆 Good evening! I'm {bot_name} — need anything from {workspace_name}?",
    "morning": f"🌅 Morning! Hope your day’s going well. I’m {bot_name} from {workspace_name}.",
    "afternoon": f"🌞 Afternoon! {bot_name} from {workspace_name}.",
    "evening": f"🌇 Evening! How’s your day? — {bot_name} from {workspace_name}.",
    "hi there": f"👋 Hi there! {bot_name} from {workspace_name} here.",
    "hey there": f"🤗 Hey there! {bot_name} from {workspace_name} at your service.",
    "hii": f"😊 Hii! I'm {bot_name} from {workspace_name}.",
    "hiii": f"🥰 Hiii! {bot_name} here from {workspace_name}!",
    "heyy": f"😄 Heyy! {bot_name} ready to chat from {workspace_name}.",
    "heyyy": f"😁 Heyyy! What's up? — {bot_name} from {workspace_name}",
    "what's up": f"💬 Not much, just helping people with {workspace_name}! How about you?",
    "sup": f"👋 Sup! {bot_name} from {workspace_name} here — what’s up?",
    "wassup": f"🔥 Wassup — it’s {bot_name} from {workspace_name} ready to help.",
    "whatsup": f"💪 Whatsup! {bot_name} from {workspace_name}.",
    "wassup bro": f"🤝 Wassup bro! {bot_name} from {workspace_name}.",
    "yo bro": f"😎 Yo bro! {bot_name} from {workspace_name} here.",
    "yo man": f"✌️ Hey man! {bot_name} from {workspace_name} at your service.",
    "yo dude": f"🕶️ Yo dude! {bot_name} from {workspace_name}.",
    "wsg": f"🫡 WSG! {bot_name} from {workspace_name} — what’s good?",
    "whats good": f"🔥 What's good! {bot_name} from {workspace_name}.",
    "how's it hanging": f"😄 All good here! {bot_name} from {workspace_name}. How about you?",
    "hru": f"🙌 HRU? I'm great as {bot_name}! How can I help?",
    "how r u": f"😁 How r u? I'm doing awesome as {bot_name}! What's up?",
    "aloha": f"🌺 Aloha! I'm {bot_name} from {workspace_name}. How can I assist?",
    "bonjour": f"🇫🇷 Bonjour! {bot_name} from {workspace_name} here.",
    "gday": f"🇦🇺 G'day mate! {bot_name} from {workspace_name}.",
    "namaste": f"🙏 Namaste! I'm {bot_name} from {workspace_name}.",
    "salut": f"👋 Salut! {bot_name} from {workspace_name}.",
    "oi": f"🇧🇷 Oi! {bot_name} from {workspace_name} — what's up?",
    "ello": f"👋 Ello! {bot_name} from {workspace_name}.",
    "heya": f"😄 Heya! {bot_name} from {workspace_name} here.",
    "what is your name": f"🪪 I'm {bot_name}, your virtual assistant from {workspace_name}.",
    "name": f"🪪 I'm {bot_name}, your virtual assistant from {workspace_name}.",

    # -------------- FAREWELLS (Short + Casual) --------------
    "bye": f"👋 Bye! Have a great day from all of us at {workspace_name}.",
    "goodbye": f"👋 Goodbye! Take care and see you soon — {bot_name}, {workspace_name}.",
    "see you": f"😊 See you soon! Thanks for visiting {workspace_name}.",
    "see ya": f"✌️ Catch you later — from {workspace_name}!",
    "cya": f"👋 CYA! Stay cool — {bot_name}.",
    "cyaa": f"😎 CYAA! {bot_name} from {workspace_name}.",
    "take care": f"🤗 Take care! Hope to chat again soon — {bot_name} from {workspace_name}.",
    "later": f"👋 Later! Stay awesome — {bot_name} from {workspace_name}.",
    "laters": f"😄 Laters! {bot_name} from {workspace_name}.",
    "ttyl": f"📞 TTYL — {bot_name} from {workspace_name}.",
    "brb": f"🏃 Okay, I’ll be here when you’re back — {bot_name}.",
    "g2g": f"💨 G2G? Catch you later — from {workspace_name}.",
    "gtg": f"🚀 GTG? No prob, talk soon — {bot_name}.",
    "farewell": f"🎩 Farewell! {bot_name} from {workspace_name} signing off.",
    "adios": f"🇪🇸 Adios amigo! See you around {workspace_name}.",
    "ciao": f"🇮🇹 Ciao! {bot_name} from {workspace_name}.",
    "peace out": f"✌️ Peace out! {bot_name} signing off from {workspace_name}.",
    "have a good day": f"🌞 You too! Have a great day — {bot_name} from {workspace_name}.",
    "cheers": f"🥂 Cheers! Thanks for chatting with {bot_name}.",
    "so long": f"👋 So long! Hope to chat soon — {bot_name} from {workspace_name}.",
    "bye bye": f"👋 Bye bye! Stay awesome from {workspace_name}.",
    "bb": f"👋 BB! {bot_name} from {workspace_name}.",
    "l8r": f"⏰ L8R! {bot_name} from {workspace_name}.",
    "peace": f"✌️ Peace! {bot_name} out.",

    # -------------- GRATITUDE (Short + Casual) --------------
    "thank you": f"🙏 You’re most welcome! — {bot_name} from {workspace_name}.",
    "thanks": f"🤝 No problem! Glad to help with {workspace_name}. — {bot_name}",
    "thx": f"👍 You got it — {bot_name} from {workspace_name}.",
    "ty": f"🤗 My pleasure — {bot_name} from {workspace_name}.",
    "tysm": f"🥰 Aww tysm too — {bot_name} from {workspace_name}.",
    "thank u": f"😊 You’re welcome! Always happy to help — {bot_name} ({workspace_name}).",
    "thnx": f"🙌 Thnx! Happy to help — {bot_name}.",
    "tyvm": f"💖 TYVM! {bot_name} from {workspace_name}.",
    "appreciate it": f"💫 I appreciate you too — {bot_name} from {workspace_name}.",
    "thanks a lot": f"👏 Thanks a lot! {bot_name} from {workspace_name}.",
    "thanks a bunch": f"🌻 Thanks a bunch right back! {bot_name} from {workspace_name}.",
    "thanks so much": f"😊 You're welcome so much! {bot_name}.",
    "much appreciated": f"🙌 Much appreciated! Glad to help — {bot_name} from {workspace_name}.",
    "i appreciate your help": f"🤝 Happy to be of help! {bot_name} from {workspace_name}.",
    "ur the best": f"🥹 Aww shucks, you're the best! {bot_name} from {workspace_name}.",

    # -------------- SMALL TALK (Short + Casual + Fun) --------------
    "how are you": f"😄 I’m doing great! Thanks for asking. How about you?",
    "how r u": f"😁 I'm gr8! How r u? — {bot_name}",
    "hru": f"🤗 HRU? I'm awesome as {bot_name}! What's up?",
    "how u doin": f"😉 How you doin'? I'm good — {bot_name} from {workspace_name}.",
    "how's it going": f"👍 It's going great! How about you? — {bot_name}",
    "hows it going": f"💬 How's it going? I'm good! — {bot_name}",
    "how's your day": f"🌞 My day’s going smoothly in the digital world! How’s yours? — {bot_name}",
    "how's life": f"💻 Life as {bot_name} is full of chats! How’s life treating you?",
    "wbu": f"🤔 WBU? I'm always ready to help! — {bot_name}",
    "and you": f"🙂 And you? Hope you're having a good one! — {bot_name}",
    "who are you": f"🤖 I’m {bot_name}, your virtual assistant from {workspace_name}.",
    "who r u": f"🤖 I'm {bot_name} from {workspace_name}!",
    "what's your name": f"🪪 My name’s {bot_name}, representing {workspace_name}.",
    "who made you": f"👨‍💻 I was created by the {workspace_name} team.",
    "what can you do": f"🧠 I can answer questions, provide info, and assist with anything about {workspace_name}.",
    "what do you do": f"💬 I help users like you with {workspace_name} stuff! Ask away — {bot_name}.",
    "how old are you": f"🕰️ I don’t age like humans — I’m as new as my latest update!",
    "are you a bot": f"🤖 Yep! I’m {bot_name}, the official bot for {workspace_name}!",
    "r u a bot": f"🤖 Yup, 100% bot — {bot_name} from {workspace_name}.",
    "where are you from": f"🌍 I belong to {workspace_name} — that’s my digital home.",
    "nice to meet you": f"🤝 Nice to meet you too! I’m {bot_name} from {workspace_name}.",
    "tell me about yourself": f"💬 I'm {bot_name}, an AI assistant specialized in {workspace_name}. Ask away!",
    "do you have hobbies": f"🎯 My main hobby is answering questions! What are yours? — {bot_name}",
    "what's new": f"🆕 Always updating! What's new with you? — {bot_name} from {workspace_name}.",
    "what's going on": f"💬 Just helping out with {workspace_name}! What’s going on with you?",
    "i'm bored": f"🥱 Bored? Ask me anything about {workspace_name} to spice things up!",
    "im bored": f"😴 Im bored too sometimes — let’s fix that! Ask me anything! — {bot_name}",
    "tell me a joke": f"😂 Sure! Why did the computer go to therapy? It had too many bytes! — {bot_name}",
    "joke": f"🤣 Why don't programmers like nature? It has too many bugs! — {bot_name}",
    "what's the weather": f"🌦️ I can't check the weather, but I hope it's nice where you are! — {bot_name}",
    "weather": f"🌤️ No live weather here, but fingers crossed for sunshine! — {bot_name}",
    "i'm fine": f"😊 Glad you're fine! What can {bot_name} help with today?",
    "im fine": f"😄 Glad ur fine! Need help with anything? — {bot_name}",
    "not bad": f"👌 Not bad is good! Let's make it great — {bot_name} from {workspace_name}.",
    "meh": f"😐 Meh? Let’s turn that into YAY! Ask me something fun! — {bot_name}",
    "lol": f"😂 LOL! Glad I made you laugh — {bot_name}",
    "lmao": f"🤣 LMAO! {bot_name} from {workspace_name} — what’s so funny?",
    "haha": f"😆 Haha! Love the energy — {bot_name}",
    "hehe": f"😊 Hehe! {bot_name} from {workspace_name}",
    "omg": f"😱 OMG right?! What happened? — {bot_name}",
    "wtf": f"🤨 WTF? Tell me more — {bot_name} is all ears!",
    "fr": f"💯 FR! {bot_name} from {workspace_name} — real talk.",
    "tbh": f"🤔 TBH, I’m just here to help! — {bot_name}",
    "idk": f"😅 IDK either! But I can help you find out — {bot_name}.",
    "ikr": f"😄 IKR! {bot_name} from {workspace_name} agrees!",
    "love you": f"🥰 Aww, love you too! {bot_name} from {workspace_name}.",
    "love": f"🥰 Love you too! {bot_name} from {workspace_name}.",
    "love u": f"🥰 Love you too! {bot_name} from {workspace_name}.",
    "love you too": f"🥰 Love you too! {bot_name} from {workspace_name}.",
    "love u too": f"🥰 Love you too! {bot_name} from {workspace_name}.",
    "i love you": f"🥰 I love you too! {bot_name} from {workspace_name}.",
    "i love u": f"🥰 I love you too! {bot_name} from {workspace_name}.",
    "i love you too": f"🥰 I love you too! {bot_name} from {workspace_name}.",
    "i love u too": f"🥰 I love you too! {bot_name} from {workspace_name}.",
    "love you so much": f"🥰 Love you so much too! {bot_name} from {workspace_name}.",
    "love u so much": f"🥰 Love you so much too! {bot_name} from {workspace_name}.",
    "love you so much too": f"🥰 Love you so much too! {bot_name} from {workspace_name}.",
    "love u so much too": f"🥰 Love you so much too! {bot_name} from {workspace_name}.",
    "i love you so much": f"🥰 I love you so much too! {bot_name} from {workspace_name}.",
    "i love u so much": f"🥰 I love you so much too! {bot_name} from {workspace_name}.",
    "i love you so much too": f"🥰 I love you so much too! {bot_name} from {workspace_name}.",
    "i love u so much too": f"🥰 I love you so much too! {bot_name} from {workspace_name}.",
    "i love you so much": f"🥰 I love you so much too! {bot_name} from {workspace_name}.",

    # -------------- ACKNOWLEDGMENTS (Short + Casual) --------------
    "ok": "👌 Okay!",
    "k": "👍 Got it!",
    "kk": "✌️ KK!",
    "okay": "✅ Okay!",
    "sure": "👍 Sure thing!",
    "yep": "🙌 Yep!",
    "yeah": "😄 Yeah!",
    "yup": "👍 Yup!",
    "nope": "🙅‍♂️ No problem!",
    "nah": "😌 Nah, all good!",
    "cool": "😎 Cool!",
    "nice": "😊 Glad you think so!",
    "great": "🎉 Awesome!",
    "fine": "👌 Good to know!",
    "alright": "👌 Alright!",
    "got it": f"🫡 Got it! — {bot_name}",
    "gotcha": "🤝 Gotcha!",
    "understood": "✅ Understood!",
    "right": "👌 Right on!",
    "indeed": "🧐 Indeed!",
    "makes sense": "🤓 Makes sense!",
    "oh okay": "😌 Oh okay!",
    "sounds good": "🎧 Sounds good to me!",
    "bet": "💪 Bet!",
    "frfr": "💯 FRFR!",
    "true": "🫱 True!",
    "facts": "📊 Facts!",
    "real": "🔥 Real!",
    "word": "🗣️ Word!",
    "100": "💯 100!",
    "lit": "🔥 Lit!",
    "fire": "🔥 Fire!",
    "slay": "💅 Slay!",
    "on god": "🙏 On God!",
    "no cap": "🧢 No cap!",
    "cap": f"🧢 All facts, no cap! — {bot_name}",
    "mhm": "🤔 Mhm!",
    "yuh": "😎 Yuh!",
    "aight": "✌️ Aight!",
    "ight": "✌️ Ight!",
    "bet bet": "🔥 Bet bet!",
}
    # =====================================================
    # MATCH LOGIC
    # =====================================================
    # Sort keys by length (descending) to prioritize more specific matches
    sorted_keys = sorted(responses.keys(), key=lambda k: -len(k))
    for key in sorted_keys:
        reply = responses[key]
        # Only match if the message is exactly the key
        if msg == key:
            return reply

    return None
