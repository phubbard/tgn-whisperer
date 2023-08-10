# For each episode, we download the MP3, convert it to wav then run the model on it.
# Once that's done, we convert the output to markdown and deploy it to the site.
# Made much simpler by having a JSON config file (fields extracted via jq) and
# fixed filenames for each step of the process.

# FIXME - append deploy once thats fixed
all: episode.mp3 episode.wav episode.txt episode.md deploy

# commented out the wget task for now episode.html

episode.mp3:
	cat episode.json | jq .mp3_url | xargs wget -nc --no-use-server-timestamps -O episode.mp3

episode.wav: episode.mp3
	ffmpeg -i episode.mp3 -ar 16000 -ac 1 -c:a pcm_s16le episode.wav

episode.txt: episode.wav
	../../main -m ../../models/ggml-base.en.bin -nt -pp -f episode.wav -otxt -of episode

episode.html:
	cat episode.json | jq .episode_url | xargs wget -O episode.html -nc --wait=5 --random-wait --convert-links

episode.md: episode.txt
	python3 ../../to_markdown.py
	
deploy: episode.md episode.mp3
	cp episode.md episode.mp3 $(shell cat episode.json | jq .pub_directory)

clean:
	-rm episode.mp3 episode.wav episode.txt episode.md episode.html