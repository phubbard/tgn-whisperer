
# FIXME - append deploy once thats fixed
all: episode.mp3 episode.wav episode.txt episode.md episode.html

episode.mp3: episode.json
	cat episode.json | jq .mp3_url | xargs wget -nc --no-use-server-timestamps -O episode.mp3

episode.wav: episode.mp3
	ffmpeg -i episode.mp3 -ar 16000 -ac 1 -c:a pcm_s16le episode.wav

episode.txt: episode.wav
	../../main -m ../../models/ggml-base.en.bin -nt -pp -f episode.wav -otxt -of episode

episode.html: episode.json
	cat episode.json | jq .episode_url | xargs wget -O episode.html -nc --wait=5 --random-wait --convert-links

episode.md: episode.txt episode.html
	python3 ../../to_markdown.py
	
deploy: episode.md episode.mp3
	# FIXME - see https://www.gnu.org/software/make/manual/html_node/Simple-Assignment.html
	# FIXME - destination directory should be the basename
	-mkdir ../../TheGreyNATO/docs/episodes/$(shell cat episode.json | jq .number)
	cp episode.md ../../TheGreyNATO/docs/episodes/$(shell cat episode.json | jq .number)
	cp episode.mp3 ../../TheGreyNATO/docs/episodes/$(shell cat episode.json | jq .number)
	
clean:
	-rm episode.mp3 episode.wav episode.txt episode.md episode.html