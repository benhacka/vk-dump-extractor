import asyncio
from datetime import datetime

import aiofiles
import aiohttp

try:
    from typing import Optional, List
except ImportError:
    raise Exception('Update your fucking python to 3.5+ for good coroutines')

import os
import re
from enum import Enum, auto

from bs4 import BeautifulSoup


def get_soup(html_file_path):
    return BeautifulSoup(html_file_path, 'html.parser')


class HtmlTypeDoc(Enum):
    PHOTOS_ONLY = auto()
    DIALOG = auto()


class ParserMode(Enum):
    TARGET_FILE = auto()
    AUTO_SEARCH = auto()


POSSIBLE_HTML_EXT = ['html', 'htm']


class Image:
    def __init__(self, source_file, url, author='', date=''):
        self._path = self.path_generator(source_file, url, author, date)
        self._url = url

    @property
    def path(self):
        return self._path

    @property
    def url(self):
        return self._url

    @property
    def file_dir(self):
        return os.path.dirname(self.path)

    @staticmethod
    def path_generator(source_file, url, author, date):
        name = '_'.join((date, author, url.split('/')[-1]))
        name = re.sub(r'[_]+', '_', name)
        return os.path.join(os.path.dirname(source_file), 'photo', name)


class Downloader:
    def __init__(self, thread_count):
        self._header = {
            'Accept':
            'text/html,application/xhtml+xml,'
            'application/xml;q=0.9,image/webp,image/apng,'
            '*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Encoding':
            'gzip, deflate, br',
            'User-Agent':
            'Mozilla/5.0 (Windows NT 6.1; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/80.0.3987.149 Safari/537.36'
        }
        self._semaphore = asyncio.Semaphore(thread_count)
        self._download_list = []
        self._link_set = set()

    async def save_photo(self, img: Image):
        async with aiohttp.ClientSession(headers=self._header) as session:
            try:
                async with self._semaphore, session.get(img.url) as resp:
                    if resp.status == 200:
                        os.makedirs(img.file_dir, exist_ok=True)
                        try:
                            file = await aiofiles.open(img.path, mode='wb')
                            await file.write(await resp.read())
                        finally:
                            await file.close()
            except Exception as e:
                print(f'{e} - {img.url}')

    async def download_files(self):
        await asyncio.gather(
            *[self.save_photo(file) for file in self._download_list])

    def _link_validator(self, url: str):
        if (not url.startswith('http') or not url.endswith('.jpg')
                or url in self._link_set):
            return False
        return True

    def push_img(self, source_file, url, author='', date=''):
        if not self._link_validator(url):
            return
        self._link_set.add(url)
        self._download_list.append(Image(source_file, url, author, date))


class FileChecker:
    def __init__(self,
                 common_title='Общий лист фотографий',
                 photo_html_name='photos.html',
                 dialog_pattern=r'history_.\d?\.html'):
        self._common_title = common_title
        self._photo_html = photo_html_name
        self._dialog_pattern = dialog_pattern

    def check_by_html(self, file_path: str) -> Optional[HtmlTypeDoc]:
        print('extra check')
        with open(file_path, encoding='utf-8') as file:
            soup = get_soup(file)
            title = soup.title
            if title is None:
                return None
            if title.text == self._common_title:
                return HtmlTypeDoc.PHOTOS_ONLY
            return HtmlTypeDoc.DIALOG

    def check_by_file_name(self, file_path: str,
                           need_to_check_file=False) -> \
            Optional[HtmlTypeDoc]:
        file_name = os.path.basename(file_path)
        if file_name == self._photo_html:
            return HtmlTypeDoc.PHOTOS_ONLY
        if re.search(self._dialog_pattern, file_name):
            return HtmlTypeDoc.DIALOG
        if need_to_check_file:
            return self.check_by_html(file_path)


class HtmlFile:
    def __init__(self, file_path: str, file_type: HtmlTypeDoc):
        self._file_path = file_path
        self._file_type = file_type

    @property
    def filename(self):
        return os.path.basename(self._file_path)

    @property
    def file_path(self):
        return self._file_path

    @property
    def file_type(self):
        return self._file_type


class Parser:
    def __init__(self,
                 file_checker: FileChecker,
                 download_manager: Downloader,
                 *,
                 include_common_girls: bool = False,
                 include_common_boys: bool = False,
                 include_chat_with_girls: bool = False,
                 include_chat_with_boys: bool = False,
                 manual_file=False,
                 include_path_name: str = 'Вложения',
                 chat_path_name: str = 'Диалоги',
                 girls_dir: str = 'Девочки',
                 boys_dir: str = 'Парни'):
        self._file_checker = file_checker
        self._download_manager = download_manager
        self._include_common_girls = include_common_girls
        self._include_common_boys = include_common_boys
        self._include_chat_with_girls = include_chat_with_girls
        self._include_chat_with_boys = include_chat_with_boys
        if not any(
            (include_common_girls, include_chat_with_girls,
             include_common_boys, include_chat_with_boys)) and not manual_file:
            raise ValueError('No sources to download!')
        self._mode = (ParserMode.TARGET_FILE
                      if manual_file else ParserMode.AUTO_SEARCH)
        self._include_path_name = include_path_name
        self._chat_path_name = chat_path_name
        self._girls_dir = girls_dir
        self._boys_dir = boys_dir
        self._common_path = None
        self._chat_path = None

    @property
    def parser_mode(self):
        return self._mode

    @staticmethod
    def _path_generator(root_folder, folder, include):
        if root_folder is None or not include:
            return '\0'
        return os.path.join(root_folder, folder)

    @property
    def _common_girls(self):
        return self._path_generator(self._common_path, self._girls_dir,
                                    self._include_common_girls)

    @property
    def _common_boys(self):
        return self._path_generator(self._common_path, self._boys_dir,
                                    self._include_common_boys)

    @property
    def _chat_girls(self):
        return self._path_generator(self._chat_path, self._girls_dir,
                                    self._include_chat_with_girls)

    @property
    def _chat_boys(self):
        return self._path_generator(self._chat_path, self._boys_dir,
                                    self._include_chat_with_boys)

    @property
    def _common_paths(self):
        return self._common_girls, self._common_boys

    @property
    def _chat_paths(self):
        return self._chat_boys, self._chat_girls

    def _get_normal_files(self, dir_path: str, file_type: HtmlTypeDoc):
        files = []
        for file in os.listdir(dir_path):
            file_name = os.path.join(dir_path, file)
            if self._file_checker.check_by_file_name(file_name) is file_type:
                files.append(HtmlFile(file_name, file_type))
        return files

    def _get_files(self, dir_path, filenames):
        if not any((filename.endswith('.html') for filename in filenames)):
            return []
        for common in self._common_paths:
            if common in dir_path:
                return self._get_normal_files(dir_path,
                                              HtmlTypeDoc.PHOTOS_ONLY)
        for chat in self._chat_paths:
            if chat in dir_path:
                return self._get_normal_files(dir_path, HtmlTypeDoc.DIALOG)
        return []

    async def _parse_links_from_dialog(self, file):
        async with aiofiles.open(file, encoding='utf-8') as f:
            html = await f.read()
        soup = BeautifulSoup(html, 'html.parser')
        for message in soup.find_all('div', {'class': 'im_in'}):
            photos = message.find_all('a', {'class': 'download_photo_type'},
                                      href=True)
            if not photos:
                continue
            photos = [img['href'] for img in photos]
            author = message.find('div', {
                'class': 'im_log_author_chat_name'
            }).text
            str_date = message.find('a', {'class': 'im_date_link'}).text
            date_time = datetime.strptime(str_date, '%d.%m.%Y %H:%M')
            date = date_time.strftime('%Y%m%d%H%M')
            for url in photos:
                self._download_manager.push_img(file, url, author, date)

    async def _parse_links_from_common(self, file):
        async with aiofiles.open(file, encoding='utf-8') as f:
            html = await f.read()
        soup = BeautifulSoup(html, 'html.parser')
        photos = soup.find_all('a', {'class': 'download_photo_type'},
                               href=True)
        for photo in photos:
            url = photo.get('href')
            if url and url.startswith('http'):
                self._download_manager.push_img(file, url)

    def search_html(self, root_path_for_search: str):
        files = []

        for dir_path, dir_names, filenames in os.walk(root_path_for_search):
            if os.path.basename(dir_path) == self._include_path_name:
                if not any((
                        self._include_common_boys,
                        self._include_common_girls,
                )):
                    continue
                self._common_path = dir_path
            elif os.path.basename(dir_path) == self._chat_path_name:
                if not any((self._include_chat_with_boys,
                            self._include_chat_with_girls)):
                    continue
                self._chat_path = dir_path
            files.extend(self._get_files(dir_path, filenames))
        return files

    def get_manual_file(self, file_path):
        file_type = self._file_checker.check_by_html(file_path)
        if file_type is None:
            raise ValueError('Incorrect file')
        return HtmlFile(file_path, file_type)

    async def parse_url_from_html(self, html_file: HtmlFile):
        if html_file.file_type is HtmlTypeDoc.DIALOG:
            return await self._parse_links_from_dialog(html_file.file_path)
        elif html_file.file_type is HtmlTypeDoc.PHOTOS_ONLY:
            return await self._parse_links_from_common(html_file.file_path)


class Extractor:
    def __init__(self,
                 thread_count,
                 *,
                 include_common_girls: bool = False,
                 include_common_boys: bool = False,
                 include_chat_with_girls: bool = False,
                 include_chat_with_boys: bool = False,
                 manual_file=False,
                 include_path_name: str = 'Вложения',
                 chat_path_name: str = 'Диалоги',
                 girls_dir: str = 'Девочки',
                 boys_dir: str = 'Парни'):
        self._file_checker = FileChecker()
        self._downloader = Downloader(thread_count)
        self._parser = Parser(self._file_checker,
                              self._downloader,
                              include_common_girls=include_common_girls,
                              include_common_boys=include_common_boys,
                              include_chat_with_girls=include_chat_with_girls,
                              include_chat_with_boys=include_chat_with_boys,
                              manual_file=manual_file,
                              include_path_name=include_path_name,
                              chat_path_name=chat_path_name,
                              girls_dir=girls_dir,
                              boys_dir=boys_dir)

    @property
    def parser(self):
        return self._parser

    @property
    def downloader(self):
        return self._downloader

    def download_from_html_files(self, files: List[HtmlFile]):
        async def async_main():
            coroutines = [
                self.parser.parse_url_from_html(file) for file in files
            ]
            await asyncio.gather(*coroutines)
            await self.downloader.download_files()

        event_loop.run_until_complete(async_main())

    def get_files(self, target_path: str):
        if (any(target_path.endswith(ext) for ext in POSSIBLE_HTML_EXT)
                and os.path.isfile(target_path)):
            return [self.parser.get_manual_file(target_path)]
        if os.path.isdir(target_path):
            return self.parser.search_html(target_path)
        raise ValueError('Unknown target')


def main():
    root_dir = r'.'
    extractor = Extractor(100, include_chat_with_girls=True)
    files = extractor.parser.search_html(root_dir)
    extractor.download_from_html_files(files)


if __name__ == '__main__':
    event_loop = asyncio.get_event_loop()
    main()