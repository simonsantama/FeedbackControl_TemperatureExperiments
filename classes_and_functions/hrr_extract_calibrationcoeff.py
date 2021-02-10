"""
Algorithm that extracts the calibration coefficinets for the lamps from the
latest calibration performed.

"""

import os
import pandas as pd

def hrr_extract_calibrationcoeff():
	"""
	Determines the latest polynomial fit coefficients to 
	relate heat flux in kW/m2 to the voltage to the lamps
	in VDC
	
	Parameters:
	----------
	None

	Returns:
	-------
	coefficients: list
		list of tupples that contains the coefficients for the linear fit on the
		different channels used for HRR calculations
		[oxygen, oxygen_inlet, CO, CO2]

	"""
	
	# determine the newest file in the calibration_data folder
	path = "C:\\Users\\FireLab\\Desktop\\Simon\\FeedbackControl_MassExperiments\\hrr_calibration_data"
	
	files = os.listdir(path)
	paths = [os.path.join(path, basename) for basename in files if ".xlsx" in basename]
	latest_file = max(paths, key=os.path.getctime)

	# read the coefficients from the latest file
	file_path = os.path.join(path, latest_file)
	fit_data = pd.read_excel(file_path, sheet_name = "polynomial_fit")
	a_coefficients = fit_data.loc[:, "coeff_a"].values
	b_coefficients = fit_data.loc[:, "coeff_b"].values
	coefficients = list(zip(a_coefficients, b_coefficients))

	return coefficients