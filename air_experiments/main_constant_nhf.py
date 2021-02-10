"""
FPA experiments
This algorithm uses a PID to control the IHF from the FPA's lamps so 
that the sample absorbs a constant rate of energy

Experimental procedure:
1. Lamps follow a linear heating ramp, with lambda 
(irradiation rate) = 0.25 kW/m^2 for at least 250 seconds and
 until the mlr is within 20% of the desired value.
2. Once the nhf is within the desired value, the control of the lamps is 
passed to the PID controller, until the test is ended.

This file can be greatly improved by re-factoring it and using an OOP approach.
Dirty implementation but it works and it is what was needed.

Use command: 'prompt $g' to shorten command prompt
"""

#####
# IMPORT LIBRARIES, CLASSES AND FUNCTIONS
#####

# libraries
import numpy as np
import sys
import time
import msvcrt
import csv
import os
import pickle

# add path to import functions and classes (absolute path on the FPA's computer)
sys.path.insert(1, r"C:\\Users\\FireLab\\Desktop\\Simon\\FeedbackControl_TemperatureExperiments\\classes_and_functions")
from loadcell import MettlerToledoDevice
from datalogger import DataLogger
from PID import PID_IHF as PID
from lamps_extract_calibrationcoeff import extract_calibrationcoeff
from hrr_extract_calibrationcoeff import hrr_extract_calibrationcoeff

#####
# CONNECT TO LOAD CELL AND DATA LOGGER AND INSTANTIATE CLASSES
#####

# create instance of the data logger and check connection
print("\nConnection to data logger")
rm, logger = DataLogger().new_instrument()


#####
# REQUEST FROM THE USER THE DESIRED NHF (CONSTANT) AND THE NAME OF THE EXPERIMENT
#####
while True:
	try:
		nhf_desired = float(input("\nInput nhf to be kept contant"
			" throughout the test (kW/m2):\n"))
		number_of_test = input("Input number of test in format XXX:\n" )
		material = input("Input material:\n").lower()

		name_of_file = f"air_{number_of_test}_{material}_{nhf_desired}kWm-2.csv"

		# confirm the values entered by user
		confirmation = input(f"\nDesired mlr = {nhf_desired} g/m2s. \nName of file: {name_of_file}.\nProceed?\n")
		if not confirmation.lower() in ["yes", "y"]:
			continue
		else:
			break

	except Exception as e:
		print("Invalid file name or nhf")
		print(e)

		# turn off the lamps and close the instrument
		logger.write(':SOURce:VOLTage %G,(%s)' % (0.0, '@304'))
		logger.close()
		rm.close()
		sys.exit()

name_of_folder = name_of_file.split(".csv")[0]
full_name_of_file = os.path.join(name_of_folder, name_of_file)
# create folder with the name of the file
if not os.path.exists(name_of_folder):
	os.mkdir(name_of_folder)
# do not overwrite the file
else:
	print("File already exists")
	sys.exit()



#####
# INITIALIZE USEFUL PARAMETERS AND START TEST
#####

print("Starting test")

# experiment parameters
time_pretesting_period = 5  # s
time_logging_period = 0.1    # s
surface_area = 0.09*0.09     # m2
irradiation_rate = 0.25      # kWm-2s-1
conductivity = 0.19          # W/mK

# epsilon is percentage of mlr_desired used to forcefully reduce oscillations
epsilon = 0.2   # %

# FPA lamps
max_lamp_voltage = 4.5
min_lamp_voltage = 0.25

# extract regression coefficients from the latest calibration file
coeff_hftovolts, coeff_voltstohf = extract_calibrationcoeff()
coeff_hrr = hrr_extract_calibrationcoeff()

# create arrays large enough to accomodate one hour of data at the 
# pre-set maximum logging frequency - ugly but it works
t_array = np.zeros(int(3600/time_logging_period))

IHF_volts = np.zeros_like(t_array)
o2_volts = np.zeros_like(t_array)
DPT_volts = np.zeros_like(t_array)
co_volts = np.zeros_like(t_array)
co2_volts = np.zeros_like(t_array)
APT_volts = np.zeros_like(t_array)
o2_inlet_volts = np.zeros_like(t_array)
rh_volts = np.zeros_like(t_array)

T4 = np.zeros_like(t_array)
T8 = np.zeros_like(t_array)
T12 = np.zeros_like(t_array)
T16 = np.zeros_like(t_array)
nhf = np.zeros_like(t_array)
IHF = np.zeros_like(t_array)

o2_percentage = np.zeros_like(t_array)
o2_inlet_percentage = np.zeros_like(t_array)
co_ppm = np.zeros_like(t_array)
co2_ppm = np.zeros_like(t_array)
Duct_TC_K = np.zeros_like(t_array)
Ambient_TC_K = np.zeros_like(t_array)


# PID
PID_state = "not_active"
PID_kp = 0.2
PID_ki = 0.04
PID_kd = 0.2
PID_integral_term_array = np.zeros_like(t_array)
PID_proportional_term_array = np.zeros_like(t_array)
PID_derivative_term_array = np.zeros_like(t_array)

# open csv file to write data
with open(full_name_of_file, "w", newline = "") as handle:
	writer = csv.writer(handle)
	writer.writerows([['time_seconds', 
		"T4_K",
		"T8_K",
		"T12_K",
		"T16_K",
		"NHF_kwm-2", 
		"IHF_volts", 
		"IHF_kwm-2", 
		"Observations", 
		"PID_state", 
		"O2_%", 
		"O2_inlet_%",
		"DPT_volts",
		"CO_ppm", 
		"CO2_ppm", 
		"APT_volts", 
		"Duct_TC_K",
		"Ambient_TC_K", 
		"RH_volts"]])

	# record the number of readings
	time_step = 0

	# ------
	# record temperatures for a period of 60 seconds before starting
	# ------
	print(f"\nGathering data for {time_pretesting_period} seconds before testing")
	time.sleep(2)

	time_start_logging = time.time()
	previous_log = time.time()
	while time.time() - time_start_logging < time_pretesting_period:

		# enforce a maximum logging frequency given by 1/time_logging_period
		if time.time() - previous_log < time_logging_period:
			continue
		else:

			t_array[time_step] = time.time() - time_start_logging			
			response_sample_temperatures = DataLogger.query_data_for_sampletemperatures(
				logger)		
			T4[time_step] = float(response_sample_temperatures.split(",")[0]) + 273
			T8[time_step] = float(response_sample_temperatures.split(",")[1]) + 273
			T12[time_step] = float(response_sample_temperatures.split(",")[2]) + 273
			T16[time_step] = float(response_sample_temperatures.split(",")[3]) + 273

			# calculate nhf using quadratic fit
			coefficients = np.polyfit([0.004, 0.008, 0.012, 0.016],
				[T4[time_step], T8[time_step], T12[time_step], T16[time_step]], 2)
			nhf[time_step] = 0
			# nhf[time_step] = - conductivity * coefficients[1]

			# read HRR associated data from the logger
			response_volts, response_temperatures = DataLogger.query_data_for_HRR(
				logger)
			o2_volts[time_step] = response_volts[0]
			DPT_volts[time_step] = response_volts[1]
			co_volts[time_step] = response_volts[2]
			co2_volts[time_step] = response_volts[3]
			APT_volts[time_step] = response_volts[4]
			o2_inlet_volts[time_step] = response_volts[5]
			rh_volts[time_step] = response_volts[6]

			Duct_TC_K[time_step] = float(response_temperatures.split(",")[0])
			Ambient_TC_K[time_step] = float(response_temperatures.split(",")[1])

			# convert to engineering units
			o2_percentage[time_step] = np.polyval(
				list(coeff_hrr[0]), o2_volts[time_step])
			o2_inlet_percentage[time_step] = np.polyval(
				list(coeff_hrr[1]), o2_inlet_volts[time_step])
			co_ppm[time_step] = np.polyval(
				list(coeff_hrr[2]), co_volts[time_step])
			co2_ppm[time_step] = np.polyval(
				list(coeff_hrr[3]), co2_volts[time_step])

			# write data to the csv file
			if time_step == 0:
				message = "start_logging"
			else:
				message = ""
			writer.writerows([[t_array[time_step],
				T4[time_step],
				T8[time_step],
				T12[time_step],
				T16[time_step],
				nhf[time_step]/1000,
				IHF_volts[time_step],
				IHF[time_step],
				message,
				PID_state,
				o2_percentage[time_step],
				o2_inlet_percentage[time_step],
				DPT_volts[time_step],
				co_ppm[time_step],
				co2_ppm[time_step],
				APT_volts[time_step],
				Duct_TC_K[time_step],
				Ambient_TC_K[time_step],
				rh_volts[time_step]]])

			previous_log = time.time()
			time_step_lastpretest = time_step
			time_step += 1

		# end if ESC is pressed
		if msvcrt.kbhit():
			if ord(msvcrt.getch()) == 27:
				break

	# ------
	# define additional parameters for start of test
	# ------

	bool_start_test = True
	bool_PID_active = False
	time_start_test = time.time()
	previous_log = time_start_test
	print("\nStarting lamps")

	while True:
		try:

			# enforce a maximum logging frequency given by 1/time_logging_period
			if time.time() - previous_log < time_logging_period:
				continue
			else:

				# record time for this reading
				t_array[time_step] = time.time() - time_start_logging

				# query temperatures and cal
				response_sample_temperatures = DataLogger.query_data_for_sampletemperatures(
					logger)		
				T4[time_step] = float(response_sample_temperatures.split(",")[0]) + 273
				T8[time_step] = float(response_sample_temperatures.split(",")[1]) + 273
				T12[time_step] = float(response_sample_temperatures.split(",")[2]) + 273
				T16[time_step] = float(response_sample_temperatures.split(",")[3]) + 273
				
				# calculate nhf using quadratic fit
				coefficients = np.polyfit([0.004, 0.008, 0.012, 0.016],
					[T4[time_step], T8[time_step], T12[time_step], T16[time_step]], 2)
				nhf[time_step] = - conductivity * coefficients[1]
				surface_temperature = coefficients[2]
				nhf_alt = IHF[time_step] - (28 * (surface_temperature - 288))/1000

				# read HRR associated data from the logger
				response_volts, response_temperatures = DataLogger.query_data_for_HRR(
					logger)
				o2_volts[time_step] = response_volts[0]
				DPT_volts[time_step] = response_volts[1]
				co_volts[time_step] = response_volts[2]
				co2_volts[time_step] = response_volts[3]
				APT_volts[time_step] = response_volts[4]
				o2_inlet_volts[time_step] = response_volts[5]
				rh_volts[time_step] = response_volts[6]

				Duct_TC_K[time_step] = float(response_temperatures.split(",")[0])
				Ambient_TC_K[time_step] = float(response_temperatures.split(",")[1])

				# convert to engineering units
				o2_percentage[time_step] = np.polyval(
					list(coeff_hrr[0]), o2_volts[time_step])
				o2_inlet_percentage[time_step] = np.polyval(
					list(coeff_hrr[1]), o2_inlet_volts[time_step])
				co_ppm[time_step] = np.polyval(
					list(coeff_hrr[2]), co_volts[time_step])
				co2_ppm[time_step] = np.polyval(
					list(coeff_hrr[3]), co2_volts[time_step])

				# start with a ramped IHF, and once mlr reaches 0.8*mlr_desired, activate PID
				if PID_state == "not_active":
					IHF[time_step+1] = (t_array[time_step] - 
						t_array[time_step_lastpretest]) * irradiation_rate
					# IHF[time_step+1] = 20
					IHF_volts[time_step+1] = np.polyval(
						coeff_hftovolts,IHF[time_step+1])
					voltage_output = IHF_volts[time_step+1]

					if voltage_output > max_lamp_voltage:
						voltage_output = max_lamp_voltage
						IHF_volts[time_step+1] = max_lamp_voltage
						IHF[time_step+1] = np.polyval(
							coeff_voltstohf, IHF_volts[time_step+1])

					if (nhf[time_step] > 0.95 * nhf_desired * 1000) and (
						time.time() - time_start_test > 100):
						PID_state = "active"
						print("\n-----")
						print("PID ACTIVE")
						print("-----\n")

						# set pid parameters
						previous_pid_time = time.time()
						last_error = nhf_desired - nhf[time_step]
						last_input = nhf[time_step]
						pid_integral_term = voltage_output
						pid_proportional_term = 0
						pid_derivative_term = 0


				# call PID
				elif PID_state == "active":
					pass
					voltage_output, previous_pid_time, last_error, pid_proportional_term, \
					pid_integral_term, pid_derivative_term = \
											PID(
											input_nhf, nhf_desired, previous_pid_time, 
											last_error, last_input, pid_integral_term,
											PID_kp, PID_ki, PID_kd,
											max_lamp_voltage, min_lamp_voltage)
					IHF_volts[time_step+1] = voltage_output
					IHF[time_step+1] = np.polyval(
						coeff_voltstohf, IHF_volts[time_step+1])
					last_input = nhf[time_step]

					PID_proportional_term_array[time_step] = pid_proportional_term
					PID_integral_term_array[time_step] = pid_integral_term
					PID_derivative_term_array[time_step] = pid_derivative_term

				# write IHF to the lamps
				logger.write(':SOURce:VOLTage %G,(%s)' % (voltage_output, '@304'))

				# write data to the csv file
				if bool_start_test:
					message = "start_test"
					bool_start_test = False
				else:
					message = ""
				writer.writerows([[t_array[time_step],
					T4[time_step],
					T8[time_step],
					T12[time_step],
					T16[time_step],
					nhf[time_step]/1000,
					IHF_volts[time_step],
					IHF[time_step],
					message,
					PID_state,
					o2_percentage[time_step],
					o2_inlet_percentage[time_step],
					DPT_volts[time_step],
					co_ppm[time_step],
					co2_ppm[time_step],
					APT_volts[time_step],
					Duct_TC_K[time_step],
					Ambient_TC_K[time_step],
					rh_volts[time_step]]])

				# save data as a a dict in a pickle to be read and plotted by another algorithm
				data_for_pickle = {"time":t_array,
									"IHF": IHF,
									"IHF_volts": IHF,
									"T4": T4,
									"T8": T8,
									"T12": T12,
									"T16": T16,
									"nhf": nhf,
									"time_step": time_step,
									"PID_proportional":PID_proportional_term_array,
									"PID_integral": PID_integral_term_array,
									"PID_derivative": PID_derivative_term_array,
									"O2_volts": o2_volts,
									"O2_percentage": o2_percentage, 
									"O2_inlet_volts": o2_inlet_volts,
									"o2_inlet_percentage": o2_inlet_percentage,
									"DPT_volts": DPT_volts,
									"CO_volts": co_volts,
									"CO_ppm": co_ppm,
									"CO2_volts": co2_volts, 
									"CO2_ppm": co2_ppm, 
									"APT_volts": APT_volts, 
									"Duct_TC_K": Duct_TC_K,
									"Ambient_TC_K": Ambient_TC_K, 
									"RH_volts": rh_volts,
									}
				with open(f"{full_name_of_file.split('.csv')[0]}.pkl", "wb") as handle:
					pickle.dump(data_for_pickle, handle)

				# print the result of this iteration to the terminal window
				print(f"\nPID state: {PID_state}")
				print(f"time:{np.round(time.time() - time_start_test,4)}")
				print(f"IHF:{np.round(IHF[time_step+1],4)}")
				print(f"nhf: {np.round(nhf[time_step]/1000, 4)}", nhf_alt/1000)
				print(f"T4:{T4[time_step]}")
				print(f"T8:{T8[time_step]}")
				print(f"T12:{T12[time_step]}")
				print(f"T16:{T16[time_step]}")

				previous_log = time.time()
				time_step += 1
 
			# end if ESC is pressed
			if msvcrt.kbhit():
				if ord(msvcrt.getch()) == 27:
					writer.writerows([["", "", "", "", "", "", "end_test"]])
					break

		## ---- handle an exception during testing and continue logging the data
		except Exception as e:
			print(f"\nInstantaneous error at {np.round(time.time() - time_start_logging, 2)} seconds")
			exc_type, exc_obj, exc_tb = sys.exc_info()
			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			print(exc_type, fname, exc_tb.tb_lineno)
			print(e)
			print("- Logging continues -")

			# end if ESC is pressed
			if msvcrt.kbhit():
				if ord(msvcrt.getch()) == 27:
					writer.writerows([["", "", "", "", "","", "end_test"]])
					break


#####
# CLOSE CONNECTION TO THE LOGGER, TURN OFF LAMPS AND FINISH THE EXPERIMENT
#####

# turn off the lamps and close the instrument
logger.write(':SOURce:VOLTage %G,(%s)' % (0.0, '@304'))
logger.close()
rm.close()

# finish the experiment
print("\n\nExperiment finished")
print(f"Total duration = {np.round((time.time() - time_start_logging)/60,1)} minutes")

