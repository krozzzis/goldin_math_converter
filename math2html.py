import os
import shutil
import re
import requests
import zipfile
import latex2mathml.converter
import hashlib
import ziamath as zm
from ebooklib import epub


def _download_file(url: str, file_path: str, force=False):
    if os.path.exists(file_path) and not force:
        print(f"Using existing {file_path}")
        return
    print(f"Downloading {file_path}...")
    file = requests.get(url)
    open(file_path, "wb").write(file.content)


def get_files(url="https://notabug.org/amg/math/archive/master.zip", output=""):
    zip_path = output + "master.zip"
    math_path = output + "math"

    _download_file(url, zip_path)

    if os.path.exists(math_path):
        print(f"Using existing {math_path}")
    else:
        print(f"Extracting {zip_path}")

        with zipfile.ZipFile(zip_path, mode="r") as archive:
            archive.extract(output + "math/math.zip")

    print("Extracting math.zip")
    with zipfile.ZipFile(output + "math/math.zip", mode="r") as archive:
        archive.extractall(path=output + "math")


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


def gen_index(chapters: list, create_svg: bool=False) -> str:
    result = []
    result += ['<article>']
    result += ['<nav>']
    result += ['<ul>']

    for chapter in chapters[1:]:
        name = chapter[1]
        path = chapter[0]
        result += ["<li>"]
        if create_svg:
            result += [f'<a href="{path}_svg.html">{name}</a>']
        else:
            result += [f'<a href="{path}_mathml.html">{name}</a>']
        result += ["</li>"]

    result += ['</ul>']
    result += ['</nav>']
    result += ['</article>']
    return "\n".join(result)


def convert_formula_svg(content: str, display: bool=False) -> str:
    try:
        filename = hashlib.md5(content.encode()).hexdigest()
        if not os.path.exists(f'result/images/{filename}.svg'):
            content = content.replace('\\exist', '\\exi')
            content = content.replace('\\tg', 'tg')
            svg_img = zm.Math.fromlatex(content, size=16).svg()
            with open(f'result/images/{filename}.svg', 'w') as file:
                file.write(svg_img)
        content = ""
        if display:
            content = f'<img class="disp_formula" src="images/{filename}.svg"/>'
        else:
            content = f'<img class="formula" src="images/{filename}.svg"/>'
        return content
    except Exception as e:
        print(f'Error: {content} | {e}')
        return "<p>ABOBA</p>"

def convert_formula_mathml(content: str, display: bool=False) -> str:
    mathml = latex2mathml.converter.convert(content)
    content = ""
    if display:
        content = f'<span class="disp_formula">{mathml}</p>'
    else:
        content = f'{mathml}'
    return content


def process_content(content: str, chapter_num: int, practice_def: int=0, mathml: bool=True) -> str:
    # file.write('.formula { display: block; text-align: center; margin: 1em 0; }')
    content = content.replace('---', '—')
    content = content.replace('--', '–')
    content = content.replace('\\vc', '\\overrightarrow')

    for cont in re.finditer(r'__(.+?)__', content, flags=re.DOTALL):
        content = content.replace(cont.group(), f'<nobr>{cont.group(1)}</nobr>')

    # integral
    for integral in re.finditer(r'\\Int{(.*?)}{(.*?)}', content, flags=re.DOTALL):
        a = integral.group(1)
        b = integral.group(2)
        if a and b:
            content = content.replace(integral.group(), r'\int\limits^{' + b + r'}_{' + a + r'}')
        else:
            content = content.replace(integral.group(), r'\int ')

    # display formulas
    for formula in re.finditer(r'\$\$(.+?)\$\$', content, flags=re.DOTALL):
        ff = formula.group(1)
        if len(ff) == 0:
            continue
        content = content.replace(formula.group(), convert_formula_mathml(ff, display=True) if mathml \
                else convert_formula_svg(ff, display=True))

    # in-text formulas
    for formula in re.finditer(r'\$(.+?)\$', content, flags=re.DOTALL):
        ff = formula.group(1)
        if len(ff) == 0:
            continue
        content = content.replace(formula.group(), convert_formula_mathml(ff) if mathml \
                else convert_formula_svg(ff))

    # display images
    for img in re.finditer(r'\[\[(.+?)\]\]', content, flags=re.DOTALL):
        fields = img.group(1).split("^")
        file_name = fields[0] + ".svg"
        # with open(f'math/img/{file_name}') as f:
        #     cnt = re.search(r'<svg.*svg>', f.read(), flags=re.DOTALL).group()
        #     content = content.replace(img.group(), cnt)
        shutil.copyfile(f'math/img/{file_name}', f'result/images/{file_name}')
        res = f'<img class="figure" style="width: {fields[1]}cm; display: block; margin: 12pt auto 12pt" src="images/{file_name}">' 
        if len(fields) >= 3:
            res += f'<figcaption style="text-align: center; font-size: 90%;">{fields[2]}</figcaption>'
        content = content.replace(img.group(), res)

    content = re.sub(r'\\so{(.+?)}', r'<span class="razr">\1</span>', content)


    for (i, match) in enumerate(re.finditer(r'\\punkt{(.*?)}', content)):
        a = re.search(r'\\punkt{(.*?)}', match.group()).group(1)
        content = content.replace(match.group(), f'<strong>{chapter_num}.{i+1} <b>{a}</b></strong>')

    counter = practice_def
    for _ in re.finditer(r'\\zNum', content): 
        content = content.replace(r'\zNum', f'<em style="font-weight: bold; font-style: normal; background: #eee; padding:2px;">{counter}</em>', 1)
        counter += 1

    content = re.sub(r'[\n]{3,}', r'\n\n', content)
    ps = content.split("\n\n")
    for a in ps:
        p = a.strip()
        if len(p) == 0:
            continue
        content = content.replace(a, f'<p>{p}</p>')

    return content


def basic_template(content: str) -> str:
    result = []
    result += ["<!DOCTYPE html>"]
    result += ["<html>"]

    result += ["<head>"]
    result += ["<style>"]
    result += [".disp_formula { display: block; text-align: center; margin: 1em 0; }"]
    result += [".formula { vertical-align: middle; display: inline-block; }"]
    result += [".razr { text-spacing: 3px; }"]
    result += [".figure { display: block; margin: 12pt auto 12pt}"]
    result += ["figcaption { text-align: center; font-size: 90%; }"]
    result += ["em { font-weight: bold; font-style: normal; background: #eee; padding:2px; margin-right: 5px; }"]
    result += ["body { width: 17cm; margin: auto; }"]
    result += ["</style>"]
    result += ["</head>"]

    result += ["<body>"]
    result += [content]
    result += ["</body>"]

    result += ["</html>"]
    return "\n".join(result)


def get_content(path: str) -> str:
    with open(path, 'r') as file:
        content = file.read()
        content = content.split('`')[1]
        return content


def main():
    create_svg = False
    get_files()
    chapters = get_chapters("math/static/config.js")
    try:
        os.mkdir("result")
    except:
        pass

    try:
        os.mkdir("result/images")
    except:
        pass

    # book = epub.EpubBook()
    # book.set_identifier('ABOBA')
    # book.set_title('ABOBA')
    # book.set_language('ru')
    # book.add_author('Goldin')
    # book.add_metadata('DC', 'description', 'This is description for my book')

    # generate index file
    index = gen_index(chapters, create_svg)
    with open("result/index.html", "w") as f:
        content = basic_template(index)

        # c1 = epub.EpubHtml(title='index',
        #            file_name=f'index.xhtml',
        #            lang='ru')
        # c1.set_content(content)
        # book.add_item(c1)
        # book.spine += [c1]

        f.write(content)

    toc = []
    for (num, chapter) in enumerate(chapters):
        path = chapter[0]
        start_with = 1
        if len(chapter) >= 3:
            start_with = int(chapter[2]) + 1

        content = get_content(f'math/content/{path}.js')
        if create_svg:
            print(f"Processing {path}_svg")
            content_svg = process_content(content, num, start_with, mathml=False)
            content_svg = basic_template(content_svg)

        print(f"Processing {path}_mathml")
        content_mathml = process_content(content, num, start_with)
        content_mathml = basic_template(content_mathml)

        # c1 = epub.EpubHtml(title=f'{path}',
        #            file_name=f'{path}.xhtml',
        #            lang='ru')
        # content = basic_template(content)
        # c1.set_content(content)
        # book.add_item(c1)
        # book.spine += [c1]
        # toc += [epub.Link(f'{path}.xhtml', path, path)]

        if create_svg:
            with open(f'result/{path}_svg.html', "w") as f:
                f.write(content_svg)

        with open(f'result/{path}_mathml.html', "w") as f:
            f.write(content_mathml)

    # for file in os.listdir("result/images"):
    #     if file.endswith(".svg"):
    #         with open(f'result/images/{file}') as f:
    #             img = epub.EpubItem(uid=file,
    #                                     file_name=f'images/{file}',
    #                         media_type="image/svg",
    #                         content=f.read())
    #             book.add_item(img)
    # book.add_item(epub.EpubNcx())
    # book.add_item(epub.EpubNav())
    # book.toc = toc
    # epub.write_epub('math.epub', book)


if __name__ == "__main__":
    main()
