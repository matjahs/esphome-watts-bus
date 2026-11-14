import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import binary_sensor, sensor
from esphome.const import (
    CONF_ID,
    CONF_TEMPERATURE,
    DEVICE_CLASS_DURATION,
    DEVICE_CLASS_TEMPERATURE,
    ENTITY_CATEGORY_DIAGNOSTIC,
    STATE_CLASS_MEASUREMENT,
    UNIT_CELSIUS,
    UNIT_PERCENT,
    UNIT_SECOND,
)

from . import CONF_WATTS_BUS_ID, WattsBus, WattsThermostat

DEPENDENCIES = ["watts_bus"]
AUTO_LOAD = ["binary_sensor"]

CONF_THERMOSTAT_ID = "thermostat_id"
CONF_SETPOINT = "setpoint"
CONF_HEAT_DEMAND = "heat_demand"
CONF_COOLING = "cooling"
CONF_REPORT_INTERVAL = "report_interval"

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(WattsThermostat),
        cv.GenerateID(CONF_WATTS_BUS_ID): cv.use_id(WattsBus),
        cv.Required(CONF_THERMOSTAT_ID): cv.hex_uint16_t,
        cv.Optional(CONF_TEMPERATURE): sensor.sensor_schema(
            unit_of_measurement=UNIT_CELSIUS,
            accuracy_decimals=1,
            device_class=DEVICE_CLASS_TEMPERATURE,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
        cv.Optional(CONF_SETPOINT): sensor.sensor_schema(
            unit_of_measurement=UNIT_CELSIUS,
            accuracy_decimals=1,
            device_class=DEVICE_CLASS_TEMPERATURE,
            state_class=STATE_CLASS_MEASUREMENT,
            icon="mdi:thermostat",
        ),
        cv.Optional(CONF_HEAT_DEMAND): sensor.sensor_schema(
            unit_of_measurement=UNIT_PERCENT,
            accuracy_decimals=0,
            state_class=STATE_CLASS_MEASUREMENT,
            icon="mdi:radiator",
        ),
        # Only the Master H&C thermostat switches between heating and cooling.
        cv.Optional(CONF_COOLING): binary_sensor.binary_sensor_schema(icon="mdi:snowflake"),
        # Time since the previous report of this thermostat. Lost reports show as longer intervals.
        cv.Optional(CONF_REPORT_INTERVAL): sensor.sensor_schema(
            unit_of_measurement=UNIT_SECOND,
            accuracy_decimals=0,
            device_class=DEVICE_CLASS_DURATION,
            state_class=STATE_CLASS_MEASUREMENT,
            entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
            icon="mdi:timer-outline",
        ),
    }
)

SENSOR_SETTERS = {
    CONF_TEMPERATURE: "set_temperature_sensor",
    CONF_SETPOINT: "set_setpoint_sensor",
    CONF_HEAT_DEMAND: "set_heat_demand_sensor",
    CONF_REPORT_INTERVAL: "set_report_interval_sensor",
}


async def to_code(config):
    bus = await cg.get_variable(config[CONF_WATTS_BUS_ID])
    thermostat = cg.new_Pvariable(config[CONF_ID], config[CONF_THERMOSTAT_ID])
    cg.add(bus.register_thermostat(thermostat))

    for key, setter in SENSOR_SETTERS.items():
        if key not in config:
            continue
        sens = await sensor.new_sensor(config[key])
        cg.add(getattr(thermostat, setter)(sens))

    if CONF_COOLING in config:
        cooling = await binary_sensor.new_binary_sensor(config[CONF_COOLING])
        cg.add(thermostat.set_cooling_binary_sensor(cooling))
