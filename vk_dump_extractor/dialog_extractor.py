#!/usr/bin/env python3

import asyncio
import sys
from argparse import ArgumentParser
from datetime import datetime

try:
    from typing import Optional, List
    if sys.version_info <= (3, 7):
        raise ImportError
except ImportError as error:
    raise Exception(
        'Update your python to 3.7+ for good coroutines') from error

import os
import re
from enum import Enum, auto
from multiprocessing.dummy import Pool as ThreadPool

import aiofiles
import aiohttp
from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm


def get_soup(html_file_path):
    return BeautifulSoup(html_file_path, 'html.parser')


class HtmlTypeDoc(Enum):
    PHOTOS_ONLY = auto()
    DIALOG = auto()


class ParserMode(Enum):
    TARGET_FILE = auto()
    AUTO_SEARCH = auto()


POSSIBLE_HTML_EXT = ['html', 'htm']
VALID_PICTURE_TRAIL = ['.jpg', 'type=album']


class DefaultDirNames(Enum):
    ATTACHMENT_PATH_NAME = 'Вложения'
    CHAT_PATH_NAME = 'Диалоги'
    GIRLS_DIR = 'Девочки'
    BOYS_DIR = 'Парни'


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
        name = name.split('?')[0]
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
        # self._link_set = set()  # deprecated
        self._name_set = set()
        self._session = None

    @property
    def total_count(self):
        return len(self._download_list)

    async def save_photo(self, img: Image):
        if os.path.isfile(img.path):
            return None
        try:
            async with self._semaphore, self._session.get(img.url) as resp:
                if resp.status != 200:
                    raise aiohttp.ClientError(
                        f'{img.url} '
                        f'return code {resp.status} (not 200)')
                os.makedirs(img.file_dir, exist_ok=True)
                async with aiofiles.open(img.path, mode='wb') as file:
                    await file.write(await resp.read())
                return False
        except (aiohttp.ClientError, OSError, TimeoutError) as err:
            print(f'{err} - {img.url}')
            return img

    async def download_files(self):
        async with aiohttp.ClientSession(
                headers=self._header) as self._session:
            results = await tqdm.gather(
                *[self.save_photo(file) for file in self._download_list])
            skipped_count = len([res for res in results if res is None])
            downloaded_count = (len([res for res in results if not res]) -
                                skipped_count)
            error_count = len(results) - skipped_count - downloaded_count
            print(f'Skipped file count: {skipped_count}')
            print(f'Downloaded file count: {downloaded_count}')
            print(f'Error file count: {error_count}')

    @staticmethod
    def _link_validator(url: str):
        if (not url.startswith('http') or
                not (any(url.endswith(trail)
                         for trail in VALID_PICTURE_TRAIL))):
            return False
        return True

    @staticmethod
    def generate_image_object(source_file, url, author='', date=''):
        return Image(source_file, url, author, date)

    def push_img(self, image: Image):
        if image.path in self._name_set:
            return True
        if not self._link_validator(image.url):
            return False
        self._name_set.add(image.path)
        self._download_list.append(image)
        return True


class FileChecker:
    def __init__(self,
                 common_title='Общий лист фотографий',
                 photo_html_name='photos.html',
                 dialog_pattern=r'history_.\d?\.htm'):
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
        return None


class HtmlFile:
    def __init__(self, file_path: str, file_type: HtmlTypeDoc):
        self._file_path = file_path
        self._file_type = file_type

    @property
    def is_htm(self):
        return not self._file_path.endswith('html')

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
                 include_attachment_girls: bool = False,
                 include_attachment_boys: bool = False,
                 include_chat_with_girls: bool = False,
                 include_chat_with_boys: bool = False,
                 manual_file=False,
                 attachment_path_name: str = 'Вложения',
                 chat_path_name: str = 'Диалоги',
                 girls_dir: str = 'Девочки',
                 boys_dir: str = 'Парни'):
        self._file_checker = file_checker
        self._download_manager = download_manager
        self._include_attachment_girls = include_attachment_girls
        self._include_attachment_boys = include_attachment_boys
        self._include_chat_with_girls = include_chat_with_girls
        self._include_chat_with_boys = include_chat_with_boys
        if not any((include_attachment_girls, include_chat_with_girls,
                    include_attachment_boys,
                    include_chat_with_boys)) and not manual_file:
            raise ValueError(
                'No sources type (attach or/and dialog) to download!')
        self._mode = (ParserMode.TARGET_FILE
                      if manual_file else ParserMode.AUTO_SEARCH)
        self._attachment_path_name = attachment_path_name
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
                                    self._include_attachment_girls)

    @property
    def _common_boys(self):
        return self._path_generator(self._common_path, self._boys_dir,
                                    self._include_attachment_boys)

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
        if not any(
                file.endswith(ext) for ext in POSSIBLE_HTML_EXT
                for file in filenames):
            return []
        for common in self._common_paths:
            if common in dir_path:
                return self._get_normal_files(dir_path,
                                              HtmlTypeDoc.PHOTOS_ONLY)
        for chat in self._chat_paths:
            if chat in dir_path:
                return self._get_normal_files(dir_path, HtmlTypeDoc.DIALOG)
        return []

    @staticmethod
    def _get_image_container_and_a_filter(file):
        if file.is_htm:
            return 'tr', None
        return 'div', {'class': 'download_photo_type'}

    def _collect_links_from_dialog(self, file):
        file_name = file.file_path
        with open(file_name, encoding='utf-8') as f:
            html = f.read()
        result = []
        img_container, a_filter = self._get_image_container_and_a_filter(file)
        for message in BeautifulSoup(html, 'html.parser').find_all(
                img_container, {'class': 'im_in'}):
            photos = message.find_all('a', a_filter, href=True)
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
                if not url:
                    continue
                result.append(
                    self._download_manager.generate_image_object(
                        file_name, url, author, date))
        print(f'{len(result)} links parsed from {file_name}')
        return result

    def _collect_links_from_attachment(self, file):
        file_name = file.file_path
        with open(file_name, encoding='utf-8') as f:
            html = f.read()
        soup = BeautifulSoup(html, 'html.parser')
        _, a_filter = self._get_image_container_and_a_filter(file)
        photos = soup.find_all('a', a_filter, href=True)
        result = []
        for photo in photos:
            url = photo.get('href')
            if url and url.startswith('http'):
                result.append(
                    self._download_manager.generate_image_object(
                        file_name, url))
        print(f'{len(result)} links parsed from {file_name}')
        return result

    def search_html(self, root_path_for_search: str):
        files = []

        for dir_path, _, filenames in os.walk(root_path_for_search):
            if os.path.basename(dir_path) == self._attachment_path_name:
                if not any((
                        self._include_attachment_boys,
                        self._include_attachment_girls,
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

    def parse_url_from_html(self, html_file: HtmlFile):
        if html_file.file_type is HtmlTypeDoc.DIALOG:
            return self._collect_links_from_dialog(html_file)
        if html_file.file_type is HtmlTypeDoc.PHOTOS_ONLY:
            return self._collect_links_from_attachment(html_file)
        raise NotImplementedError


class Extractor:
    def __init__(self,
                 thread_count,
                 *,
                 include_attachment_girls: bool = False,
                 include_attachment_boys: bool = False,
                 include_chat_with_girls: bool = False,
                 include_chat_with_boys: bool = False,
                 manual_file=False,
                 attachment_path_name: str = 'Вложения',
                 chat_path_name: str = 'Диалоги',
                 girls_dir: str = 'Девочки',
                 boys_dir: str = 'Парни',
                 photo_file_name: str = 'photos.html'):
        self._file_checker = FileChecker(photo_html_name=photo_file_name)
        self._downloader = Downloader(thread_count)
        self._parser = Parser(
            self._file_checker,
            self._downloader,
            include_attachment_girls=include_attachment_girls,
            include_attachment_boys=include_attachment_boys,
            include_chat_with_girls=include_chat_with_girls,
            include_chat_with_boys=include_chat_with_boys,
            manual_file=manual_file,
            attachment_path_name=attachment_path_name,
            chat_path_name=chat_path_name,
            girls_dir=girls_dir,
            boys_dir=boys_dir)

    @property
    def parser(self):
        return self._parser

    @property
    def downloader(self):
        return self._downloader

    async def download_from_html_files(self, files: List[HtmlFile]):
        print(f'Total file count: {len(files)}')
        if len(files) == 1:
            result = self.parser.parse_url_from_html(files[0])
        else:
            with ThreadPool() as pool:
                result = pool.map(self.parser.parse_url_from_html, files)
                result = sum(result, [])

        print(f'Urls collected: {len(result)}')
        print('Start filtering')
        for img in result:
            if not self.downloader.push_img(img):
                print(f'Invalid image url: {img.url}')
        print(f'Valid images after filtering: '
              f'{self.downloader.total_count}')
        print('Start downloading files')
        await self.downloader.download_files()

    @classmethod
    def is_input_html_file(cls, target_path):
        if not os.path.exists(target_path):
            raise OSError('Target source not exists')
        if (any(target_path.endswith(ext) for ext in POSSIBLE_HTML_EXT)
                and os.path.isfile(target_path)):
            return True
        return False

    def get_files(self, target_path: str,
                  is_manual_html: bool) -> List[HtmlFile]:
        if is_manual_html:
            return [self.parser.get_manual_file(target_path)]
        if os.path.isdir(target_path):
            return self.parser.search_html(target_path)
        raise ValueError('Unknown target')


def arg_parser():
    parser = ArgumentParser()
    parser.add_argument('-t',
                        '--target-dir-file-path',
                        help='Target path',
                        required=True)
    parser.add_argument('-ag',
                        '--attachment-girls',
                        action='store_true',
                        default=False,
                        help='Download photos from attachment with girls')
    parser.add_argument('-ab',
                        '--attachment-boys',
                        action='store_true',
                        default=False,
                        help='Download photos from attachment with boys')
    parser.add_argument('-cg',
                        '--chat-girls',
                        action='store_true',
                        default=False,
                        help='Download photos from attachment with girls')
    parser.add_argument('-cb',
                        '--chat-boys',
                        action='store_true',
                        default=False,
                        help='Download photos from attachment with boys')
    parser.add_argument(
        '-an',
        '--attachment-dir-name',
        default=DefaultDirNames.ATTACHMENT_PATH_NAME.value,
        help=(f'Attachment directory name. '
              f'Default: {DefaultDirNames.ATTACHMENT_PATH_NAME.value}'))
    parser.add_argument(
        '-dn',
        '--dialog-dir-name',
        default=DefaultDirNames.CHAT_PATH_NAME.value,
        help=(f'Dialog directory name. '
              f'Default: {DefaultDirNames.CHAT_PATH_NAME.value}'))
    parser.add_argument('-gn',
                        '--girl-dir-name',
                        default=DefaultDirNames.GIRLS_DIR.value,
                        help=(f'Girl dir name. '
                              f'Default: {DefaultDirNames.GIRLS_DIR.value}'))
    parser.add_argument('-bn',
                        '--boy-dir-name',
                        default=DefaultDirNames.BOYS_DIR.value,
                        help=(f'Boy dir name. '
                              f'Default: {DefaultDirNames.BOYS_DIR.value}'))
    default_photo_file_name = 'photos.html'
    parser.add_argument('-pn',
                        '--photo-file-name',
                        default=default_photo_file_name,
                        help=(f'Photo htm(l) file name. '
                              f'Default {default_photo_file_name}'))
    default_thread_count = 100
    parser.add_argument('--thread-count',
                        default=default_thread_count,
                        type=int,
                        help=(f'Max download coroutines (thread) count. '
                              f'Default: {default_thread_count}'))
    return parser.parse_args()


async def amain():
    args = arg_parser()
    target = args.target_dir_file_path
    is_manual_file = Extractor.is_input_html_file(target)
    extractor = Extractor(args.thread_count,
                          include_attachment_girls=args.attachment_girls,
                          include_attachment_boys=args.attachment_boys,
                          include_chat_with_girls=args.chat_girls,
                          include_chat_with_boys=args.chat_boys,
                          manual_file=is_manual_file,
                          attachment_path_name=args.attachment_dir_name,
                          chat_path_name=args.dialog_dir_name,
                          girls_dir=args.girl_dir_name,
                          boys_dir=args.boy_dir_name,
                          photo_file_name=args.photo_file_name)
    files = extractor.get_files(target, is_manual_file)
    await extractor.download_from_html_files(files)


def main():
    asyncio.run(amain())


if __name__ == '__main__':
    main()
