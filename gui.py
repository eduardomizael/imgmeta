import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Tenta importar as funções do CLI existente
try:
    from imgmeta import imgmeta as core  # quando rodar a partir da raiz do repo
except Exception:
    # fallback: permite "python imgmeta/gui.py" diretamente
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import imgmeta as core  # type: ignore

# Preview opcional com Pillow
try:
    from PIL import Image, ImageTk  # type: ignore
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False


DEFAULT_EXTS = ["jpg", "jpeg", "png", "heic", "tif", "tiff"]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ImgMeta - Editor de Pessoas/Tags")
        self.geometry("980x600")

        try:
            core.check_exiftool()
        except SystemExit:
            # check_exiftool finaliza; capturamos para mostrar ao usuário
            messagebox.showerror(
                "ExifTool ausente",
                "Erro: exiftool não encontrado. Instale em https://exiftool.org"
            )
            self.destroy()
            return

        self.dir_var = tk.StringVar(value=str(Path.cwd()))
        self.recursive_var = tk.BooleanVar(value=False)
        self.ext_var = tk.StringVar(value=", ".join(DEFAULT_EXTS))
        self.status_var = tk.StringVar(value="Pronto")

        self.files: list[Path] = []
        self.current_path: Path | None = None

        self._build_ui()

    # UI
    def _build_ui(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Pasta:").pack(side=tk.LEFT)
        e_dir = ttk.Entry(top, textvariable=self.dir_var)
        e_dir.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 6))
        ttk.Button(top, text="Procurar…", command=self._choose_dir).pack(side=tk.LEFT)
        ttk.Checkbutton(top, text="Recursivo", variable=self.recursive_var).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(top, text="Extensões:").pack(side=tk.LEFT, padx=(8, 0))
        ttk.Entry(top, width=28, textvariable=self.ext_var).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(top, text="Carregar", command=self.load_files).pack(side=tk.LEFT, padx=(8, 0))

        body = ttk.Frame(self, padding=(8, 0, 8, 8))
        body.pack(fill=tk.BOTH, expand=True)

        # Lista de arquivos como miniaturas (esquerda)
        left = ttk.Frame(body)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Label(left, text="Arquivos").pack(anchor=tk.W)
        left_mid = ttk.Frame(left)
        left_mid.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.use_thumbs = PIL_AVAILABLE
        self.thumb_items: list[dict] = []  # para modo miniatura
        # parâmetros de miniatura
        self._thumb_size = (160, 160)
        self._thumb_pad = 6
        self._thumb_cols = 1
        if self.use_thumbs:
            # Canvas com rolagem e um frame interno para as miniaturas
            self.thumb_canvas = tk.Canvas(left_mid, highlightthickness=0)
            self.thumb_scroll = ttk.Scrollbar(left_mid, orient="vertical", command=self.thumb_canvas.yview)
            self.thumb_canvas.configure(yscrollcommand=self.thumb_scroll.set)
            self.thumb_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.thumb_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            self.thumb_frame = ttk.Frame(self.thumb_canvas)
            self.thumb_window_id = self.thumb_canvas.create_window((0, 0), window=self.thumb_frame, anchor="nw")
            self.thumb_frame.bind(
                "<Configure>",
                lambda e: self.thumb_canvas.configure(scrollregion=self.thumb_canvas.bbox("all"))
            )
            # suporte a rolagem com roda do mouse
            self.thumb_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
            # reflow ao redimensionar
            self.thumb_canvas.bind("<Configure>", self._on_thumb_canvas_configure)
        else:
            # Fallback: Listbox textual
            self.file_list = tk.Listbox(left_mid, activestyle="dotbox", selectmode=tk.EXTENDED)
            self.file_list.pack(fill=tk.BOTH, expand=True)
            self.file_list.bind("<<ListboxSelect>>", self._on_select_file)

        # Botões inferiores da coluna esquerda
        btns_left = ttk.Frame(left)
        btns_left.pack(side=tk.BOTTOM, fill=tk.X, pady=(6, 0))
        ttk.Button(btns_left, text="Atualizar seleção", command=self.refresh_current).pack(side=tk.LEFT)
        ttk.Button(btns_left, text="Abrir seleção", command=self._open_selection).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(btns_left, text="Abrir imagem", command=lambda: self._open_current(False)).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(btns_left, text="Abrir miniatura", command=lambda: self._open_current(True)).pack(side=tk.LEFT, padx=(6, 0))

        btns_left = ttk.Frame(left)
        btns_left.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(btns_left, text="Atualizar seleção", command=self.refresh_current).pack(side=tk.LEFT)
        ttk.Button(btns_left, text="Abrir imagem", command=lambda: self._open_current(False)).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(btns_left, text="Abrir miniatura", command=lambda: self._open_current(True)).pack(side=tk.LEFT, padx=(6, 0))

        # Metadados (direita)
        right = ttk.Frame(body)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12, 0))

        meta_top = ttk.Frame(right)
        meta_top.pack(fill=tk.X)
        self.path_label = ttk.Label(meta_top, text="(nenhum arquivo)")
        self.path_label.pack(anchor=tk.W)

        grid = ttk.Frame(right)
        grid.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        # Pessoas
        ttk.Label(grid, text="Pessoas").grid(row=0, column=0, sticky="w")
        self.people_list = tk.Listbox(grid, height=10, exportselection=False)
        self.people_list.grid(row=1, column=0, sticky="nsew")
        self.people_entry = ttk.Entry(grid)
        self.people_entry.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        ppl_btns = ttk.Frame(grid)
        ppl_btns.grid(row=3, column=0, sticky="w", pady=(4, 0))
        ttk.Button(ppl_btns, text="Adicionar", command=self._add_person).pack(side=tk.LEFT)
        ttk.Button(ppl_btns, text="Remover", command=self._remove_person).pack(side=tk.LEFT, padx=(6, 0))

        # Tags
        ttk.Label(grid, text="Tags").grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.tags_list = tk.Listbox(grid, height=10, exportselection=False)
        self.tags_list.grid(row=1, column=1, sticky="nsew", padx=(12, 0))
        self.tags_entry = ttk.Entry(grid)
        self.tags_entry.grid(row=2, column=1, sticky="ew", pady=(4, 0), padx=(12, 0))
        tag_btns = ttk.Frame(grid)
        tag_btns.grid(row=3, column=1, sticky="w", pady=(4, 0), padx=(12, 0))
        ttk.Button(tag_btns, text="Adicionar", command=self._add_tag).pack(side=tk.LEFT)
        ttk.Button(tag_btns, text="Remover", command=self._remove_tag).pack(side=tk.LEFT, padx=(6, 0))

        # Expandir colunas/linhas
        grid.rowconfigure(1, weight=1)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        # Preview
        preview_box = ttk.Frame(right)
        preview_box.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        ttk.Label(preview_box, text="Preview").pack(anchor=tk.W)
        self.preview_area = tk.Label(preview_box, relief=tk.SUNKEN, anchor=tk.CENTER)
        self.preview_area.config(width=48, height=16)  # dimensão em caracteres; apenas placeholder
        self.preview_area.pack(fill=tk.BOTH, expand=True)

        # Ações
        actions = ttk.Frame(right)
        actions.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(actions, text="Salvar metadados (definir)", command=self.save_current).pack(side=tk.LEFT)
        ttk.Button(actions, text="Reverter (reler)", command=self.refresh_current).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(actions, text="Limpar tudo (seleção)", command=self._clear_lists).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(actions, text="Adicionar (seleção)", command=self._apply_add_selected).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Button(actions, text="Remover (seleção)", command=self._apply_remove_selected).pack(side=tk.LEFT, padx=(6, 0))

        # Status bar
        status = ttk.Frame(self)
        status.pack(fill=tk.X)
        ttk.Label(status, textvariable=self.status_var, anchor="w").pack(fill=tk.X, padx=8, pady=6)

        # Carregamento inicial
        self.load_files()

    # Eventos / ações
    def _choose_dir(self):
        d = filedialog.askdirectory(initialdir=self.dir_var.get() or str(Path.cwd()))
        if d:
            self.dir_var.set(d)
            self.load_files()

    def _exts(self) -> list[str]:
        items = [e.strip().lstrip(".").lower() for e in self.ext_var.get().split(",")]
        return [e for e in items if e]

    def load_files(self):
        base = Path(self.dir_var.get()).expanduser()
        if not base.exists() or not base.is_dir():
            messagebox.showerror("Pasta inválida", "Selecione uma pasta existente.")
            return
        exts = self._exts() or DEFAULT_EXTS
        self.files = list(core.iter_targets([base], recursive=self.recursive_var.get(), exts=exts))
        self.files.sort()
        if self.use_thumbs:
            self._render_thumbnails()
        else:
            self.file_list.delete(0, tk.END)
            for p in self.files:
                try:
                    label = str(p.relative_to(base))
                except Exception:
                    label = str(p)
                self.file_list.insert(tk.END, label)
        self.status_var.set(f"{len(self.files)} arquivo(s) carregado(s)")
        if self.files:
            if self.use_thumbs:
                # seleciona o primeiro automaticamente
                if self.thumb_items:
                    self._set_tile_selected(self.thumb_items[0], True)
                    self._update_selection_meta()
            else:
                self.file_list.selection_clear(0, tk.END)
                self.file_list.selection_set(0)
                self._on_select_file()
        else:
            self._show_meta([])

    def _get_selected_paths(self) -> list[Path]:
        if self.use_thumbs:
            return [it["path"] for it in self.thumb_items if it.get("selected")]
        sel = self.file_list.curselection()
        out: list[Path] = []
        for idx in sel:
            if 0 <= idx < len(self.files):
                out.append(self.files[idx])
        return out

    def _on_select_file(self, event=None):
        paths = self._get_selected_paths()
        self._show_meta(paths)

    def _show_meta(self, paths: list[Path]):
        path: Path | None = paths[0] if paths else None
        self.current_path = path
        self.people_list.delete(0, tk.END)
        self.tags_list.delete(0, tk.END)
        if not path:
            self.path_label.config(text="(nenhum arquivo)")
            self._set_preview(None)
            return
        # Quando múltiplos arquivos estão selecionados, mostramos apenas o primeiro na prévia
        label = str(path) if len(paths) <= 1 else f"{len(paths)} arquivo(s) selecionado(s) — mostrando: {path.name}"
        try:
            meta = core.read_values(path)
        except Exception as e:
            messagebox.showerror("Erro ao ler metadados", str(e))
            self.path_label.config(text=label)
            self._set_preview(None)
            return
        self.path_label.config(text=label)
        for v in meta.get("people", []):
            self.people_list.insert(tk.END, v)
        for v in meta.get("tags", []):
            self.tags_list.insert(tk.END, v)
        self._set_preview(path)

    # Miniaturas
    def _on_mousewheel(self, event):
        if not self.use_thumbs:
            return
        # Windows: event.delta é múltiplo de 120
        delta = int(-1 * (event.delta / 120) * 30)
        self.thumb_canvas.yview_scroll(delta, "units")

    def _render_thumbnails(self):
        # limpa itens antigos
        for child in list(self.thumb_frame.winfo_children()):
            child.destroy()
        self.thumb_items.clear()

        # cria itens (posicionamento será feito por _layout_thumbnails)
        for idx, p in enumerate(self.files):
            tile = tk.Frame(self.thumb_frame, bd=2, relief=tk.RIDGE, bg="#f0f0f0")
            # grid será ajustado depois
            # imagem
            img_label = tk.Label(tile, bg="#ddd")
            img_label.pack(fill=tk.BOTH, expand=True)
            photo = self._make_thumb_image(p, self._thumb_size)
            if photo is not None:
                img_label.config(image=photo)
            else:
                img_label.config(text="(sem preview)")

            # texto
            name_label = tk.Label(tile, text=p.name, bg="#f0f0f0")
            name_label.pack(fill=tk.X)

            item = {"path": p, "frame": tile, "img": img_label, "name": name_label, "photo": photo, "selected": False}
            self.thumb_items.append(item)

            # binds
            def make_handler(i=item):
                def _h(ev=None):
                    ctrl = (ev.state & 0x0004) != 0 if ev is not None else False
                    self._handle_tile_click(i, additive=ctrl)
                return _h
            for w in (tile, img_label, name_label):
                w.bind("<Button-1>", make_handler())
                w.bind("<Double-Button-1>", lambda e, pp=p: self._open_path(pp))

        self._layout_thumbnails()

    def _set_tile_selected(self, item: dict, value: bool):
        item["selected"] = value
        if value:
            item["frame"].config(bg="#98c1ff")
            item["name"].config(bg="#98c1ff")
        else:
            item["frame"].config(bg="#f0f0f0")
            item["name"].config(bg="#f0f0f0")

    def _handle_tile_click(self, item: dict, additive: bool = False):
        if not additive:
            # limpa seleção atual
            for it in self.thumb_items:
                self._set_tile_selected(it, False)
        # alterna item
        self._set_tile_selected(item, not item.get("selected"))
        self._update_selection_meta()

    def _update_selection_meta(self):
        paths = [it["path"] for it in self.thumb_items if it.get("selected")]
        self._show_meta(paths)

    def _open_path(self, path: Path):
        try:
            core.open_in_viewer(path)
        except Exception as e:
            messagebox.showerror("Falha ao abrir", str(e))

    def _make_thumb_image(self, path: Path, size: tuple[int, int]):
        if not PIL_AVAILABLE:
            return None
        try:
            try:
                from PIL import ImageOps  # type: ignore
            except Exception:
                ImageOps = None  # type: ignore
            # tenta abrir a própria imagem
            im = Image.open(path)
            if "exif" in im.info and 'getexif' in dir(im) and ImageOps is not None:
                try:
                    im = ImageOps.exif_transpose(im)
                except Exception:
                    pass
        except Exception:
            # fallback para miniatura via exiftool
            try:
                tmp = core.extract_thumbnail_to_temp(path)
                im = Image.open(tmp)
                try:
                    Path(tmp).unlink(missing_ok=True)
                except Exception:
                    pass
            except Exception:
                return None
        try:
            im.thumbnail(size)
            return ImageTk.PhotoImage(im)
        except Exception:
            return None

    def _on_thumb_canvas_configure(self, event):
        # manter frame com a mesma largura do canvas e refazer layout
        try:
            self.thumb_canvas.itemconfigure(self.thumb_window_id, width=event.width)
        except Exception:
            pass
        self._layout_thumbnails(event.width)

    def _layout_thumbnails(self, width: int | None = None):
        if not self.thumb_items:
            return
        if width is None:
            try:
                width = int(self.thumb_canvas.winfo_width())
            except Exception:
                width = 600
        tile_w = self._thumb_size[0]
        pad = self._thumb_pad
        # estimativa de largura por coluna: tile + paddings + borda
        col_w = tile_w + pad * 2 + 8
        cols = max(1, width // max(1, col_w))
        if cols != self._thumb_cols:
            self._thumb_cols = cols
        # limpar grid atual
        for it in self.thumb_items:
            it["frame"].grid_forget()
        # aplicar novo grid
        for idx, it in enumerate(self.thumb_items):
            r = idx // self._thumb_cols
            c = idx % self._thumb_cols
            it["frame"].grid(row=r, column=c, padx=pad, pady=pad, sticky="nsew")
        # expandir colunas
        for c in range(self._thumb_cols):
            self.thumb_frame.grid_columnconfigure(c, weight=1)

    def _open_selection(self):
        paths = self._get_selected_paths()
        if not paths:
            return
        # abrir de forma sequencial (sistema deve gerenciar múltiplas janelas)
        for p in paths:
            try:
                core.open_in_viewer(p)
            except Exception as e:
                messagebox.showerror("Falha ao abrir", f"{p}: {e}")

    def refresh_current(self):
        self._show_meta([self.current_path] if self.current_path else [])

    def _add_person(self):
        v = self.people_entry.get().strip()
        if not v:
            return
        # suporta múltiplos, separados por vírgula
        for part in [x.strip() for x in v.split(",") if x.strip()]:
            if part and part not in self._listbox_values(self.people_list):
                self.people_list.insert(tk.END, part)
        self.people_entry.delete(0, tk.END)

    def _remove_person(self):
        self._remove_selected(self.people_list)

    def _add_tag(self):
        v = self.tags_entry.get().strip()
        if not v:
            return
        for part in [x.strip() for x in v.split(",") if x.strip()]:
            if part and part not in self._listbox_values(self.tags_list):
                self.tags_list.insert(tk.END, part)
        self.tags_entry.delete(0, tk.END)

    def _remove_tag(self):
        self._remove_selected(self.tags_list)

    def _remove_selected(self, lb: tk.Listbox):
        sel = list(lb.curselection())
        sel.reverse()
        for i in sel:
            lb.delete(i)

    def _listbox_values(self, lb: tk.Listbox) -> list[str]:
        return [lb.get(i) for i in range(lb.size())]

    def _clear_lists(self):
        paths = self._get_selected_paths()
        if not paths:
            return
        if not messagebox.askyesno("Confirmar", f"Limpar pessoas e tags em {len(paths)} arquivo(s)?"):
            return
        ok = 0
        err = 0
        for p in paths:
            try:
                core.clear_values(p, clear_people=True, clear_tags=True)
                ok += 1
            except Exception:
                err += 1
        self.status_var.set(f"Limpeza concluída: {ok} ok, {err} erro(s)")
        self.refresh_current()

    def save_current(self):
        paths = self._get_selected_paths()
        if not paths:
            messagebox.showinfo("Sem arquivo", "Selecione ao menos um arquivo na lista.")
            return
        people = self._listbox_values(self.people_list)
        tags = self._listbox_values(self.tags_list)
        if not messagebox.askyesno("Confirmar",
                                   f"Definir pessoas/tags em {len(paths)} arquivo(s)?\nIsto substitui os valores atuais." ):
            return
        ok = 0
        err = 0
        for p in paths:
            try:
                core.clear_values(p, clear_people=True, clear_tags=True)
                if people or tags:
                    core.add_values(p, people=people, tags=tags)
                ok += 1
            except Exception:
                err += 1
        self.status_var.set(f"Salvo: {ok} ok, {err} erro(s)")
        messagebox.showinfo("Concluído", f"Atualização concluída: {ok} ok, {err} erro(s)")
        self.refresh_current()

    def _open_current(self, use_thumb: bool):
        path = self.current_path
        if not path:
            return
        try:
            if use_thumb:
                tmp = core.extract_thumbnail_to_temp(path)
                core.open_in_viewer(tmp)
            else:
                core.open_in_viewer(path)
        except Exception as e:
            messagebox.showerror("Falha ao abrir", str(e))

    # Preview helpers
    def _set_preview(self, path: Path | None):
        if not PIL_AVAILABLE:
            self.preview_area.config(text="Pillow não instalado. Preview indisponível.")
            self.preview_area.image = None
            return
        if not path:
            self.preview_area.config(text="", image="")
            self.preview_area.image = None
            return
        # Tenta miniatura embutida; se falhar, usa a própria imagem
        img_path = None
        tmp_to_remove = None
        try:
            try:
                tmp = core.extract_thumbnail_to_temp(path)
                img_path = tmp
                tmp_to_remove = tmp
            except Exception:
                img_path = path
            if img_path is None:
                raise RuntimeError("Sem caminho de imagem")
            im = Image.open(img_path)
            im.thumbnail((512, 512))
            tkimg = ImageTk.PhotoImage(im)
            self.preview_area.config(image=tkimg, text="")
            self.preview_area.image = tkimg  # manter referência
        except Exception:
            self.preview_area.config(text="Falha ao carregar preview.", image="")
            self.preview_area.image = None
        finally:
            # remove o thumb temporário, se criado
            try:
                if tmp_to_remove:
                    Path(tmp_to_remove).unlink(missing_ok=True)
            except Exception:
                pass

    def _apply_add_selected(self):
        paths = self._get_selected_paths()
        if not paths:
            return
        people = self._listbox_values(self.people_list)
        tags = self._listbox_values(self.tags_list)
        if not (people or tags):
            messagebox.showinfo("Nada a adicionar", "Informe pessoas e/ou tags para adicionar.")
            return
        ok = 0
        err = 0
        for p in paths:
            try:
                core.add_values(p, people=people, tags=tags)
                ok += 1
            except Exception:
                err += 1
        self.status_var.set(f"Adicionar: {ok} ok, {err} erro(s)")
        self.refresh_current()

    def _apply_remove_selected(self):
        paths = self._get_selected_paths()
        if not paths:
            return
        people = self._listbox_values(self.people_list)
        tags = self._listbox_values(self.tags_list)
        if not (people or tags):
            messagebox.showinfo("Nada a remover", "Informe pessoas e/ou tags para remover.")
            return
        ok = 0
        err = 0
        for p in paths:
            try:
                core.remove_values(p, people=people, tags=tags)
                ok += 1
            except Exception:
                err += 1
        self.status_var.set(f"Remover: {ok} ok, {err} erro(s)")
        self.refresh_current()


def main():
    app = App()
    # Se exiftool não existir, a App fecha no __init__ e app não terá mainloop útil
    try:
        app.mainloop()
    except Exception:
        pass


if __name__ == "__main__":
    main()
