# imgmeta 🖼️🔖

**CLI para gerenciar metadados (pessoas e tags) em imagens usando [ExifTool](https://exiftool.org).**

Permite **adicionar, remover, limpar, listar e buscar** valores em campos XMP/IPTC como:

* **Pessoas em imagem** (`XMP-Iptc4xmpExt:PersonInImage`)
* **Tags/keywords** (`XMP-dc:Subject` e `IPTC:Keywords`)

---

## ⚙️ Requisitos

* Python **3.8+**
* [ExifTool](https://exiftool.org) instalado e disponível no `PATH`

Verifique com:

```bash
exiftool -ver
```

---

## 🚀 Instalação

Clone o repositório e torne o script executável:

```bash
git clone https://github.com/usuario/imgmeta.git
cd imgmeta
chmod +x imgmeta.py
```

Rode com:

```bash
./imgmeta.py --help
```

Ou via Python:

```bash
python imgmeta.py --help
```

---

## 📦 Instalação Global

Além de rodar o script manualmente, você pode instalar como comando global usando **`uv`**.

### 🔹 Usando uv

[`uv`](https://github.com/astral-sh/uv) é uma alternativa rápida:

```bash
uv tool install git+https://github.com/usuario/imgmeta.git
```

Ou se quiser rodar sem instalar globalmente:

```bash
uvx git+https://github.com/usuario/imgmeta.git -- --help
```

---



## 📖 Uso

### Sintaxe geral

```bash
imgmeta [opções globais] <comando> [argumentos]
```

### Opções globais

| Opção             | Descrição                                                       |
| ----------------- | --------------------------------------------------------------- |
| `--ext EXT ...`   | Extensões aceitáveis (default: jpg, jpeg, png, heic, tif, tiff) |
| `-r, --recursive` | Percorre diretórios recursivamente                              |
| `-q, --quiet`     | Saída reduzida                                                  |

---

## 🔧 Comandos

### 1. Adicionar pessoas/tags

```bash
imgmeta add <arquivos/pastas> [--people NOME ...] [--tags TAG ...]
```

Exemplo:

```bash
imgmeta add fotos/ --people "Maria Silva" "João" --tags viagem praia -r
```

---

### 2. Remover pessoas/tags

```bash
imgmeta remove <arquivos/pastas> [--people NOME ...] [--tags TAG ...]
```

Exemplo:

```bash
imgmeta remove fotos/ --tags praia
```

---

### 3. Limpar valores

```bash
imgmeta clear <arquivos/pastas> [--people] [--tags]
```

* `--people` → limpa somente pessoas
* `--tags` → limpa somente tags
* se nenhum for passado → **não faz nada** (proteção)

Exemplo:

```bash
imgmeta clear fotos/ --tags
```

---

### 4. Listar metadados

```bash
imgmeta list <arquivos/pastas>
```

Exemplo:

```bash
imgmeta list fotos/ -r
```

Saída:

```
fotos/img1.jpg
  pessoas: Maria Silva
  tags   : viagem, praia
```

---

### 5. Buscar imagens

```bash
imgmeta search <arquivos/pastas> [--people NOME ...] [--tags TAG ...] [--mode any|all] [--show-meta]
```

* `--mode any` → corresponde a **qualquer** item (default)
* `--mode all` → corresponde a **todos** os itens
* `--show-meta` → exibe também os metadados

Exemplo:

```bash
imgmeta search fotos/ --people "Maria Silva" --tags praia --mode all --show-meta
```

---

## ⚡ Exemplos rápidos

Adicionar uma tag:

```bash
imgmeta add img1.jpg --tags "aniversário"
```

Adicionar pessoas e tags a várias imagens:

```bash
imgmeta add pasta/*.jpg --people "João" --tags festa amigos
```

Listar todas as imagens e seus metadados:

```bash
imgmeta list fotos/ -r
```

Buscar imagens de João com a tag "viagem":

```bash
imgmeta search fotos/ --people João --tags viagem --mode all
```

---

## 📜 Saída típica

```bash
[add] fotos/img1.jpg
[add] fotos/img2.jpg
Concluído: 2 arquivo(s).
```

---

## 📄 Licença

Uso livre. Cite o autor se for redistribuir.
