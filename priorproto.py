
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


def safeInsert(key, value, dictish):
    """If and only if the key is not present, insert it."""
    if key in dictish:
        existing = dictish[key]
        raise Exception(f"Cannot supplant at {str(key)=} ...\n  EXISTING {str(existing)} \n  NEW      {str(value)}")
    dictish[key] = value
    return value



class Podcast:
    def __init__(self, abbreviation, full_name, rss_url):
        self.PODCAST_ABBREVIATION = needType(abbreviation, str)
        self.PODCAST_FULL_NAME    = needType(full_name, str)
        self.PODCAST_RSS_URL      = needType(rss_url, str)

        self.__uniqueEpisodeName = {}
        self.__episodeIdentities = {}

    def make_episode_identity(self, episode_name):
        rv = EpisodeIdentity(self, episode_name)
        safeInsert(rv.EPID_UNIQUE, rv, self.__uniqueEpisodeName)
        safeInsert(rv, rv, self.__episodeIdentities)
        return rv


class EpisodeIdentity:
    def __init__(self, podcast, unique):
        self.EPID_PODCAST = needType(podcast, Podcast)
        self.EPID_UNIQUE  = needType(unique, str)


class Act:
    def __init__(self, engine, *priors):
        self.ACT_ENGINE = needType(engine, Engine)
        self.ACT_PRIORS = tuple(needType(prior, Act) for prior in priors)
        raise Exception("MUST REGISTER SELF WITH ENGINE.  Here?  Just outside initializer?")

    def act_fulfill(self): raise Exception("Must override")


class Engine:
    def __init__(self, cache_directory):
        self.ENGINE_CACHE = cache_directory

        self.__podcasts             = {}
        self.__uniquePodcastAbbrevs = {}
        self.__uniquePodcastName    = {}

        self.__readyActs   = []
        self.__blockedActs = []

    def make_podcast(self, abbreviation, full_name, rss_url):
        rv = Podcast(abbreviation,full_name,rss_url)
        safeInsert(rv,                      rv, self.__podcasts)
        safeInsert(rv.PODCAST_ABBREVIATION, rv, self.__uniquePodcastAbbrevs)
        safeInsert(rv.PODCAST_FULL_NAME,    rv, self.__uniquePodcastName)
        return rv

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

    def specify_episode_markdown(self, episode_identity, mp3, attribution, *htmls):
        pass

    def specify_mkdocs(self, rss, *episode_markdowns):
        pass


class Resource(Act):
    def __init__(self, engine, url, category, moniker):
        super().__init__(engine)

    def get_bytes(self) async:
        raise Exception("CHECK FOR MISSING PRIOR ACTS?  Hmm, no")
        pass


