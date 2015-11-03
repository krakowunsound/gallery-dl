# -*- coding: utf-8 -*-

# Copyright 2015 Mike Fährmann
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Extract manga pages from http://www.mangareader.net/"""

from .common import AsynchronousExtractor, Message
from .. import text
import os.path

info = {
    "category": "mangareader",
    "extractor": "MangaReaderExtractor",
    "directory": ["{category}", "{manga}", "c{chapter:>03} - {title}"],
    "filename": "{manga}_c{chapter:>03}_{page:>03}.{extension}",
    "pattern": [
        r"(?:https?://)?(?:www\.)?mangareader\.net((/[^/]+)/(\d+))",
        r"(?:https?://)?(?:www\.)?mangareader\.net(/\d+-\d+-\d+(/[^/]+)/chapter-(\d+).html)",
    ],
}

class MangaReaderExtractor(AsynchronousExtractor):

    url_base = "http://www.mangareader.net"

    def __init__(self, match):
        AsynchronousExtractor.__init__(self)
        self.part, self.url_title, self.chapter = match.groups()

    def items(self):
        page = self.request(self.url_base + self.part).text
        data = self.get_job_metadata(page)
        yield Message.Version, 1
        yield Message.Directory, data
        for i in range(1, int(data["count"])+1):
            next_url, image_url, image_data = self.get_page_metadata(page)
            image_data.update(data)
            image_data["page"] = i
            yield Message.Url, image_url, image_data
            if next_url:
                page = self.request(next_url).text

    def get_job_metadata(self, chapter_page):
        """Collect metadata for extractor-job"""
        page = self.request(self.url_base + self.url_title).text
        data = {
            "category": info["category"],
            "chapter": self.chapter,
            "lang": "en",
            "language": "English",
        }
        data, _ = text.extract_all(page, (
            (None, '<td class="propertytitle">Name:', ''),
            ("manga", '<h2 class="aname">', '</h2>'),
            (None, '<td class="propertytitle">Year of Release:', ''),
            ('manga-release', '<td>', '</td>'),
            (None, '<td class="propertytitle">Author:', ''),
            ('author', '<td>', '</td>'),
            (None, '<td class="propertytitle">Artist:', ''),
            ('artist', '<td>', '</td>'),
            (None, '<div id="readmangasum">', ''),
            ('title', ' ' + self.chapter + '</a> : ', '</td>'),
            ('chapter-date', '<td>', '</td>'),
        ), values=data)
        data, _ = text.extract_all(chapter_page, (
            (None, '<select id="pageMenu"', ''),
            ('count', '</select> of ', '</div>'),
        ), values=data)
        for key in ("author", "artist"):
            data[key] = text.unescape(data[key])
        return data

    def get_page_metadata(self, page):
        """Collect next url, image-url and metadata for one manga-page"""
        extr = text.extract
        width = None
        test , pos = extr(page, "document['pu']", '')
        if test is None:
            return None, None, None
        if page.find("document['imgwidth']", pos, pos+200) != -1:
            width , pos = extr(page, "document['imgwidth'] = ", ";", pos)
            height, pos = extr(page, "document['imgheight'] = ", ";", pos)
        _  , pos = extr(page, '<div id="imgholder">', '')
        url, pos = extr(page, ' href="', '"', pos)
        if width is None:
            width , pos = extr(page, '<img id="img" width="', '"', pos)
            height, pos = extr(page, ' height="', '"', pos)
        image, pos = extr(page, ' src="', '"', pos)
        filename = text.unquote(text.filename_from_url(image))
        name, ext = os.path.splitext(filename)

        return self.url_base + url, image, {
            "width": width,
            "height": height,
            "name": name,
            "extension": ext[1:],
        }