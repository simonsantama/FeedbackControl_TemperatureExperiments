"""
Algorithm used to calibrate the lamps every morning.

"""

# libraries
import numpy as np
import sys
import time
import msvcrt
import csv
import os
import pickle
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import pandas as pd
from pandas import ExcelWriter
from datalogger import DataLogger

# establish general constants and parameters
number_reads_per_calib = 20
span_O2_concentration = 20.95
span_CO_concentration = 422
span_CO2_concentration = 2350

# create instance of the data logger and check connection
print("\nConnection to data logger")
rm, logger = DataLogger().new_instrument()

print("Starting HRR calibration procedure.\n")

# calibrate DPT
dpt_input = input("Ready to calibrate DPT?\n")
dpt_zero = np.zeros(number_reads_per_calib)
if dpt_input.lower() in ["y", "yes"]:
	for i in range(number_reads_per_calib):
		response, _ = DataLogger.query_data_for_HRR(logger)
		dpt_zero[i] = response[1]
print(f" - Mean zero value in volts for:\n  DPT: {dpt_zero.mean()}")


# calibrate zero levels for the gases
gases_zero_input = input("\nReady to calibrate zero for gases?\n")
oxygen_zero = np.zeros_like(dpt_zero)
oxygen_inlet_zero = np.zeros_like(dpt_zero)
co_zero = np.zeros_like(dpt_zero)
co2_zero = np.zeros_like(dpt_zero)
if gases_zero_input.lower() in ["y", "yes"]:
	for i in range(number_reads_per_calib):
		response, _ = DataLogger.query_data_for_HRR(logger)
		oxygen_zero[i] = response[0]
		oxygen_inlet_zero[i] = response[5]
		co_zero[i] = response[2]
		co2_zero[i] = response[3]
print(f" - Mean zero value in volts for:\n  O2: {oxygen_zero.mean()}\n  O2_inlet: {oxygen_inlet_zero.mean()}\n  CO: {co_zero.mean()}\n  CO2: {co2_zero.mean()}")

# calibrate span levels for oxygen
oxygen_span_input = input("\nReady to calibrate span for oxygen sensors?\n")
oxygen_span = np.zeros_like(dpt_zero)
oxygen_inlet_span = np.zeros_like(dpt_zero)
if oxygen_span_input.lower() in ["y", "yes"]:
	for i in range(number_reads_per_calib):
		response, _ = DataLogger.query_data_for_HRR(logger)
		oxygen_span[i] = response[0]
		oxygen_inlet_span[i] = response[5]
print(f" - Mean span value in volts for:\n  O2: {oxygen_span.mean()}\n  O2_inlet: {oxygen_inlet_span.mean()}")


# calibrate span levels for oxygen
coco2_span_input = input("\nReady to calibrate span for CO/CO2?\n")
co_span = np.zeros_like(dpt_zero)
co2_span = np.zeros_like(dpt_zero)
if coco2_span_input.lower() in ["y", "yes"]:
	for i in range(number_reads_per_calib):
		response, _ = DataLogger.query_data_for_HRR(logger)
		co_span[i] = response[2]
		co2_span[i] = response[3]
print(f" - Mean span value in volts for:\n  CO: {co_span.mean()}\n  CO2: {co2_span.mean()}")

# save all readings into one data frame
data = {"oxygen_zero":oxygen_zero,
	"oxygen_span":oxygen_span,
	"oxygen_inlet_zero":oxygen_inlet_zero,
	"oxygen_zero_span":oxygen_inlet_span,
	"CO_zero":co_zero, "CO_span":co_span,
	"CO2_zero":co2_zero, "CO2_span":co2_span,
	"DPT_zero": dpt_zero}
all_readings = pd.DataFrame(data=data)

# create linear fits for the O2, CO and CO2 analysers
poly_degree = 1
mean_zeros = [oxygen_zero.mean(), oxygen_inlet_zero.mean(),
	co_zero.mean(), co2_zero.mean()]
mean_spans = [oxygen_span.mean(), oxygen_inlet_span.mean(),
	co_span.mean(), co2_span.mean()]

all_coefficients = []
x_pairs = [(oxygen_zero.mean(), oxygen_span.mean()),
	(oxygen_inlet_zero.mean(), oxygen_inlet_span.mean()),
	(co_zero.mean(), co_span.mean()),
	(co2_zero.mean(), co2_span.mean())]
y_pairs = [(0, span_O2_concentration), 
	(0, span_O2_concentration),
	(0, span_CO_concentration), 
	(0, span_CO2_concentration)]

all_coefficients = []
for i in range(len(mean_zeros)):
	all_coefficients.append(np.polyfit(x_pairs[i], y_pairs[i],
		poly_degree))
coefficients = list(zip(*all_coefficients))
data = {"Gas": ["oxygen", "oxygen_inlet", "CO", "CO2"],
	"zero_mean": mean_zeros, "span_mean": mean_spans,
	"coeff_a": coefficients[0],
	"coeff_b": coefficients[1]}
all_coeff_data = pd.DataFrame(data = data)



# save data into calibration data file
address_folder = "C:\\Users\\FireLab\\Desktop\\Simon\\FeedbackControl_MassExperiments\\hrr_calibration_data"
name_file = f"{datetime.now().strftime('%Y-%m-%d-%H%M%S')}.xlsx"
address_file = os.path.join(address_folder, name_file)

with ExcelWriter(address_file) as writer:
	all_readings.to_excel(writer, sheet_name = "calibration_data", index = False)
	all_coeff_data.to_excel(writer, sheet_name = "polynomial_fit")

# finish the calibration
logger.write(':SOURce:VOLTage %G,(%s)' % (0.0, '@304'))
logger.close()
rm.close()
print("\n\nCalibration finished")