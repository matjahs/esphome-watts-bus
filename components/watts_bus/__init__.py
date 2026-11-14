import esphome.codegen as cg
import esphome.config_validation as cv
from esphome import automation, pins
from esphome.components import sensor as sensor_component  # "sensor" is this package's own sensor.py
from esphome.const import (
    CONF_ID,
    CONF_PIN,
    CONF_TRIGGER_ID,
    ENTITY_CATEGORY_DIAGNOSTIC,
    STATE_CLASS_TOTAL_INCREASING,
)

CODEOWNERS = ["@matjahs"]
AUTO_LOAD = ["sensor"]

CONF_STALE_TIMEOUT = "stale_timeout"
CONF_WATTS_BUS_ID = "watts_bus_id"
CONF_ON_FRAME = "on_frame"
CONF_ON_REJECTED = "on_rejected"
CONF_REJECTED_BURSTS = "rejected_bursts"

watts_bus_ns = cg.esphome_ns.namespace("watts_bus")
WattsBus = watts_bus_ns.class_("WattsBus", cg.Component)
WattsThermostat = watts_bus_ns.class_("WattsThermostat")
FrameTrigger = watts_bus_ns.class_(
    "FrameTrigger",
    automation.Trigger.template(cg.uint16, cg.uint8, cg.float_, cg.float_, cg.float_, cg.std_string),
)
RejectedTrigger = watts_bus_ns.class_("RejectedTrigger", automation.Trigger.template(cg.uint32, cg.uint32))

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(WattsBus),
        # Input only: the component listens on R/T and never drives the bus.
        cv.Required(CONF_PIN): pins.internal_gpio_input_pin_schema,
        cv.Optional(CONF_STALE_TIMEOUT, default="10min"): cv.positive_time_period_milliseconds,
        # Bursts on the bus that did not decode: collisions, noise or unknown traffic.
        cv.Optional(CONF_REJECTED_BURSTS): sensor_component.sensor_schema(
            accuracy_decimals=0,
            state_class=STATE_CLASS_TOTAL_INCREASING,
            entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
            icon="mdi:alert-decagram-outline",
        ),
        # Runs for every confirmed frame. Variables: id, frame_type, temperature, setpoint, heat_demand, raw.
        cv.Optional(CONF_ON_FRAME): automation.validate_automation(
            {cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(FrameTrigger)}
        ),
        # Runs for every burst that did not decode. Variables: edges, duration_us.
        cv.Optional(CONF_ON_REJECTED): automation.validate_automation(
            {cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(RejectedTrigger)}
        ),
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    pin = await cg.gpio_pin_expression(config[CONF_PIN])
    cg.add(var.set_pin(pin))
    cg.add(var.set_stale_timeout(config[CONF_STALE_TIMEOUT]))

    if CONF_REJECTED_BURSTS in config:
        sens = await sensor_component.new_sensor(config[CONF_REJECTED_BURSTS])
        cg.add(var.set_rejected_bursts_sensor(sens))

    for conf in config.get(CONF_ON_FRAME, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(
            trigger,
            [
                (cg.uint16, "id"),
                (cg.uint8, "frame_type"),
                (cg.float_, "temperature"),
                (cg.float_, "setpoint"),
                (cg.float_, "heat_demand"),
                (cg.std_string, "raw"),
            ],
            conf,
        )
    for conf in config.get(CONF_ON_REJECTED, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [(cg.uint32, "edges"), (cg.uint32, "duration_us")], conf)
