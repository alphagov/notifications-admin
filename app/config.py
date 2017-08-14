import os
from datetime import timedelta


if os.environ.get('VCAP_SERVICES'):
    # on cloudfoundry, config is a json blob in VCAP_SERVICES - unpack it, and populate
    # standard environment variables from it
    from app.cloudfoundry_config import extract_cloudfoundry_config
    extract_cloudfoundry_config()


class Config(object):
    ADMIN_CLIENT_SECRET = os.environ['ADMIN_CLIENT_SECRET']
    API_HOST_NAME = os.environ['API_HOST_NAME']
    SECRET_KEY = os.environ['SECRET_KEY']
    DANGEROUS_SALT = os.environ['DANGEROUS_SALT']
    DESKPRO_API_HOST = os.environ['DESKPRO_API_HOST']
    DESKPRO_API_KEY = os.environ['DESKPRO_API_KEY']

    # if we're not on cloudfoundry, we can get to this app from localhost. but on cloudfoundry its different
    ADMIN_BASE_URL = os.environ.get('ADMIN_BASE_URL', 'http://localhost:6012')

    TEMPLATE_PREVIEW_API_HOST = os.environ.get('TEMPLATE_PREVIEW_API_HOST', 'http://localhost:6013')
    TEMPLATE_PREVIEW_API_KEY = os.environ.get('TEMPLATE_PREVIEW_API_KEY', 'my-secret-key')

    # Hosted graphite statsd prefix
    STATSD_PREFIX = os.getenv('STATSD_PREFIX')

    # Logging
    DEBUG = False
    LOGGING_STDOUT_JSON = os.getenv('LOGGING_STDOUT_JSON') == '1'

    DESKPRO_DEPT_ID = 5
    DESKPRO_ASSIGNED_AGENT_TEAM_ID = 5

    ADMIN_CLIENT_USER_NAME = 'notify-admin'
    ASSETS_DEBUG = False
    AWS_REGION = 'eu-west-1'
    DEFAULT_SERVICE_LIMIT = 50
    EMAIL_EXPIRY_SECONDS = 3600 * 24 * 7  # one week
    HEADER_COLOUR = '#FFBF47'  # $yellow
    HTTP_PROTOCOL = 'http'
    MAX_FAILED_LOGIN_COUNT = 10
    NOTIFY_APP_NAME = 'admin'
    NOTIFY_LOG_LEVEL = 'DEBUG'
    NOTIFY_LOG_PATH = '/var/log/notify/application.log'
    PERMANENT_SESSION_LIFETIME = 20 * 60 * 60  # 20 hours
    SEND_FILE_MAX_AGE_DEFAULT = 365 * 24 * 60 * 60  # 1 year
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_NAME = 'notify_admin_session'
    SESSION_COOKIE_SECURE = True
    SESSION_REFRESH_EACH_REQUEST = True
    SHOW_STYLEGUIDE = True
    # TODO: move to utils
    SMS_CHAR_COUNT_LIMIT = 459
    TOKEN_MAX_AGE_SECONDS = 3600
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    CSV_UPLOAD_BUCKET_NAME = 'local-notifications-csv-upload'
    DESKPRO_PERSON_EMAIL = 'donotreply@notifications.service.gov.uk'
    ACTIVITY_STATS_LIMIT_DAYS = 7
    TEST_MESSAGE_FILENAME = 'Report'

    STATSD_ENABLED = False
    STATSD_HOST = "statsd.hostedgraphite.com"
    STATSD_PORT = 8125
    NOTIFY_ENVIRONMENT = 'development'

    manually_added_domains = [
        r"gov\.uk",
        r"mod\.uk",
        r"mil\.uk",
        r"ddc-mod\.org",
        r"slc\.co\.uk",
        r"gov\.scot",
        r"parliament\.uk",
        r"nhs\.uk",
        r"nhs\.net",
        r"police\.uk",
        r"dclgdatamart\.co\.uk",
        r"ucds\.email",
        r"naturalengland\.org\.uk",
        r"hmcts\.net",
        r"scotent\.co\.uk",
        r"assembly\.wales",
        r"cjsm\.net",
        r"cqc\.org\.uk",
        r"bl\.uk",
        r"stfc\.ac\.uk",
    ]

    # See https://gist.github.com/quis/9c2625225b7e381da2b0d523ae54b3b7
    # for how to generate a new list
    domains_scraped_from_gov_uk = [
        r"acas\.org\.uk",
        r"ahdb\.org\.uk",
        r"ahrc\.ac\.uk",
        r"arb\.org\.uk",
        r"artscouncil\.org\.uk",
        r"bankofengland\.co\.uk",
        r"bbc\.co\.uk",
        r"bbsrc\.ac\.uk",
        r"bfi\.org\.uk",
        r"biglotteryfund\.org\.uk",
        r"bl\.uk",
        r"boundarycommission\.org\.uk",
        r"british-business-bank\.co\.uk",
        r"britishcouncil\.org",
        r"britishmuseum\.org",
        r"caa\.co\.uk",
        r"careerswales\.com",
        r"catribunal\.org\.uk",
        r"ccwater\.org\.uk",
        r"channel4\.com",
        r"chevening\.org",
        r"citb\.co\.uk",
        r"comisiynyddygymraeg\.org",
        r"cqc\.org\.uk",
        r"dpecgb\.co\.uk",
        r"dsfc\.ac\.uk",
        r"dsma\.uk",
        r"ebbsfleetdc\.org\.uk",
        r"ecitb\.org\.uk",
        r"eis2win\.co\.uk",
        r"electoralcommission\.org\.uk",
        r"epsrc\.ac\.uk",
        r"equalityhumanrights\.com",
        r"esrc\.ac\.uk",
        r"fca\.org\.uk",
        r"finds\.org\.uk",
        r"fireservicecollege\.ac\.uk",
        r"fleetairarm\.com",
        r"gbcc\.org\.uk",
        r"geffrye-museum\.org\.uk",
        r"gov\.scot",
        r"greeninvestmentbank\.com",
        r"hblb\.org\.uk",
        r"hefce\.ac\.uk",
        r"hesa\.ac\.uk",
        r"historicengland\.org\.uk",
        r"hlf\.org\.uk",
        r"horniman\.ac\.uk",
        r"housing-ombudsman\.org\.uk",
        r"hrp\.org\.uk",
        r"ico\.org\.uk",
        r"icrev\.org\.uk",
        r"imb\.org\.uk",
        r"intelligencecommissioner\.com",
        r"iocco-uk\.info",
        r"ipt-uk\.com",
        r"iraqinquiry\.org\.uk",
        r"iwm\.org\.uk",
        r"kew\.org",
        r"lcrhq\.co\.uk",
        r"lease-advice\.org",
        r"legalombudsman\.org\.uk",
        r"legalservicesboard\.org\.uk",
        r"lgo\.org\.uk",
        r"liverpoolmuseums\.org\.uk",
        r"marshallscholarship\.org",
        r"mrc\.ac\.uk",
        r"nam\.ac\.uk",
        r"nationalforest\.org",
        r"nationalgallery\.org\.uk",
        r"nerc\.ac\.uk",
        r"nestpensions\.org\.uk",
        r"newcoventgardenmarket\.com",
        r"nhm\.ac\.uk",
        r"nhmf\.org\.uk",
        r"nhsla\.com",
        r"nic\.org\.uk",
        r"nice\.org\.uk",
        r"nihrc\.org",
        r"nipolicingboard\.org\.uk",
        r"nlb\.org\.uk",
        r"nmrn\.org\.uk",
        r"northumberlandnationalpark\.org\.uk",
        r"northyorkmoors\.org\.uk",
        r"npg\.org\.uk",
        r"nsandi\.com",
        r"ofcom\.org\.uk",
        r"offa\.org\.uk",
        r"ogauthority\.co\.uk",
        r"ombudsman\.org\.uk",
        r"onr\.org\.uk",
        r"ordnancesurvey\.co\.uk",
        r"paradescommission\.org",
        r"pbni\.org\.uk",
        r"pensionprotectionfund\.org\.uk",
        r"pensions-ombudsman\.org\.uk",
        r"pensionsadvisoryservice\.org\.uk",
        r"pharmacopoeia\.com",
        r"portonbiopharma\.com",
        r"ppfo\.org\.uk",
        r"professionalstandards\.org\.uk",
        r"psr\.org\.uk",
        r"qeiicc\.co\.uk",
        r"rafmuseum\.org\.uk",
        r"registrarofconsultantlobbyists\.org\.uk",
        r"rmg\.co\.uk",
        r"royalarmouries\.org",
        r"royalmarinesmuseum\.co\.uk",
        r"royalmint\.com",
        r"royalparks\.org\.uk",
        r"rssb\.co\.uk",
        r"s4c\.co\.uk",
        r"safetyatsportsgrounds\.org\.uk",
        r"sciencemuseum\.org\.uk",
        r"seafish\.org",
        r"sentencingcouncil\.org\.uk",
        r"servicecomplaintsombudsman\.org\.uk",
        r"slc\.co\.uk",
        r"soane\.org",
        r"sportengland\.org",
        r"stfc\.ac\.uk",
        r"submarine-museum\.co\.uk",
        r"supremecourt\.uk",
        r"tate\.org\.uk",
        r"theatrestrust\.org\.uk",
        r"theccc\.org\.uk",
        r"thecrownestate\.co\.uk",
        r"theipsa\.org\.uk",
        r"transportfocus\.org\.uk",
        r"trinityhouse\.co\.uk",
        r"ukad\.org\.uk",
        r"ukri\.org",
        r"vam\.ac\.uk",
        r"victimscommissioner\.org\.uk",
        r"visitbritain\.org",
        r"visitengland\.com",
        r"wallacecollection\.org",
        r"wfd\.org",
        r"wiltonpark\.org\.uk",
        r"yorkshiredales\.org\.uk",
    ]

    EMAIL_DOMAIN_REGEXES = set(
        manually_added_domains + domains_scraped_from_gov_uk
    )

    LOGO_UPLOAD_BUCKET_NAME = 'public-logos-local'


class Development(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    SESSION_PROTECTION = None
    STATSD_ENABLED = False
    CSV_UPLOAD_BUCKET_NAME = 'development-notifications-csv-upload'
    LOGO_UPLOAD_BUCKET_NAME = 'public-logos-tools'


class Test(Development):
    DEBUG = True
    TESTING = True
    STATSD_ENABLED = True
    WTF_CSRF_ENABLED = False
    CSV_UPLOAD_BUCKET_NAME = 'test-notifications-csv-upload'
    LOGO_UPLOAD_BUCKET_NAME = 'public-logos-test'
    NOTIFY_ENVIRONMENT = 'test'
    TEMPLATE_PREVIEW_API_HOST = 'http://localhost:9999'


class Preview(Config):
    HTTP_PROTOCOL = 'https'
    HEADER_COLOUR = '#F499BE'  # $baby-pink
    STATSD_ENABLED = True
    CSV_UPLOAD_BUCKET_NAME = 'preview-notifications-csv-upload'
    LOGO_UPLOAD_BUCKET_NAME = 'public-logos-preview'
    NOTIFY_ENVIRONMENT = 'preview'


class Staging(Config):
    SHOW_STYLEGUIDE = False
    HTTP_PROTOCOL = 'https'
    HEADER_COLOUR = '#6F72AF'  # $mauve
    STATSD_ENABLED = True
    CSV_UPLOAD_BUCKET_NAME = 'staging-notify-csv-upload'
    LOGO_UPLOAD_BUCKET_NAME = 'public-logos-staging'
    NOTIFY_ENVIRONMENT = 'staging'


class Live(Config):
    SHOW_STYLEGUIDE = False
    HEADER_COLOUR = '#005EA5'  # $govuk-blue
    HTTP_PROTOCOL = 'https'
    STATSD_ENABLED = True
    CSV_UPLOAD_BUCKET_NAME = 'live-notifications-csv-upload'
    LOGO_UPLOAD_BUCKET_NAME = 'public-logos-production'
    NOTIFY_ENVIRONMENT = 'live'


class CloudFoundryConfig(Config):
    pass


# CloudFoundry sandbox
class Sandbox(CloudFoundryConfig):
    HTTP_PROTOCOL = 'https'
    HEADER_COLOUR = '#F499BE'  # $baby-pink
    STATSD_ENABLED = True
    CSV_UPLOAD_BUCKET_NAME = 'cf-sandbox-notifications-csv-upload'
    LOGO_UPLOAD_BUCKET_NAME = 'cf-sandbox-notifications-logo-upload'
    NOTIFY_ENVIRONMENT = 'sandbox'


configs = {
    'development': Development,
    'test': Test,
    'preview': Preview,
    'staging': Staging,
    'live': Live,
    'production': Live,
    'sandbox': Sandbox
}
