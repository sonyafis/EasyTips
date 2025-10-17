import random
import uuid

ADJECTIVES = [
    "quick", "silent", "happy", "bright", "dark", "lucky",
    "brave", "cool", "smart", "wild", "blue", "red", "green"
]

NOUNS = [
    "fox", "tiger", "dragon", "wolf", "eagle", "lion",
    "star", "cloud", "stone", "river", "tree", "moon", "sun"
]


def generate_avatar_url(seed=None, style_type="fun", **kwargs):
    if seed is None:
        seed = str(uuid.uuid4())

    base_configs = {
        "fun": {
            "styles": ["bottts", "micah", "miniavs"],
            "params": {"mood": "happy", "smile": "true"}
        },
        "normal": {
            "styles": ["personas", "identicon", "initials"],
            "params": {"mood": "neutral"}
        },
        "professional": {
            "styles": ["personas", "initials"],
            "params": {"backgroundColor": "f0f0f0"}
        }
    }

    config = base_configs.get(style_type, base_configs["normal"])
    style = random.choice(config["styles"])

    base_url = f"https://api.dicebear.com/7.x/{style}/svg?seed={seed}"

    for key, value in config["params"].items():
        base_url += f"&{key}={value}"

    for key, value in kwargs.items():
        base_url += f"&{key}={value}"

    return base_url


def generate_random_name():
    adjective = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)
    number = random.randint(1, 9999)
    return f"{adjective}_{noun}{number}"