# Kuebiko Cubing

This is currently the active repo for Kuebiko Cubing hosted at https://www.kuebiko-cubing.com. I'm not affiliated with the original creator at all, I just saw it went EOL and the domain was available and decided to host it myself lol

This codebase probably won't get maintained much. I do have a more permanent hosting setup as of 2025/03/09 so the official website should stay online for the foreseeable future.

## development/hosting quickstart with docker

- `cp .env.example .env`
- (edit .env to your liking)
- `docker build -t kuebiko-cubing .`
- `docker run -v ./wca_data:/downloads --name kuebiko-cubing -p 5000:5000 kuebiko-cubing`
- if you want the WCA ID input to work on the homepage, you need to download https://www.worldcubeassociation.org/export/results/WCA_export.tsv.zip and put it in the wca_data folder (with that same filename)

Codebase seems to require specifically Python 3.6 to install requirements and run properly. I added a Dockerfile and .env configuration to make things easier to work with.

You can still run it without Docker, just use Python 3.6 and install the requirements.txt in a virtual environment.

## shoutout to the original creator

Kuebiko Cubing was created by [tussosedan](https://github.com/tussosedan/), props to him for making such a cool project.