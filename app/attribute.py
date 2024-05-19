# pfh and brad hyslop 5/18/2024 - use LLM to do speaker attribution. Claude3 has a 200k token window so
# we can do the whole episode in one go. Yay!

import json
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()  # take environment variables from .env.

INPUT_FILE = "junk.json"
OUTPUT_FILE = "speaker-map.json"


def check_conditions(input_fn, output_fn, client):
    # exception on fatal errors, False if output file exists
    if not os.path.exists(input_fn):
        print(f"Input file {input_fn} does not exist.")
        raise FileNotFoundError
    if os.path.exists(output_fn):
        print(f"Output file {output_fn} already exists.")
        return False
    if not client:
        print("Client not initialized. Check API key and network connection.")
        raise ValueError
    return True


# See https://github.com/anthropics/anthropic-cookbook/blob/main/misc/how_to_enable_json_mode.ipynb
def extract_between_tags(tag: str, string: str, strip: bool = False) -> list[str]:
    ext_list = re.findall(f"<{tag}>(.+?)</{tag}>", string, re.DOTALL)
    if strip:
        ext_list = [e.strip() for e in ext_list]
    return ext_list


def call_claude(client, text: str) -> dict:
    message = client.messages.create(
        max_tokens=1000,
        system="The following is a podcast transcript. Please produce a JSON dictionary mapping speakers to their labels. "
               "For example, {'SPEAKER_00': 'Jason Heaton', 'SPEAKER_01': 'James'}. Put this dictionary in <attribution> tags.",
        messages=[
            {
                "role": "user",
                "content": text,
            }
        ],
        model="claude-3-haiku-20240307",
    )

    # Now the tricky bit - pull the dict outta the message, convert to json and then python dict.
    # Also, log enough to debug if/when it fails.
    try:
        inter = extract_between_tags("attribution", message.content[0].text, strip=True)
        jsd = json.loads(inter[0])
        pprint(jsd)
    except json.JSONDecodeError as e:
        print(f"Error converting LLM output into valid JSON. {e=} {message.content=} {inter=}")
        # Sketchy. Save to a text file for later analysis.
        with open("llm_output.txt", "w") as f:
            f.write(inter)
        raise e

    return jsd


def process_episode(directory='.', overwrite=False, input_fn=INPUT_FILE, output_fn=OUTPUT_FILE):
    input_fn = Path(directory) / input_fn
    output_fn = Path(directory) / output_fn
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    rc = check_conditions(input_fn, output_fn, client)
    if rc is False and overwrite is True:
        print("Overwriting existing file.")
    if rc is False and overwrite is False:
        print("Skipping existing file.")
        return

    print(f"Processing episode in {directory}.")
    text = input_fn.read_text()
    print(f"Calling claude with {len(text)} characters.")
    speaker_map = call_claude(client, text)
    print(f"{len(speaker_map)} speaker(s) found.")
    output_fn.write_text(json.dumps(speaker_map))
    print(f"Results written to {output_fn}.")

    """
    Load the input file as json. This is a list of tuples, each of which is a start time, speaker, and text chunk.
    Stuff the speaker names into a set, check cardinality for sanity checking the results back from Claude.
    Send json.dumps to Claude, get back a json dictionary of speaker names.
    Compare cardinality of the two sets, and if they match, write the results to the output file.
    Save results to speaker-map.json
    Trigger a reprocess of the episode with the new speaker map. 
    """


if __name__ == "__main__":
    dir = "/Users/pfh/code/tgn-whisperer/podcasts/tgn/116.0"
    process_episode(dir, overwrite=False)
