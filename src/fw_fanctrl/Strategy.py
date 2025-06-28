class Strategy:
    name = None
    fan_speed_update_frequency = None
    moving_average_interval = None
    speed_curve = None
    ramp_up_time = None
    ramp_down_time = None
    ramp_quickly_temperature = None
    ramp_quickly_time = None
    critical_temperature = None

    def __init__(self, name, parameters):
        self.name = name
        self.fan_speed_update_frequency = parameters["fanSpeedUpdateFrequency"]
        if self.fan_speed_update_frequency is None or self.fan_speed_update_frequency == "":
            self.fan_speed_update_frequency = 5
        self.moving_average_interval = parameters["movingAverageInterval"]
        if self.moving_average_interval is None or self.moving_average_interval == "":
            self.moving_average_interval = 20
        self.speed_curve = parameters["speedCurve"]
        self.ramp_up_time = parameters.get("rampUpTime", 3)
        self.ramp_down_time = parameters.get("rampDownTime", 3)
        self.ramp_quickly_temperature = parameters.get("rampQuicklyTemperature", 85)
        self.ramp_quickly_time = parameters.get("rampQuicklyTime", 1)
        self.critical_temperature = parameters.get("criticalTemperature", 95)
