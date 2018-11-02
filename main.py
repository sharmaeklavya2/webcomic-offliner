#!/usr/bin/env python3

"""
Crawl and scrape a website. Originally written for webcomics.
"""

import sys
import os
from os.path import join as pjoin
import argparse
import json
from collections import OrderedDict
from collections.abc import Sequence

import shutil
import time
from lxml import etree
from urllib.parse import urljoin
import jinja2

import scrape
from scrape import ScrapeError, ConfigError
from fetch import Response, TimedFetcher
import theme


def get_raw_data(url, id=None, out_dir=None, fetcher=None):
    if fetcher is None:
        fetcher = TimedFetcher()
    if out_dir is None:
        return fetcher.fetch(url)
    else:
        raw_path = pjoin(out_dir, 'raw', id + '.html')
        if os.path.isfile(raw_path):
            with open(raw_path, 'rb') as fobj:
                response = Response(fobj.read())
        else:
            response = fetcher.fetch(url)
            with open(raw_path, 'wb') as fobj:
                fobj.write(response.data)
        return response


def check_path_belongs(fpath, parent_path):
    abs_parent_path = os.path.abspath(parent_path)
    abs_fpath = os.path.abspath(pjoin(parent_path, fpath))
    lca = os.path.commonpath([abs_fpath, abs_parent_path])
    if lca != abs_parent_path:
        raise ValueError('{} does not lie in {}'.format(fpath, parent_path))


def download_resources(url, config, info, out_dir, fetcher=None):
    if isinstance(config, Sequence):
        for subconfig in config:
            download_resources(url, subconfig, info, out_dir, fetcher)
    else:
        info2 = {k: v for k, v in info.items() if v is not None}
        try:
            url_template = config['url']
            fpath_template = config['fpath']
        except KeyError as e:
            raise ConfigError('download should contain url and fpath') from e
        try:
            url2 = url_template.format(**info2)
        except KeyError as e:
            scrape.scrape_warn(url, e.args[0], 'key not found for download url replacement')
            url2 = None
        try:
            fpath = fpath_template.format(**info2)
        except KeyError as e:
            scrape.scrape_warn(url, e.args[0], 'key not found for download fpath replacement')
            fpath = None
        if fpath is None or url2 is None:
            return

        url2 = urljoin(url, url2)
        check_path_belongs(fpath, pjoin(out_dir, 'site'))
        fpath = pjoin(out_dir, 'site', fpath)
        if not os.path.isfile(fpath):
            os.makedirs(os.path.dirname(fpath), exist_ok=True)
            if fetcher is None:
                fetcher = TimedFetcher()
            response = fetcher.fetch(url2)
            with open(fpath, 'wb') as fobj:
                fobj.write(response.data)


def fetch_and_scrape(url, config, out_dir=None, fetcher=None, download=True, info=None):
    if info is None:
        info = OrderedDict()
    info['_url'] = url

    # apply url config
    for k, d in config['url'].items():
        info[k] = scrape.apply_url_config(url, d)

    # get id
    id = info.get('id', None)
    if id is None:
        raise ScrapeError('id is null for url ' + url)
    if id == '':
        raise ScrapeError("id is '' for url " + url)

    # get cached info
    if out_dir is not None:
        info_path = pjoin(out_dir, 'info', id + '.json')
        if os.path.isfile(info_path):
            with open(info_path) as fobj:
                info2 = json.load(fobj, object_pairs_hook=OrderedDict)
                info.update(info2)
            found_info = True
        else:
            found_info = False

    # create info using document
    if not found_info:
        response = get_raw_data(url, id, out_dir, fetcher)
        info['_url'] = response.url or url
        document = etree.HTML(response.data)
        scrape.apply_document_config(url, document, config['document'], info)

    # save info
    if out_dir is not None:
        info_path = pjoin(out_dir, 'info', id + '.json')
        with open(info_path, 'w') as fobj:
            json.dump(info, fobj, indent=4)

    # download resources
    if download and out_dir is not None and 'download' in config:
        download_resources(url, config['download'], info, out_dir, fetcher)

    return info


def id_exists(id, out_dir, config):
    fpath = pjoin(out_dir, 'info', id + '.json')
    return os.path.isfile(fpath)

def url_to_id(url, config):
    return scrape.apply_url_config(url, config['url']['id'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out_dir', help='Output directory of project')
    parser.add_argument('--config', help='Path to config file (file will be copied to out_dir)')
    parser.add_argument('--theme', help='Directory containing theme to apply to generated site')

    parser.add_argument('--max-pages', type=int, help='maximum number of pages that will be read')
    parser.add_argument('--delay', type=float, default=1,
        help='time in seconds for which to wait between 2 http requests')
    parser.add_argument('--chip', choices=('soft', 'hard'),
        help='soft: purge last info and generated webpage; hard: purge last info, generated webpage and raw webpage')
    parser.add_argument('--reset', action='store_true', default=False,
        help='reset progress (deletes status.json and sets --explore-old)')
    parser.add_argument('--verbosity', type=int, default=2,
        help='1: print error messages, 2: print fetch messages, 3: print sno')
    parser.add_argument('--explore-old', action='store_true', default=False,
        help='Explore old info files')

    parser.add_argument('--index-order', default='sno', help='key for ordering pages for index')
    parser.add_argument('--no-index', dest='create_index', action='store_false', default=True,
        help='do not generate index files')
    parser.add_argument('--no-copy-static', dest='copy_static', action='store_false', default=True,
        help='do not copy static files from theme to generated site')
    parser.add_argument('--skip-downloads', dest='download', action='store_false', default=True,
        help='do not download additional content (like images)')
    parser.add_argument('--force-render', action='store_true', default=False,
        help='render pages (using theme) even if pages already exist')
    parser.add_argument('--reverse', action='store_true', default=False,
        help='reverse crawling order')
    parser.add_argument('--sno', type=int, default=1, help='serial number to start with')
    parser.add_argument('--genesis-url', help='override genesis url in config')
    args = parser.parse_args()

    if args.config:
        shutil.copyfile(args.config, pjoin(args.out_dir, 'config.json'))

    if args.index_order in ('none', 'null'):
        args.index_order = None
    if args.index_order == 'sno':
        args.index_order = '_sno'

    errfile_path = pjoin(args.out_dir, 'error.log')
    scrape.SCRAPE_ERR_FPS.append(open(errfile_path, 'a'))
    if args.verbosity > 0:
        scrape.SCRAPE_ERR_FPS.append(sys.stderr)

    # Load config
    config_path = pjoin(args.out_dir, 'config.json')
    with open(config_path) as fobj:
        config = json.load(fobj)
    os.makedirs(pjoin(args.out_dir, 'info'), exist_ok=True)
    os.makedirs(pjoin(args.out_dir, 'raw'), exist_ok=True)

    # load template and copy static files
    if args.theme is not None:
        page_template = theme.get_template(args.theme, 'page.html')
        if args.copy_static:
            theme.copy(pjoin(args.theme, 'static'), pjoin(args.out_dir, 'site'))
    else:
        page_template = None

    fetcher = TimedFetcher(args.delay, args.verbosity <= 1)

    # Load and save status
    status_path = pjoin(args.out_dir, 'status.json')
    status_path_exists = False
    if args.reset:
        args.explore_old = True
    else:
        try:
            with open(status_path) as fobj:
                status = json.load(fobj)
            status_path_exists = True
        except FileNotFoundError:
            pass

    if status_path_exists:
        url, sno = status['url'], status['sno']
    else:
        url, sno = args.genesis_url or config['genesis'], args.sno

    id = url_to_id(url, config)
    # Chip away latest page
    if args.chip is not None:
        paths_to_delete = []
        if args.chip == 'hard':
            paths_to_delete.append(pjoin(args.out_dir, 'raw', id + '.html'))
        paths_to_delete.append(pjoin(args.out_dir, 'info', id + '.json'))
        paths_to_delete.append(pjoin(args.out_dir, 'site', id + '.html'))
        for path in paths_to_delete:
            try:
                os.remove(path)
            except FileNotFoundError:
                pass

    print('Starting at url:', url)
    print('Starting at sno:', sno)
    pending_urls = [url]
    if args.explore_old:
        seen_ids = set()
    render_count = 0

    try:
        while pending_urls and (args.max_pages != 0):
            url = pending_urls.pop()
            id = url_to_id(url, config)
            if args.explore_old:
                if id in seen_ids:
                    continue
                seen_ids.add(id)
            else:
                if id_exists(id, args.out_dir, config):
                    continue

            if args.max_pages is not None:
                args.max_pages -= 1
            if args.verbosity > 2:
                print('sno:', sno)

            if not status_path_exists:
                with open(status_path, 'w') as fobj:
                    json.dump({'url': url, 'sno': sno}, fobj)
            status_path_exists = False

            info = OrderedDict()
            info['_sno'] = sno
            sno += 1
            fetch_and_scrape(url, config, args.out_dir, fetcher, download=args.download, info=info)
            adj = OrderedDict()

            empty_urls = ('', '/', '#', '/#')
            if args.reverse:
                edges = reversed(config['crawl'])
            else:
                edges = config['crawl']
            for e in edges:
                url2 = info.get(e)
                if url2 is None or url2 in empty_urls:
                    continue
                id2 = url_to_id(url2, config)
                adj[e] = id2
                url2 = urljoin(url, url2)
                if args.explore_old:
                    id2_exists = id2 in seen_ids
                else:
                    id2_exists = id_exists(id2, args.out_dir, config)
                if not id2_exists:
                    pending_urls.append(url2)

            info['_adj'] = adj

            # save info
            info_path = pjoin(args.out_dir, 'info', id + '.json')
            with open(info_path, 'w') as fobj:
                json.dump(info, fobj, indent=4)

            if page_template is not None:
                output = page_template.render(info)
                outpath = pjoin(args.out_dir, 'site', info['id'] + '.html')
                if args.force_render or not os.path.isfile(outpath):
                    with open(outpath, 'w') as fobj:
                        fobj.write(output)
                    render_count += 1

        if args.theme is not None and args.create_index:
            found_index = theme.create_index(args.theme, args.out_dir, order=args.index_order)
            if found_index:
                print('Added index')
    except KeyboardInterrupt as e:
        pass
    finally:
        scrape.SCRAPE_ERR_FPS[0].close()

        print()
        print('Downloaded {} webpages/resources'.format(fetcher.count))
        print('Rendered {} pages'.format(render_count))


if __name__ == '__main__':
    main()
