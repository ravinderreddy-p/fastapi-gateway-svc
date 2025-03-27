import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
handler = logging.StreamHandler() #Log to console
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
