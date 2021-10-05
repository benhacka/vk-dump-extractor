# VK DUMP EXTRACTOR 

###### Простенький консольный скриптик для скачки фото из html/htm, которые генерирует *какой-то* дампер.

## Зависимости
Все зависимости в `requirements.txt`:
- `aiofiles`
- `aiohttp`
- `beautifulsoup4`
- `tqdm`

## Установка
Если `python3` не находится при вводе в терминал, но он точно стоит, то скорее всего нужный альяс `python`.

### Установка из исходников

#### [var 1]. Установка через PIP с гита
```
pip install git+https://github.com/benhacka/vk_dump_extractor
```
или по правильному: 
```
python3 -m pip install git+https://github.com/benhacka/vk_dump_extractor
```


#### [var 2]. Установка из локально скаченных исходников
```
cd
git clone https://github.com/benhacka/vk_dump_extractor
cd vk_dump_extractor
python3 setup.py install --user
```


После установки запустить скрипт можно набрав в командной строке `vk-dump-extractor`

### Запуск без установки - херовый вар
В случае такого запуска необходимо вручную установить зависимости, которые лежат в корне:  
`pip install -r requirements.txt`  
В пакете `vk_dump_extracotor` лежит модуль `dialog_extractor.py`, в целом можно запускать только его по классике из командной строки:  
`python3 dialog_extractor.py`  
Для лини можно сделать исполняемым:  
`chmod +x dialog_extractor.py`
и после этого из терминала: `./dialog_extractor.py`  

## Help menu (`vk-dump-extractor --help`):
Описание ниже...
```bash
usage: vk-dump-extractor [-h] -t TARGET_DIR_FILE_PATH [-ag] [-ab] [-cg] [-cb]
                         [-an ATTACHMENT_DIR_NAME] [-dn DIALOG_DIR_NAME]
                         [-gn GIRL_DIR_NAME] [-bn BOY_DIR_NAME] [-pn PHOTO_FILE_NAME]
                         [--thread-count THREAD_COUNT]

optional arguments:
  -h, --help            show this help message and exit
  -t TARGET_DIR_FILE_PATH, --target-dir-file-path TARGET_DIR_FILE_PATH
                        Target path
  -ag, --attachment-girls
                        Download photos from attachment with girls
  -ab, --attachment-boys
                        Download photos from attachment with boys
  -cg, --chat-girls     Download photos from attachment with girls
  -cb, --chat-boys      Download photos from attachment with boys
  -an ATTACHMENT_DIR_NAME, --attachment-dir-name ATTACHMENT_DIR_NAME
                        Attachment directory name. Default: Вложения
  -dn DIALOG_DIR_NAME, --dialog-dir-name DIALOG_DIR_NAME
                        Dialog directory name. Default: Диалоги. "." for root dir (old
                        style hierarchy)
  -gn GIRL_DIR_NAME, --girl-dir-name GIRL_DIR_NAME
                        Girl dir name. Default: Девочки
  -bn BOY_DIR_NAME, --boy-dir-name BOY_DIR_NAME
                        Boy dir name. Default: Парни
  -pn PHOTO_FILE_NAME, --photo-file-name PHOTO_FILE_NAME
                        Photo htm(l) file name. Default photos.html
  --thread-count THREAD_COUNT
                        Max download coroutines (thread) count. Default: 100

```

## Использование

### Иерархии:

Известно 2 вида иерархий:
1. Новая иерархия:
```bash
.
├── ./Вложения
│   ├── ./Вложения/Девочки
│   │   ├── ./Вложения/Девочки/photos.html
│   │   └── ./Вложения/Девочки/videos.html
│   └── ./Вложения/Парни
│       ├── ./Вложения/Парни/photos.html
│       └── ./Вложения/Парни/videos.html
├── ./Диалоги
│   ├── ./Диалоги/Девочки
│   │   ├── .../*.html
│   └── ./Диалоги/Парни
│       ├── .../*.html
```
2. Старая иерархия:
```bash
.
├── ./all_images
│   ├── ./all_images/parni
│   │      └── ./all_images/parni/images.htm
│   └── ./all_images/telki
│       └── ./all_images/telki/images.htm
├── ./all_videos
│   ├── ./all_videos/parni
│   │   └── ./all_videos/parni/videos.htm
│   └── ./all_videos/telki
│       └── ./all_videos/telki/videos.htm
├── ./parni
│   ├── .../*.htm
├── ./telki
│   ├── .../*.htm
```

Из коробки скрипт заточен на новую иерархию (заданы нужные имена каталогов по умолчанию), но можно натравить его и на старую, задавая нужные аргументы запуска.

### Аргументы запуска:
- `-t` - папка с дампом
- `-ag` - скачка всех фото из вложений с Ж  
- `-ab` - скачка все фото из вложений с М
- `-cg`- скачка все фото из диалогов с Ж
- `-cb` - скачка всех фото из диалогов с М
- `-an` - имя каталога со вложениями **[по умолчанию: Вложения]**
- `-dn` - имя каталога с диалогами, можно указать точку, 
  что укажет на корень папки (полезно для старой иерархии) **[по умолчанию: Диалоги]**
- `-gn` - имя каталога с Ж **[по умолчанию: Девочки]**
- `-bn` - имя каталога с М **[по умолчанию: Парни]**
- `-pn` - имя файла с фото (вложения) **[по умолчанию: photos.html]**
- `--thread-count` - количество потоков (корутин) для скачки **[по умолчанию: 100]**

### Про скачку:
*Нет смысла скачивать сразу и из вложений и из диалогов, там все равно одно и тоже. В чем разница:*
- парсинг из вложений происходит почти моментально, однако в сгенерированных там ссылках нет информации об отправителе и времени.
- парсинг из диалогов происходит дольше, но при этом есть информация о времени отправки фото и самом отправителе, при этом они хранятся для каждого диалога отдельно

Если не жалко времени на парс (который происходит на всех потоках процах), тогда на мой взгляд лучше парсить из диалогов, это дает больше гибкости при последующей ручной фильтрации.

### Примеры применения
Предположим, что контент в _Anna FooBar_  
_для удобства можно перейти в нужную папку в терминале и в качестве аргумента -t передавать `.`, 
то есть базовый запуску будет `vk-dump-extractor -t .`_  
**Для новой иерархии**:
- скачка всех фото из диалогов
    - с М: `vk-dump-extractor -t "./Anna FooBar" -cb`
    - с Ж: `vk-dump-extractor -t "./Anna FooBar" -cg`
- скачка всех фото из диалогов
    - с М: `vk-dump-extractor -t "./Anna FooBar" -ab`
    - с Ж: `vk-dump-extractor -t "./Anna FooBar" -ag`
    
**Для старой иерархии**:
- скачка всех фото из диалогов
    - с М: `vk-dump-extractor -t "./Anna FooBar" -cb -bn parni -dn .`
    - с Ж: `vk-dump-extractor -t "./Anna FooBar" -cg -gn telki -dn .`
- скачка всех фото из диалогов
    - с М: `vk-dump-extractor -t "./Anna FooBar" -ab -an all_images  -bn parni -pn images.htm`
    - с Ж: `vk-dump-extractor -t "./Anna FooBar" -ag -an all_images  -gn telki -pn images.htm`
    


В целом можно комбинировать аргументы или вообще запустить со всеми, для скачки требует хотя бы один из `-c[b/g]` или `-a[b/g]`  

**Скачка всего, что есть:**
- Скачать все с новой иерархией:
`vk-dump-extractor -t "./Anna FooBar" -cb -cg -ab -ag`
- Скачать все со старой иерархией:
`vk-dump-extractor -t "./Anna FooBar" -cb -cg -ab -ag -dn . -bn parni -gn telki -an all_image -pn images.htm`  


### Переместить все фото в одну папку (bash):  
Перейти в терминале в корневую папку с диалогами пола.
Пусть интересуют фотографии, которые были отправлены _парням_:  
- Новая иерархия `cd ./Диалоги/Парни`
- Старая иерархия `cd ./parni`  

И в этой папке выполнить команду, которая создает общую папку, рекурсивно ищет jpg исключая саму папку и перемещает. 
```bash
mkdir -p common_photos
find . -name "*.jpg" -not -path "./common_photos/*"  | xargs -I '{}' mv {} common_photos
```

Также манипулируя глоб-аргументом `-name`, который в базовом примере `*.jpg`, можно например переместить только фотографии нужного человека, имя человека зашито в имя фото (а вот и выигрыш от долго парса).