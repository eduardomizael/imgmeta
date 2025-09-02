
import argparse
import subprocess
from shutil import which
from pathlib import Path
import json
import sys
import tempfile, webbrowser, os, platform


EXIFTOOL = "exiftool"

def check_exiftool():
    if which(EXIFTOOL) is None:
        print("Erro: exiftool não encontrado. Instale em https://exiftool.org", file=sys.stderr)
        sys.exit(1)

def iter_targets(paths, recursive=False, exts=None):
    exts = {e.lower().lstrip(".") for e in (exts or [])}
    for p in paths:
        p = Path(p)
        if p.is_dir():
            glob = "**/*" if recursive else "*"
            for f in p.glob(glob):
                if f.is_file():
                    if not exts or f.suffix.lower().lstrip(".") in exts:
                        yield f
        elif p.is_file():
            if not exts or p.suffix.lower().lstrip(".") in exts:
                yield p
        else:
            # glob pattern
            for f in Path().glob(str(p)):
                if f.is_file():
                    if not exts or f.suffix.lower().lstrip(".") in exts:
                        yield f

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return r.stdout

def add_values(path, people=None, tags=None):
    cmd = [EXIFTOOL, "-overwrite_original", "-charset", "iptc=utf8"]
    if tags:
        for t in tags:
            cmd += [f"-XMP-dc:Subject+={t}", f"-IPTC:Keywords+={t}"]
    if people:
        for p in people:
            cmd += [f"-XMP-Iptc4xmpExt:PersonInImage+={p}"]
    cmd += [str(path)]
    run(cmd)

def remove_values(path, people=None, tags=None):
    cmd = [EXIFTOOL, "-overwrite_original", "-charset", "iptc=utf8"]
    if tags:
        for t in tags:
            cmd += [f"-XMP-dc:Subject-={t}", f"-IPTC:Keywords-={t}"]
    if people:
        for p in people:
            cmd += [f"-XMP-Iptc4xmpExt:PersonInImage-={p}"]
    cmd += [str(path)]
    run(cmd)

def clear_values(path, clear_people=False, clear_tags=False):
    if not (clear_people or clear_tags):
        return
    cmd = [EXIFTOOL, "-overwrite_original", "-charset", "iptc=utf8"]
    if clear_tags:
        cmd += ["-XMP-dc:Subject=", "-IPTC:Keywords="]
    if clear_people:
        cmd += ["-XMP-Iptc4xmpExt:PersonInImage="]
    cmd += [str(path)]
    run(cmd)

def read_values(path):
    # Usa JSON do exiftool pra evitar parsing frágil
    out = run([EXIFTOOL, "-json",
               "-XMP-dc:Subject",
               "-XMP-Iptc4xmpExt:PersonInImage",
               "-IPTC:Keywords",
               str(path)])
    data = json.loads(out)[0]
    def norm(v):
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            return [v]
        return []
    return {
        "file": str(path),
        "tags": sorted(set(norm(data.get("Subject", [])) + norm(data.get("Keywords", [])))),
        "people": sorted(set(norm(data.get("PersonInImage", []))))
    }

def matches_filters(meta, people_any, people_all, tags_any, tags_all):
    ppl = set(m.lower() for m in meta["people"])
    tgs = set(m.lower() for m in meta["tags"])
    if people_any and not (set(x.lower() for x in people_any) & ppl):
        return False
    if people_all and not set(x.lower() for x in people_all).issubset(ppl):
        return False
    if tags_any and not (set(x.lower() for x in tags_any) & tgs):
        return False
    if tags_all and not set(x.lower() for x in tags_all).issubset(tgs):
        return False
    return True

def cmd_add(args):
    check_exiftool()
    count = 0
    for f in iter_targets(args.paths, args.recursive, args.ext):
        add_values(f, args.people, args.tags)
        if not args.quiet:
            print(f"[add] {f}")
        count += 1
    if not args.quiet:
        print(f"Concluído: {count} arquivo(s).")

def cmd_remove(args):
    check_exiftool()
    count = 0
    for f in iter_targets(args.paths, args.recursive, args.ext):
        remove_values(f, args.people, args.tags)
        if not args.quiet:
            print(f"[remove] {f}")
        count += 1
    if not args.quiet:
        print(f"Concluído: {count} arquivo(s).")

def cmd_clear(args):
    check_exiftool()
    count = 0
    for f in iter_targets(args.paths, args.recursive, args.ext):
        clear_values(f, clear_people=args.people, clear_tags=args.tags)
        if not args.quiet:
            print(f"[clear] {f}")
        count += 1
    if not args.quiet:
        print(f"Concluído: {count} arquivo(s).")

def cmd_list(args):
    check_exiftool()
    items = []
    for f in iter_targets(args.paths, args.recursive, args.ext):
        meta = read_values(f)
        items.append(meta)

    # Se pediu JSON, imprime tudo em formato estruturado
    if getattr(args, "json", False):
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return

    # Caso contrário, saída "bonita" em texto
    for meta in items:
        print(meta["file"])
        if meta["people"]:
            print("  pessoas:", ", ".join(meta["people"]))
        if meta["tags"]:
            print("  tags   :", ", ".join(meta["tags"]))
        if not meta["people"] and not meta["tags"]:
            print("  (sem pessoas/tags)")
        if not args.quiet:
            print()


def cmd_search(args):
    check_exiftool()
    results = []
    for f in iter_targets(args.paths, args.recursive, args.ext):
        meta = read_values(f)
        people_any = args.people if args.mode == "any" else None
        people_all = args.people if args.mode == "all" else None
        tags_any = args.tags if args.mode == "any" else None
        tags_all = args.tags if args.mode == "all" else None
        if matches_filters(meta, people_any, people_all, tags_any, tags_all):
            results.append(meta)

    # Se pediu JSON, imprime todos os resultados de forma estruturada
    if getattr(args, "json", False):
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    # Saída textual (como era antes)
    for m in results:
        print(m["file"])
        if args.show_meta:
            if m["people"]:
                print("  pessoas:", ", ".join(m["people"]))
            if m["tags"]:
                print("  tags   :", ", ".join(m["tags"]))
            print()
    print(f"Total: {len(results)} arquivo(s).")

def open_in_viewer(path: Path):
    # tentar no navegador (funciona bem para imagens)
    try:
        webbrowser.open(path.resolve().as_uri())
        return
    except Exception:
        pass
    # fallback por SO
    system = platform.system()
    if system == "Darwin":
        subprocess.run(["open", str(path)])
    elif system == "Windows":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        subprocess.run(["xdg-open", str(path)])

def extract_thumbnail_to_temp(path: Path) -> Path:
    # extrai ThumbnailImage com exiftool (-b = binary) e salva num arquivo temporário
    tmp = Path(tempfile.mkstemp(suffix=".jpg")[1])
    out = subprocess.run(
        [EXIFTOOL, "-b", "-ThumbnailImage", str(path)],
        capture_output=True
    )
    if out.returncode != 0 or not out.stdout:
        raise RuntimeError("Sem miniatura embutida (ThumbnailImage) ou erro ao extrair.")
    with open(tmp, "wb") as f:
        f.write(out.stdout)
    return tmp

def cmd_show(args):
    check_exiftool()
    if len(args.paths) != 1:
        print("Use exatamente um arquivo no comando 'show'.", file=sys.stderr)
        sys.exit(2)

    f = next(iter_targets(args.paths, False, args.ext), None)
    if not f:
        print("Arquivo não encontrado ou extensão não permitida.", file=sys.stderr)
        sys.exit(2)

    meta = read_values(f)

    if args.json:
        print(json.dumps(meta, ensure_ascii=False, indent=2))
    else:
        print(meta["file"])
        if meta["people"]:
            print("  pessoas:", ", ".join(meta["people"]))
        if meta["tags"]:
            print("  tags   :", ", ".join(meta["tags"]))
        if not meta["people"] and not meta["tags"]:
            print("  (sem pessoas/tags)")

    if args.open:
        try:
            if args.thumb:
                thumb_path = extract_thumbnail_to_temp(Path(meta["file"]))
                open_in_viewer(thumb_path)
            else:
                open_in_viewer(Path(meta["file"]))
        except Exception as e:
            print(f"Falha ao abrir: {e}", file=sys.stderr)
            sys.exit(3)

def build_parser():
    p = argparse.ArgumentParser(
        prog="imgmeta",
        description="CLI para gerenciar pessoas e tags (XMP/IPTC) em imagens usando exiftool."
    )
    p.add_argument("--ext", nargs="*", default=["jpg","jpeg","png","heic","tif","tiff"],
                   help="Extensões aceitáveis (sem ponto). Default: comuns de imagem.")
    p.add_argument("-r", "--recursive", action="store_true", help="Percorre diretórios recursivamente.")
    p.add_argument("-q", "--quiet", action="store_true", help="Menos saída.")

    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common_targets(sp):
        sp.add_argument("paths", nargs="+", help="Arquivos, pastas ou padrões glob.")

    def add_people_tags(sp, need_any=False):
        sp.add_argument("--people", "--pessoas", nargs="*", default=[],
                        help="Nomes de pessoas (use aspas p/ nomes com espaço).")
        sp.add_argument("--tags", nargs="*", default=[],
                        help="Tags/keywords.")
        if need_any:
            sp.add_argument("--mode", choices=["any","all"], default="any",
                            help="Combinação para busca: any (padrão) ou all.")

    sp_add = sub.add_parser("add", help="Adiciona pessoas/tags sem sobrescrever o que já existe.")
    add_common_targets(sp_add)
    add_people_tags(sp_add)

    sp_remove = sub.add_parser("remove", help="Remove pessoas/tags específicas.")
    add_common_targets(sp_remove)
    add_people_tags(sp_remove)

    sp_clear = sub.add_parser("clear", help="Apaga todos os valores de pessoas e/ou tags.")
    add_common_targets(sp_clear)
    sp_clear.add_argument("--people", action="store_true", help="Limpa somente pessoas.")
    sp_clear.add_argument("--tags", action="store_true", help="Limpa somente tags.")
    # se nenhum for passado, não faz nada (proteção)

    sp_list = sub.add_parser("list", help="Lista pessoas/tags dos arquivos.")
    add_common_targets(sp_list)
    sp_list.add_argument("--json", action="store_true", help="Saída em JSON.")

    sp_search = sub.add_parser("search", help="Busca imagens por pessoas/tags.")
    add_common_targets(sp_search)
    add_people_tags(sp_search, need_any=True)
    sp_search.add_argument("--show-meta", action="store_true", help="Exibe metadados nos resultados.")
    sp_search.add_argument("--json", action="store_true", help="Saída em JSON.")

    sp_show = sub.add_parser("show", help="Mostra metadados de um único arquivo e opcionalmente abre a imagem.")
    sp_show.add_argument("paths", nargs=1, help="Arquivo alvo (somente um).")
    sp_show.add_argument("--open", action="store_true", help="Abre a imagem (ou miniatura) no visualizador padrão.")
    sp_show.add_argument("--thumb", action="store_true", help="Com --open, abre a ThumbnailImage embutida.")
    sp_show.add_argument("--json", action="store_true", help="Saída em JSON.")
    sp_show.add_argument("--ext", nargs="*", default=["jpg","jpeg","png","heic","tif","tiff"],
                         help="Extensões aceitáveis (sem ponto).")

    return p

def main():
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.cmd == "add":
            cmd_add(args)
        elif args.cmd == "remove":
            cmd_remove(args)
        elif args.cmd == "clear":
            cmd_clear(args)
        elif args.cmd == "list":
            cmd_list(args)
        elif args.cmd == "search":
            cmd_search(args)
        elif args.cmd == "show":
            cmd_show(args)
        else:
            parser.print_help()
    except RuntimeError as e:
        print(f"Erro: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
