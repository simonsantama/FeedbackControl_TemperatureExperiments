"""
This script plots the data while the main script is reading from the FPA data
loggers and the load cells. Not sure this is the best way to implement the
simultaneous plotting, but it does separate the two algorithms so that if there
is a problem with the plotting, the logging is not afected.

"""

# import libraries
import msvcrt
import matplotlib.pyplot as plt
import numpy as np
import pickle
import os
import time
import sys

#####
# DETERMINE WHERE THE DATA FOR THE MOST RECENT EXPERIMENT IS
#####

# find the most recently created folder
path = "C:\\Users\\Firelab\\Desktop\\Simon\\FeedbackControl_MassExperiments\\air_experiments"
all_folders = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]

folder_creation_time = 0
for folder in all_folders:
	ts = os.path.getmtime(os.path.join(path, folder))
	if ts > folder_creation_time:
		latest_folder = folder
		folder_creation_time = ts

#####
# CREATE AND FORMAT FIGURES
#####

# plotting parameters
fontsize_labels = 16
fontsize_legend = 14
linewidth_grid = 1
figure_size = (18,8)


# create figures 
plt.ion()
fig0, axes0 = plt.subplots(2,1, constrained_layout = True)
fig1, ax1 = plt.subplots(1,1, constrained_layout = True)


# format the plots
for a,ax in enumerate(axes0):
	ax.set_ylabel(["IHF [kW]", "MLR [g/m2s]"][a], fontsize = fontsize_labels)
	ax.set_xlabel("Time [s]", fontsize = fontsize_labels)
	ax.yaxis.grid(True, linewidth = linewidth_grid, linestyle = "--", color = "gainsboro")
	ax.set_ylim([[-5,70],[-0.5,12.5]][a])
	ax.set_yticks([np.linspace(0,70,8), np.linspace(0,12,13)][a])
	ax.set_xlim([0,1200])
	ax.set_xticks(np.linspace(0,1200,13))
ax1.set_ylabel("PID terms [-]", fontsize = fontsize_labels)
ax1.set_xlabel("Time [s]", fontsize = fontsize_labels)
ax1.yaxis.grid(True, linewidth = linewidth_grid, linestyle = "--", color = "gainsboro")
ax1.set_ylim([-0.5,5.5])
ax1.set_yticks(np.linspace(0,5,11))
ax1.set_xlim([0,1200])
ax1.set_xticks(np.linspace(0,1200,13))

# add lines and legend for plots in figure 0
ihf_line, = axes0[0].plot([],[], color = "maroon", alpha = 0.75, linewidth = 2)
mlr_line, = axes0[1].plot([],[], color = "gray", alpha = 0.75, marker = "o", 
	label = "mlr", linestyle = "")
mlr_movingaverage_line, = axes0[1].plot([],[], color = "maroon", alpha = 0.75, 
	linewidth = 2,
	label = "mlr_moving_average")
axes0[1].legend(fancybox = True, loc = "upper left", fontsize = fontsize_legend)

# add legend for PID coefficients plot in figure 1
list_PIDterms_plots = []
for i in range(3):
	l, = ax1.plot([],[], color = ["maroon", "dodgerblue", "black"][i], linewidth = 1,
		linestyle = ["-", "--", ":"][i], 
		label = ["Proportional", "Integral", "Derivative"][i])
	list_PIDterms_plots.append(l)
ax1.legend(fancybox = True, loc = "upper right", fontsize = fontsize_legend)


#####
# KEEP UPLOADING, READING AND PLOTTING THE DATA WHILE THE EXPERIMENT CONTINUES
#####

latest_folder_path = os.path.join(path, latest_folder)
bool_filecreation = False
# main file takes some time to create the pickle
while not bool_filecreation:
	try:
		for file in os.listdir(latest_folder_path):
			if ".pkl" in file:
				pickle_file = file

		pickle_file_path = os.path.join(latest_folder_path, pickle_file)
		print(f"Latest file is: {pickle_file.split('.')[0]}")
		bool_filecreation = True
	except:
		print("Pickle file not created yet")
		time.sleep(10)

# do an infinite loop where it reads the data and plots it to both figures
while True:

	try:
		with open(pickle_file_path, "rb") as handle:
			all_data = pickle.load(handle)
			
			# extract the data
			time_array = all_data["time"]
			ihf = all_data["IHF"]
			mlr = all_data["mlr"]
			mlr_moving_average = all_data["mlr_moving_average"]
			time_step = all_data["time_step"]
			PID_prop = all_data["PID_proportional"]
			PID_integral = all_data["PID_integral"]
			PID_dev = all_data["PID_derivative"]

			# modify plots in figure 0
			ihf_line.set_data([time_array[:time_step]],
				[ihf[:time_step]])
			mlr_line.set_data(time_array[:time_step],
				mlr[:time_step])
			mlr_movingaverage_line.set_data(time_array[:time_step],
				mlr_moving_average[:time_step])

			# modify plots in figure 1
			for l, line in enumerate(list_PIDterms_plots):
				line.set_data(time_array[:time_step],
					[PID_prop, PID_integral, PID_dev][l][:time_step])

			# pause the figure
			plt.pause(0.5)



	except Exception as e:
		# print(f"\nError when loading pickle or plotting data\n")
		# print(e)
		time.sleep(0.5)


	if msvcrt.kbhit():
	    if ord(msvcrt.getch()) == 27:
	    	# exit and save figures if ESC is pressed
	    	folder_path = os.path.join(path, latest_folder)
	    	for f, figure in enumerate([fig0, fig1]):
	    		figure.savefig(f'{folder_path}/{["IHF_MLR.pdf","PID_terms.pdf"][f]}')
	    	print("Exiting plotting script")
	    	sys.exit(0)
plt.show()