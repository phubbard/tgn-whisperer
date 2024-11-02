from pathlib import Path
from unittest import TestCase
from workflow import url_to_file
from prefect import flow
from prefect.testing.utilities import prefect_test_harness
from prefect.logging import disable_run_logger


class Test(TestCase):
    def test_url_to_file(self):
        with disable_run_logger():
            with prefect_test_harness():
                fh = url_to_file.fn('https://www.phfactor.net/tgn/276.0/episode.mp3', Path('/tmp/junk.mp3'))
                assert fh.exists()
                assert fh.stat().st_size > 0
                fh.unlink()
