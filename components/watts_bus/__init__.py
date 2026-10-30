import esphome.codegen as cg
import esphome.config_validation as cv
from esphome import pins
from esphome.const import CONF_ID, CONF_PIN

CODEOWNERS = ["@matjahs"]

CONF_STALE_TIMEOUT = "stale_timeout"
CONF_WATTS_BUS_ID = "watts_bus_id"

watts_bus_ns = cg.esphome_ns.namespace("watts_bus")
WattsBus = watts_bus_ns.class_("WattsBus", cg.Component)
WattsThermostat = watts_bus_ns.class_("WattsThermostat")

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(WattsBus),
        # Input only: the component listens on R/T and never drives the bus.
        cv.Required(CONF_PIN): pins.internal_gpio_input_pin_schema,
        cv.Optional(CONF_STALE_TIMEOUT, default="10min"): cv.positive_time_period_milliseconds,
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    pin = await cg.gpio_pin_expression(config[CONF_PIN])
    cg.add(var.set_pin(pin))
    cg.add(var.set_stale_timeout(config[CONF_STALE_TIMEOUT]))
