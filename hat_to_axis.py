"""Joystic Gremlin plugin to assign buttons to control a vjoy axis."""

import functools
import math
import gremlin
from gremlin.user_plugin import *
from gremlin.macro import Macro, HoldRepeat, VJoyAction, MacroManager

manager = MacroManager()

mode = ModeVariable(
    "Mode",
    "The mode to use for this mapping"
)

vjoy_axis_x = VirtualInputVariable(
    "Output Axis X",
    "vJoy X axis to move with the LEFT and RIGHT directions of the hat",
    [gremlin.common.InputType.JoystickAxis],
)

vjoy_axis_y = VirtualInputVariable(
    "Output Axis Y",
    "vJoy Y axis to move with the UP and DOWN directions of the hat",
    [gremlin.common.InputType.JoystickAxis],
)

input_hat = PhysicalInputVariable(
    "Input Hat",
    "Button that will increase the axis position.",
    [gremlin.common.InputType.JoystickHat],
)

min_step_rate = IntegerVariable(
    "Min rate",
    "Minimal step size to increase /decrease the axis value",
    3,
    0,
    1024,
)

max_step_rate = IntegerVariable(
    "Max rate",
    "Maximal step size to increase / decrease the axis value",
    1,
    0,
    1024,
)

rate_groth = IntegerVariable(
    "Rate groth",
    "How quick the step size increastes during holding",
    1,
    0,
    1024,
)

# Decorators for the physical buttons
hat_in = input_hat.create_decorator(mode.value)


# axis_x = vjoy_axis_x.create_decorator(mode.value)
# axis_y = vjoy_axis_z.create_decorator(mode.value)

class AxisStepMacro(Macro):
    def __init__(self, vjoy_id, input_id, min_rate, max_rate, rate_groth):
        super(AxisStepMacro, self).__init__()
        self._vjoy_id = vjoy_id
        self._input_id = input_id
        self._min_rate = min_rate
        self._max_rate = max_rate
        self._rate_groth = rate_groth
        self._current_rate = 0
        self._direction = 0
        self._running = False
        self._axis = gremlin.joystick_handling.VJoyProxy()[vjoy_id].axis(input_id)
        self._last_axis_value = None
        self._reset_axis = VJoyAction(
            self._vjoy_id,
            gremlin.common.InputType.JoystickAxis,
            self._input_id,
            0,
            "absolute"
        )
        self.repeat = HoldRepeat()

    def _start(self):
        self._current_rate = self._min_rate
        self._last_axis_value = None
        self._running = True
        manager.queue_macro(self)

    def _stop(self):
        self._current_rate = 0
        self._reset_axis()
        self._last_axis_value = None
        self._running = False
        manager.terminate_macro(self)

    def set_direction(self, direction):
        self._direction = direction
        if direction != 0 and not self._running:
            self._start()

    @property
    def sequence(self):
        gremlin.util.log("---axis: " + str(self._axis.value))
        # if self._last_axis_value is None or self._last_axis_value != self._axis.value:
        self._current_rate += self._rate_groth
        if self._direction > 0:  # increase rate
            vjoy_rate = self._current_rate / 1000
        elif self._direction < 0:  # decrease rate
            vjoy_rate = -self._current_rate / 1000

        self._current_rate = max(min(self._max_rate, self._current_rate), -self._max_rate)  # clamp rate


        if self._direction == 0:
            vjoy_rate = -(self._axis.value * 1000 / 2 ) - math.copysign(2 * self._min_rate, self._axis.value)
            self._current_rate = abs(vjoy_rate)
            vjoy_rate /= 1000
            gremlin.util.log("shrink: " + str(vjoy_rate))
            if (self._axis.value + vjoy_rate) / self._axis.value <= 0 or abs(self._axis.value) < 2 * self._min_rate / 1000:
                gremlin.util.log("Stop!")
                self._stop()
                return []

        gremlin.util.log("rate: " + str(vjoy_rate))
        self._last_axis_value = self._axis.value
        action = VJoyAction(
            self._vjoy_id,
            gremlin.common.InputType.JoystickAxis,
            self._input_id,
            vjoy_rate,
            "relative"
        )

        return [action,]


macro_x = AxisStepMacro(
    vjoy_axis_x.vjoy_id,
    vjoy_axis_x.input_id,
    min_step_rate.value,
    max_step_rate.value,
    rate_groth.value
)

macro_y = AxisStepMacro(
    vjoy_axis_y.vjoy_id,
    vjoy_axis_y.input_id,
    min_step_rate.value,
    max_step_rate.value,
    rate_groth.value
)

@hat_in.hat(input_hat.input_id)
def process_input(event):
    # gremlin.util.log("Value: "+str(event.value))
    # gremlin.util.log("is pressed: "+str(event.is_pressed))
    macro_x.set_direction(event.value[0])
    macro_y.set_direction(event.value[1])
