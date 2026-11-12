# TeamViewer VPN Prototype

Prototype desktop-app (Windows) waarmee een supportmedewerker met **één klik** een
VPN-verbinding opzet met een computer die al in **TeamViewer Classic** is
geconfigureerd. De apparatenlijst komt uit de TeamViewer REST API
(`GET /api/v1/devices`); de daadwerkelijke VPN-tunnel wordt gestart door de lokaal
geïnstalleerde TeamViewer-client via command-line parameters, want de REST API kan
zelf geen VPN opzetten.

## Werking

1. Bij opstarten wordt de Computers & Contacts-lijst opgehaald via de REST API en in
   het geheugen gecached (bij zoeken géén extra API-calls).
2. In het zoekveld kun je direct, case-insensitive en op delen van de systeemnaam
   (`alias`) zoeken. Per resultaat zie je naam, TeamViewer ID en online-status.
3. Per systeem zit een knop **VPN** (start `TeamViewer.exe -i <id> --Password <pw> --VPN`)
   en een knop **Remote** (zelfde commando zonder `--VPN`).
4. Is een systeem offline, dan verschijnt er een waarschuwing; na het starten
   verschijnt een succes- of foutmelding in de statusbalk.

## Tech stack

Python 3.10+ met **alleen de standaardbibliotheek** (`tkinter` voor de GUI, `urllib`
voor de REST-calls, `ctypes` voor de Windows Credential Manager). Geen externe
dependencies — in plaats van CustomTkinter/PySide6 is bewust gekozen voor `tkinter`,
omdat het prototype dan zonder `pip install` draait.

## Installatie

1. Installeer Python 3.10+ op Windows (standaard installer van python.org; tkinter
   wordt meegeïnstalleerd).
2. Kopieer `settings.example.json` naar `settings.json` en vul in (zie hieronder).
3. Start de app: `python main.py`

## Configuratie

### 1. API-token aanmaken (TeamViewer Management Console)

1. Log in op de [TeamViewer Management Console](https://login.teamviewer.com).
2. Ga naar je profiel → **Apps** → maak een **API-token** (script token) aan.
3. Zet alléén het recht **Computers & Contacts → Read** aan; meer rechten zijn niet nodig.
4. Sla het token veilig op:
   - **Aanbevolen:** in de Windows Credential Manager onder target `TeamViewerVPN/api_token`
     (de app leest het token eerst hieruit), óf
   - als `"api_token"` in `settings.json` (zet `settings.json` nóóit in versiebeheer —
     hij staat in `.gitignore`).

### 2. `settings.json`

```json
{
  "api_base_url": "https://webapi.teamviewer.com/api/v1",
  "api_timeout_seconds": 15,
  "teamviewer_exe": "C:\\Program Files\\TeamViewer\\TeamViewer.exe",
  "simulate": false,
  "fake_teamviewer_script": "",
  "api_token": ""
}
```

- `teamviewer_exe`: pad naar de lokale `TeamViewer.exe` (TeamViewer **Classic**).
- `api_token`: alleen als fallback; bij voorkeur via de Credential Manager.
- `simulate` / `fake_teamviewer_script`: zie testinstructie hieronder.

### 3. Wachtwoorden per computer

Bij de eerste VPN/Remote-klik wordt om het TeamViewer-wachtwoord van die computer
gevraagd. Het wordt opgeslagen in de **Windows Credential Manager**
(target `TeamViewerVPN/device/<teamviewer_id>`) — nooit hardcoded in de broncode en
nooit gelogd. Op niet-Windows systemen (alleen development) valt de opslag terug op
`data/credentials.local.json` met rechten `0600`.

## Testinstructie (gesimuleerde TeamViewer-omgeving)

Zonder echte TeamViewer-installatie kun je de end-to-end flow testen:

1. Zet in `settings.json`: `"simulate": true`.
2. Zet `FAKE_TV_LOG` (omgevingsvariabele) op bijv. `C:\temp\fake_tv.log`.
3. Start de app met een geldige API-token (of test de launcher los, zie tests).
4. Klik op **VPN** bij een systeem. In het logbestand verschijnt een JSON-regel met
   de gegenereerde argumenten, bijv. `["-i", "123456789", "--Password", "...", "--VPN"]`.
5. Unit-tests draaien met: `python -m unittest discover -s tests -v`

Met een echte omgeving: zet `"simulate": false`, controleer het pad naar
`TeamViewer.exe`, en klik op **VPN** bij een online systeem.

## Beperkingen en aandachtspunten

- VPN via command line werkt **alleen met TeamViewer Classic op Windows**; het
  nieuwe TeamViewer Remote-platform ondersteunt dit niet.
- Het wachtwoord staat als command-line parameter in het proceslijst zichtbaar
  (TeamViewer Classic accepteert ditcurrently alleen zo) — workaround: per computer
  een sterk, uniek wachtwoord gebruiken.
- Het script token krijgt alléén leesrechten op Computers & Contacts.
- Het API-token wordt nooit gelogd of in foutmeldingen getoond.
- Dit is een prototype: focus op de werkende end-to-end flow.

## Structuur

```
main.py                  entrypoint
tv_vpn/config.py         settings.json laden/opslaan
tv_vpn/api.py            REST API + zoeken (filter_devices)
tv_vpn/credentials.py    Windows Credential Manager (+ file-fallback)
tv_vpn/launcher.py       TeamViewer.exe command line + simulatie
tv_vpn/gui.py            tkinter-GUI
simulate/                nep TeamViewer-client voor tests
tests/                   unit-tests (geen echte API of GUI nodig)
```
