# Commands

<!-- TOC -->
* [Commands](#commands)
  * [fw-fanctrl](#fw-fanctrl)
  * [fw-fanctrl-setup](#fw-fanctrl-setup)
<!-- TOC -->

## fw-fanctrl

Here is a list of commands and options used to interact with the service.

The base of all commands is the following

```shell
fw-fanctrl [commands and options]
```

First, the global options

| Option                    | Optional | Choices       | Default | Description                                                                    |
|---------------------------|----------|---------------|---------|--------------------------------------------------------------------------------|
| --socket-controller, --sc | yes      | unix          | unix    | the socket controller to use for communication between the cli and the service |
| --output-format           | yes      | NATURAL, JSON | NATURAL | the client socket controller output format                                     |

**run**

Run the service manually

If you have installed it correctly, the systemd `fw-fanctrl.service` service will do this for you, so you probably will
never need those.

| Option                      | Optional | Choices        | Default              | Description                                                                       |
|-----------------------------|----------|----------------|----------------------|-----------------------------------------------------------------------------------|
| \<strategy>                 | yes      |                | the default strategy | the name of the strategy to use                                                   |
| --config                    | yes      | \[CONFIG_PATH] |                      | the configuration file path                                                       |
| --silent, -s                | yes      |                |                      | disable printing speed/temp status to stdout                                      |
| --hardware-controller, --hc | yes      | ectool         | ectool               | the hardware controller to use for fetching and setting the temp and fan(s) speed |
| --no-battery-sensors        | yes      |                |                      | disable checking battery temperature sensors (for mainboards without batteries)   |

**use**

Change the current strategy

| Option      | Optional | Description                     |
|-------------|----------|---------------------------------|
| \<strategy> | no       | the name of the strategy to use |

**reset**

Reset to the default strategy

**reload**

Reload the configuration file

**pause**

Pause the service

**resume**

Resume the service

**print**

Print the selected information

| Option             | Optional | Choices                   | Default | Description            |
|--------------------|----------|---------------------------|---------|------------------------|
| \<print_selection> | yes      | all, current, list, speed | all     | what should be printed |

| Choice  | Description                      |
|---------|----------------------------------|
| all     | All details                      |
| current | The current strategy being used  |
| list    | List available strategies        |
| speed   | The current fan speed percentage |

## fw-fanctrl-setup

The `fw-fanctrl-setup` command allows the user to uninstall or re-install the current service version setup.

> If you installed the service with a package manager,
> please do not use this command and manage it with the package manager instead.

The base of all commands is the following

```shell
fw-fanctrl-setup [commands and options]
```

**run**

It takes a single command (`run`) and multiple options

| Option               | Optional | Choices | Default                            | Description                                                    |
|----------------------|----------|---------|------------------------------------|----------------------------------------------------------------|
| --remove, -r         | yes      |         | false                              | uninstall additional files from the system                     |
| --prefix-dir, -p     | yes      |         | `/usr`                             | specify an installation prefix directory                       |
| --dest-dir, -d       | yes      |         |                                    | specify an installation destination directory                  |
| --sysconf-dir, -s    | yes      |         | `/etc`                             | specify a default configuration directory                      |
| --no-sudo            | yes      |         | false                              | disable root privilege requirement                             |
| --no-ectool          | yes      |         | false                              | disable ectool installation                                    |
| --no-pre-uninstall   | yes      |         | false                              | disable pre-uninstall process                                  |
| --no-post-install    | yes      |         | false                              | disable post-install process                                   |
| --no-battery-sensors | yes      |         | false                              | disable checking battery temperature sensors                   |
| --python-prefix-dir  | yes      |         | `[dest-dir]/[prefix-dir]`          | specify the python prefix directory of the installed package   |
| --executable-path    | yes      |         | `[executable-path]/bin/fw-fanctrl` | `fw-fanctrl` executable path                                   |
| --keep-config        | yes      |         | false                              | do not delete the existing configuration during uninstallation |
