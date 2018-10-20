# Webcomic Offliner

This program downloads a webcomic website for offline viewing.
It also removes unnecessary clutter (like headers, footers, etc.).

**Warning: Web crawling and scraping may be illegal depending on circumstances.**

### What it does

* It crawls a website and downloads all the relevant webpages.
* It scrapes out information from those webpages.
* It downloads any related content, like images.
* It generates an offline website using all that information.

### How to use it

* Create a directory where the program's output will be stored.
  Let's call this directory `out_dir`.

* Create a file named `config.json` in `out_dir`.
  `config.json` specifies how to crawl and scrape a website.
  Instructions for creating `config.json` can be found below.
  See `xkcd.json` for a configuration file for [xkcd](https://xkcd.com).

* Create a theme directory which specifies how an offline version will be generated
  using crawled information. You can use the bundled directory `theme`,
  but that might not always work depending on your target website.

* Run `python3 main.py <out_dir> --theme=<theme>` and wait for it to finish.

* The website will be generated in `out_dir/site`.

There are other features of this program which you can check out
below and by running `main.py --help`.

## How it works

This briefly explains how this program works.
Knowing this can be helpful if you're facing problems with crawling or scraping.

### Comic identification

* id: Each comic on the website is assigned an id.
  The id is textual (not numeric).
  An id can be used to look up a certain comic on the web or in your generated site.

* sno: Each crawled comic is given a serial number (numeric, not textual) by this program.
  The i<sup>th</sup> comic which was downloaded gets serial number i.

### Life-cycle of a page

* A webpage is downloaded from its web URL.
  The downloaded web page is stored at `out_dir/raw/<id>.html`.
* The raw webpage is scraped to get useful information.
  This information is stored in a file called the 'info file'.
  The info file is stored at `out_dir/info/<id>.json`.
* The info file is rendered as a webpage.
  This webpage is stored at `out_dir/site/<id>.html`.

### Config file

A config file has the following sections, each of which serves a specific purpose.

* `genesis`: The URL of a comic from where crawling starts.
* `url`: How to compute a comic's id (and possibly other attributes) from its URL.
  Keys of this object are also keys in the info file.
* `document`: How to extract information from the comic's html page.
  This is mostly specified using CSS selectors.
  Keys of this object are also keys in the info file.
* `crawl`: How to jump to other comic pages from the current page.
  This is a list of keys in the info file which contain URLs.
* `download`: Additional resources to download, like images.

### Scraping in multiple runs

Sometimes a single run of the program is not sufficient to scrape the whole website.
This could be because it takes very long to scrape and you can't keep your computer running for that long.
You could also be facing network connectivity problems, which will stop the crawler,
forcing you to try again.

This program supports crawling and scraping in multiple runs.
If you want to manually stop the program, you can press `Ctrl+C` to stop it.
You can then run it again whenever you like.
If a network connectivity issue stops the program, you can just run the program again.

This program keeps track of its progress in two ways:

* It maintains a `status.json` file, which tells it which URL to start scraping from.
  In the first run of the program, this file doesn't exist, so the genesis URL is used to start scraping.
  This file is updated every time a new URL is considered for downloading.
  You can force the program to start at the genesis URL by deleting `status.json`
  or by using the command-line argument `--reset`.
* Downloaded data, scraped data and rendered data is never discarded.
  The program downloads, scrapes or renders only if the output file doesn't already exist.
  You can force the program to download, scrape or render again by deleting appropriate files in
  `out_dir/raw`, `out_dir/info` and `out_dir/site`.

Some command-line arguments for forcing download/scrape/render:

* You can force re-rendering by using the `--force-render` flag.
* If the program stops after visiting the current URL but before updating the URL in `status.json`
  to a different URL, nothing will happen on running the program again, because the current URL has already been visited.
  Using `--chip=soft` will delete the info and rendered page of the current URL to force the program to continue.
  Alternatively, you can use `--explore-old`, which will examine all info files to check if there are unfetched pages.
* If the last webpage of a website changes, you can get a fresh copy by using `--chip=hard`.
  This will delete the info, raw webpage and rendered webpage of the current URL.

### Generating local website

`theme/templates/page.html` contains the template to render each page.
The context for the template is the info file.

You might require additional resources like stylesheets, JavaScript files or images.
These can be added to `theme/fixed/`. They will be copied to `out_dir/site`.

You can also add an index page at `out_dir/index.html`.
The template for it should be at `theme/templates/index.html`.
The context for it contains a list of all info objects called `info_list`.

### Downloading extra content

Sometimes extra content has to be downloaded apart from webpages, like images.
This is done after scraping the page but before rendering it.
This can be controlled by using the `download` section of the config file.
These files are saved in `out_dir/site`.

## Config file specification

`genesis`: URL of website to begin crawling from.

### `url`

The value of this key should be an object.
Each key of this object is an attribute which will be stored in an info file.
Each value of this object should be a `urlspec`.

A `urlspec` is an object which specifies how to extract a string from a URL.
It can have the following key-value pairs:

* `component`: String which specifies which component of the URL to use.
  Component is defined as in the return type of python's
  [`urllib.parse.urlparse`](https://docs.python.org/3/library/urllib.parse.html#urllib.parse.urlparse).
  Currently only `path` is supported.
* `index`: An integer used to index a list. If the component is a path, the list is created by splitting it on `/`.

### `document`

The value of this key should be an object.
Each key of this object is an attribute which will be stored in an info file.
Each value of this object should be a `scrape_config`.

A `scrape_config` is an object which specifies how to extract a certain string from an HTML document.
It can have the following key-value pairs:

* `css` (string): The CSS selector used to get a list of tags.
* `index` (integer): Index to choose a tag from the list of selected tags. Default value is 0.
* `attr` (string or `null`): Which attribute of the tag to use to get a string.
  If this is null, the text of the tag is used. Default value is null.
* `url` (`urlspec`): `urlspec` used to get a value from the string. This is optional.
* `validate` (`true`, `false`, `null`): If the string couldn't be found and validate is `true`, log an error message.

### `crawl`

The value of this key should be a list of attributes in info which can be used to get a url.
These urls will be crawled.

### `download`

The value of this key should either be an object or a list of object.
Each object specifies a resource to download. Each object has 2 keys:

* `url`: URL of the resource to download.
* `fpath`: Path (relative to `out_dir/site`) at which the resource will be saved.

Both `url` and `fpath` can be [python formatstrings](https://docs.python.org/3/library/stdtypes.html#str.format).
These formatstrings will be rendered by passing the info object as keyword arguments.
