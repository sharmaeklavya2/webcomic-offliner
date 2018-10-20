#!/usr/bin/env python3

import sys
import os
from os.path import join as pjoin

import json
import shutil
import jinja2

DEFAULT_ORDER = '_sno'


def copy(source, dest):
    'Copy all files in source to dest'
    os.makedirs(dest, exist_ok=True)
    for fname in os.listdir(source):
        source_path = pjoin(source, fname)
        dest_path = pjoin(dest, fname)
        shutil.copy(source_path, dest_path)


def get_template(theme_dir, fname):
    template_path = pjoin(theme_dir, 'templates', fname)
    try:
        with open(template_path) as fobj:
            return jinja2.Template(fobj.read())
    except FileNotFoundError:
        print(template_path + ' was not found.', file=sys.stderr)
        return None


def create_index(theme_dir, out_dir, order=DEFAULT_ORDER):
    'Create index.html and other related files'
    result = True

    info_dir = pjoin(out_dir, 'info')
    info_list = []
    for fname in os.listdir(info_dir):
        if os.path.splitext(fname)[1] == '.json':
            info_path = pjoin(info_dir, fname)
            with open(info_path) as fobj:
                info = json.load(fobj)
            info_list.append(info)

    if order is not None:
        info_list.sort(key=(lambda info: info[order]))

    os.makedirs(pjoin(out_dir, 'site'), exist_ok=True)

    index_template = get_template(theme_dir, 'index.html')
    if index_template is None:
        result = False
    else:
        page = index_template.render(info_list=info_list)
        with open(pjoin(out_dir, 'site', 'index.html'), 'w') as fobj:
            fobj.write(page)

    redirect_template = get_template(theme_dir, 'redirect.html')
    if redirect_template is None:
        result = False
    else:
        for name, index in [('first', 0), ('last', -1)]:
            page = redirect_template.render(id=info_list[index]['id'])
            with open(pjoin(out_dir, 'site', '_{}.html'.format(name)), 'w') as fobj:
                fobj.write(page)

    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Apply theme to output directory')
    parser.add_argument('out_dir')
    parser.add_argument('theme')
    parser.add_argument('--order', default=DEFAULT_ORDER)
    args = parser.parse_args()

    copy(pjoin(args.theme, 'fixed'), pjoin(args.out_dir, 'site'))
    found_index = create_index(args.theme, args.out_dir, order=args.order)
    if found_index:
        print('created index')


if __name__ == '__main__':
    main()
