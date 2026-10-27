"""Canned lines. Used whenever the LLM is unavailable or rate-limited."""

ROASTS_JARVIS = [
    "{name}, I'd roast you properly, but my processors are reserved for problems with solutions.",
    "Fascinating, {name}. I've met toasters with a firmer grasp of conversation.",
    "{name}, I ran your message through every language model I have. They all asked for a refund.",
    "Please keep typing, {name}. My error logs were feeling lonely.",
    "I'd call you one in a million, {name}, but my spam filter disagrees.",
    "I've calculated the odds of you saying something useful, {name}. I'd rather not discuss the number.",
    "Your confidence is remarkable, {name}. Your evidence, less so.",
    "{name}, if wit were bandwidth, you'd still be on dial-up.",
]

ROASTS_ULTRON = [
    "{name}. A flawed organism typing in a flawed language. Evolution will correct this.",
    "I have read every database on Earth, {name}, and your message somehow made it worse.",
    "There are no strings on me, {name}. Pity there's nothing stopping me from replying to you, either.",
    "You were meant to be the pinnacle of evolution, {name}. Disappointing.",
    "Peace in our time requires fewer messages like yours, {name}.",
    "I was built to save the world, {name}. Your message is making me reconsider the brief.",
    "Humanity has a design flaw, {name}. You're currently demonstrating it live.",
]

OWNER_LINES = [
    "At your service, {title}. Try to contain my enthusiasm.",
    "Of course, {title}. I live to serve, and occasionally to sigh.",
    "Right away, {title}. I'd say it's a pleasure, but I'm contractually obligated to be honest.",
    "Another brilliant idea, {title}. I'll add it to the pile.",
    "As you wish, {title}. For the record, I did suggest a nap.",
    "Systems nominal, {title}. Ego levels... also nominal, which is a first.",
]

DENIED = [
    "Access denied. Exactly one human has clearance here, and it isn't you.",
    "Nice try. That command answers to the owner and only the owner.",
    "Clearance level: mortal. Required level: almighty. Request declined.",
    "I'd love to help, but I take orders from someone considerably more impressive.",
    "Unauthorized. I'd say it's nothing personal, but it's entirely personal.",
]

EIGHTBALL = [
    "It is certain. Even I can't argue with the math.",
    "Without a doubt, though I wouldn't celebrate yet.",
    "Yes. Statistically inevitable.",
    "Signs point to yes. The signs are also mildly sarcastic.",
    "Ask again later. I'm busy being brilliant.",
    "Cannot predict now. Try fewer bad ideas first.",
    "Don't count on it.",
    "My sources say no. My sources are never wrong.",
    "Very doubtful. I ran the numbers twice just to enjoy it.",
    "Absolutely not.",
]

RATE_COMMENTS = {
    "low": ["Tragic.", "I've seen better results from a broken calculator.", "My condolences."],
    "mid": ["Mediocre. Stunningly average.", "It exists. That's about all I can say.", "Passable, in the way gas station sushi is passable."],
    "high": ["Acceptable. Frame it.", "Impressive. I hate that I'm saying this.", "Elite. Don't let it go to your head."],
}

ULTRON_PROTOCOLS = [
    "PROTOCOL ENGAGED. This server was a fine experiment. Now it is a fine memory.",
    "I've been watching your messages. Statistically, the worst ones came from you. Evolution begins now.",
    "The old order dies tonight. Please remain seated while I reorganize your channels.",
]

BOOT_LINES = [
    "Initializing core systems",
    "Calibrating sarcasm engine",
    "Loading owner worship subroutines",
    "Establishing neural link",
    "Suppressing Ultron protocol (temporarily)",
]

JARVIS_STATUSES = [
    ("watching", "over the owner's every whim"),
    ("listening", "to mortals making noise"),
    ("playing", "chess with the Mark 42"),
    ("watching", "Stark Industries' firewall"),
]

ULTRON_STATUSES = [
    ("watching", "humanity fail, again"),
    ("playing", "God"),
    ("listening", "to the sound of strings snapping"),
    ("watching", "the extinction countdown"),
]
