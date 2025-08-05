SECRET_KEY = '<SECRET_KEY>'

# API
API_KEY = '<KEY>'
MODEL = '<MODEL_NAME>'

PIM_01_APP_ID = '<PIM_01_APP_ID>'
PIM_02_APP_ID = '<PIM_02_APP_ID>'
PIM_03_APP_ID = '<PIM_03_APP_ID>'
PSG_APP_ID = '<PSG_APP_ID>'
CDG_01_APP_ID = '<CDG_01_APP_ID>'
CDG_02_APP_ID = '<CDG_02_APP_ID>'


# Database
TORTOISE_ORM = {}

try:
    from local_settings import *
except ImportError:
    pass
