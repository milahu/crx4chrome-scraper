#!/usr/bin/env python3

import sys
import os
import re
import asyncio
import json
import time
import glob
import shutil
import hashlib

from types import SimpleNamespace

# slow init -> import later
#import aiohttp_chromium as aiohttp

class Crx:

    id = None
    num = None
    name = None
    version = None
    date = None
    requires = None
    size = None
    md5 = None
    sha1 = None
    sha256 = None

    def set_version(self, version):
        if version[0] == "v":
            version = version[1:]
        self.version = version



# https://stackoverflow.com/questions/22058048/hashing-a-file-in-python

def checksum(algo, file_path=None, data=None):
    fn = getattr(hashlib, algo)
    if data:
        return fn(data).digest()
    assert file_path
    BUF_SIZE = 65536
    hash = fn()
    with open(file_path, 'rb') as f:
        while data := f.read(BUF_SIZE):
            hash.update(data)
    return hash.digest()

def sha256sum(file_path=None, data=None):
    return checksum("sha256", file_path=file_path, data=data)

def sha1sum(file_path=None, data=None):
    return checksum("sha1", file_path=file_path, data=data)

def md5sum(file_path=None, data=None):
    return checksum("md5", file_path=file_path, data=data)



async def main():

    extension_id = sys.argv[1]
    assert len(extension_id) == 32
    assert re.fullmatch(r"[a-p]{32}", extension_id) != None

    os.makedirs(extension_id, exist_ok=True)

    done_json_files = glob.glob(f"{extension_id}/*.json")

    #sys.path.append("/path/to/aiohttp_chromium/src")

    import aiohttp_chromium as aiohttp
    import selenium_driverless
    from selenium_driverless.types.by import By

    async with aiohttp.ClientSession() as session:

        # test
        #if True:
        if False:
            url = "https://www.crx4chrome.com/crx/30710/"
            async with session.get(url) as resp:
                driver = resp._driver
                css = "#blocks-left > div > div > div:nth-child(6) > blockquote:nth-child(1) > div:nth-child(6) > p:nth-child(2) > a"
                elem = await driver.find_element(By.CSS_SELECTOR, css, timeout=10)
                text = await elem.text
                href = await elem.get_attribute("href")
                print("link", text, href)

                if True:

                    # this fails? no...
                    # ok, this works
                    referrer = url
                    url = href

                    async with session.get(url, referrer=referrer) as resp:

                        print("resp.status", resp.status)
                        print("resp._filepath", resp._filepath)

                        print("resp._wait_complete ...")
                        await resp._wait_complete(timeout=2*60)
                        print("resp._wait_complete done")

                        driver = resp._driver

                        print("sleep"); await asyncio.sleep(9999)
                else:
                    pass
            return

        print("crx_num ...")
        url = f"https://www.crx4chrome.com/apps/{extension_id}/"
        latest_crx_num = None
        crx_name = None

        async with session.get(url) as resp:

            #print(resp.status)
            #print(await resp.text())
            html = await resp.text()
            # href="/history/12345/"
            match = re.search(r'href="/history/([0-9]+)/"', html)
            assert match != None, f"not found latest_crx_num in html:\n{html}"
            latest_crx_num = int(match.group(1))
            match = re.search(r'<title>(.*?)</title>', html)
            assert match != None, f"not found title in html:\n{html}"
            # <title>Boxy SVG 3.79.3 - Free Productivity App for Chrome - Crx4Chrome</title>
            # "Boxy SVG"
            crx_name = " ".join(match.group(1).split(" - ")[0].split(" ")[:-1])

        print("latest_crx_num", latest_crx_num)
        print("crx_name", repr(crx_name))

        # loop pages of history
        print("history ...")
        history_page = 0
        num_versions = None

        crx_list = []

        print("fetching metadata")

        has_next_page = True

        while has_next_page:

            history_page += 1

            url = f"https://www.crx4chrome.com/history/{latest_crx_num}/{history_page}/"

            async with session.get(url) as resp:

                # wait for page load
                # TODO dynamic
                # TODO remove?
                await asyncio.sleep(5)

                #print(resp.status)
                #print(await resp.text())
                #html = await resp.text()

                if num_versions == None:

                    print("num_versions ...")
                    driver = resp._driver
                    css = "#blocks-left > div > div > p > b"
                    elem = await driver.find_element(By.CSS_SELECTOR, css, timeout=10)
                    text = await elem.text
                    num_versions = int(text)
                    print("num_versions", num_versions)

                    if num_versions == len(done_json_files):

                        print("we already have all json files -> stopping the history pages loop")
                        break

                # has next page?
                css = "#blocks-left > div > div > div.pagination > a.page-numbers.next"
                try:
                    await driver.find_element(By.CSS_SELECTOR, css, timeout=10)
                    print(f"parsing history page {history_page}")
                except (TimeoutError, selenium_driverless.types.webelement.NoSuchElementException):
                    print(f"parsing last history page {history_page}")
                    has_next_page = False

                # parse crx history list
                css = "#blocks-left > div > div > div:nth-child(5) > ol.history > li"

                for idx, elem in enumerate(await driver.find_elements(By.CSS_SELECTOR, css)):

                    text = await elem.text
                    crx = Crx()
                    crx.id = extension_id
                    crx.name = crx_name
                    crx_json_path = None
                    ##f"{crx.name} {crx.version}.json"
                    # loop paragraphs

                    for idx2, elem in enumerate(await elem.find_elements(By.CSS_SELECTOR, "p")):

                        if idx2 == 0:
                            # download link
                            """
                            <p style="font-size:15px;"><strong><a title="Download Boxy SVG v3.79.3 Crx" class="readmore" href="/crx/13821/">Boxy SVG v3.79.3</a> (Latest Version Crx File)</strong></p>
                            <p style="font-size:15px;"><a title="Download Boxy SVG v3.75.1 Crx" class="readmore" href="/crx/274993/">Boxy SVG v3.75.1</a> (Old Version Crx File)</p>
                            """
                            elem = await elem.find_element(By.CSS_SELECTOR, "strong > a, a")
                            href = await elem.get_attribute("href")
                            text = await elem.text # Boxy SVG v3.79.3
                            crx.set_version(text.split(" ")[-1])
                            crx.num = int(href.split("/")[-2]) # href = "https://www.crx4chrome.com/crx/274993/"
                            crx_json_path = f"{crx.id}/{crx.version}.json"
                            if os.path.exists(crx_json_path):
                                # stop parsing metadata from html
                                break
                            continue

                        """
                        <p style="padding:6px 0 0 0;">&#9658; Updated: March 20, 2022</p>
                        <p style="padding:3px 0 0 0;">&#9658; Require: Chrome 95 an up</p>
                        <p style="padding:3px 0 0 0;">&bull; File Size: 2.50 MB (2617500 Bytes)</p>
                        <p style="padding:3px 0 0 0;">&bull; MD5: dcbba472df6e7eadb29ab5e5926e5834</p>
                        <p style="padding:3px 0 0 0;">&bull; SHA1: fb2aeb4af2782b4eeeca80dc38ffdb241b524e63</p>
                        <p style="padding:3px 0 0 0;">&bull; SHA256: 075a785c515f721611785dc57601cf2ab82de96d6fa20874d0142fe9788c0686</p>
                        """
                        text = await elem.text
                        # &#9658; == triangle
                        # &bull; == circle
                        # these are decoded from html to unicode
                        # so its only 1 char
                        char0 = text[0]
                        print("char0", repr(char0))
                        text = text[2:]
                        print("text", repr(text))
                        key, val = text.split(": ")
                        print("key val", repr(key), repr(val))
                        date_format = "%B %d, %Y" # 'July 5, 2017'
                        if key == "Updated":
                            date = time.strptime(val, date_format)
                            crx.date = time.strftime("%Y-%m-%d", date)
                            continue
                        if key == "Require": crx.requires = val.replace(" an up", " and up"); continue
                        if key == "File Size":
                            try:
                                # byte size can be missing
                                # y: File Size: 2.66 MB (2785450 Bytes)
                                # n: File Size: 2.41 MB
                                crx.size = int(val.split("(")[1].split(" ")[0])
                            except IndexError:
                                pass
                            continue
                        if key == "MD5": crx.md5 = val; continue
                        if key == "SHA1": crx.sha1 = val; continue
                        # sha256 can be missing
                        if key == "SHA256": crx.sha256 = val; continue

                    if os.path.exists(crx_json_path):
                        print("reading", crx_json_path)
                        with open(crx_json_path, "r") as f:
                            # dict -> object
                            crx = json.load(f, object_hook=lambda x: SimpleNamespace(**x))
                    else:
                        #crx_json = json.dumps(crx.__dict__); print("crx_json", crx_json)
                        print("writing", crx_json_path)
                        with open(crx_json_path, "w") as f:
                            json.dump(crx.__dict__, f)

                    crx_list.append(crx)

                #await asyncio.sleep(999999)



        if num_versions == len(done_json_files):

            print("reading done json files")

            for crx_json_path in done_json_files:

                print("reading", crx_json_path)
                with open(crx_json_path, "r") as f:
                    # dict -> object
                    crx = json.load(f, object_hook=lambda x: SimpleNamespace(**x))

                crx_list.append(crx)



        print("fetching crx files")

        for crx in crx_list:

            crx_path = f"{crx.id}/{crx.version}.crx"

            if os.path.exists(crx_path):
                # TODO check file checksums
                print("keeping", crx_path)
                continue

            print("fetching", crx_path)

            url = f"https://www.crx4chrome.com/crx/{crx.num}/"

            async with session.get(url) as resp:

                driver = resp._driver

                # loop download links
                print("looping download links")
                css = "#blocks-left > div > div > div:nth-child(6) > blockquote:nth-child(1) > div:nth-child(6) > p > a"

                for idx, elem in enumerate(await driver.find_elements(By.CSS_SELECTOR, css)):

                    text = await elem.text
                    href = await elem.get_attribute("href")

                    print("text", repr(text))
                    print("href", repr(href))

                    # ignore non-download links: "Available in the Chrome Web Store"
                    if text != "Crx4Chrome":
                        print("ignoring link", repr(text))
                        continue

                    print("opening download link", repr(href))
                    referrer = url
                    url = href

                    async with session.get(url, referrer=referrer) as resp:

                        if resp.status != 200:
                            print(f"download failed with status {resp.status} -> trying next download link")
                            continue

                        print(f"resp._filepath = {repr(resp._filepath)}")

                        print("resp._wait_complete ...")
                        await resp._wait_complete(timeout=2*60)
                        print("resp._wait_complete done")

                        print("writing", crx_path)
                        if resp._filepath != None:
                            print("shutil.move resp._filepath")
                            shutil.move(resp._filepath, crx_path)
                        else:
                            # TODO implement resp._filepath
                            print("read resp.content")
                            crx_bytes = await resp.content.read()
                            with open(crx_path, "wb") as f:
                                f.write(crx_bytes)

                    is_bad_file = False

                    print("checking file", crx_path)

                    def bad_file(key, actual, expected):
                        print("checking key", key)
                        nonlocal crx_path
                        nonlocal is_bad_file
                        if actual == expected:
                            # not a bad file
                            return False
                        print(f"bad crx file {crx_path}: {key} mismatch: {actual} != {expected}")
                        is_bad_file = True
                        bad_file_path = f"{crx_path}.broken"
                        print("moving {crx_path} to {bad_file_path}")
                        os.rename(crx_path, bad_file_path)
                        print("retrying file with next download link")
                        return True

                    if hasattr(crx, "size") and crx.size:
                        actual = os.path.getsize(crx_path)
                        if bad_file("size", actual, crx.size):
                            continue

                    for algo in ["md5", "sha1", "sha256"]:
                        if not hasattr(crx, algo):
                            continue
                        expected = getattr(crx, algo)
                        if expected == None:
                            continue
                        actual = checksum(algo, crx_path).hex()
                        if bad_file(algo, actual, expected):
                            break

                    if is_bad_file:
                        continue

                    # TODO? add missing values to crx json file: size, sha256, ...

                    #await asyncio.sleep(999999)

                    # stop looping download links
                    print("done file", crx_path)
                    break



asyncio.run(main())
