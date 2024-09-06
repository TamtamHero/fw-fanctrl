# Table of Content

- [Configuration](#configuration)
  * [Default strategy](#default-strategy)
  * [Charging/Discharging strategies](#chargingdischarging-strategies)
  * [Editing strategies](#editing-strategies)

# Configuration

After installation, you will find the configuration file in the following location:

`/etc/fw-fanctrl/config.json`

If you have modified the `dest-dir` or `sysconf-dir`, here is the corresponding pattern

`[dest-dir(/)][sysconf-dir(/etc)]/fw-fanctrl/config.json`

It contains a list of strategies, ranked from the quietest to loudest, as well as the default and discharging
strategies.

For example, one could use a lower fan speed strategy on discharging to optimise battery life (- noise, + heat),
and a high fan speed strategy on AC (+ noise, - heat).

You can add or edit strategies, and if you think you have one that deserves to be shared, feel free to make a PR to this
repo :)

## Default strategy

The default strategy is the one used when the service is started.

It can be changed by replacing the value of the `defaultStrategy` field with one of the strategies present in the
configuration.

```json
"defaultStrategy": "[STRATEGY NAME]"
```

## Charging/Discharging strategies

The discharging strategy is the one that will be used when the laptop is not on AC,
Otherwise the default strategy is used.

It can be changed by replacing the value of the `strategyOnDischarging` field with one of the strategies present in the
configuration.

```json
"strategyOnDischarging": "[STRATEGY NAME]"
```

This is optional and can be left empty to have the same strategy at all times.

## Editing strategies

Strategies can be configured with the following parameters:

> **SpeedCurve**:
>
> It is represented by the curve points for `f(temperature) = fan(s) speed`.
>
> ```json
> "speedCurve": [
>     { "temp": [TEMPERATURE POINT], "speed": [PERCENTAGE SPEED] },
>     ...
> ]
> ```
>
> `fw-fanctrl` measures the CPU temperature, calculates a moving average of it, and then finds an
> appropriate `fan speed`
> value by interpolating on the curve.

> **FanSpeedUpdateFrequency**:
>
> It is the interval in seconds between fan speed calculations.
>
> ```json
> "fanSpeedUpdateFrequency": [UPDATE FREQUENCY]
> ```
>
> This is for comfort, otherwise the speed will change too often, which is noticeable and annoying, especially at low
> speed.
>
> For a more responsive fan, you can reduce this setting.
>
> **Defaults to 5 seconds.** (minimum 1)

> **MovingAverageInterval**:
>
> It is the number of seconds over which the moving average of temperature is calculated.
>
> ```json
> "movingAverageInterval": [AVERAGING INTERVAL]
> ```
>
> Increase it, and the fan speed changes more gradually. Lower it, and it becomes more responsive.
>
> **Defaults to 20 seconds.** (minimum 1)

> **CriticalTemp**:
>
> It is a temperature after which the moving average is ignored and only the current temperature is considered.
>
> ```json
> "criticalTemp": [CRITICAL TEMPERATURE]
> ```
>
> Increase it, and the moving average applies for longer. Lower it, and the moving average is disabled sooner.
>
> If it is unset or set to null, the moving average is always considered (effectively the same as setting it to a
> very high number).
>
> **Defaults to null.**

---

Once the configuration has been changed, you must reload it with the following command

```bash
fw-fanctrl reload
```
