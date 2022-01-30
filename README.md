# Setting Up

1. Change `config.yaml` to your own preferences. Fields which are mandatory are commented with #required

2. Create a file with a `.env` extension and fill in the following:
    - TOKEN: Discord Bot token (Mandatory)
    - YOUTUBE_API_KEY: YouTube Data API key, see https://developers.google.com/youtube/v3/getting-started (If this is not provided, the bot will only play audio from valid youtube URLs)
    - DATABASE_URI: postgres connection string (If this is not provided, the Tags extension will not be loaded.)

# Running

Run as a python module (`python -m HK`)

# Adding new features

HK uses discord.py 2.0.0a.
To add your own features, create extensions as shown in https://discordpy.readthedocs.io/en/latest/ext/commands/extensions.html, and add them to the extensions list in config.yaml.

