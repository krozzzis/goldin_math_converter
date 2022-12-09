import os
import re
import requests
import zipfile


def download_file(url: str, file_path: str, force=False):
    if os.path.exists(file_path) and not force:
        print(f"Using existing {file_path}")
        return
    print(f"Downloading {file_path}...")
    file = requests.get(url)
    open(file_path, "wb").write(file.content)


def get_files():
    zip_url = "https://notabug.org/amg/math/archive/master.zip"
    zip_path = "master.zip"
    math_path = "math"

    download_file(zip_url, zip_path)

    if os.path.exists(math_path):
        print(f"Using existing {math_path}")
    else:
        print(f"Extracting {zip_path}")

        with zipfile.ZipFile(zip_path, mode="r") as archive:
            archive.extract("math/math.zip")

    print("Extracting math.zip")
    with zipfile.ZipFile("math/math.zip", mode="r") as archive:
        archive.extractall(path="math")


def get_chapters(path: str) -> list:
    chapters = []
    with open(path, "r") as file:
        content = file.read()
        values = re.findall(r'\[.*\]', content)
        for chapter in values:
            components = chapter.replace('[', '').replace(']', '').split(',')
            components = list(map(lambda x: x.strip().replace('"', ''), components))

            chapters.append(components)
    return chapters


def gen_index(path: str, chapters: list):
    with open(path, "w") as file:
        file.write("<!DOCTYPE html><html>")
        file.write('<head><style>\n')
        file.write('.content{\n')
        file.write('display: grid;\n')
        file.write('}</style></head>')
        file.write('<body><div class="content">')
        for chapter in chapters:
            name = chapter[1]
            path = chapter[0]
            file.write(f'<a href="{path}.html">{name}</a>')
        file.write("</div></body></html>")

def main():
    get_files()
    chapters = get_chapters("math/static/config.js")
    try:
        os.mkdir("result")
    except:
        pass
    gen_index("result/index.html", chapters)

if __name__ == "__main__":
    main()
