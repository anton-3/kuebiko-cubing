# Kuebiko Cubing

This is currently the active repo for Kuebiko Cubing hosted at https://www.kuebiko-cubing.com. I'm not affiliated with the original creator at all, I just saw it went EOL and the domain was available and decided to host it myself lol

This codebase probably won't get maintained much. I do have a more permanent hosting setup as of 2025/03/09 so the official website should stay online for the foreseeable future.

## development/hosting quickstart

project SHOULD work on python 3.10+, does NOT support 3.9 or older

- `cp .env.example .env`
- (edit .env to your liking)

without docker:

- `python3 -m venv .venv`
- `source .venv/bin/activate`
- `pip install -r requirements.txt`
- `python app.py`

with docker:

- `docker compose up --build`

- if you want the WCA ID input to work on the homepage, you need to download https://www.worldcubeassociation.org/export/results/WCA_export.tsv.zip and put it in the wca_data folder (with that same filename)
  - I wrote a script `scripts/update_wca_data.py` that automatically polls WCA for new data exports and downloads them into the `wca_data` folder. If you're hosting, you can set this up with a cronjob
  - e.g. daily `0 0 * * * python3 <repo path>/scripts/update_wca_data.py`

## shoutout to the original creator

Kuebiko Cubing was created by [tussosedan](https://github.com/tussosedan/), props to him for making such a cool project.