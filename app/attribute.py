# pfh and brad hyslop 5/18/2024 - use LLM to do speaker attribution. Claude3 has a 200k token window so
# we can do the whole episode in one go. Yay!
# API docs https://pypi.org/project/anthropic/
# Loguru https://www.pythonpapers.com/p/an-intro-to-logging-with-loguru

from collections import defaultdict
import json
import os
import re
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic
from loguru import logger as log
from tenacity import retry, stop_after_attempt


load_dotenv()  # take environment variables from .env.

INPUT_FILE = "junk.json"
SPEAKER_MAPFILE = "speaker-map.json"
SYNOPSIS_FILE = "synopsis.txt"


@log.catch
def check_conditions(input_fn, output_fn, client):
    # exception on fatal errors, False if output file exists
    if not os.path.exists(input_fn):
        log.error(f"Input file {input_fn} does not exist.")
        raise FileNotFoundError
    if os.path.exists(output_fn):
        log.warning(f"Output file {output_fn} already exists.")
        return False
    if not client:
        log.error("Client not initialized. Check API key and network connection.")
        raise ValueError
    return True


# See https://github.com/anthropics/anthropic-cookbook/blob/main/misc/how_to_enable_json_mode.ipynb
def extract_between_tags(tag: str, string: str, strip: bool = False) -> list[str]:
    ext_list = re.findall(f"<{tag}>(.+?)</{tag}>", string, re.DOTALL)
    if strip:
        ext_list = [e.strip() for e in ext_list]
    return ext_list


prompt = '''
The following is a public podcast transcript. Please write a two paragraph synopsis in a <synopsis> tag
and a JSON dictionary mapping speakers to their labels inside an <attribution> tag.
For example, {"SPEAKER_00": "Jason Heaton", "SPEAKER_01": "James"}. 
If you can't determine speaker, put "Unknown".
If for any reason an answer risks reproduction of copyrighted material, explain why.
'''



# Call Claude with the text and return the speaker map.
@retry(stop=(stop_after_attempt(2)))
@log.catch(reraise=True)
def call_claude(client, text: str) -> (defaultdict, str):
    message = client.messages.create(
        max_tokens=1000,
        system=prompt,
        messages=[
            {
                "role": "user",
                "content": text,
            }
        ],
        model="claude-3-5-sonnet-20240620"
        #model="claude-3-sonnet-20240229",
        # model="claude-3-opus-20240229",
    )

    # Log the prompt and output in a file with a timestamp as name.
    terse_timestamp_now = re.sub(r"[^0-9]", "", str(datetime.now()))

    logfile = Path(f"claude_output_{terse_timestamp_now}.txt")
    with open(logfile, "w") as f:
        # get full absolute filename from f
        log.info(f"Output written to {logfile.absolute()}")
        f.write(f"{prompt}\n\n{text}\n\n{message.content[0].text}")

    speaker_map = defaultdict(lambda: "Unknown")
    log.info(f"{message.model=}")
    # Now the tricky bit - pull the dict outta the message, convert to json and then python dict.
    # Also, log enough to debug if/when it fails.
    try:
        inter = extract_between_tags("attribution", message.content[0].text, strip=True)
        speaker_map = json.loads(inter[0])
        log.debug(speaker_map)
    except json.JSONDecodeError as e:
        log.error(f"Error converting LLM output into valid JSON. {e=} {message.content=} {inter=}")
        raise e
    except IndexError as e:
        log.error(f"Error extracting JSON from LLM output. {e=} {message.content[0].text=}")
        raise e

    try:
        syn_innerval = extract_between_tags("synopsis", message.content[0].text, strip=True)
        synopsis = syn_innerval[0]
        log.debug(f"{synopsis=}")
    except IndexError as e:
        log.error(f"Error extracting synopsis from LLM output. {e=} {message.content[0].text=}")
        raise e

    # Sometimes, the LLM misses a name. So use defaultdict to fill in the blanks with a string I can
    # grep for later on that is also understandable to a human.
    rc = defaultdict(lambda: "Unknown")
    for k, v in speaker_map.items():
        rc[k] = v
    return rc, synopsis


def process_episode(directory='.', overwrite=False) -> (dict,str):
    input_filename = Path(directory) / INPUT_FILE
    speaker_filename = Path(directory) / SPEAKER_MAPFILE
    synopsis_filename = Path(directory) / SYNOPSIS_FILE
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    speaker_filename.write_text(' ')
    synopsis_filename.write_text(' ')

    rc = check_conditions(input_filename, speaker_filename, client)
    if rc is False and overwrite is True:
        log.info("Overwriting existing file.")
    if rc is False and overwrite is False:
        log.info("Skipping existing file.")
        return {}, None

    log.info(f"Processing episode in {directory}.")
    text = input_filename.read_text()
    log.info(f"Calling claude with {len(text)} characters.")
    speaker_map, synopsis = call_claude(client, text)
    log.info(f"{len(speaker_map)} speaker(s) found.")
    speaker_filename.write_text(json.dumps(speaker_map))
    log.info(f"Results written to {speaker_filename}.")
    synopsis_filename.write_text(synopsis)

    return speaker_map, synopsis


if __name__ == "__main__":
    dir = "/Users/pfh/code/tgn-whisperer/podcasts/tgn/120.0"
    process_episode(dir, overwrite=True)
