
from django.conf import settings
import logging, os

#############################################################################
#############################################################################

def logger_init_default(logger_name, logfile_basename, test_logging):

  #LOG_FILENAME = os.path.join(settings.LOG_FILE_LOCATION, 'views.log')
  LOG_FILENAME = os.path.join(settings.LOG_FILE_LOCATION, logfile_basename)

  if hasattr(settings, "LOGGING_FORMAT_DEFAULT"):
    FORMAT = settings.LOGGING_FORMAT_DEFAULT
  else:
    FORMAT = '%(asctime)s %(levelname)s: %(message)s'

  if hasattr(settings, "LOG_LEVEL"):
    if settings.LOG_LEVEL == "error":
      LOG_LEVEL = logging.ERROR
    elif settings.LOG_LEVEL == "warn":
      LOG_LEVEL = logging.WARN
    elif settings.LOG_LEVEL == "info":
      LOG_LEVEL = logging.INFO
    elif settings.LOG_LEVEL == "debug":
      LOG_LEVEL = logging.DEBUG
    else:
      LOG_LEVEL = settings.LOG_LEVEL
  else:
    if settings.DEBUG:
      LOG_LEVEL = logging.DEBUG
    else:
      LOG_LEVEL = logging.INFO


  # init format of the root logger, if not already done
  logging.basicConfig(format=FORMAT)

  # prepare specific, named logger
  logger = logging.getLogger(logger_name)
  handler = logging.FileHandler(LOG_FILENAME)
  formatter = logging.Formatter(FORMAT)
  handler.setFormatter(formatter)
  logger.addHandler(handler)

  orig_level = logger.level
  logger.setLevel(LOG_LEVEL)

  if test_logging:
    logger.error("logger_init_default(): "+logger_name+": log level orig="+str(orig_level)+" ; ERROR="+str(logging.ERROR)+" INFO="+str(logging.INFO)+" DEBUG="+str(logging.DEBUG))
    logger.error("logger_init_default(): "+logger_name+": error test")
    logger.info("logger_init_default(): "+logger_name+": info test")
    logger.debug("logger_init_default(): "+logger_name+": debug test")

  return logger

