# Commands

Here is a list of commands and options used to interact with the service.

the base of all commands is the following

```shell
fw-fanctrl [commands and options]
```

First, the global options

| Option                    | Optional | Choices       | Default | Description                                                                    |
|---------------------------|----------|---------------|---------|--------------------------------------------------------------------------------|
| --socket-controller, --sc | yes      | unix          | unix    | the socket controller to use for communication between the cli and the service |
| --output-format           | yes      | NATURAL, JSON | NATURAL | the client socket controller output format                                     |

**run**

run the service manually

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

change the current strategy

| Option      | Optional | Description                     |
|-------------|----------|---------------------------------|
| \<strategy> | no       | the name of the strategy to use |

**reset**

reset to the default strategy

**reload**

reload the configuration file

**pause**

pause the service

**resume**

resume the service

**print**

print the selected information

| Option             | Optional | Choices                   | Default | Description            |
|--------------------|----------|---------------------------|---------|------------------------|
| \<print_selection> | yes      | all, current, list, speed | all     | what should be printed |

| Choice  | Description                      |
|---------|----------------------------------|
| all     | All details                      |
| current | The current strategy being used  |
| list    | List available strategies        |
| speed   | The current fan speed percentage |
