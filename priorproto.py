
import inspect


class Logger:
    def __init__(self): pass

    def log_event(self, message):
        caller = inspect.getframeinfo(inspect.stack()[1][0])
        _, filename = os.path.split(caller.filename)

        print("%s(%d): %s" % (filename, caller.lineno, message))


log = Logger()


def needType(obj, neededType, doc_IGNORED=None):
    """Assert that the named object is exactly of the type specified."""
    if not isinstance(obj, neededType):
        raise Exception(f"WRONG TYPE.  Needed:{neededType.__name__} but saw {obj.__class__.__name__}")
    return obj


class Podcast:
    def __init__(self, abbreviation, full_name, rss_url):
        self.PODCAST_ABBREVIATION = needType(abbreviation, str)
        self.PODCAST_FULL_NAME    = needType(full_name, str)
        self.PODCAST_RSS_URL      = needType(rss_url, str)


class EpisodeIdentity:
    def __init__(self, unique):
        self.EPID_UNIQUE = needType(unique, str)


class Act:
    def __init__(self, engine, *priors):
        for prior in priors:
            if not isinstance(prior, Act): raise Exception("NOPE! NOT AN ACT")
        self.ACT_PRIORS = priors

    def act_fulfill(self): raise Exception("Must override")


class Engine:
    def __init__(self, cache_directory):
        self.ENGINE_CACHE = cache_directory

        self.__readyActs   = []
        self.__blockedActs = []

    def specify_podcast(self, abbreviation, full_name, podcast_rss_url):
        pass

    def specify_episode_identity(self, rss, episode_name):
        pass

    def specify_html(self, url, episode_identity):
        pass

    def specify_mp3(self, mp3_url, episode_identity):
        pass

    def specify_transcript(self, episode_identity):
        pass

    def specify_stt(self, mp3_url):
        pass

    def specify_attribution(self, stt):
        pass

    def specify_epmd(self, episode_identity, mp3, attribution, *htmls):
        pass

    def specify_mkdocs(self, rss, *epmds):
        pass


class Resource(Act):
    def __init__(self, url, category, moniker):
        pass


