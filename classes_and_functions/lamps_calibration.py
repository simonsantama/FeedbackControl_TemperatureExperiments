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


# add path to import functions and classes (absolute path on the FPA's computer)
sys.path.insert(1, r"C:\\Users\\FireLab\\Desktop\\Simon\\FeedbackControl_MassExperiments\\classes_and_functions")
from datalogger import DataLogger


#####
# CONNECT TO LOAD CELL AND DATA LOGGER AND INSTANTIATE CLASSES
#####

# create instance of the data logger and check connection
print("\nConnection to data logger")
rm, logger = DataLogger().new_instrument()


#####
# CALIBRATE THE LAMPS.
#####

# define constants
lamp_voltage_limit = 4.5

# define arrays used for polynomial fitting
hf_gauge_factor = 0.0001017          # V/kW/m2
nmbr_readings_pervoltage = 20
output_voltages = np.linspace(0,lamp_voltage_limit,20)
all_output_voltages = np.zeros(nmbr_readings_pervoltage*len(output_voltages)*2)
all_input_voltages = np.zeros_like(all_output_voltages)
all_input_kWm2 = np.zeros_like(all_output_voltages)


t = 0
time_start_logging = time.time()

print("\n\n---")
print("INCREASING")
print("---\n\n")
# increasing the heat flux in steps
for output_voltage in output_voltages:

	# protect the lamps
	if output_voltage > lamp_voltage_limit:
		output_voltage = lamp_voltage_limit

	# send voltage to lamps
	print(f"\n\n ---- Voltage output to the lamps: {np.round(output_voltage,4)} V\n")
	logger.write(':SOURce:VOLTage %G,(%s)' % (output_voltage, '@304'))

	# wait 10 seconds for the lamps to estabilise
	time.sleep(10)
	

	for nmr_readings in range(nmbr_readings_pervoltage):

		# read voltage from the  hf gauge
		input_voltage = float(logger.query(':MEASure:VOLTage:DC? (%s)' % ('@110')))
		print(f"Voltage readings from the hf gauge: {np.round(input_voltage*1000,6)} mV")
		print(f"Corresponding heat flux: {np.round(input_voltage/hf_gauge_factor,3)} kW/m2\n")

		# save the data
		all_output_voltages[t] = output_voltage
		all_input_voltages[t] = input_voltage
		all_input_kWm2[t] = input_voltage/hf_gauge_factor

		# update the counter
		t += 1


# decreasing the heat flux in steps
print("\n\n---")
print("DECREASING")
print("---\n\n")

for output_voltage in np.flip(output_voltages):

	# protect the lamps
	if output_voltage > lamp_voltage_limit:
		output_voltage = lamp_voltage_limit

	print(f"\n\n ---- Voltage output to the lamps: {np.round(output_voltage,4)} V\n")
	logger.write(':SOURce:VOLTage %G,(%s)' % (output_voltage, '@304'))

	# wait 10 seconds for the lamps to estabilise
	time.sleep(10)

	for nmr_readings in range(nmbr_readings_pervoltage):

		# read voltage from the  hf gauge
		input_voltage = float(logger.query(':MEASure:VOLTage:DC? (%s)' % ('@110')))
		print(f"Voltage readings from the hf gauge: {np.round(input_voltage*1000,6)} mV")
		print(f"Corresponding heat flux: {np.round(input_voltage/hf_gauge_factor,2)} kW/m2\n")

		# save the data
		all_output_voltages[t] = output_voltage
		all_input_voltages[t] = input_voltage
		all_input_kWm2[t] = input_voltage/hf_gauge_factor

		# update the counter
		t += 1


# condense all data into data frames
all_data = pd.DataFrame()
all_data.loc[:, "input_voltage_fromgauge"] = all_input_voltages
all_data.loc[:, "heat_flux_kWm-2"] = all_input_kWm2
all_data.loc[:, "output_voltage_tolamps"] = all_output_voltages


# polynomial fit (third degree) for heat flux gauge
poly_degree = 3
x = all_data.loc[:, "heat_flux_kWm-2"]
y = all_data.loc[:, "output_voltage_tolamps"]
coeff_heatflux_to_voltage = np.polyfit(x,y, poly_degree)
coeff_voltage_to_heatflux = np.polyfit(y,x, poly_degree)

coeff_data = pd.DataFrame()
coeff_data.loc[:, "coefficients_heatflux_to_voltage"] = coeff_heatflux_to_voltage
coeff_data.loc[:, "coefficients_voltage_to_heatflux"] = coeff_voltage_to_heatflux
coeff_data.loc[0, "Notes"] = "Polyfit. c[0]*x^3 + c[1]*x^2 + c[2]*x + c[3]"

all_data.loc[:, "polyfit_heatflux_to_voltage"] = np.polyval(
	coeff_heatflux_to_voltage, all_data.loc[:, "heat_flux_kWm-2"])
all_data.loc[:, "polyfit_voltage_to_heatflux"] = np.polyval(
	coeff_voltage_to_heatflux, all_data.loc[:, "output_voltage_tolamps"])

# save data into calibration data file
address_folder = "C:\\Users\\FireLab\\Desktop\\Simon\\FeedbackControl_MassExperiments\\calibration_data"
name_file = f"{datetime.now().strftime('%Y-%m-%d-%H%M%S')}.xlsx"
address_file = os.path.join(address_folder, name_file)

with ExcelWriter(address_file) as writer:
	all_data.to_excel(writer, sheet_name = "calibration_data", index = False)
	coeff_data.to_excel(writer, sheet_name = "polynomial_fit")

# plot
fig, axes = plt.subplots(1,2,figsize = (12,8))
x = all_data.loc[:, "heat_flux_kWm-2"]
y = all_data.loc[:, "output_voltage_tolamps"]

# format the plot
for a, ax in enumerate(axes):
	ax.set_xlim([[0,70],[0,5]][a])
	ax.set_xticks([np.linspace(0,70,8), np.linspace(0,5,6)][a])
	ax.set_ylim([[0,5],[0,70]][a])
	ax.set_yticks([np.linspace(0,5,6), np.linspace(0,70,8)][a])
	ax.set_xlabel(["Heat Flux [kW/m2]", "Voltage to lamps (VDC)"][a])
	ax.set_ylabel(["Voltage to lamps (VDC)", "Heat Flux [kW/m2]"][a])

# plot both regressions
axes[1].scatter(y,x,
	color = "dodgerblue", alpha = 0.5)
axes[1].plot(y, all_data.loc[:, "polyfit_voltage_to_heatflux"],
	color = "maroon",
	linewidth = 2)
axes[0].scatter(x,y,
	color = "dodgerblue", alpha = 0.5)
axes[0].plot(x, all_data.loc[:, "polyfit_heatflux_to_voltage"],
	color = "maroon",
	linewidth = 2)


address_plot = f"{address_file.split('.xlsx')[0]}.pdf"
plt.savefig(address_plot)

# finish the calibration
logger.write(':SOURce:VOLTage %G,(%s)' % (0.0, '@304'))
logger.close()
rm.close()

print("\n\nCalibration finished")
print(f"Total duration = {np.round((time.time() - time_start_logging)/60,1)} minutes")