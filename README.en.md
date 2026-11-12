# wsc-local · WoltLab Workbench

**[Deutsch (default)](README.md) · [English](README.en.md)**

A local workbench for WoltLab Suite. You install forums on your own computer, start and stop them, back them up, and prepare a move to a server. The browser dashboard and the `./wsc` command control the same projects. Each project has its own files, database, ports, and credentials.

The interface is German. You switch to English in the dashboard. The number in the version badge is the latest release.

[![Version](https://img.shields.io/github/v/release/benjarogit/wsc-local?sort=semver&label=Version)](https://github.com/benjarogit/wsc-local/releases/latest)
[![Download ZIP](https://img.shields.io/badge/Download-ZIP-0969da)](https://github.com/benjarogit/wsc-local/releases/latest/download/wsc-local.zip)
![Linux](https://img.shields.io/badge/Linux-6e7781?logo=linux&logoColor=white)
![macOS](https://img.shields.io/badge/macOS-6e7781?logo=apple&logoColor=white)
![Windows through WSL2](https://img.shields.io/badge/Windows%20WSL2-6e7781?logo=windows&logoColor=white)

[Changes](CHANGELOG.md) · [Security reports](SECURITY.md)

## Start

Two ways: clone with the command block, or download the ZIP from the download badge and unpack it. Then work in that folder. The Windows launchers are in the same folder. On GitHub, each command block has its own copy button.

### Linux and macOS

```bash
git clone https://github.com/benjarogit/wsc-local.git
cd wsc-local
./setup.sh
```

`./setup.sh` checks the prerequisites, guides the one-time HTTPS trust step in the terminal, and opens the dashboard. **System check** shows anything still missing.

Next time, start it again. `./panel.sh` does the same.

```bash
./start.sh
```

Without a browser window:

```bash
./start.sh --no-open
```

Another dashboard port:

```bash
./start.sh --port 9199
```

Address in the browser:

```text
http://127.0.0.1:9099/
```

### Windows

1. Install [WSL2](https://learn.microsoft.com/windows/wsl/install) with a Linux distribution.
2. Start Docker Desktop, use **Linux containers**, and enable WSL integration for that distribution.
3. Install Python and mkcert in WSL. Also install mkcert on Windows so the Windows browser trusts the same local certificate authority.
4. Clone the repository and **double-click `Start-wsc-local.cmd`**, or run `./setup.sh` in the WSL terminal.

With several distributions:

```powershell
Start-wsc-local.ps1 -Distribution Ubuntu
```

[Commands and details](docs/platforms.md#windows-mit-wsl2)

<details>
<summary><strong>Programs you need once</strong></summary>

Linux and macOS:

```bash
bash ./setup.sh --install-deps
```

Windows, in PowerShell:

```powershell
Start-wsc-local.ps1 -InstallDependencies
```

Or double-click `Install-wsc-local.cmd`. Then open the normal launcher. If the dashboard is already running, **System check → Set up missing prerequisites** starts the same flow after a preview.

Setup installs missing packages and configures local HTTPS in the system terminal. Linux uses apt, dnf, or pacman, macOS uses Homebrew, and Windows uses winget and WSL2. Enter system passwords only in the terminal or the operating-system dialog. WSL initialization, Docker Desktop approval, a restart, or signing in again may still be required. An existing Docker installation is not replaced. If there is a conflict, the system check names the next step. [Platform details and limitations](docs/platforms.md)

You can also install the prerequisites yourself:

| Program | What it is for |
|---|---|
| Python 3.10 or newer | Dashboard and the `./wsc` command |
| Docker with Docker Compose, Linux containers, reachable by your user | Web server, PHP, and database |
| mkcert, and on Linux NSS for the browser if needed | trusted local HTTPS |
| Internet | Container images and the Core download. Your own installation ZIP also works |

[Platform instructions](docs/platforms.md) cover Linux, macOS, and Windows/WSL2, including certificate trust. Node.js is needed only for the development tests.

</details>

## Three steps in the dashboard

| Step | What you do | What you have afterwards |
|---|---|---|
| 1. Prepare | **New project:** choose a name and Suite version, then look at the generated credentials. | A prepared installation, not a finished website yet |
| 2. Set up | Click **Set up** and wait. | A local website |
| 3. Sign in | Click **Open ACP**. | You are in the administration |

You do not click through the WoltLab installer yourself. A spinner shows progress. Reloading the page reconnects to the running task.

<details>
<summary><strong>What setup actually does</strong></summary>

1. **Prepare the project:** choose a name, Suite version, and source. Nginx/PHP-FPM with MariaDB is the default. Apache, matching PHP profiles, MySQL 8, and your own admin values are under the optional settings.
2. **Check language and login:** choose DE or EN at the top. The suite uses that language during setup. Look at the generated admin account and change the name, email, or password if you want.
3. **Set up:** the Workbench starts the environment, configures HTTPS, and finishes the WoltLab installation. It checks the website, assets, and a real administrator login. Then open the website, or sign in to the administration with **Open ACP**.

There is no manual WoltLab installer click-through. A spinner and the work steps show progress. Reloading reconnects to a running task, even if the first start response was lost.

</details>

<a href="docs/screenshots/home-en.png"><img src="docs/screenshots/home-en.png" alt="wsc-local: first start with no projects and guided onboarding" width="1100"></a>

<p align="center">Click a preview to open the screenshot at full size.</p>

<details>
<summary><strong>All screens</strong></summary>

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

The pictures show the Workbench with real local WoltLab test projects. Passwords stay masked. The published version is the badge above, not a number inside a picture. Two pictures are examples: the system check with missing HTTPS approval, and an update dialog. The version number in that dialog is an example, not the installed version. [Capture details](docs/screenshots/README.md)

</details>

## Areas in the dashboard

| Area | What it is for |
|---|---|
| Project card | Status, open the website, administration, start and stop |
| Manage | Overview, credentials, services, backups, tools |
| System check | If Python, Docker, or local HTTPS trust is missing, the next step is here |
| Updates | Check and install a new Workbench version. This does not update the forum itself |
| Help | A short introduction in the same interface |

Information icons open explanations. Confirmations appear in dialogs with Cancel and keyboard use. [Tools and migration in detail](docs/tools.md)

<details>
<summary><strong>Projects, credentials, services</strong></summary>

- **Open ACP:** signs you in to the administration with the saved admin account. A short-lived one-time handoff carries the session. Passwords are not put in URLs. If the password changed or two-factor sign-in is on, the dialog offers the normal ACP login.
- **Credentials:** view and copy the admin account and the separate database account. Passwords start hidden. After installation you change the admin account inside WoltLab.
- **Services:** status and logs of the web server, PHP, and the database. Turn the optional Mailpit test mailbox on separately. For test mail in WoltLab, with no login:

```text
mail:1025
```

- **Backups:** save files and database together, check checksums, and restore a state. Before a restore, the current state is saved.
- **Export and server move:** download a package with files, SQL dump, project configuration, checksums, and import instructions. **Prepare server migration** adds the explanation for the target server and uses the same export format. Import on the server is guided. SSH deployment is not included.
- **WoltLab tools:** diagnostics, upload limits with a preview of the change, the official Recovery Tool, and removing it again. Domain and directory tools create a backup and open the instructions. They do not change application paths or database values by themselves.
- **Custom code (optional):** under Tools, create local Git for packages and styles only, work copies for extra agent windows, and optionally a private GitHub repository named `wsc-<project>`. The running installation and credentials stay outside that repository. If Git or the GitHub CLI is missing, a dialog shows the command for your system. The Workbench does not install them itself. Sign-in on github.com asks for your credentials. The dashboard stores no password and no token. The information icon explains the steps. Deleting the project leaves a linked GitHub repository in place.
- **Remove:** after you type the project name, project files, database, containers, networks, and local credentials are removed. Shared base images, download caches, and the local certificate authority stay.

</details>

<details>
<summary><strong>Language and light or dark</strong></summary>

**German is the default**, regardless of the browser language. The **DE/EN switch with the globe icon** at the top changes the dashboard language. The choice stays in this browser. Open project sections are restored. Command output and technical service logs stay in their original language.

When you click **Set up**, a new WoltLab installation uses the current dashboard language for the suite default and the first admin user. Switching language while setup is already running does not change that choice. Existing websites stay as they are. The CLI uses the system language (`LC_ALL`, `LC_MESSAGES`, `LANG`; English maps to EN, otherwise German) or an explicit choice. Resuming keeps the saved choice.

```bash
./wsc install my-forum --language en
```

The monitor, sun, and moon icons choose **System, Light, or Dark**. The active mode is marked. System follows the device setting. This changes the Workbench, not the design of your WoltLab website.

</details>

<details>
<summary><strong>Which WoltLab version</strong></summary>

The profiles follow the [official WoltLab manual](https://manual.woltlab.com/en/php-compatibility/). Alpha and legacy need an explicit confirmation.

| Profile | Badge | What you get |
|---|---|---|
| WSC 6.2 | ![default](https://img.shields.io/badge/default-2da44e) | Core 6.2.8 downloaded automatically, with a SHA-256 check, or your own ZIP. PHP 8.4 and local HTTPS |
| WSC 6.3 | ![unofficial](https://img.shields.io/badge/unofficial-bf8700) | A development build from [YoureCom/wsc-63-testbuilds](https://github.com/YoureCom/wsc-63-testbuilds), built from WoltLab/WCF. PHP 8.5 and HTTPS, for local tests |
| WSC 5.5, 6.0, 6.1 | ![your own ZIP](https://img.shields.io/badge/your_own_ZIP-6e7781) | A matching installation ZIP from you. The profiles are marked as legacy |

You pick your own ZIP in the dashboard, at most 256 MiB, and it must contain `install.php`. Licensed applications need your own suitable archive and a matching WoltLab license. The free Core does not ask for license credentials during local setup.

The inspected WSC 6.2/6.3 files need a targeted correction for local ports. The Workbench replaces only the exactly recognized code block and records the original file and checksums under `config/compatibility/`. After a WoltLab update this compatibility has to be checked again.

</details>

<details>
<summary><strong>The same tasks on the command line</strong></summary>

Version and system check:

```bash
./wsc --version
./wsc check
```

Create and install a project. `my-forum` is the example name:

```bash
./wsc create my-forum --download-core
./wsc install my-forum
```

Day to day:

```bash
./wsc list
./wsc start my-forum
./wsc stop my-forum
./wsc status my-forum
```

Logs and diagnostics:

```bash
./wsc logs my-forum --service database
./wsc doctor my-forum
```

Backup and export:

```bash
./wsc snapshot my-forum
./wsc snapshots my-forum
./wsc export my-forum
```

Restore. Replace `PATH_TO_BACKUP` with the real path:

```bash
./wsc restore my-forum PATH_TO_BACKUP
```

Remove asks for the project name and deletes that project:

```bash
./wsc remove my-forum
```

A project profile downloaded under **Overview** contains only the Suite, PHP, web server, and database choices. It has no passwords and no local ports:

```bash
./wsc create second-project --profile my-forum.wsc-local.json --download-core
```

The new project gets its own credentials and ports. The profile does not contain website files or database contents. Use a backup or an export for that.

</details>

<details>
<summary><strong>Where files, passwords, and HTTPS live</strong></summary>

Projects and secrets stay apart. On Windows the paths are inside WSL. `WSC_LOCAL_HOME` and `XDG_CONFIG_HOME` change them.

```text
~/.local/share/wsc-local/projects/
~/.config/wsc-local/secrets/
```

The dashboard and published container ports bind to loopback. Local HTTPS uses mkcert. Let's Encrypt is for a public domain on the target server, not for `localhost`.

Exports remove the Workbench's local database credentials from `config.inc.php` and do not contain the local `.env` or TLS keys. WoltLab content and its database stay in the package. Treat it as a full backup. Temporary recovery and authentication files are left out.

```bash
./wsc import SOURCE project-name
```

The command recognizes older wsc-local files, old snapshots, and Workbench export packages. Old raw database folders are not copied between database profiles. A complete state needs a matching dump or export. [Test coverage and limits](docs/user-test.md)

</details>

<details>
<summary><strong>Update the Workbench itself</strong></summary>

From **1.2.0** onward, the Workbench reports new stable releases in the dashboard. Under **Updates** you can install after a preview, or open the manual instructions. Git and ZIP installations are recognized. Checksums, protection of local changes, a recovery point, and an automatic dashboard restart are part of the flow. WoltLab projects and credentials stay in place.

Look for a newer version:

```bash
./wsc update --check
```

Install after the preview and your confirmation:

```bash
./wsc update
```

Update it yourself instead:

```bash
./wsc update --guide
```

**From 1.1.0 or older**, once:

```bash
git pull --ff-only
./start.sh
```

For a ZIP installation, copy the program files into the existing folder as the guide describes and keep personal data. After that, later releases can use the update function. [Updates, conflicts, and recovery](docs/updating.md#english)

**Releases are created automatically.** A new version tag starts the GitHub checks. After they succeed, the workflow publishes the ZIP and the SHA-256 checksum. The version is the badge at the top of this README and the footer of the dashboard.

The older single stack is still available with `./setup.sh --legacy` and `./start.sh --legacy`. `tools.sh` and `reset.sh` belong to that old stack. For Workbench projects use the dashboard or `./wsc`.

</details>

<details>
<summary><strong>Checks and origins</strong></summary>

In this order, only if you are checking the Workbench itself:

```bash
python3 -m unittest discover -s tests -v
npm ci
npx playwright install chromium
npm run test:ui
```

The short local check is `python3 scripts/check.py`. `--ui` also runs the Chromium tests, `--release` checks release metadata and builds the ZIP once, and `--metadata` checks only the version notes. `python3 scripts/check_repo.py` checks that the repository stays clean. CI is the authority: it checks portable logic on Linux, macOS, and Windows, and browser flows with isolated API responses. Real WoltLab and Docker installations were tested locally on Linux. Full Docker and browser acceptance on macOS and Windows/WSL2 are separate platform tests. [Detailed test notes](docs/user-test.md)

[wsc-dockerized](https://github.com/SoftCreatRMedia/wsc-dockerized) supplies WoltLab-specific ideas; [DDEV](https://github.com/ddev/ddev) project configuration; [Lando](https://docs.lando.dev/plugins/) profiles and optional services; [XAMPP](https://github.com/ApacheFriends/xampp-control-windows) direct service controls. The Workbench stays focused on WoltLab. Font Awesome Free is bundled locally, with [license and sources](panel/vendor/fontawesome/).

[Product principles](docs/product.md) · [Changes and release notes](CHANGELOG.md) · [Security reports](SECURITY.md) · [GitHub releases](https://github.com/benjarogit/wsc-local/releases)

</details>
