import random
import uuid


def generate_avatar_url(seed=None):
    if seed is None:
        seed = str(uuid.uuid4())

    #random avatars DiceBear
    avatar_styles = [
        "avataaars",
        "bottts",
        "micah",
        "miniavs",
        "personas",
    ]

    style = random.choice(avatar_styles)
    return f"https://api.dicebear.com/7.x/{style}/svg?seed={seed}"

ADJECTIVES = [
    "quick", "silent", "happy", "bright", "dark", "lucky",
    "brave", "cool", "smart", "wild", "blue", "red", "green"
]

NOUNS = [
    "fox", "tiger", "dragon", "wolf", "eagle", "lion",
    "star", "cloud", "stone", "river", "tree", "moon", "sun"
]

def generate_random_name():
    adjective = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)
    number = random.randint(1, 9999)
    return f"{adjective}_{noun}{number}"