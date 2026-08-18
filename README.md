# Sänka skepp i Tkinter

Kör appen med standardbiblioteket. Inga externa pip-paket behövs.

## Windows

```bash
python app.py
```

Om du använder ett venv i Windows/PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -c "import tkinter; print('tkinter finns')"
python app.py
```

## WSL/Ubuntu

Installera Tkinter i WSL:

```bash
sudo apt update
sudo apt install python3-tk
```

Gå till appmappen från WSL. Windows-disken ligger normalt under `/mnt/c`:

```bash
cd /mnt/c/Users/paldah/Documents/Codex/2026-08-18/referenced-chatgpt-conversation-this-is-an/outputs/battleship_tk
```

Testa att Tkinter fungerar:

```bash
python3 -m tkinter
```

Kör appen:

```bash
python3 app.py
```

Om du använder ett venv i WSL:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m tkinter
python app.py
```

Om `python -m tkinter` fungerar men inget fönster syns är problemet WSL:s grafikstöd, inte Python-paketen. På Windows 11 med WSLg fungerar GUI normalt direkt. På äldre WSL-miljöer kan du behöva en X-server på Windows.

`tkinter` installeras inte via `pip` och ska därför inte ligga i `requirements.txt`.
Ett venv ärver Tkinter-stödet från den Python-installation som venv:et skapades med.
Om importtestet misslyckas behöver Tkinter installeras i basmiljön först. Skapa sedan om venv:et.

Appen startar med ett 10x10-bräde och flottan:

```text
5,4,4,3,3,3,3,3
```

Du kan ändra rader, kolumner och flotta i överkanten innan du trycker `Nytt spel`.
Skepp placeras slumpmässigt och får inte nudda varandra, inte heller diagonalt.
Du kan också välja spelmotor för maskinen. I `Maskin mot maskin` kan Maskin A
och Maskin B använda olika motorer.

## Lägen

- `Människa mot maskin`: ditt bräde visas öppet till vänster. Maskinens bräde visas till höger, men bara kända rutor visas.
- `Maskin mot maskin`: båda brädena visas öppet, och du kan följa spelet med `Start/paus`.

## Motor-API

En spelmotor ärver från `PlayerEngine` i `battleship.py` och implementerar:

```python
def choose_shot(self, view: ShotView) -> tuple[int, int]:
    ...
```

`view` ger motståndarens kända spelstatus:

```python
view.rows
view.cols
view.state_at(row, col)
view.available_targets()
```

Det finns en enkel referensmotor:

```python
from battleship import RandomEngine
```

Det finns också en heuristisk motor:

```python
from battleship import Pal17Engine
```

`Pal17Engine.score_targets(view)` returnerar en score per tillåten ruta:

- `0` för vanlig sökning efter nästa skepp.
- `10` för tillåtna ortogonala grannar till en ensam träff på ett ännu osänkt skepp.
- `20` för tillåtna förlängningar i ändarna av två eller fler linjerade träffar.

En tillåten ruta ligger på spelplanen, är inte redan beskjuten och ligger inte
intill ett säkert sänkt skepp, inklusive diagonalt.

För att koppla in fler motorer, lägg till en `PlayerEngine`-klass i `battleship.py`
och registrera den i `ENGINE_TYPES` i `app.py`.

## Headless benchmark

Benchmarken kör maskin mot maskin utan Tkinter, animation, sleep eller `after()`.
Den använder samma `Board`, `receive_shot()`, `public_view()` och motor-API som UI:t.

Exempel:

```bash
python benchmark.py --games 100000 --engine-a pal17 --engine-b random --seed 123
```

Andra användbara varianter:

```bash
python benchmark.py --games 10000 --engine-a pal17 --engine-b pal17 --seed 123
python benchmark.py --games 10000 --engine-a random --engine-b random --start-policy random
```

Rapporten visar antal matcher, vinster per motor, statistik för vinnarens antal
skott och matcher per sekund. Standardläget alternerar startspelare mellan A och
B så jämna motorpar inte snedvrids av first-move bias.
