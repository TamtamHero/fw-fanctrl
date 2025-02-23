# Table of Content

<!-- TOC -->
* [Table of Content](#table-of-content)
* [Configuration](#configuration)
  * [Default Strategy](#default-strategy)
  * [Discharging Strategy](#discharging-strategy)
  * [Strategies](#strategies)
    * [Requirements](#requirements)
    * [Speed Curve](#speed-curve)
    * [Fan Speed Update Frequency](#fan-speed-update-frequency)
    * [Moving Average Interval](#moving-average-interval)
<!-- TOC -->

# Configuration

The service uses these configuration files by default:

- Main configuration: `/etc/fw-fanctrl/config.json`
- JSON Schema: `/etc/fw-fanctrl/config.schema.json`

For custom installations using dest-dir or sysconf-dir parameters:

- `[dest-dir(/)][sysconf-dir(/etc)]/fw-fanctrl/config.json`
- `[dest-dir(/)][sysconf-dir(/etc)]/fw-fanctrl/config.schema.json`

The configuration contains a list of strategies, ranked from the quietest to loudest,
as well as the default and discharging strategies.

For example, one could use a lower fan speed strategy on discharging to optimize battery life (- noise, + heat),
and a high fan speed strategy on AC (+ noise, - heat).

**The schema contains the structure and restrictions for a valid configuration.**

You can add or edit strategies, and if you think you have one that deserves to be shared,
feel free to share it in [#110](https://github.com/TamtamHero/fw-fanctrl/issues/110).

## Default Strategy

The default strategy serves as the initial fan control profile when the service starts.

It remains active unless you manually select a different strategy,
at which point your chosen strategy takes precedence until you reset to the default strategy explicitly,
or the service restarts.

It can be changed by replacing the value of the `defaultStrategy` field with one of the strategies present in the
configuration.

e.g.:

```
"defaultStrategy": "medium"
```

## Discharging Strategy

The discharging strategy will be used when on default strategy behavior and battery power.

It can be changed by replacing the value of the `strategyOnDischarging` field with one of the strategies present in the
configuration.

```
"strategyOnDischarging": "laziest"
```

This field is optional and can be left empty for it to have the same behavior as on AC.

## Strategies

Define strategies under strategies object using this format:

```
"strategies": {
  "strategy-name": {
    "speedCurve": [ ... ],
    "fanSpeedUpdateFrequency": 5,
    "movingAverageInterval": 20
  }
}
```

### Requirements

Strategies must have unique names composed of upper/lower case letters, numbers, underscores or hyphens.

`[a-zA-Z0-9_-]+`

And, at least have the `speedCurve` property defined.

### Speed Curve

It represents by the curve points for `f(temperature) = fan(s) speed`.

The `temp` field value is a number with precision of up to 0.01°C (e.g., 15.23),
while the `speed` is a positive integer between 0 and 100 %.

It should contain at least a single temperature point.

```
"speedCurve": [
  { "temp": 40,   "speed": 20 },
  { "temp": 60.5, "speed": 50 },
  { "temp": 80.7, "speed": 100 }
]
```

> `fw-fanctrl` measures the CPU temperature, calculates a moving average of it, and then finds an
> appropriate `fan speed` value by interpolating on the curve.

### Fan Speed Update Frequency

It is the interval between fan speed adjustments.

- Lower values → faster response to temperature changes
- Higher values → smoother transitions

It is an optional positive integer comprised between 1 and 10 and defaults to 5.

```
"fanSpeedUpdateFrequency": 5
```

> This is for comfort, otherwise the speed will change too often, which is noticeable and annoying, especially at low
> speed.

### Moving Average Interval

It is the time window in seconds over which the moving average of temperature is calculated.

- Lower values → immediate reaction to spikes
- Higher values → stabilized readings

It is an optional positive integer comprised between 1 and 100 and defaults to 20.

```
"movingAverageInterval": 20
```

---

Once the configuration has been changed, you must reload it with the following command

```bash
fw-fanctrl reload
```
