#!/usr/bin/env python3
"""Make a deck .pptx open in PowerPoint (desktop and online).

Older builds stripped parts PowerPoint needs (presProps, viewProps, docProps) and blanked
every shape name. This puts the parts back from python-pptx's default template and names
each shape "Shape <id>". Safe to run on a file that is already fine.
Usage: fix_pptx.py <file.pptx> [...]"""
import io, os, re, sys, zipfile
import pptx

TPL = zipfile.ZipFile(os.path.join(os.path.dirname(pptx.__file__), "templates", "default.pptx"))
PARTS = {  # part: (content type, owning rels file, relationship type, target)
    "ppt/presProps.xml": ("application/vnd.openxmlformats-officedocument.presentationml.presProps+xml",
                          "ppt/_rels/presentation.xml.rels",
                          "http://schemas.openxmlformats.org/officeDocument/2006/relationships/presProps", "presProps.xml"),
    "ppt/viewProps.xml": ("application/vnd.openxmlformats-officedocument.presentationml.viewProps+xml",
                          "ppt/_rels/presentation.xml.rels",
                          "http://schemas.openxmlformats.org/officeDocument/2006/relationships/viewProps", "viewProps.xml"),
    "docProps/core.xml": ("application/vnd.openxmlformats-package.core-properties+xml", "_rels/.rels",
                          "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties", "docProps/core.xml"),
    "docProps/app.xml": ("application/vnd.openxmlformats-officedocument.extended-properties+xml", "_rels/.rels",
                         "http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties", "docProps/app.xml"),
}


def fix(path):
    zin = zipfile.ZipFile(path)
    files = {n: zin.read(n) for n in zin.namelist()}
    infos = {i.filename: i for i in zin.infolist()}
    zin.close()
    added = []
    for part, (ctype, rels, rtype, target) in PARTS.items():
        if part in files:
            continue
        files[part] = TPL.read(part)
        ct = files["[Content_Types].xml"]
        files["[Content_Types].xml"] = ct.replace(
            b"</Types>", f'<Override PartName="/{part}" ContentType="{ctype}"/></Types>'.encode())
        r = files[rels]
        used = {int(x) for x in re.findall(rb'Id="rId(\d+)"', r)}
        rid = max(used | {0}) + 1
        while rid in used:
            rid += 1
        files[rels] = r.replace(b"</Relationships>",
                                f'<Relationship Id="rId{rid}" Type="{rtype}" Target="{target}"/></Relationships>'.encode())
        added.append(part)
    named = 0
    for n in list(files):
        if re.match(r"ppt/slides/slide\d+\.xml$", n):
            def name(m):
                return m.group(1) + b' name="Shape ' + m.group(2) + b'"'
            new, k = re.subn(rb'(<p:cNvPr id="(\d+)") name=""', name, files[n])
            files[n] = new
            named += k
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        # [Content_Types].xml first, as Office expects
        for n in ["[Content_Types].xml"] + [n for n in files if n != "[Content_Types].xml"]:
            z.writestr(infos.get(n) or zipfile.ZipInfo(n, date_time=(2026, 1, 1, 0, 0, 0)), files[n],
                       compress_type=zipfile.ZIP_DEFLATED)
    open(path, "wb").write(out.getvalue())
    print(path, "added", added or "nothing", "named", named, "shapes")


if __name__ == "__main__":
    for f in sys.argv[1:]:
        fix(f)
