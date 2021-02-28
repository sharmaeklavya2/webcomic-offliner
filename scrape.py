from collections import OrderedDict
from collections.abc import Sequence, Mapping
from urllib.parse import urlparse, parse_qs
import logging

logger = logging.getLogger('scrape')


class ConfigError(ValueError):
    'Raised when the config is incorrect'


class ScrapeError(ValueError):
    'Raised when info cannot be generated from a config'


def validate_text(url, text, config, key):
    err_msg = None
    if config is None or config is False:
        return
    elif config is True:
        if not text:
            logger.warning('{}:\t{}:\t{}'.format(url, key, 'not found'))
    elif isinstance(config, Sequence):
        err_msg = []
        for subconfig in config:
            sub_err_msg = validate_text(text, config, key)
            err_msg.append(sub_err_msg)
    elif isinstance(config, Mapping):
        pass
    else:
        raise ConfigError('Unsupported value in validate')
    return err_msg


def apply_url_config(url, config):
    try:
        part_name = config['component']
    except KeyError:
        raise ConfigError("url subconfig does not contain 'component'")
    text = None
    url_parts = urlparse(url)
    if part_name == 'path':
        path = url_parts.path
        if 'index' in config:
            components = path.strip('/').split('/')
            index = config['index']
            try:
                text = components[index]
            except (IndexError, TypeError):
                pass
        else:
            text = path
        if 'sep' in config:
            text = text.strip('/').replace('/', config['sep'])
    elif part_name == 'query':
        qs_dict = parse_qs(url_parts.query)
        if 'key' in config:
            key = config['key']
            try:
                text = qs_dict[key][0]
            except (IndexError, KeyError, TypeError):
                pass
        else:
            raise ConfigError("key is needed to retrieve data from url's querystring")
    # TODO: add other components
    return text


def apply_document_config(url, document, config, result=None):
    if result is None:
        result = OrderedDict()
    scrape_errors = OrderedDict()
    for k, d in config.items():
        text = None

        # get tags
        if 'css' in d:
            tags = document.cssselect(d['css'])
        else:
            tags = []

        # get tag
        index = d.get('index', 0)
        try:
            tag = tags[index]
        except IndexError:
            tag = None

        # get text
        if tag is not None:
            attr = d.get('attr')
            if attr is None:
                text = ''.join(tag.itertext())
            else:
                text = tag.attrib.get(attr)

        # url process
        if text is not None and d.get('url') is not None:
            text = apply_url_config(text, d['url'])

        # text validation
        err_msg = validate_text(url, text, d.get('validate', True), k)
        if err_msg is not None:
            scrape_errors[k] = err_msg

        result[k] = text

    if scrape_errors:
        result['_scrape_errors'] = scrape_errors
    return result
