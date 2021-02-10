"""
PID function to calculate the IHF (output) based on a set_point (mlr_desired)
and an input (mlr_averaged)

See:
http://brettbeauregard.com/blog/2011/04/improving-the-beginners-pid-introduction/
"""

import time
import numpy as np

def PID_IHF(current_input, setpoint, previous_time, last_error, last_input, integral_term, kp, ki, kd, max_lamp_voltage,
	min_lamp_voltage):
    """
    Uses a PID algorithm to calculate the IHF based a target mlr and the current mlr calculated


	Parameters:
	----------
	current_input: float
		current mlr (calculated instantaneously and then averaged for smoothing)

	setpoint: float
		desired mlr

	previous_time: time.time()
		previous time that the PID controller was called in seconds

	last_error: float
		previous error calculated by the PID algorithm

	last_input: float
		previous mlr value

	integral_term: float
		stores the sum of the error*ki for every iteration

	kp: float
		proportional coefficient

	ki: float
		integral coefficient

	kd: float
		derivate coefficient

	max_lamp_voltage: float
		maximum voltage that can be send to the FPA lamps

	min_lamp_voltage: float
		minimum voltage that can send to the FPA lamps


	Returns:
	-------
	output: float
		IHF (volts) to be sent to the lamps

	now: time.time()
		time at which this iteration of the PID took place (serves as preivous
		time for the next call of the PID)

	error: float
		current error

	proportional_term: float
		proportional term in the PID eq.

	integral_term: float
		integral term in the PID eq. To be recorded

	derivative_term: float
		derivative term in the PID eq.

    """

    # how long since we last calculated
    now = time.time()
    time_change = now - previous_time

    # compute all the working error variables
    error = setpoint - current_input
    error_sum = error * time_change
    d_input = (current_input - last_input) / time_change

    # compute all the terms
    proportional_term = kp*error
    integral_term += ki * error_sum

    # clamp the integral term so that the PID understand the limits of the lamps
    if integral_term > max_lamp_voltage:
    	integral_term = max_lamp_voltage
    elif integral_term < min_lamp_voltage:
    	integral_term = min_lamp_voltage


    derivative_term = kd * d_input

    # Compute the Output
    output = proportional_term + integral_term - derivative_term

    # protect the FPA ()
    if output > max_lamp_voltage:
        output = max_lamp_voltage
    elif output < min_lamp_voltage:
    	output = min_lamp_voltage

    return output, now, error, proportional_term, integral_term, derivative_term