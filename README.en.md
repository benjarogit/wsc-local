# wsc-local · WoltLab Workbench

**[Deutsch (default)](README.md) · [English](README.en.md)**

**Current version:** [![Version](https://img.shields.io/github/v/release/benjarogit/wsc-local?sort=semver)](https://github.com/benjarogit/wsc-local/releases/latest) · [Download ZIP](https://github.com/benjarogit/wsc-local/releases/latest/download/wsc-local.zip) · [Changes](CHANGELOG.md)

Prepare, automatically install, and manage local WoltLab Suite installations through a clear browser dashboard and the same CLI. Multiple projects run separately, each with its own files, database, ports, and credentials.

**Linux · macOS · Windows through WSL2** · **German by default, English available in the dashboard**

<a href="docs/screenshots/home-en.png"><img src="docs/screenshots/home-en.png" alt="wsc-local: first start with no projects and guided onboarding" width="1100"></a>

<p align="center">Click a thumbnail to open the full-size screenshot.</p>

<table align="center">
  <tr>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/create-en.png" title="Prepare a project"><img src="docs/screenshots/create-en.png" alt="Prepare a project" width="160"><br><sub>Prepare a project</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/advanced-en.png" title="Advanced settings"><img src="docs/screenshots/advanced-en.png" alt="Advanced settings" width="160"><br><sub>Advanced settings</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/installing-en.png" title="Automatic setup"><img src="docs/screenshots/installing-en.png" alt="Automatic setup" width="160"><br><sub>Automatic setup</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/overview-en.png" title="Project details"><img src="docs/screenshots/overview-en.png" alt="Project details" width="160"><br><sub>Project details</sub></a></td>
  </tr>
  <tr>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/credentials-en.png" title="Credentials – masked"><img src="docs/screenshots/credentials-en.png" alt="Credentials – masked" width="160"><br><sub>Credentials – masked</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/services-en.png" title="Services and logs"><img src="docs/screenshots/services-en.png" alt="Services and logs" width="160"><br><sub>Services and logs</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/backups-en.png" title="Backups and export"><img src="docs/screenshots/backups-en.png" alt="Backups and export" width="160"><br><sub>Backups and export</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/tools-en.png" title="WoltLab tools"><img src="docs/screenshots/tools-en.png" alt="WoltLab tools" width="160"><br><sub>WoltLab tools</sub></a></td>
  </tr>
  <tr>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/system-en.png" title="System checks"><img src="docs/screenshots/system-en.png" alt="System checks" width="160"><br><sub>System checks</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/help-en.png" title="Help and getting started"><img src="docs/screenshots/help-en.png" alt="Help and getting started" width="160"><br><sub>Help and getting started</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/migration-en.png" title="Migration dialog"><img src="docs/screenshots/migration-en.png" alt="Migration dialog" width="160"><br><sub>Migration dialog</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/dark-en.png" title="Dark mode"><img src="docs/screenshots/dark-en.png" alt="Dark mode" width="160"><br><sub>Dark mode</sub></a></td>
  </tr>
  <tr>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/setup-language-en.png" title="Installation language"><img src="docs/screenshots/setup-language-en.png" alt="Installation language" width="160"><br><sub>Installation language</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/acp-en.png" title="Signed in to the ACP"><img src="docs/screenshots/acp-en.png" alt="Signed in to the ACP" width="160"><br><sub>Signed in to the ACP</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/prerequisites-en.png" title="Prerequisites (example)"><img src="docs/screenshots/prerequisites-en.png" alt="Prerequisites (example)" width="160"><br><sub>Prerequisites (example)</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/mobile-en.png" title="Mobile view"><img src="docs/screenshots/mobile-en.png" alt="Mobile view" height="110"><br><sub>Mobile view</sub></a></td>
  </tr>
  <tr>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/updates-en.png" title="Updates (example)"><img src="docs/screenshots/updates-en.png" alt="Updates (example)" width="160"><br><sub>Updates (example)</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/update-confirm-en.png" title="Confirm update"><img src="docs/screenshots/update-confirm-en.png" alt="Confirm update" width="160"><br><sub>Confirm update</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/update-guide-en.png" title="Update instructions"><img src="docs/screenshots/update-guide-en.png" alt="Update instructions" width="160"><br><sub>Update instructions</sub></a></td>
    <td align="center" valign="top" width="25%"><a href="docs/screenshots/update-progress-en.png" title="Update progress"><img src="docs/screenshots/update-progress-en.png" alt="Update progress" width="160"><br><sub>Update progress</sub></a></td>
  </tr>
</table>

These screenshots show the current version with real WoltLab test projects; passwords stay masked. Prerequisite and update dialogs illustrate labeled examples: missing HTTPS approval and a local test update from 1.2.0 to 1.2.1. Update screenshots come from an actual application replacement and dashboard restart in an isolated test directory; the 1.2.1 shown there has been publicly available since 29 October 2026. [Capture details](docs/screenshots/README.md)

## Quick start

First download the repository ([ZIP](https://github.com/benjarogit/wsc-local/releases/latest/download/wsc-local.zip) or Git) and extract it. Run the following commands from the project directory, which also contains the Windows launchers.

### Install prerequisites once

**Guided setup:** Linux/macOS: `bash ./setup.sh --install-deps`. Windows: **double-click `Install-wsc-local.cmd`** (or `Start-wsc-local.ps1 -InstallDependencies`). Then open the normal launcher. If the dashboard is already running, **System check → Set up missing prerequisites** starts the same flow after a preview.

Setup installs missing packages and configures local HTTPS in your system terminal. Linux uses apt/dnf/pacman, macOS uses Homebrew, and Windows uses winget and WSL2. Enter system passwords only in the terminal or operating system prompt. WSL initialization, first-time Docker Desktop approval, restarting or signing in again may still be required. Existing Docker installations are not replaced; the system check explains remaining conflicts. [Platform details and limitations](docs/platforms.md)

You can also install prerequisites yourself:

- **Python 3.10 or newer.**
- **Docker with Docker Compose**, running and accessible to your user. Linux containers are required.
- **mkcert** for trusted local HTTPS; Linux browsers may also require NSS.
- Internet access for container images and Core downloads. Your own installation ZIP is also supported.

[Platform instructions](docs/platforms.md) cover Linux, macOS, and Windows/WSL2, including certificate trust. Node.js is needed only for development tests.

### Linux and macOS

```bash
git clone https://github.com/benjarogit/wsc-local.git
cd wsc-local
./setup.sh
```

Setup checks prerequisites, guides the one-time HTTPS trust step in your terminal, and opens the dashboard. **System check** explains missing prerequisites and the next steps.

Later, use `./start.sh` or `./panel.sh`. To skip opening a browser: `./start.sh --no-open`. To choose another dashboard port: `./start.sh --port 9199`. The default address is `http://127.0.0.1:9099/`.

### Windows

1. Install [WSL2](https://learn.microsoft.com/windows/wsl/install) with a Linux distribution.
2. Start Docker Desktop, use **Linux containers**, and enable WSL integration for that distribution.
3. Install Python and mkcert in WSL. Also install mkcert on Windows so your Windows browser trusts the same local CA.
4. Clone the repository and **double-click `Start-wsc-local.cmd`**, or run `./setup.sh` inside WSL.

With multiple distributions: `Start-wsc-local.ps1 -Distribution Ubuntu`. [Detailed commands and setup](docs/platforms.md#windows-mit-wsl2)

## Your Suite in three steps

1. **Prepare project:** choose a name, Suite version, and source. Nginx/PHP-FPM with MariaDB is recommended. Optional settings include Apache, compatible PHP profiles, MySQL 8, and a custom administrator account.
2. **Review language and login details:** select DE or EN in the header; the suite will use that language during setup. Inspect the securely generated account and optionally change the name, email, and password.
3. **Set up:** the Workbench starts the environment, configures HTTPS, and completes WoltLab installation. It verifies the website, assets, and actual administrator login. Afterwards, open the website or use **Open ACP** to sign in directly to the administration.

You do not need to click through the WoltLab installer. A spinner and installation stages show progress. Reloading reconnects to running tasks, even if the initial start response was lost.

## Interface and features

- **Projects:** status, website, administration, and start/stop directly on the card. **Manage** opens Overview, Credentials, Services, Backups, and Tools.
- **Open ACP:** signs in to the administration using the saved administrator credentials. A short-lived, one-use handoff transfers the session; passwords never appear in URLs. If the password changed or two-factor authentication is enabled, a dialog offers the normal ACP login.
- **Credentials:** view and copy administrator and separately grouped database credentials. Passwords start masked. Change administrator credentials in WoltLab after installation.
- **Services:** web server, PHP, and database status and logs. Enable the optional Mailpit mailbox separately. For WoltLab test mail, use SMTP `mail:1025` without authentication.
- **Backups:** capture files and database together, verify checksums, and restore a matching state. Restore first backs up the current state.
- **Export and server migration:** download files, SQL dump, project configuration, checksums, and import instructions. **Prepare server migration** adds target-server guidance and uses the same export format. Restoring on the target server is guided; direct SSH deployment is not included.
- **WoltLab tools:** diagnostics, upload limits with a change preview, and the official Recovery Tool with cleanup. Domain and directory tools create a backup and show instructions; they do not automatically change application paths or database values.
- **Removal:** delete project files, database, containers, networks, and local credentials after typing the project name. Shared images, download caches, and the local CA remain available.

Information buttons open explanations. Confirmations, inputs, and previews use keyboard-accessible dialogs with Cancel. [Tool and migration details](docs/tools.md)

### Language and appearance

**German is the default**, regardless of your browser language. Use the **DE/EN switch with its globe icon** in the header to switch dashboard language. The choice is saved in this browser, and open project sections are restored. CLI output and technical service logs retain their original language.

When you click **Set up**, a new WoltLab installation uses the current dashboard language for the suite default and the first administrator account. Switching dashboard language during setup does not change the selection already submitted. Existing websites stay unchanged. The CLI uses the system locale (`LC_ALL`, `LC_MESSAGES`, `LANG`; English → EN, otherwise German), or an explicit choice: `./wsc install my-forum --language en`. Retrying retains the saved choice.

Monitor, sun, and moon icons directly select **System, Light, or Dark**. The active mode is highlighted; System follows your device preference. This changes the Workbench appearance, not your WoltLab website's design.


## Suite versions and installation archives

Profiles follow the [official WoltLab documentation](https://manual.woltlab.com/en/php-compatibility/). Alpha and legacy versions require explicit acknowledgement.

- **WSC 6.2:** automatic Core 6.2.8 download with SHA-256 verification, or your own ZIP. The default profile uses PHP 8.4 and local HTTPS.
- **WSC 6.3:** an unofficial development archive from [YoureCom/wsc-63-testbuilds](https://github.com/YoureCom/wsc-63-testbuilds), built from WoltLab/WCF. The profile uses PHP 8.5 and HTTPS for local tests.
- **WSC 5.5, 6.0, and 6.1:** a matching installation ZIP is required. Legacy profiles are marked accordingly.

Select custom ZIPs directly in the dashboard: up to 256 MiB and containing `install.php`. Licensed applications require your own suitable archive and valid WoltLab license. Local installation of the free Core does not require license credentials.

The inspected WSC 6.2/6.3 code needs a targeted correction for local ports. Only an exactly recognized code block is changed; originals and checksums are documented under `config/compatibility/`. Compatibility must be rechecked after WoltLab updates.

## CLI and shareable project profiles

```bash
./wsc --version
./wsc check
./wsc create my-forum --download-core
./wsc install my-forum
./wsc list
./wsc start my-forum
./wsc stop my-forum
./wsc status my-forum
./wsc logs my-forum --service database
./wsc doctor my-forum
./wsc snapshot my-forum
./wsc snapshots my-forum
./wsc restore my-forum SNAPSHOT_PATH
./wsc export my-forum
./wsc remove my-forum
```

Download a project profile under **Overview**. It contains Suite, PHP, web server, and database selections, without passwords or local ports:

```bash
./wsc create second-project --profile my-forum.wsc-local.json --download-core
```

The new project gets independent credentials and ports. Profiles exclude website files and database content; use a backup or export for complete data.

## Data, HTTPS, and migration

Projects default to `~/.local/share/wsc-local/projects/`; secrets stay separately in `~/.config/wsc-local/secrets/`. Override these with `WSC_LOCAL_HOME` and `XDG_CONFIG_HOME`. On Windows, these paths are inside WSL.

The dashboard and published container ports bind to loopback. Local HTTPS uses mkcert. Let's Encrypt belongs to public target-server domains, not `localhost`.

Exports remove Workbench-managed local database credentials from `config.inc.php` and exclude local `.env` and TLS keys. They still contain WoltLab content and its database; handle them as complete backups. Temporary recovery and authentication files are excluded.

`./wsc import SOURCE project-name` detects older wsc-local files, legacy snapshots, and Workbench export packages. Raw database directories are not copied between database profiles; a complete migration requires a matching dump or export. [Test coverage and limitations](docs/user-test.md)

## Updates and older installations

From **1.2.0**, the Workbench announces new stable releases in the dashboard. **Updates** offers an installation preview and automatic update, or manual instructions. Git and ZIP installations are detected. Checksums, local-change protection, a recovery point and automatic dashboard restart are part of the flow; WoltLab projects and credentials are preserved.

```bash
./wsc update --check   # Find a newer release
./wsc update           # Install after preview and confirmation
./wsc update --guide   # Follow manual instructions instead
```

**From 1.1.0 or earlier:** perform the first upgrade with `git pull --ff-only` and `./start.sh`. For ZIP installations, merge the new application files into the existing directory while preserving personal data. The new updater is then available for future releases. [Updates, conflicts and recovery](docs/updating.md#english)

**Releases are automated:** a new version tag triggers GitHub checks; after they pass, the workflow publishes the ZIP and SHA-256 checksum. The current version is visible at the top of this README and in the dashboard footer.

The previous single-instance stack is explicitly available through `./setup.sh --legacy` and `./start.sh --legacy`. `tools.sh` and `reset.sh` belong to that older stack. Use the dashboard or `./wsc` for Workbench projects.

## Tests, inspiration, and release

```bash
python3 -m unittest discover -s tests -v
npm ci
npx playwright install chromium
npm run test:ui
```

For a quick local check, run `python3 scripts/check.py`; add `--ui` to include the Chromium suite, `--release` to validate the release metadata and build the ZIP once, and `--metadata` to check only the version information. `python3 scripts/check_repo.py` verifies repository hygiene. CI remains authoritative and checks portable logic on Linux, macOS, and Windows plus browser flows using isolated API responses. Real WoltLab/Docker installations were tested locally on Linux. Full Docker/browser acceptance on macOS and Windows/WSL2 remains a separate platform check. [Detailed test notes](docs/user-test.md)

[wsc-dockerized](https://github.com/SoftCreatRMedia/wsc-dockerized) informs WoltLab-specific profiles; [DDEV](https://github.com/ddev/ddev) project configuration; [Lando](https://docs.lando.dev/plugins/) profiles and optional services; [XAMPP](https://github.com/ApacheFriends/xampp-control-windows) direct service controls. The Workbench remains WoltLab-specific. Font Awesome Free is bundled locally with [license and sources](panel/vendor/fontawesome/).

[Product principles](docs/product.md) · [Changes and release notes](CHANGELOG.md) · [GitHub releases](https://github.com/benjarogit/wsc-local/releases)
