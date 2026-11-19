"""Read-only checks for a trusted CAD-exported DXF and matching PDF."""
import argparse
from collections import Counter
import json
from pathlib import Path

import ezdxf
from omnicad.paper import check_pdf


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dxf",type=Path)
    parser.add_argument("pdf",type=Path)
    parser.add_argument("--sheet-mm",nargs=2,type=float,required=True)
    parser.add_argument("--count",action="append",default=[],metavar="SPACE:TYPE=COUNT",
                        help="SPACE is model or the exact named layout")
    options=parser.parse_args()
    doc=ezdxf.readfile(options.dxf)
    audit=doc.audit()
    checks=[]
    for item in options.count:
        space,raw=item.split(":",1)
        typ,expected=raw.split("=",1)
        layout=doc.modelspace() if space=="model" else doc.layouts.get(space)
        found=Counter(e.dxftype() for e in layout)[typ.upper()]
        checks.append({"space":space,"type":typ,"actual":found,"expected":int(expected),"ok":found==int(expected)})
    paper=check_pdf(options.pdf,{"sheet":{"size_mm":options.sheet_mm}})
    result={"audit_errors":len(audit.errors),"audit_fixes":len(audit.fixes),"counts":checks,"paper":paper,
            "content_equivalence":"Not inferred from page dimensions or entity counts."}
    print(json.dumps(result,ensure_ascii=True,indent=2))
    return int(bool(audit.errors or audit.fixes or not paper["paper_and_crop_ok"] or any(not q["ok"] for q in checks)))


if __name__=="__main__":
    raise SystemExit(main())
